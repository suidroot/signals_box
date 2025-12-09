# pylint: disable=line-too-long
#!/usr/bin/env python3
# TODO: Build Application API handler
# TODO: device setup handlers
# TODO: by serial number radio setting eg: PPM
# TODO: better handle service status - eg: running, stopped, etc.
# TODO: Fix up out processes exec handler (eg: pagermon client or other nont-systemd programs)
# TODO: add reset status option
# TODO: Update radio selection when running

"""
This app is used to manage SDR related services and applications
"""

import logging
import logging.config
import yaml
import subprocess
from flask import Flask, request, render_template
from signalsmanager import SignalsManager
# from services import SystemdServiceManager, CliService, DockerService, KismetStatus
# from usbs import UsbDevices


app = Flask(__name__)

with open("logging.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

logging.config.dictConfig(config)
logger = logging.getLogger(__name__)

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
            <td style="width:20%">{sdr_entry['Product']}</td>
            <td style="width:20%">{sdr_entry['Serial']}</td>
            <td style="width:5%">{sdr_entry['Rtl Id']}</td>
            <td style="width:10%">{sdr_entry['status']}</td>
        </tr>
        """
        table_rows.append(row)

    return ''.join(table_rows)

def render_sdr_drop_list(usb_dev_list, name, select_default=None):
    """
    Render HTML Drop down list of SDR detected on the system.
    """

    selection = f"<select NAME=\"sdr_{name}\">\n"
    selection += f"""<option value="">Select SDR</option>\n"""

    for sdr_entry in usb_dev_list:
        selected = ""

        if select_default and sdr_entry['Serial'] == select_default:
            selected = " selected"

        selection += f"""<option value="{sdr_entry['Serial']}"{selected}>{sdr_entry['Manufacturer']} {sdr_entry['Product']} {sdr_entry['Serial']}</option>\n"""

    selection += "</select>"

    return selection

def render_service_toggles(render_manager):
    """
    Docstring for render_service_toggles

    :param render_manager: Description
    """
    usb_dev_list = render_manager.get_all_sdrs()

    table_rows = ["<tr><th></th><th>Service</th><th>Status</th><th>Select SDR</th><th>Link</th><th>Actions</th></tr>"]
    for _, service_id in enumerate(render_manager.services):

        set_radio_button = ""

        status, _ = render_manager.get_single_service_status(service_id)
        render_manager.services[service_id]['current_status'] = status


        if status == "unavailable":
            color = "#2727F5"   # blue
        elif not status:
            color = "grey"  # red #f8d7da
        elif status == 'inactive':
            color = "grey"  # red #f8d7da
        elif status == 'failed':
            color = "#F52727"  # red #f8d7da
        elif status:
            color = "#27F527"   # green
        else:
            color = "#2727F5"   # blue

        if render_manager.services[service_id]['link']:
            link = f"<a href=\"{render_manager.services[service_id]['link']}\" target=\"_blank\">{render_manager.services[service_id]['description']}</a>"
        else:
            link = ""

        if render_manager.services[service_id]['require_sdr']:
            if 'default_sdr' in render_manager.services[service_id]:
                sdr_selection = render_sdr_drop_list(usb_dev_list, service_id, \
                    select_default=render_manager.services[service_id]['default_sdr'])
            else:
                sdr_selection = render_sdr_drop_list(usb_dev_list, service_id)

            set_radio_button = f"<button type=\"submit\" name=\"set_radio\" value=\"{service_id}\">Set Radio</button>"            
        else:
            sdr_selection = ""

        row = f"""
        <tr>
            <td style="background:{color}; width:2%">&nbsp;</td>
            <td style="width:20%"><strong>{render_manager.services[service_id]['description']}</strong></td>
            <td style="width:20%">{status}</td>
            <td style="width:20%">{sdr_selection}</td>
            <td style="width:20%">{link}</td>
            <td style="width:20%" align="right">
                <button type="submit" name="start" value="{service_id}">Start</button>
                <button type="submit" name="stop" value="{service_id}">Stop</button>
                {set_radio_button}
            </td>
        </tr>
        """
        table_rows.append(row)

    return ''.join(table_rows)

def render_buttons(buttons):
    # <button onClick="window.location.reload();" class="btn">Refresh Page</button>
    #   <button type="submit" name="reload_config">Reload Config</button>
    button_text = ""
    for _, button_data in enumerate(buttons):
        button_text += f"<button {button_data['html_command']} name={button_data['name']} class=\"btn\">{button_data['text']}</button>\n"
    button_text += "</p>\n"

    return button_text


manager = SignalsManager()

# --------------------------------------------------------------------
# Flask view – handles GET (show page) and POST (handle actions)
# --------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    """
    Handle Flash requests for index page
    """

    output = ""

    if request.method == "POST":
        # print(request.form.keys())

        if "stop" in request.form:
            output += f"Stopping {request.form['stop']}"
            manager.stop_service(request.form['stop'])
        elif "start" in request.form:
            output += f"Starting {request.form['start']}"
            manager.start_service(request.form['start'])
        elif "set_radio" in request.form:
            # request.form['set_radio']
            manager.set_service_radio(request.form['set_radio'], request.form[f'sdr_{request.form['set_radio']}'])
        elif "reload_config" in request.form:
            output += "Reloading Config File"
            manager.load_config()
        elif "shutdown" in request.form:
            subprocess.run(["/usr/sbin/shutdown", "now"])

    links_table = ""
    links_table = '<p name="links">\n'
    for _, link_data in enumerate(manager.links):
        links_table += f"<a href=\"{link_data['url']}\" target=\"_blank\">{link_data['name']}</a><br>\n"
    links_table += "</p>\n"

    service_rows = render_service_toggles(manager)
    usb_dev_list = manager.get_all_sdrs()
    sdrlist = render_sdr_list(usb_dev_list)
    button_text = render_buttons(manager.buttons)

    return render_template('index.html', cmd_output=output, sdrlist=sdrlist, \
        service_rows=service_rows, links_table=links_table, buttons=button_text)

if __name__ == "__main__":
    # 8080 is the same port that the original PHP page used.
    # Run with:  sudo python3 app.py
    app.run(host="0.0.0.0", port=8081, debug=False)
