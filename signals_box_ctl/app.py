# pylint: disable=line-too-long
#!/usr/bin/env python3

# SDR Device
# TODO: device setup handlers
# TODO: by serial number radio setting eg: PPM
# Services
# TODO: Fix up out processes exec handler (eg: pagermon client or other nont-systemd programs)
# TODO: add reset status option

"""
    This app is used to manage SDR related services and applications
"""

import logging
import logging.config
import subprocess
import yaml
from flask import Flask, request, render_template
from signalsmanager import SignalsManager

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

    logger.debug("Render SDR Information")
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
        row = f"""
        <tr>
            <td>{sdr_entry['Manufacturer']}</td>
            <td>{sdr_entry['Product']}</td>
            <td>{sdr_entry['Serial']}</td>
            <td>{sdr_entry['Rtl Id']}</td>
            <td>{sdr_entry['status']}</td>
        </tr>
        """
        table_rows.append(row)

    return ''.join(table_rows)

def render_sdr_drop_list(usb_dev_list, name, select_default=None, multi=False):
    """
    Render HTML select list of SDR detected on the system.
    multi=True renders a multi-select listbox; multi=False renders a single-select dropdown.
    """
    logger.debug("Rendering SDR Drop for Service")

    if multi:
        size = max(2, len(usb_dev_list))
        selection = f'<select name="sdr_{name}" multiple size="{size}">\n'
    else:
        selection = f'<select name="sdr_{name}">\n'
        selection += '<option value="">Select SDR</option>\n'

    if select_default is None:
        defaults = set()
    elif isinstance(select_default, list):
        defaults = {str(s) for s in select_default}
    else:
        defaults = {str(select_default)}

    for sdr_entry in usb_dev_list:
        selected = ' selected' if sdr_entry['Serial'] in defaults else ''
        selection += f'<option value="{sdr_entry["Serial"]}"{selected}>{sdr_entry["Manufacturer"]} {sdr_entry["Product"]} {sdr_entry["Serial"]}</option>\n'

    selection += "</select>"

    return selection

def render_service_toggles(render_manager):
    """
    Docstring for render_service_toggles

    :param render_manager: Description
    """

    logger.debug("Rendering Service Toggles")

    statuses = {
        "unavailable"   : "#2727F5", # blue
        'unknown'       : "#2727F5", # blue
        'running'       : "#27F527", # green
        'stopping'      : "grey",
        'stopped'       : "#F52727", # red #f8d7da
    }

    # Update all current_status values first so get_all_sdrs/update_sdr_status
    # sees fresh data when annotating which SDR each service is using.
    service_statuses = {}
    for service_id in render_manager.services:
        status, _ = render_manager.get_single_service_status(service_id)
        render_manager.services[service_id]['current_status'] = status
        service_statuses[service_id] = status

    usb_dev_list = render_manager.get_all_sdrs()

    table_rows = ["<tr><th>Service</th><th>Status</th><th>Select SDR</th><th>Freq</th><th>Link</th><th>Actions</th></tr>"]
    for _, service_id in enumerate(render_manager.services):

        set_radio_button = ""
        freq_input = ""
        link = ""
        sdr_selection = ""

        status = service_statuses[service_id]
        color = statuses.get(status, "#2727F5")

        description = render_manager.services[service_id].get('description', service_id)

        if render_manager.services[service_id].get('link'):
            link = f"<a href=\"{render_manager.services[service_id]['link']}\" target=\"_blank\">{description}</a>"

        if render_manager.services[service_id].get('require_sdr', False):
            multi = render_manager.services[service_id].get('multi_sdr', False)
            if 'default_sdr' in render_manager.services[service_id]:
                sdr_selection = render_sdr_drop_list(usb_dev_list, service_id,
                    select_default=render_manager.services[service_id]['selected_sdr'],
                    multi=multi)
            else:
                sdr_selection = render_sdr_drop_list(usb_dev_list, service_id, multi=multi)

            if 'freq_input' in render_manager.services[service_id]:
                freq_value = render_manager.services[service_id]['freq_input']
                freq_input = f"<input type=\"text\" name=\"freq_{service_id}\" value=\"{freq_value}\" size=\"11\">"

            set_radio_button = f"<button type=\"submit\" name=\"set_radio\" value=\"{service_id}\" class=\"btn btn-neutral\">Set Radio</button>"

        # Build Row HTML
        row = f"""
        <tr>
            <td style="border-left:4px solid {color};padding-left:12px;"><strong>{description}</strong></td>
            <td>{status}</td>
            <td>{sdr_selection}</td>
            <td>{freq_input}</td>
            <td>{link}</td>
            <td align="right">
                <button type="submit" name="start" value="{service_id}" class="btn btn-start">Start</button>
                <button type="submit" name="stop" value="{service_id}" class="btn btn-stop">Stop</button>
                {set_radio_button}
            </td>
        </tr>
        """
        table_rows.append(row)

    return ''.join(table_rows)

