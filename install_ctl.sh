#!/bin/sh

mkdir /opt/signals_box_ctl

cp -R signalsboxctl/* /opt/signals_box_ctl/
cp signals_ctl.service /etc/systemd/system/
cd /opt/signals_box_ctl/
python -m venv /opt/signals_box_ctl/venv
/opt/signals_box_ctl/venv/bin/pip install -r /opt/signals_box_ctl/requirements.txt

# Install Service
systemctl enable signals_ctl.service
systemctl start signals_ctl.service
