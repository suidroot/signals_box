#!/usr/bin/env python3
"""
    DigiPi control panel – 100 % Python equivalent of the old PHP page.

    *   Displays the status of every service
    *   Lets you start / stop each one with a form button
    *   Provides the same “Reboot / Shutdown / Save Configs” actions
    *   Resets services that systemd has marked as *failed*
    *   Runs everything through ``sudo`` – the process must therefore
        be executed as root (or have the user in the sudoers file).

    Installation
    -------------

        pip install flask
        # Run the app with root privileges
        sudo python3 app.py

    The app listens on ``0.0.0.0:80`` by default – just like the original
    PHP page that was served by Apache on the Raspberry Pi.
"""

import subprocess
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)

# --------------------------------------------------------------------
# CONFIGURATION – services that the panel knows about
# --------------------------------------------------------------------
SERVICES = {
    #  key  :  ("display name",   "systemd unit")
    "tnc"       : ("TNC FT8 / FT9",           "tnc"),
    "tnc300b"   : ("TNC FT8/FT9 300B",         "tnc300b"),
    "digipeater": ("APRS Digipeater",          "digipeater"),
    "webchat"   : ("APRS Webchat",             "webchat"),
    "node"      : ("Linux Node AX.25",         "node"),
    "winlinkrms": ("Winlink Email Server",    "winlinkrms"),
    "pat"       : ("Pat Winlink Email Client", "pat"),
    "js8call"   : ("JS8Call",                  "js8call"),
    "sstv"      : ("Slow Scan TV",             "sstv"),
    "wsjtx"     : ("WSJTX FT8",                "wsjtx"),
    "fldigi"    : ("FLDigi",                   "fldigi"),
    "ardop"     : ("ARDOP Modem",              "ardop"),
    "rigctld"   : ("Rig Control Daemon",      "rigctld"),
    "wsjtx"     : ("WSJTX FT8",                "wsjtx"),
    "sstv"      : ("Slow Scan TV",             "sstv"),
    "fldigi"    : ("FLDigi",                   "fldigi"),
    "wsjtx"     : ("WSJTX FT8",                "wsjtx"),
}

# --------------------------------------------------------------------
# Helper functions – wrapper around systemctl / subprocess
# --------------------------------------------------------------------
def _run(cmd: str) -> subprocess.CompletedProcess:
    """Run a shell command via ``sudo`` – no error handling."""
    return subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True
    )

def service_status(name: str) -> str:
    """Return the output of ``systemctl is-active <service>``."""
    r = _run(f"sudo systemctl is-active {name}")
    return r.stdout.strip()

def start_service(name: str) -> str:
    return _run(f"sudo systemctl start {name}").stdout

def stop_service(name: str) -> str:
    return _run(f"sudo systemctl stop {name}").stdout

def reset_failed(*names: str):
    """Reset all the listed services – silence errors."""
    for n in names:
        _run(f"sudo systemctl reset-failed {n} 2> /dev/null")

