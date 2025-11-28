# VNC
# https://gist.github.com/dragolabs/8e559113567faed32327ef24fdce775b

sudo apt update

sudo apt install -y git curl vim htop net-tools python3-pip python3-setuptools virtualenvwrapper docker.io docker-compose 

# dbus-python build
sudo apt install libglib2.0-dev libdbus-1-dev
# Rpi
sudo apt-get install lightdm

sudo usermod -a -G docker $USER


nmcli connection add type bridge con-name bridge0 ifname bridge0
nmcli connection modify bridge0 ipv4.method auto
nmcli con mod br0 bridge.stp no
nmcli connection add type ethernet slave-type bridge con-name bridge0-port1 ifname enp1s0 master bridge0
nmcli connection add type ethernet slave-type bridge con-name bridge0-port2 ifname enp2s0 master bridge0
nmcli connection add type ethernet slave-type bridge con-name bridge0-port3 ifname enp3s0 master bridge0
nmcli connection add type ethernet slave-type bridge con-name bridge0-port4 ifname enp4s0 master bridge0

## Build RTLSDR drivers

sudo apt purge ^librtlsdr
sudo rm -rvf /usr/lib/librtlsdr* /usr/include/rtl-sdr* /usr/local/lib/librtlsdr* /usr/local/include/rtl-sdr* /usr/local/include/rtl_* /usr/local/bin/rtl_* 

sudo apt install libusb-1.0-0-dev git cmake build-essential pkg-config python3-venv
sudo apt install debhelper

git clone https://github.com/osmocom/rtl-sdr
cd rtl-sdr
sudo dpkg-buildpackage -b --no-sign
cd ..

sudo dpkg -i librtlsdr0_*.deb
sudo dpkg -i librtlsdr-dev_*.deb
sudo dpkg -i rtl-sdr_*.deb

sudo cp rtl-sdr/rtl-sdr.rules /etc/udev/rules.d/
sudo udevadm trigger

sudo usermod -a -G plugdev $USER
sudo usermod -a -G audio $USER
sudo usermod -a -G pulse $USER
sudo usermod -a -G dialout $USER

sudo apt install gnuradio gqrx-sdr

# sudo add-apt-repository ppa:myriadrf/gnuradio
# sudo apt-get update
sudo apt-get install gr-limesdr

# LimeSDR
sudo add-apt-repository -y ppa:myriadrf/drivers
sudo apt-get update
sudo apt-get install limesuite liblimesuite-dev limesuite-udev limesuite-images
sudo apt-get install soapysdr0.8-tools soapysdr0.8-module-lms7 soapysdr0.8-module-rtlsdr


wget -qO - https://repo.myriadrf.org/lime-microsystems-public.gpg | gpg --dearmor | sudo tee /etc/apt/keyrings/lime-microsystems-public.gpg > /dev/null
echo "deb [signed-by=/etc/apt/keyrings/lime-microsystems-public.gpg] https://repo.myriadrf.org/apt stable main" | sudo tee /etc/apt/sources.list.d/repo.myriadrf.org.list
sudo apt-get update
sudo apt-get install limesuiteng

# Kismet https://www.kismetwireless.net/packages/
wget -O - https://www.kismetwireless.net/repos/kismet-release.gpg.key --quiet | gpg --dearmor | sudo tee /usr/share/keyrings/kismet-archive-keyring.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/kismet-archive-keyring.gpg] https://www.kismetwireless.net/repos/apt/release/jammy jammy main' | sudo tee /etc/apt/sources.list.d/kismet.list >/dev/null
sudo apt update
sudo apt install kismet rtl-433
sudo usermod -a -G kismet $USER

# https://github.com/DSheirer/sdrtrunk


sudo apt install icecast2 ices2 darkice
# https://www.linuxjournal.com/article/9280

# TODO: AIS
# https://jvde-github.github.io/AIS-catcher-docs/installation/ubuntu-debian/

# Pagermon - https://github.com/pagermon/pagermon
sudo apt install multimon-ng 
sudo apt install nodejs npm

cd /opt
sudo git clone https://github.com/pagermon/pagermon.git
create docker-compose.yml in the `/opt/pagermon/server` directory

## Fix for client crash
# locutus@signals:~/pagermon/client$ diff reader.js reader\ copy.js
# 121c121
# <             message = line.match(/FLEX[:|].*[|\[][0-9 ]*[|\]] ?...[ |]{0,1}(.*)/)[1].trim();
# ---
# >             message = line.match(/FLEX[:|].*[|\[][0-9 ]*[|\]] ?...[ |](.+)/)[1].trim();
# 163c163
# <   if (address.length > 2 && message && trimMessage.length > 1) {
# ---
# >   if (address.length > 2 && message) {

## Openwebrx+
# https://fms.komkon.org/OWRX/#INSTALL-DOCKER
sudo mkdir -p /opt/owrx-docker/var /opt/owrx-docker/etc /opt/owrx-docker/plugins/{receiver,map}
# Create docker-compose.yml in /opt/owrx-docker


### 
sudo apt install python3-flask python3-usb python3-dbus
