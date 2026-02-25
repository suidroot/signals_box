# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Flask web application that runs on a Linux SDR (Software Defined Radio) host to manage SDR-related services — systemd units, Docker containers, and CLI processes — through a single web UI. It also enumerates attached RTL-SDR USB dongles and queries GPS/Kismet status.

**Requires Linux** (systemd D-Bus, USB access). Must be run as root or with elevated privileges.

## Running

**Debug mode:**
```bash
sudo python3 app.py
# Listens on 0.0.0.0:8081
```

**Production (gunicorn via wsgi.py):**
```bash
sudo gunicorn --bind 0.0.0.0:8081 wsgi:app
```

**Install dependencies:**
```bash
pip install -r requirements.txt
# System packages also needed: dbus-python requires libdbus-dev, pyrtlsdr requires rtl-sdr
```

## Configuration

Two required YAML files (loaded from the working directory at startup):

- **`config.yml`** — defines services, buttons, and links. Each service entry has a `type` (`systemd`, `docker`, or `cli`) plus type-specific fields. Services are keyed by `service_id` (e.g. `kismet`, `openwebex`).
- **`creds.yml`** — Kismet credentials. Copy from `creds.yml.sample` to create. Not committed to the repo.

Logging is configured by **`logging.yml`** (rotating file at `logs/app.log` + console, both at INFO).

Config is reloaded at runtime via the "Reload Config" button (POST `reload_config`), which calls `manager.load_config()`.

## Architecture

```
app.py               Flask routes + HTML-building render_* functions
signalsmanager.py    SignalsManager — central orchestrator, owns caching
services.py          SystemdServiceManager, DockerService, CliService, KismetStatus
usbs.py              UsbDevices — enumerates RTL-SDR USB dongles
templates/index.html Single Jinja2 template (injects pre-built HTML strings via | safe)
```

### Key design decisions

**HTML is built in Python, not Jinja2.** `render_service_toggles()`, `render_sdr_list()`, `render_sdr_drop_list()`, `render_buttons()`, and `render_gps_status()` in `app.py` return raw HTML strings. The template injects them with `| safe`. This means there is **no auto-escaping** on those sections.

**`SignalsManager` is a module-level singleton** instantiated at import time (`manager = SignalsManager()` in `app.py`). It holds live references to `SystemdServiceManager` and `DockerService`.

**TTL caching** (`_CACHE_TTL = 10s`) is used for SDR enumeration (`get_all_sdrs`) and GPS queries (`get_gps_status`) to avoid hitting USB/gpsd on every page load.

**Service `current_status`** in `config.yml` starts as `null` and is updated in memory at runtime. It is **not persisted** back to disk; a restart resets it to `null`.

### Service types

| Type | Backend | Key config fields |
|------|---------|-------------------|
| `systemd` | D-Bus via `dbus-python` | `system_ctl_name` |
| `docker` | Docker socket via `docker` SDK | `container_name` |
| `cli` | `subprocess.Popen` | `cmd_line`, `working_dir` |

`cli` services support `<placeholder>` substitution in `cmd_line` using other keys from the service config dict.

### Hard import failures

`services.py` raises `Exception` (not `ImportError`) at module load if `dbus`, `docker`, or `kismet_rest` are missing. The app will not start without all three libraries installed.

### SDR status flow

On each page load: `get_all_sdrs()` → `UsbDevices.list_rtlsdr_devices()` (USB enumeration) → `update_sdr_status()` (cross-references running services and Kismet datasources to annotate which dongle is in use). The result is cached for 10s.

`KismetStatus` is instantiated fresh on each SDR cache miss (inside `update_sdr_status`) only when the `kismet` service shows `current_status == "running"`.
