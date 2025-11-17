#!/usr/bin/env python3
# TODO: something kismet API - https://github.com/kismetwireless/python-kismet-rest
# https://www.kismetwireless.net/docs/api/datasources/
# TODO: device setup handlers
# TODO: build out processes exec handler (eg: pagermon client or other nont-systemd programs)
# TODO: by serial number radio setting eg: PPM


import logging
import logging.config
import yaml
from services import SystemdServiceManager, CliService
from usbs import UsbDevices
from flask import Flask, request, redirect, url_for, render_template


app = Flask(__name__)

with open("logging.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Apply the config
logging.config.dictConfig(config)
logger = logging.getLogger(__name__)
# logger = logging.basicConfig(level=logging.DEBUG)

class SignalsManager:

    def __init__(self, config_file="config.yml"):
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        logger.debug("Loading config file: %s", self.config_file)

        with open(self.config_file, "r" ) as file_handle:
            cfg = yaml.safe_load(file_handle)
            self.services = cfg['services']
            self.http_base_url = cfg['http_base_url']
            self.links = cfg['links']
            self.systemd_svc_mgr = SystemdServiceManager()

    def get_all_service_status(self):
        
        logger.debug("Getting all service status")
        for index, service_id  in enumerate(self.services):

            if self.services[service_id]['type'] == "systemd":
                status_data = self.systemd_svc_mgr.status_service(self.services[service_id]['system_ctl_name'])

                if status_data:
                    if status_data.get('ActiveState'):
                        self.services[service_id]['current_status'] = True
                    else:
                        self.services[service_id]['current_status'] = False

                else:
                    self.services[service_id]['current_status'] = False

            elif self.services[service_id]['type'] == "cli":

                if not 'cli_status_obj' in self.services[service_id]:
                    self.services[service_id]['cli_status_obj'] = CliService(service_id, self.services[service_id])

                self.services[service_id]['current_status'] = self.services[service_id]['cli_status_obj'].is_running()

        return 
    
    def get_single_service_status(self, service_id):

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

        elif self.services[service_id]['type'] == "cli":

            if not 'cli_status_obj' in self.services[service_id]:
                self.services[service_id]['cli_status_obj'] = CliService(service_id, self.services[service_id])
            self.services[service_id]['current_status'] = self.services[service_id]['cli_status_obj'].is_running()
            status = self.services[service_id]['current_status']

        return status, status_data

    def start_service(self, service_id):

        if self.services[service_id]['type'] == "systemd":
            self.systemd_svc_mgr.start_service(self.services[service_id]['system_ctl_name'])

        elif self.services[service_id]['type'] == 'cli':
            if not 'cli_status_obj' in self.services[service_id]:
                    self.services[service_id]['cli_status_obj'] = CliService(service_id, self.services[service_id])

            self.services[service_id]['cli_status_obj'].start()

        return self.get_single_service_status(service_id)


    def stop_service(self, service_id):

        if self.services[service_id]['type'] == "systemd":
            self.systemd_svc_mgr.start_service(self.services[service_id]['system_ctl_name'])
        elif self.services[service_id]['type'] == 'cli':
            if not 'cli_status_obj' in self.services[service_id]:
                    self.services[service_id]['cli_status_obj'] = CliService(service_id, self.services[service_id])

            self.services[service_id]['cli_status_obj'].stop()

        return self.get_single_service_status(self.services[service_id])



    ### SDR 
    def get_all_sdrs(self):
        usb_dev = UsbDevices()
        return usb_dev.list_rtlsdr_devices()


######## HTML Rendered
def render_sdr_list(usb_dev_list):
    table_rows = []

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

    selection = f"<select NAME=\"{name}\">\n"

    for sdr_entry in usb_dev_list:
        selection += f"""<option value="{sdr_entry['Serial']}">{sdr_entry['Manufacturer']} {sdr_entry['Product']} {sdr_entry['Serial']}</option>\n"""

    selection += "</select>"

    return selection

def render_service_toggles(manager):
    usb_dev_list = manager.get_all_sdrs()

    table_rows = []
    for index, service_id in enumerate(manager.services):
        status, _ = manager.get_single_service_status(service_id)
        manager.services[service_id]['current_status'] = status


        if status == "unavailable":
            color = "#f0f0f0"   # grey
        elif not status:
            color = "#f8d7da"   # red
        elif status:
            color = "#d4edda"   # green
        else:
            color = "#f0f0f0"   # grey

        if manager.services[service_id]['link']:
            link = f"<a href=\"{manager.services[service_id]['link']}\" target=\"_blank\">{manager.services[service_id]['description']}</a>"
        else:
            link = ""

        if manager.services[service_id]['require_sdr']:
            sdr_selection = render_sdr_drop_list(usb_dev_list, service_id)
        else:
            sdr_selection = ""

        row = f"""
        <tr>
            <td style="background:{color}; width:2%">&nbsp;</td>
            <td style="width:20%"><strong>{manager.services[service_id]['description']}</strong></td>
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
            output += f"Reloading Config File"
            manager.load_config()

        # start Services
        # Stop Services
            

    links_table = ""
    links_table = '<p name="links">\n'
    for _, link_data in enumerate(manager.links):
        links_table += f"<a href=\"{link_data['url']}\" target=\"_blank\">{link_data['name']}</a><br>\n"
    links_table += "</p>\n"

    service_rows = render_service_toggles(manager)
    sdrlist = render_sdr_list(usb_dev_list)

    return render_template('index.html', cmd_output=output, sdrlist=sdrlist, service_rows=service_rows, links_table=links_table)
    # return render_template_string(page)

if __name__ == "__main__":
    # 8080 is the same port that the original PHP page used.
    # Run with:  sudo python3 app.py
    app.run(host="0.0.0.0", port=8080, debug=False)