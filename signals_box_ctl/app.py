# pylint: disable=line-too-long
#!/usr/bin/env python3
# TODO: Build Application API handler
# TODO: Add kismet API application - https://github.com/kismetwireless/python-kismet-rest
# https://www.kismetwireless.net/docs/api/datasources/
# TODO: device setup handlers
# TODO: by serial number radio setting eg: PPM
# TODO: better handle service status - eg: running, stopped, etc.
# TODO: Convert to API for processing 

"""
This is a Flash app to manage SDR related services and applications
"""


import logging
import logging.config
import yaml
from flask import Flask, request, render_template
from services import SystemdServiceManager, CliService, DockerService
from usbs import UsbDevices


app = Flask(__name__)

with open("logging.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Apply the config
logging.config.dictConfig(config)
logger = logging.getLogger(__name__)

class SignalsManager:
    """
    Class containing all of the functionality for service management and USB management

    :var value: Description
    :vartype value: Any
    """

    def __init__(self, config_file="config.yml"):
        self.config_file = config_file
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
            self.systemd_svc_mgr = SystemdServiceManager()
            self.docker_svc_mgr = DockerService()

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
        logger.debug("Refreshing Service Status for service: %s")

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
    @staticmethod
    def get_all_sdrs():
        """
        Gather list of all SDRs
        """

        usb_dev = UsbDevices()
        return usb_dev.list_rtlsdr_devices()


######## HTML Rendered
def render_sdr_list(usb_dev_list):
    """
    Render HTML table of Detected SDR Devices

    :param usb_dev_list: Description
    :return: Description
    :rtype: Any
    """
    table_rows = [
        """<tr>
            <th>Manufacturer</th>
            <th>Product</th>
            <th>Serial Number</th>
            <th>Rtl Sdr ID</th>
            <th>Status</th>
        </tr>"""
    ]

    for sdr_entry in usb_dev_list:

            # Manufacturer</th><th>Product</th><th>Serial Number</th><th>Rtl Id</th><th>Status<
        row = f"""
        <tr>
            <td style="width:20%">{sdr_entry['Manufacturer']}</strong></td>
            <td style="width:40%">{sdr_entry['Product']}</td>
            <td style="width:40%">{sdr_entry['Serial']}</td>
            <td style="width:40%">{sdr_entry['Rtl Id']}</td>
            <td style="width:40%">Status Unk</td>
        </tr>
        """
        table_rows.append(row)

    return ''.join(table_rows)

def render_sdr_drop_list(usb_dev_list, name):
    """
    Render HTML Drop down list of SDR detected on the system.
    """

    selection = f"<select NAME=\"{name}\">\n"

    for sdr_entry in usb_dev_list:
        selection += f"""<option value="{sdr_entry['Serial']}">{sdr_entry['Manufacturer']} {sdr_entry['Product']} {sdr_entry['Serial']}</option>\n"""

    selection += "</select>"

    return selection

def render_service_toggles(redner_manager):
    """
    Docstring for render_service_toggles

    :param redner_manager: Description
    """
    usb_dev_list = redner_manager.get_all_sdrs()

    table_rows = []
    for _, service_id in enumerate(redner_manager.services):
        status, _ = redner_manager.get_single_service_status(service_id)
        redner_manager.services[service_id]['current_status'] = status


        if status == "unavailable":
            color = "#f0f0f0"   # grey
        elif not status:
            color = "#f8d7da"   # red
        elif status:
            color = "#d4edda"   # green
        else:
            color = "#f0f0f0"   # grey

        if redner_manager.services[service_id]['link']:
            link = f"<a href=\"{redner_manager.services[service_id]['link']}\" target=\"_blank\">{redner_manager.services[service_id]['description']}</a>"
        else:
            link = ""

        if redner_manager.services[service_id]['require_sdr']:
            sdr_selection = render_sdr_drop_list(usb_dev_list, service_id)
        else:
            sdr_selection = ""

        row = f"""
        <tr>
            <td style="background:{color}; width:2%">&nbsp;</td>
            <td style="width:20%"><strong>{redner_manager.services[service_id]['description']}</strong></td>
            <td style="width:20%">{status}</td>
            <td style="width:20%">{sdr_selection}</td>
            <td style="width:20%">{link}</td>
            <td style="width:10%" align="right">
                <button type="submit" name="start" value="{service_id}">Start</button>
                <button type="submit" name="stop" value="{service_id}">Stop</button>
            </td>
        </tr>
        """
        table_rows.append(row)

    return ''.join(table_rows)


manager = SignalsManager()

# --------------------------------------------------------------------
# Flask view – handles GET (show page) and POST (handle actions)
# --------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    """
    Handle Flash requests for index page
    """
    usb_dev_list = manager.get_all_sdrs()

    output = ""

    if request.method == "POST":
        # print(request.form.keys())

        if "stop" in request.form:
            output += f"Stopping {request.form['stop']}"
            manager.stop_service(request.form['stop'])
        elif "start" in request.form:
            output += f"Starting {request.form['start']}"
            manager.start_service(request.form['start'])
        elif "reload_config" in request.form:
            output += "Reloading Config File"
            manager.load_config()

    links_table = ""
    links_table = '<p name="links">\n'
    for _, link_data in enumerate(manager.links):
        links_table += f"<a href=\"{link_data['url']}\" target=\"_blank\">{link_data['name']}</a><br>\n"
    links_table += "</p>\n"

    service_rows = render_service_toggles(manager)
    sdrlist = render_sdr_list(usb_dev_list)

    return render_template('index.html', cmd_output=output, sdrlist=sdrlist, service_rows=service_rows, links_table=links_table)

if __name__ == "__main__":
    # 8080 is the same port that the original PHP page used.
    # Run with:  sudo python3 app.py
    app.run(host="0.0.0.0", port=8080, debug=False)
