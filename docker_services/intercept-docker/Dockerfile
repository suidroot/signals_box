FROM python:3.10-slim

# 1. Install build tools + system dependencies
# Added pciutils, usbutils, and kmod for airmon-ng hardware discovery
RUN apt-get update && apt-get install -y \
    git sudo libpcap-dev gcc g++ make cmake pkg-config \
    libusb-1.0-0-dev librtlsdr-dev iproute2 wget gnupg curl \
    aircrack-ng bluez bluez-tools readsb usbutils kmod \
    pciutils libtool doxygen expect libpulse-dev libx11-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Build RTL-SDR from source with AUTO-DETACH
WORKDIR /tmp
RUN git clone https://github.com/steve-m/librtlsdr.git \
    && cd librtlsdr && mkdir build && cd build \
    && cmake ../ -DINSTALL_UDEV_RULES=ON -DDETACH_KERNEL_DRIVER=ON \
    && make -j$(nproc) && make install && ldconfig

# 3. Build dump1090 (Aircraft)
RUN git clone https://github.com/MalcolmRobb/dump1090.git \
    && cd dump1090 \
    && make -j$(nproc) CFLAGS="-O2 -g -Wall -W -fcommon" \
    && cp dump1090 /usr/local/bin/

# 4. Build rtl_433 (IoT/Sensors)
RUN git clone https://github.com/merbanan/rtl_433.git \
    && cd rtl_433 && mkdir build && cd build \
    && cmake ../ \
    && make -j$(nproc) && make install

# 5. Build multimon-ng (Pager/Digital)
RUN git clone https://github.com/EliasOenal/multimon-ng.git \
    && cd multimon-ng && mkdir build && cd build \
    && cmake .. \
    && make -j$(nproc) && make install

# 6. Setup the main application (intercept)
WORKDIR /app
RUN git clone https://github.com/smittix/intercept.git .
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python3", "intercept.py"]
