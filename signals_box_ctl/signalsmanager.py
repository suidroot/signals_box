# pylint: disable=line-too-long
#!/usr/bin/env python3
"""
This module contains the main class for managing services.
"""

import logging
import threading
import time
import yaml

_gpsd_available = False
try:
    import gpsd
    _gpsd_available = True
except ImportError:
    pass  # GPS integration disabled; get_gps_status() will return 'unavailable'

from services import (
    SystemdServiceManager,
    CliService,
    DockerService,
    KismetStatus,
    supported_services,
    _kismet_rest_available,
)
from usbs import UsbDevices

logger = logging.getLogger(__name__)

class SignalsManager:
    """
    Class containing all of the functionality for service management and USB management

    :var value: Description
    :vartype value: Any
    """

    _CACHE_TTL = 10  # seconds

    def __init__(self, config_file="config.yml", creds_file="creds.yml"):
        if not _gpsd_available:
            logger.warning("gpsd not installed – GPS integration disabled")
        self.config_file = config_file
        self.creds_file = creds_file
        self.sdr_data = None
        self._sdr_cache = None
        self._sdr_cache_ts = 0.0
        self._sdr_lock = threading.Lock()
        self._gps_cache = None
        self._gps_cache_ts = 0.0
        self._kismet_mgr = None
        self.load_config()

    def load_config(self):
        """
        Load configuration from file and store in class variables

        :param self: Description
        """

        logger.debug("Loading Config file: %s", self.config_file)
        self._kismet_mgr = None

        # Stop any running CLI services before replacing the config dict so
        # their processes are not orphaned when self.services is reassigned.
        if hasattr(self, 'services'):
            for svc_id, svc in self.services.items():

                if svc.get('type') == 'cli' and 'cli_status_obj' in svc:
                    try:
                        if svc['cli_status_obj'].is_running():
                            logger.info("Stopping CLI service '%s' before config reload", svc_id)
                            svc['cli_status_obj'].stop()
                    except Exception:
                        logger.warning("Failed to stop CLI service '%s' during config reload", svc_id)

        logger.debug("Loading config file: %s", self.config_file)

        try:
            with open(self.config_file, "r", encoding="utf-8") as file_handle:
                cfg = yaml.safe_load(file_handle)
                self.services = cfg['services']
                self.http_base_url = cfg['http_base_url']
                self.links = cfg['links']
                self.buttons = cfg['buttons']

                self.systemd_svc_mgr = SystemdServiceManager()
                self.docker_svc_mgr = DockerService()
        except FileNotFoundError:
            logger.critical("Config file not found: %s", self.config_file)
            raise
        except (KeyError, TypeError) as e:
            logger.critical("Invalid config file %s: missing key %s", self.config_file, e)
            raise

        # init Service values
        for svc in self.services:
            if not 'current_status' in self.services[svc]:
                self.services[svc]['current_status'] = None
            
            if not 'selected_sdr' in self.services[svc]:
                self.services[svc]['selected_sdr'] = self.services[svc].get('default_sdr', None)

        logger.debug("Loading Credentials file: %s", self.creds_file)
        try:
            with open(self.creds_file, "r", encoding="utf-8") as credfile_handle:
                self.creds = yaml.safe_load(credfile_handle)
        except FileNotFoundError:
            logger.critical("Credentials file not found: %s", self.creds_file)
            raise

        return True

    def get_single_service_status(self, service_id):
        """
        Get the status of a single service

        statues
        - running
        - stopped
        - stopping
        - unknown

        :param self: Description
        :param service_id: Description
        """

        status = "unknown"
        status_data = None
        logger.debug("Refreshing Service Status for service: %s using type %s", service_id, self.services[service_id]['type'])

        if self.services[service_id]['type'] == "systemd":

            status_data = self.systemd_svc_mgr.status_service(self.services[service_id]['system_ctl_name'])

            if status_data:
                active_state = status_data.get('ActiveState')
                if active_state == 'active':
                    status = 'running'
                elif active_state == 'deactivating':
                    status = "stopping"
                elif active_state == 'inactive':
                    status = "stopped"
                else:
                    status = "unknown"
            else:
                status = "unknown"

        elif self.services[service_id]['type'] == "docker":
            status_data = self.docker_svc_mgr.status_service(self.services[service_id]['container_name'])

            if status_data:
                if status_data == 'running':
                    status = 'running'
                else:
                    status = 'stopped'
            else:
                status = 'unknown'

        elif self.services[service_id]['type'] == "cli":

            if not 'cli_status_obj' in self.services[service_id]:
                self.services[service_id]['cli_status_obj'] = CliService(service_id, self.services[service_id])

            if self.services[service_id]['cli_status_obj'].is_running():
                status = 'running'
            else:
                status = "stopped"

        return status, status_data

    def start_service(self, service_id):
        """
        Start a service and return its status.
        This is a wrapper for the various managers that are responsible for starting and stopping services.

        :param self: Description
        :param service_id: Description
        """

        self._sdr_cache = None  # force fresh SDR status on next page render
        logger.debug("Calling Start for service: %s using type %s", service_id, self.services[service_id]['type'])

        if self.services[service_id]['type'] == "systemd":
            self.systemd_svc_mgr.start_service(self.services[service_id]['system_ctl_name'])
        elif self.services[service_id]['type'] == "docker":
            self.docker_svc_mgr.start_service(self.services[service_id]['container_name'])
        elif self.services[service_id]['type'] == 'cli':
            if not 'cli_status_obj' in self.services[service_id]:
                self.services[service_id]['cli_status_obj'] = CliService(service_id, self.services[service_id])

            self.services[service_id]['cli_status_obj'].start()

        return self.get_single_service_status(service_id)


    def stop_service(self, service_id):
        """
        Stop a service and return its status.
        This is a wrapper for the various managers that are responsible for starting and stopping services.

        :param self: Description
        :param service_id: Description
        """
        
        self._sdr_cache = None  # force fresh SDR status on next page render
        if service_id == 'kismet':
            self._kismet_mgr = None
        logger.debug("Calling Stop for service: %s using type %s", service_id, self.services[service_id]['type'])


        if self.services[service_id]['type'] == "systemd":
            self.systemd_svc_mgr.stop_service(self.services[service_id]['system_ctl_name'])
        elif self.services[service_id]['type'] == "docker":
            self.docker_svc_mgr.stop_service(self.services[service_id]['container_name'])
        elif self.services[service_id]['type'] == 'cli':
            if not 'cli_status_obj' in self.services[service_id]:
                logger.error("No cli service object found for %s", service_id)
            else:
                self.services[service_id]['cli_status_obj'].stop()

        return self.get_single_service_status(service_id)

    ### SDR
    def get_all_sdrs(self):
        """
        Gather list of all SDRs, using a short-lived cache to avoid
        repeated USB enumeration and Kismet API calls on every page load.
        """

        now = time.time()
        if self._sdr_cache is not None and (now - self._sdr_cache_ts) < self._CACHE_TTL:
            logger.debug("Returning cached SDR list")
            return self._sdr_cache

        with self._sdr_lock:
            # Re-check under lock so concurrent requests don't both enumerate USB
            now = time.time()
            if self._sdr_cache is not None and (now - self._sdr_cache_ts) < self._CACHE_TTL:
                logger.debug("Returning cached SDR list")
                return self._sdr_cache

            logger.debug("Getting all SDRs")
            usb_dev = UsbDevices()
            self.sdr_data = usb_dev.list_rtlsdr_devices()
            self.update_sdr_status()
            self._sdr_cache = self.sdr_data
            self._sdr_cache_ts = now

        return self.sdr_data

    def update_sdr_status(self):
        """
            Update SDR usage status
        """

        logger.debug("Updating SDR status")

        # Get Status from Kismet
        if _kismet_rest_available and 'kismet' in self.services and self.services['kismet']['current_status'] == "running":
            logger.debug("Getting Kismet SDR usage status")
            if self._kismet_mgr is None:
                self._kismet_mgr = KismetStatus(self.creds['kismet']['username'], self.creds['kismet']['password'])
            else:
                try:
                    self._kismet_mgr.get_active_datasources()
                except Exception:
                    logger.warning("KismetStatus refresh failed, reconnecting")
                    self._kismet_mgr = KismetStatus(self.creds['kismet']['username'], self.creds['kismet']['password'])

            for index, sdr_entry in enumerate(self.sdr_data):
                kismet_result = self._kismet_mgr.lookup_by_sdr_id(sdr_entry['Rtl Id'])

                if kismet_result:
                    self.sdr_data[index]['status'] = f"Kismet: {kismet_result}"

        # Get Status from other Services

        logger.debug("Updating %s SDR status" % len(self.services))
        for service_entry in self.services:
            if self.services[service_entry]['require_sdr'] and \
                self.services[service_entry]['current_status'] == 'running' and \
                self.services[service_entry]['selected_sdr']:
                    selected = self.services[service_entry]['selected_sdr']
                    if isinstance(selected, str):
                        selected = [selected]
                    for serial in selected:
                        index = next((i for i, d in enumerate(self.sdr_data)
                                      if d.get('Serial') == str(serial)), -1)
                        if index != -1:
                            self.sdr_data[index]['status'] = f"{self.services[service_entry]['description']}"
                        else:
                            logger.error("Could not find SDR with serial %s for service %s",
                                         serial, service_entry)

    def set_service_radio(self, name, sdr_serials):
        """
        Set the radio(s) to be used by a given service.
        sdr_serials: list of serial number strings (empty list to clear).
        """
        logger.debug("Setting SDRs %s for service %s", sdr_serials, name)

        # Clear previous status annotations
        if self.sdr_data is not None:
            old = self.services[name].get('selected_sdr') or []
            if isinstance(old, str):
                old = [old]
            for serial in old:
                idx = next((i for i, d in enumerate(self.sdr_data) if d.get('Serial') == str(serial)), -1)
                if idx != -1:
                    self.sdr_data[idx]['status'] = ""

        if sdr_serials:
            self.services[name]['selected_sdr'] = [str(s) for s in sdr_serials]
            if self.sdr_data is not None:
                for serial in sdr_serials:
                    idx = next((i for i, d in enumerate(self.sdr_data) if d.get('Serial') == str(serial)), -1)
                    if idx != -1:
                        self.sdr_data[idx]['status'] = f"{self.services[name]['description']}"
        else:
            self.services[name]['selected_sdr'] = None

    def get_gps_status(self):
        """Query gpsd for GPS fix status and coordinates."""
        if not _gpsd_available:
            return {'state': 'unavailable', 'lat': None, 'lon': None, 'mode': None}

        now = time.time()
        if self._gps_cache is not None and (now - self._gps_cache_ts) < self._CACHE_TTL:
            logger.debug("Returning cached GPS status")
            return self._gps_cache

        logger.debug("Querying GPS status from gpsd")
        try:
            gpsd.connect()
            gps_data = gpsd.get_current()
            mode = gps_data.mode
            if mode >= 2:
                result = {
                    'state': 'fix_3d' if mode == 3 else 'fix_2d',
                    'lat': gps_data.lat,
                    'lon': gps_data.lon,
                    'mode': mode,
                }
            else:
                result = {'state': 'no_fix', 'lat': None, 'lon': None, 'mode': mode}
        except Exception as e:
            logger.warning("GPS status unavailable: %s", e)
            result = {'state': 'unavailable', 'lat': None, 'lon': None, 'mode': None}

        self._gps_cache = result
        self._gps_cache_ts = now
        return result
