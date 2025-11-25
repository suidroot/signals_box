#!/usr/bin/env python3
"""
This module contains the main class for managing services.
"""

from typing import Dict, List, Optional, Any
import logging
import subprocess
import shlex
import threading
import atexit
import dbus
from dbus.exceptions import DBusException


try:
    import docker
    import docker.errors
except ImportError as e:
    raise Exception ("Docker not installed on system")

logger = logging.getLogger(__name__)


class SystemdServiceManager:
    """
    Manages services using systemd. 
    """

    def __init__(self):
        self.bus = self.get_bus(False)

    # --------------------------------------------------------------------------- #
    # D‑Bus helpers
    # --------------------------------------------------------------------------- #
    @staticmethod
    def get_bus(is_user: bool) -> dbus.Bus:
        """Return the correct D‑Bus connection (system or session)."""
        return dbus.SessionBus() if is_user else dbus.SystemBus()


    def get_manager(self) -> dbus.Interface:
        """
        Get the `org.freedesktop.systemd1.Manager` interface.
        Raises RuntimeError if the interface cannot be reached.
        """
        try:
            obj = self.bus.get_object("org.freedesktop.systemd1",
                                "/org/freedesktop/systemd1")
            return dbus.Interface(obj, "org.freedesktop.systemd1.Manager")
        except DBusException as exc:
            raise RuntimeError(
                f"Unable to connect to systemd over D‑Bus: {exc}"
            ) from exc


    def get_unit_properties(self, unit_name: str) -> dict:
        """
        Fetch all properties of a unit via the `org.freedesktop.DBus.Properties`
        interface. Returns a plain dict with string keys and Python‑friendly
        values (bytes → str, etc.).
        """
        try:
            unit_obj_path = self.get_manager().GetUnit(unit_name)
            props_obj = self.bus.get_object("org.freedesktop.systemd1",
                                    str(unit_obj_path))
            props_iface = dbus.Interface(props_obj, "org.freedesktop.DBus.Properties")
            raw_props = props_iface.GetAll("org.freedesktop.systemd1.Unit")

            # Convert D‑Bus types to normal Python types for printing
            def _convert(value):
                if isinstance(value, dbus.ByteArray):
                    return bytes(value).decode()
                if isinstance(value, dbus.Byte):
                    return int(value)
                return value

            return {k: _convert(v) for k, v in raw_props.items()}
        except DBusException as exc:
            raise RuntimeError(
                f"Failed to read properties of unit '{unit_name}': {exc}"
            ) from exc

    # --------------------------------------------------------------------------- #
    # Service actions
    # --------------------------------------------------------------------------- #
    def start_service(self, name: str) -> None:
        """Start the unit with the given name."""
        manager = self.get_manager()
        try:
            manager.StartUnit(name, "replace")  # 'replace' mode starts it immediately
            print(f"✅  Started {name}")
        except DBusException as exc:
            raise RuntimeError(f"Failed to start {name}: {exc}") from exc


    def stop_service(self, name: str) -> None:
        """Stop the unit."""
        manager = self.get_manager()
        try:
            manager.StopUnit(name, "replace")
            print(f"🛑  Stopped {name}")
        except DBusException as exc:
            raise RuntimeError(f"Failed to stop {name}: {exc}") from exc


    def restart_service(self, name: str) -> None:
        """Restart the unit."""
        manager = self.get_manager()
        try:
            manager.RestartUnit(name, "replace")
            print(f"🔄  Restarted {name}")
        except DBusException as exc:
            raise RuntimeError(f"Failed to restart {name}: {exc}") from exc


    def status_service(self, name: str) -> None:
        """Print a concise status summary of the unit."""
        try:
            props = self.get_unit_properties(name)
            # print(f"Service: {props.get('Id')}")
            # print(f"  Description : {props.get('Description')}")
            # print(f"  Load state   : {props.get('LoadState')}")
            # print(f"  Active state : {props.get('ActiveState')}")
            # print(f"  Sub state    : {props.get('SubState')}")
        except RuntimeError as exc:
            print(f"Failed to status {name}: {exc}")
            props = None

        return props


    def list_services(self) -> None:
        """List all services, optionally filtering by a glob pattern."""
        manager = self.get_manager()
        try:
            units = manager.ListUnits()  # returns list of tuples
        except DBusException as exc:
            raise RuntimeError(f"Failed to list units: {exc}") from exc

        # Each unit tuple: (Id, Description, LoadState, ActiveState,
        # SubState, FollowedBy)
        # def matches(u: Tuple) -> bool:
        #     if not pattern:
        #         return True
        #     return fnmatch.fnmatch(u[0], pattern)

        print(f"{'ID':<50} {'Active':<10} {'Sub':<10} {'Description'}")
        print("-" * 90)
        for unit in units:
            # if matches(unit):
            print(f"{unit[0]:<50} {unit[3]:<10} {unit[4]:<10} {unit[1]}")


# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #
def _substitute_placeholders(cmd_line: str, params: Dict[str, Any]) -> str:
    """
    Replace placeholders of the form <1>, <2>, ... in *cmd_line*
    with the values from *params* (which may contain int, str, ...).
    If a placeholder is missing in *params*, it is left unchanged.
    """
    logger.debug("Substiute PlaceHolders: %s", cmd_line)
    result = cmd_line
    for key, val in params.items():
        placeholder = f"<{key}>"
        result = result.replace(placeholder, str(val))
    return result


def _parse_command(cmd_line: str) -> List[str]:
    """
    Convert a command string into a list suitable for subprocess.Popen.
    ``shlex.split`` handles quoting, escape sequences, etc.
    """
    logger.debug("Parse Command: %s", cmd_line)

    return shlex.split(cmd_line)


# --------------------------------------------------------------------------- #
# The core class
# --------------------------------------------------------------------------- #
class CliService:
    """
    Wraps a command‑line program so you can start/stop it from Python.

    Parameters
    ----------
    config : dict
        A dictionary containing at least the keys listed in the example
        below.  Unknown keys are ignored – they simply become part of
        the *params* namespace for placeholder replacement.
    """

    def __init__(self, svc_id, config: Dict[str, Any]) -> None:
        if not isinstance(config, dict):
            raise TypeError("config must be a dict")

        # Mandatory fields – raise if missing
        for key in ("type", "description", "cmd_line"):
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")

        # Basic attributes
        self.svc_id: str = svc_id
        self.type: str = config["type"]
        self.description: str = config["description"]
        self.cmd_line: str = config["cmd_line"]
        self.autostart: bool = config.get("autostart", False)
        self.require_sdr: bool = config.get("require_sdr", False)
        self.cwd: bool = config.get("working_dir", None)

        # All remaining keys are treated as optional params for placeholder replacement
        self.params: Dict[str, Any] = {k: v for k, v in config.items()
                                      if k not in {"svc_id", "type", \
                                                   "description", "cmd_line", \
                                                    "autostart", "require_sdr"}}

        # Internal state
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()  # guard access to _proc

        # Register cleanup on interpreter exit
        atexit.register(self._cleanup_on_exit)

        # Auto‑start if requested
        if self.autostart:
            logger.info("Autostart enabled – launching service '%s'", self.svc_id)
            self.start()

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #
    def _cleanup_on_exit(self) -> None:
        """
        Called automatically on program exit to ensure we don't leave
        orphaned processes around.
        """
        if self.is_running():
            logger.debug("Cleaning up service '%s' on exit", self.svc_id)
            self.stop()

    def _ensure_not_running(self) -> None:
        logger.debug("Checking Process Lock")
        if self.is_running():
            raise RuntimeError(f"Service '{self.svc_id}' is already running")

    def _ensure_running(self) -> None:
        logger.debug("Checking Process Lock")

        if not self.is_running():
            raise RuntimeError(f"Service '{self.svc_id}' is not running")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        """
        Launch the command as a background process.

        Raises
        ------
        RuntimeError
            If the service is already running or if the process cannot be started.
        """
        with self._lock:
            # self._ensure_not_running()

            # Perform placeholder substitution
            full_cmd = _substitute_placeholders(self.cmd_line, self.params)
            cmd_parts = _parse_command(full_cmd)

            logger.info("Starting service '%s': %s", self.svc_id, cmd_parts)

            try:
                # Use stdout/stderr = subprocess.PIPE so that the
                # child does not inherit our terminal (unless you want that)
                self._proc = subprocess.Popen(
                    cmd_parts,
                    cwd=self.cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,   # line buffered
                )
            except Exception as exc:
                self._proc = None
                logger.exception("Failed to start service '%s'", self.svc_id)
                raise RuntimeError(f"Could not start service '{self.svc_id}': {exc}") from exc

            # Optionally: spawn a thread that logs the output.
            threading.Thread(
                target=self._log_process_output,
                name=f"{self.svc_id}-stdout-logger",
                daemon=True,
            ).start()

    def _log_process_output(self) -> None:
        """
        Read from the process' stdout and stderr and log them.
        Runs in a daemon thread so it doesn't block program exit.
        """
        if not self._proc:
            return

        def _log_pipe(pipe, level):
            for line in iter(pipe.readline, ""):
                logger.log(level, "[%s] %s", self.svc_id, line.rstrip())

        if self._proc.stdout:
            threading.Thread(target=_log_pipe,
                             args=(self._proc.stdout, logging.INFO),
                             daemon=True).start()
        if self._proc.stderr:
            threading.Thread(target=_log_pipe,
                             args=(self._proc.stderr, logging.ERROR),
                             daemon=True).start()

    def stop(self, timeout: Optional[float] = 5.0) -> None:
        """
        Terminate the process gracefully.  If it does not exit within *timeout*
        seconds, it is killed.

        Parameters
        ----------
        timeout : float or None
            Number of seconds to wait after sending SIGTERM before calling SIGKILL.
            If None, the call blocks indefinitely until the process exits.
        """
        with self._lock:
            # self._ensure_running()
            assert self._proc is not None

            logger.info("Stopping service '%s'", self.svc_id)
            try:
                self._proc.terminate()   # sends SIGTERM
                try:
                    self._proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    logger.warning("Service '%s' did not terminate in %s sec – killing", self.svc_id, timeout)
                    self._proc.kill()
                    self._proc.wait()
            finally:
                self._proc = None
                logger.info("Service '%s' stopped", self.svc_id)

    def is_running(self) -> bool:
        """
        Return ``True`` if the service is currently running.
        """
        with self._lock:
            if self._proc is None:
                return False
            return self._proc.poll() is None

    # ------------------------------------------------------------------ #
    # Representation helpers
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        status = "RUNNING" if self.is_running() else "STOPPED"
        return f"<CliService id={self.svc_id!r} status={status}>"

    def __str__(self) -> str:
        return f"{self.svc_id} ({self.description}) - {self.type} - {self.cmd_line}"

