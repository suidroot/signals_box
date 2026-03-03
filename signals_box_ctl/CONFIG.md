# Configuration Reference

Signals Box requires two YAML files in the working directory at startup: `config.yml` and `creds.yml`.

---

## config.yml

### Top-level keys

| Key | Required | Description |
|-----|----------|-------------|
| `http_base_url` | Yes | Base URL of the host (e.g. `http://hostname.local`). Used as a reference value; not currently interpolated automatically. |
| `services` | Yes | Map of service entries keyed by `service_id`. |
| `buttons` | Yes | Map of button entries keyed by button name. |
| `links` | Yes | List of link entries shown in the links panel. |
| `pid_file_location` | No | Path for a PID file. Not currently used by the application. |

---

### `services`

Each key under `services` is a **service ID** (e.g. `kismet`, `openwebex`). The value is a dict with the fields below.

#### Fields common to all service types

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `type` | Yes | — | Service backend: `systemd`, `docker`, or `cli`. |
| `description` | Yes | — | Human-readable name shown in the UI. |
| `require_sdr` | No | `false` | When `true`, shows an SDR selector for this service and annotates the SDR status table when the service is running. |
| `multi_sdr` | No | `false` | When `true` (and `require_sdr` is `true`), renders a multi-select listbox instead of a single dropdown, allowing multiple SDRs to be assigned. |
| `default_sdr` | No | `null` | Serial number string of the SDR pre-selected on first load. Use `null` for no default. Only used when `require_sdr` is `true`. |
| `link` | No | `null` | URL rendered as a clickable link in the service row. Set to `null` or omit to show no link. |
| `freq_input` | No | — | Initial value for a frequency text input shown alongside the SDR selector. Only relevant when `require_sdr` is `true`. |

> **Runtime fields** — These are set automatically at startup and should not be set in the config file:
> - `current_status`: initialized to `null`; updated in memory as services are started/stopped.
> - `selected_sdr`: initialized from `default_sdr` if present.

#### `type: systemd`

Manages a systemd unit via D-Bus.

| Field | Required | Description |
|-------|----------|-------------|
| `system_ctl_name` | Yes | Full systemd unit name, e.g. `kismet.service`. |

```yaml
kismet:
    type: systemd
    system_ctl_name: kismet.service
    description: Kismet
    link: http://hostname.local:2501
```

#### `type: docker`

Manages a Docker container via the Docker socket.

| Field | Required | Description |
|-------|----------|-------------|
| `container_name` | Yes | Name of the Docker container as shown in `docker ps`. |

```yaml
openwebex:
    type: docker
    container_name: owrx-mbe
    description: "OpenWebRX+"
    link: "http://hostname.local:8073"
    require_sdr: true
    default_sdr: '1234567890'
```

#### `type: cli`

Manages a subprocess launched directly by the app.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `cmd_line` | Yes | — | Command string to execute. Supports `<key>` placeholder substitution using other fields in the same service entry (e.g. `<freq_input>` is replaced with the current value of `freq_input`). Parsed with shell-like quoting rules. |
| `working_dir` | No | `null` | Working directory for the process. |
| `autostart` | No | `false` | Start the process automatically when the app starts. |

Any extra fields in a `cli` service entry are available as placeholder values in `cmd_line`.

```yaml
pagermon_client1:
    type: cli
    description: Pagermon Client
    cmd_line: "/opt/pagermon/client/reader.sh 1 <freq_input>"
    working_dir: /opt/pagermon/client
    require_sdr: true
    freq_input: "152.592M"
    default_sdr: null
```

---

### `buttons`

Each key is a button name. Buttons are rendered as a row of controls at the top of the page.

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | HTML form field name submitted when the button is clicked. Must match the key. |
| `text` | Yes | Label displayed on the button. |
| `html_command` | Yes | Raw HTML attributes injected into the `<button>` element. Use `type="submit"` for server-side actions or `onClick="..."` for client-side actions. |
| `cli_command` | No | List of command arguments run server-side when this button is clicked. Currently used by `shutdown` and `reboot`. |

```yaml
buttons:
  refresh_page:
    name: "refresh_page"
    text: "Refresh Page"
    html_command: 'onClick="window.location.reload();"'
  shutdown:
    name: "shutdown"
    text: "Shutdown"
    html_command: 'type="submit"'
    cli_command: ["/usr/sbin/shutdown", "now"]
```

---

### `links`

A list of URLs shown in the links panel. Order is preserved.

| Field | Required | Description |
|-------|----------|-------------|
| `id` | No | Identifier for the entry (for human reference only; not used by the app). |
| `url` | Yes | The href value for the link. |
| `name` | Yes | Display text for the link. |

```yaml
links:
  - id: vnc
    url: "vnc://hostname.local:5901"
    name: VNC Access
```

---

## creds.yml

Stores credentials for external services. Not committed to the repository — copy from `creds.yml.sample` to create.

```yaml
kismet:
  username: admin
  password: yourpassword
```

| Field | Description |
|-------|-------------|
| `kismet.username` | Username for the Kismet REST API. |
| `kismet.password` | Password for the Kismet REST API. |

Kismet credentials are only used when the `kismet` service entry exists in `config.yml` and its status is `running`.
