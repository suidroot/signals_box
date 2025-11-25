#!/usr/bin/env python3

"""
Handler methods for collecing SDR USB devices
"""

from typing import Dict, Tuple, List
import logging
import sys

try:
    from rtlsdr import RtlSdr
except ImportError:
    print("pyrtlsdr is required: pip install pyrtlsdr", file=sys.stderr)
    sys.exit(1)

try:
    import usb.core
    import usb.util
except ImportError:
    print("pyusb is required: pip install pyusb", file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger(__name__)


SDR_IDS: Dict[Tuple[int, int], str] = {
    (0x0bda, 0x8176): "RTL2832U (generic RTL‑SDR)",
    (0x0bda, 0x8177): "RTL2832U (generic RTL‑SDR)",
    (0x1d50, 0x6067): "CubicSDR (Cubic Research)",
    (0x1d50, 0x6079): "CubicSDR (Cubic Research) – newer firmware",
    (0x054c, 0x06e5): "Xunlong (RTL‑SDR) – USB‑3.0 adapter",
    (0x0bda, 0x2832): "RTL2832U Generic",
    (0x0403, 0x601f): "LimeSDR Mini",
    (0x0bda, 0x2838): "RTLSDRBlog v4",
    # Add more pairs if you encounter a dongle that isn’t listed.
}

class UsbDevices:
    """
    A class to manage USB devices and their properties.
    """

    def __init__(self):
        self.sdr_ids = SDR_IDS

    @staticmethod
    def get_string(dev: usb.core.Device, index: int) -> str:
        """
        Safely fetch a string descriptor from the USB device.
        If the string descriptor is missing or an error occurs, return an empty string.
        """
        try:
            if index:
                return usb.util.get_string(dev, index)
        except usb.core.USBError:
            pass
        return ""

    @staticmethod
    def get_rtlsdr_device_number(serial_no):
        """ Get RTL-SDR Device number mapping from the device's serial number. """
        return RtlSdr.get_device_index_by_serial(str(serial_no))

    def describe_device(self, dev: usb.core.Device) -> Dict[str, str]:
        """
        Return a dictionary with the most useful information about a device.
        """
        vid, pid = dev.idVendor, dev.idProduct
        vendor_str = self.get_string(dev, dev.iManufacturer)
        product_str = self.get_string(dev, dev.iProduct)
        serial_str = self.get_string(dev, dev.iSerialNumber)
        try:
            rtl_id = RtlSdr.get_device_index_by_serial(serial_str)
        except:
            rtl_id = "na"


        # Try to find a friendly name for the dongle
        friendly = self.sdr_ids.get((vid, pid), f"Unknown VID:PID 0x{vid:04x}:0x{pid:04x}")



        return {
            "VID": f"0x{vid:04x}",
            "PID": f"0x{pid:04x}",
            "Friendly": friendly,
            "Manufacturer": vendor_str,
            "Product": product_str,
            "Serial": serial_str,
            "Bus": dev.bus,
            "Address": dev.address,
            "Rtl Id": rtl_id
        }

    def list_rtlsdr_devices(self) -> List[Dict[str, str]]:
        """
        Enumerate all USB devices and return a list of dicts for those that match
        the known RTL‑SDR IDs.
        """
        devices = usb.core.find(find_all=True)  # type: ignore
        rtlsdr_list = []

        for dev in devices:
            if (dev.idVendor, dev.idProduct) in self.sdr_ids:
                rtlsdr_list.append(self.describe_device(dev))

        return rtlsdr_list

    def list_all_usb_devices(self) -> List[Dict[str, str]]:
        """
        Enumerate all USB devices and return a list of dicts describing each one.
        Useful for debugging if your dongle isn’t showing up.
        """
        devices = usb.core.find(find_all=True)  # type: ignore
        all_list = []

        for dev in devices:
            all_list.append(self.describe_device(dev))

        return all_list