class DockerService:
    """
    Manage Services that are hosted in Docker
    """

    def __init__(self):
        self.docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')

    def start_service(self, container_name: str) -> None:
        """Start the container with the given name."""
        status = None

        try:
            container = self.docker_client.containers.get(container_name)

            status = container.start()
        except docker.errors.NotFound:
            print(f"🛑  {container_name} not found")
            status = False

        return status


    def stop_service(self, container_name: str) -> None:
        """Stop the container."""
        status = None

        try:
            container = self.docker_client.containers.get(container_name)
            status = container.stop()
        except docker.errors.NotFound:
            print(f"🛑  {container_name} not found")
            status = False

        return status


    def restart_service(self, container_name: str) -> None:
        """Restart the container."""

        status = None

        try:
            container = self.docker_client.containers.get(container_name)
            status = container.restart()
        except docker.errors.NotFound:
            print(f"🛑  {container_name} not found")
            status = False

        return status


    def status_service(self, container_name: str) -> None:
        """Print a concise status summary of the container."""
        status = None

        try:
            container = self.docker_client.containers.get(container_name)

            container_state = container.attrs['State']

            status = container_state['Status']
        except docker.errors.NotFound:
            print(f"🛑  {container_name} not found")
            status = False

        return status


if __name__ == "__main__":
    pass
