#!/usr/bin/env python3
"""
This module contains the main class for managing services.
"""

import logging
# import logging.config
import yaml
# import subprocess
from services import SystemdServiceManager, CliService, DockerService, KismetStatus
from usbs import UsbDevices

logger = logging.getLogger(__name__)

class SignalsManager:
    """
    Class containing all of the functionality for service management and USB management

    :var value: Description
    :vartype value: Any
    """

    def __init__(self, config_file="config.yml", creds_file="creds.yml"):
        self.config_file = config_file
        self.creds_file = creds_file
        self.sdr_data = None
        self.load_config()

    def load_config(self):
        """
        Load configuration from file and store in class variables

        :param self: Description
        """
        logger.debug("Loading config file: %s", self.config_file)

        with open(self.config_file, "r", encoding="utf-8") as file_handle:
            cfg = yaml.safe_load(file_handle)
            self.services = cfg['services']
            self.http_base_url = cfg['http_base_url']
            self.links = cfg['links']
            self.buttons = cfg['buttons']

            self.systemd_svc_mgr = SystemdServiceManager()
            self.docker_svc_mgr = DockerService()

        with open(self.creds_file, "r", encoding="utf-8") as credfile_handle:
            creds = yaml.safe_load(credfile_handle)
            self.creds = creds

    def get_all_service_status(self):
        """
        Get a list of the status for all configured services

        :param self: Description
        """

        logger.debug("Getting all service status")
        for _, service_id  in enumerate(self.services):

            if self.services[service_id]['type'] == "systemd":
                status_data = self.systemd_svc_mgr.status_service(self.services[service_id]['system_ctl_name'])

                if status_data:
                    if status_data.get('ActiveState'):
                        self.services[service_id]['current_status'] = True
                    else:
                        self.services[service_id]['current_status'] = False

                else:
                    self.services[service_id]['current_status'] = False
            elif self.services[service_id]['type'] == "docker":
                status_data = self.docker_svc_mgr.status_service(self.services[service_id]['container_name'])

                if status_data:
                    if status_data == 'running':
                        self.services[service_id]['current_status'] = True
                    else:
                        self.services[service_id]['current_status'] = False
                else:
                    self.services[service_id]['current_status'] = False

            elif self.services[service_id]['type'] == "cli":

                if not 'cli_status_obj' in self.services[service_id]:
                    self.services[service_id]['cli_status_obj'] = CliService(service_id, self.services[service_id])

                self.services[service_id]['current_status'] = self.services[service_id]['cli_status_obj'].is_running()

    def get_single_service_status(self, service_id):
        """
        Get the status of a single service

        :param self: Description
        :param service_id: Description
        """

        status = "not set"
        status_data = None
        logger.debug("Refreshing Service Status for service: %s", service_id)

        if self.services[service_id]['type'] == "systemd":

            status_data = self.systemd_svc_mgr.status_service(self.services[service_id]['system_ctl_name'])

            if status_data:
                if status_data.get('ActiveState'):
                    status = status_data.get('ActiveState')
                else:
                    status = "unavailable"
            else:
                status = "unavailable"
        elif self.services[service_id]['type'] == "docker":
            status_data = self.docker_svc_mgr.status_service(self.services[service_id]['container_name'])

            if status_data:
                if status_data == 'running':
                    status = True
                else:
                    status = False

            else:
                status = False


        elif self.services[service_id]['type'] == "cli":

            if not 'cli_status_obj' in self.services[service_id]:
                self.services[service_id]['cli_status_obj'] = CliService(service_id, self.services[service_id])
            self.services[service_id]['current_status'] = self.services[service_id]['cli_status_obj'].is_running()
            status = self.services[service_id]['current_status']

        return status, status_data

    def start_service(self, service_id):
        """
        Start a service and return its status.
        This is a wrapper for the various managers that are responsible for starting and stopping services.

        :param self: Description
        :param service_id: Description
        """

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

        if self.services[service_id]['type'] == "systemd":
            self.systemd_svc_mgr.stop_service(self.services[service_id]['system_ctl_name'])
        elif self.services[service_id]['type'] == "docker":
            self.docker_svc_mgr.stop_service(self.services[service_id]['container_name'])
        elif self.services[service_id]['type'] == 'cli':
            if not 'cli_status_obj' in self.services[service_id]:
                self.services[service_id]['cli_status_obj'] = CliService(service_id, self.services[service_id])

            self.services[service_id]['cli_status_obj'].stop()

        return self.get_single_service_status(service_id)

    ### SDR
    def get_all_sdrs(self):
        """
        Gather list of all SDRs
        """

        usb_dev = UsbDevices()
        self.sdr_data = usb_dev.list_rtlsdr_devices()
        self.update_sdr_status()

        return self.sdr_data

    def update_sdr_status(self):

        if 'kismet' in self.services and self.services['kismet']['current_status'] == "active":
            kismet_mgr = KismetStatus(self.creds['kismet']['username'], self.creds['kismet']['password'])

            for index, sdr_entry in enumerate(self.sdr_data):
                kismet_result = kismet_mgr.lookup_by_sdr_id(sdr_entry['Rtl Id'])

                if kismet_result:
                    self.sdr_data[index]['status'] = f"Kismet: {kismet_result}"

        for service_entry in self.services:
            if self.services[service_entry]['require_sdr']:
                if self.services[service_entry]['current_status'] or \
                    self.services[service_entry]['current_status'] == 'active':
                    for index, sdr_entry in enumerate(self.sdr_data):
                        if sdr_entry['Serial'] == str(self.services[service_entry]['selected_sdr']):
                            self.sdr_data[index]['status'] = f"Used by {self.services[service_entry]['description']}"

    def set_service_radio(self, name, sdr_serial):
        """
        Set the radio to be used by a given service
        """
        self.services[name]['selected_sdr'] = sdr_serial