# --------------------------------------------------------------------
# Flask view – handles GET (show page) and POST (handle actions)
# --------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    output = ""
    if request.method == "POST":
        # ------------------------------------------------------------------
        # 1.  Service start / stop actions – each form field contains the
        #     service name (e.g. <input name="tnc" value="Start">)
        # ------------------------------------------------------------------
        for key in SERVICES:
            if key in request.form:
                cmd = request.form[key]  # "Start" or "Stop"
                if cmd == "on":
                    output += f"<p>{key}: STARTED&nbsp;{start_service(key)}</p>"
                elif cmd == "off":
                    output += f"<p>{key}: STOPPED&nbsp;{stop_service(key)}</p>"

        # ------------------------------------------------------------------
        # 2.  Reboot / Shutdown / Save Configs
        # ------------------------------------------------------------------
        if "reboot" in request.form:
            output += "<br/><strong>Restarting DigiPi…</strong><br/>"
            _run("sudo killall direwatch.py")
            _run("sudo /home/pi/digibanner.py -b DigiPi -s Rebooting…")
            _run("sudo /sbin/shutdown -r 0")

        if "shutdown" in request.form:
            output += "<br/><strong>Shutting down DigiPi…</strong><br/>"
            _run("sudo killall direwatch.py")
            _run("sudo /home/pi/digibanner.py -b DigiPi -s Shutdown…")
            _run("sudo /sbin/shutdown -h 0")

        if "save" in request.form:
            output += "<br/><strong>Saving configuration…</strong><br/>"
            _run("sudo -i -u pi /home/pi/saveconfigs.sh")
            output += "<br/><strong>Please reboot or shutdown gracefully.</strong><br/>"

        # ------------------------------------------------------------------
        # 3.  Reset the “failed” status of services that systemd might have
        #     marked as failed because of a SIGKILL.  (Same list as the PHP file.)
        # ------------------------------------------------------------------
        reset_failed(
            "fldigi", "sstv", "wsjtx", "ardop",
            "tnc300b", "digipeater", "tnc", "node",
            "winlinkrms", "pat", "js8call"
        )

        # After the action we redirect to GET so that a page refresh
        # shows the updated status.  (The original PHP kept the POST data
        # in the same request; redirect‑after‑POST is cleaner.)
        return redirect(url_for("index"))

    # ----------------------------------------------------------------------
    # 4.  Build the HTML page (GET request)
    # ----------------------------------------------------------------------
    table_rows = []
    for key, (label, unit) in SERVICES.items():
        status = service_status(unit)
        if status == "active":
            color = "#d4edda"   # green
        elif status == "failed":
            color = "#f8d7da"   # red
        else:
            color = "#f0f0f0"   # grey
        row = f"""
        <tr>
            <td style="background:{color}; width:2%">&nbsp;</td>
            <td style="width:20%"><strong>{label}</strong></td>
            <td style="width:40%">{status}</td>
            <td style="width:20%" align="right">
                <button type="submit" name="{key}" value="on">Start</button>
                <button type="submit" name="{key}" value="off">Stop</button>
            </td>
        </tr>
        """
        table_rows.append(row)

    # Bottom‑link table – same as the PHP page
    links_table = """
    <table cellpadding="4" border="1" style="border-collapse:collapse;">
      <tr>
        <td width="100px"><a href="/pat" target="pat"><strong>PatEmail</strong></a></td>
        <td width="100px"><a href="/axcall.php" target="axcall"><strong>AXCall</strong></a></td>
        <td width="100px"><a href="/js8" target="js8"><strong>JS8Call</strong></a></td>
      </tr>
      <tr>
        <td><a href="/ft8" target="ft8"><strong>WSJTX FT8</strong></a></td>
        <td><a href="/tv" target="tv"><strong>SSTV</strong></a></td>
        <td><a href="/fld" target="fld"><strong>FLDigi</strong></a></td>
      </tr>
      <tr>
        <td><a href="/wifi.php"><strong>Wifi</strong></a></td>
        <td><a href="/shell.php" target="shell"><strong>Shell</strong></a></td>
        <td><a href="/log.php" target="log"><strong>PktLog</strong></a></td>
      </tr>
      <tr>
        <td><a href="/syslog.php" target="syslog"><strong>SysLog</strong></a></td>
        <td><a href="/"><strong>Refresh</strong></a></td>
        <td><a href="/webchat.php" target="webchat"><strong>Webchat</strong></a></td>
      </tr>
      <tr>
        <td><a href="/audio.php"><strong>Audio</strong></a></td>
      </tr>
    </table>
    """

    # The “initialize” link – shown only when the call‑sign file is missing
    init_link = ""
    if not os.path.exists("/var/cache/digipi/localized.txt"):
        init_link = """
        <tr>
            <td colspan="3">
                <a href="/setup.php" target="setup" style="color:green">
                    <strong>Initialize</strong>
                </a>
            </td>
        </tr>
        """

    # Final page template
    page = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <title>DigiPi – Web Panel</title>
      <style>
        body {{font-family:Arial,Helvetica,sans-serif;background:#222;color:#ddd;}}
        table {{width:90%;margin:auto;border-collapse:collapse;}}
        th,td {{padding:8px;}}
        .btn {{margin:4px;padding:4px 8px;background:#555;color:#fff;border:none;border-radius:3px;}}
        .btn:hover {{background:#777;}}
      </style>
    </head>
    <body>
      <h1 style="text-align:center;color:#aaa;">DigiPi Control Panel</h1>
      {output}
      <form method="post" action="">
      <table border="1">
        <tr><th></th><th>Service</th><th>Status</th><th>Action</th></tr>
        {''.join(table_rows)}
      </table>
      <br/>
      {links_table}
      <br/>
      <button type="submit" name="reboot" class="btn">Reboot</button>
      <button type="submit" name="shutdown" class="btn">Shutdown</button>
      <button type="submit" name="save" class="btn">Save Configs</button>
      <br/><br/>
      <small>©2024 KM6LYW – DigiPi</small>
      </form>
    </body>
    </html>
    """

    return render_template_string(page)

# --------------------------------------------------------------------
#  ENTRY POINT
# --------------------------------------------------------------------
if __name__ == "__main__":
    # 80 is the same port that the original PHP page used.
    # Run with:  sudo python3 app.py
    app.run(host="0.0.0.0", port=80, debug=False)