def render_buttons(buttons):
    '''
        Generate HTML for buttons
    '''

    logger.debug("Rendering Buttons")
    button_text = ""
    for button_name in buttons:
        button_text += f"<button {buttons[button_name]['html_command']} name={buttons[button_name]['name']} class=\"btn btn-neutral\">{buttons[button_name]['text']}</button>\n"
    button_text += "</p>\n"

    return button_text


def render_gps_status(gps_data):
    """Render GPS status as a fixed box in the top-right corner."""
    logger.debug("Rendering GPS status")
    state = gps_data.get('state', 'unavailable')
    color_map = {
        'unavailable': '#2727F5',  # blue
        'no_fix':      '#F5A527',  # amber
        'fix_2d':      '#27F527',  # green
        'fix_3d':      '#27F527',  # green
    }
    color = color_map.get(state, '#2727F5')
    if state in ('fix_2d', 'fix_3d'):
        fix_label = '3D Fix' if state == 'fix_3d' else '2D Fix'
        lines = [
            f'<span style="color:{color}"><strong>{fix_label}</strong></span>',
            f'Lat: <strong>{gps_data["lat"]:.6f}</strong>',
            f'Lon: <strong>{gps_data["lon"]:.6f}</strong>',
        ]
    elif state == 'no_fix':
        lines = [f'<span style="color:{color}"><strong>No Fix</strong></span>']
    else:
        lines = [f'<span style="color:{color}"><strong>Unavailable</strong></span>']

    body = '<br>'.join(lines)
    return (
        '<div class="gps-box">'
        f'<strong class="gps-label">GPS</strong><br>{body}'
        '</div>'
    )


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
        logger.debug("POST received %s", request.form)

        if "stop" in request.form:
            output += f"Stopping {request.form['stop']}"
            try:
                manager.stop_service(request.form['stop'])
            except RuntimeError as e:
                logger.error("Failed to stop service %s: %s", request.form['stop'], e)
                output += f" — Error: {e}"
        elif "start" in request.form:
            output += f"Starting {request.form['start']}"
            try:
                manager.start_service(request.form['start'])
            except RuntimeError as e:
                logger.error("Failed to start service %s: %s", request.form['start'], e)
                output += f" — Error: {e}"
        elif "set_radio" in request.form:
            service_id = request.form['set_radio']
            sdr_key = f'sdr_{service_id}'
            manager.set_service_radio(service_id, request.form.getlist(sdr_key))
        elif "reload_config" in request.form:
            output += "Reloading Config File"
            manager.load_config()
        elif "shutdown" in request.form:
            try:
                subprocess.run(manager.buttons['shutdown']['cli_command'], check=True)
            except (subprocess.CalledProcessError, KeyError) as e:
                logger.error("Shutdown command failed: %s", e)
                output += f"Shutdown failed: {e}"
        elif "reboot" in request.form:
            try:
                subprocess.run(manager.buttons['reboot']['cli_command'], check=True)
            except (subprocess.CalledProcessError, KeyError) as e:
                logger.error("Reboot command failed: %s", e)
                output += f"Reboot failed: {e}"

    links_table = ""
    links_table = '<p name="links">\n'
    for _, link_data in enumerate(manager.links):
        links_table += f"<a href=\"{link_data['url']}\" target=\"_blank\">{link_data['name']}</a><br>\n"
    links_table += "</p>\n"

    service_rows = render_service_toggles(manager)
    usb_dev_list = manager.get_all_sdrs()
    sdrlist = render_sdr_list(usb_dev_list)
    button_text = render_buttons(manager.buttons)
    gps_data = manager.get_gps_status()
    gps_status = render_gps_status(gps_data)

    return render_template('index.html', cmd_output=output, sdrlist=sdrlist, \
        service_rows=service_rows, links_table=links_table, buttons=button_text, \
        gps_status=gps_status)

if __name__ == "__main__":
    # Run with:  sudo python3 app.py
    logger.debug("Starting Signals Box Debug Control App")
    app.run(host="0.0.0.0", port=8081, debug=False)
