# VNC
# https://gist.github.com/dragolabs/8e559113567faed32327ef24fdce775b

#librtlsdr-dev librtlsdr0
sudo apt update
sudo apt install libusb-1.0-0-dev git cmake build-essential pkg-config python3-venv
sudo apt install debhelper

git clone https://github.com/osmocom/rtl-sdr
cd rtl-sdr
sudo dpkg-buildpackage -b --no-sign
cd ..

sudo dpkg -i librtlsdr0_*.deb
sudo dpkg -i librtlsdr-dev_*.deb
sudo dpkg -i rtl-sdr_*.deb

sudo usermod -a -G plugdev $USER
sudo usermod -a -G audio $USER
sudo usermod -a -G pulse $USER
sudo usermod -a -G dialout $USER

sudo apt install gnuradio gqrx 

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

# https://www.kismetwireless.net/packages/
wget -O - https://www.kismetwireless.net/repos/kismet-release.gpg.key --quiet | gpg --dearmor | sudo tee /usr/share/keyrings/kismet-archive-keyring.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/kismet-archive-keyring.gpg] https://www.kismetwireless.net/repos/apt/release/jammy jammy main' | sudo tee /etc/apt/sources.list.d/kismet.list >/dev/null
sudo apt update
sudo apt install kismet
sudo usermod -a -G kismet $USER

# https://github.com/DSheirer/sdrtrunk


sudo apt install icecast2 ices2 darkice
# https://www.linuxjournal.com/article/9280

# AIS
# https://jvde-github.github.io/AIS-catcher-docs/installation/ubuntu-debian/

# Pagermon - https://github.com/pagermon/pagermon
sudo apt install multimon-ng


locutus@signals:~/pagermon/client$ diff reader.js reader\ copy.js
121c121
<             message = line.match(/FLEX[:|].*[|\[][0-9 ]*[|\]] ?...[ |]{0,1}(.*)/)[1].trim();
---
>             message = line.match(/FLEX[:|].*[|\[][0-9 ]*[|\]] ?...[ |](.+)/)[1].trim();
163c163
<   if (address.length > 2 && message && trimMessage.length > 1) {
---
>   if (address.length > 2 && message) {