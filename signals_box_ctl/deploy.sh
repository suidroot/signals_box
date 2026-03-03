 #!/bin/sh
 #

cp requirements.txt /opt/signals_box_ctl
cp *.py /opt/signals_box_ctl
cp static/* /opt/signals_box_ctl/static/
cp templates/* /opt/signals_box_ctl/templates

systemctl restart signals_ctl.service
