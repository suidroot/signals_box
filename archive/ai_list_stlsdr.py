#!/usr/bin/env python3
"""
list_rtlsdr.py – List all RTL‑SDR USB dongles attached to the system.

Author:   OpenAI ChatGPT
License:  MIT (free to use and adapt)
"""

from __future__ import annotations

import sys
import argparse
from typing import Dict, Tuple, List

try:
    import usb.core
    import usb.util
except ImportError:
    print("pyusb is required: pip install pyusb", file=sys.stderr)
    sys.exit(1)

# --------------------------------------------------------------------------- #
# Known RTL‑SDR vendor/product ID pairs.  (VID, PID) → Human‑readable name.
# These are the most common dongles; if you have a custom RTL‑SDR you can add it here.
# --------------------------------------------------------------------------- #
RTL_IDS: Dict[Tuple[int, int], str] = {
    (0x0bda, 0x8176): "RTL2832U (generic RTL‑SDR)",
    (0x0bda, 0x8177): "RTL2832U (generic RTL‑SDR)",
    (0x1d50, 0x6067): "CubicSDR (Cubic Research)",
    (0x1d50, 0x6079): "CubicSDR (Cubic Research) – newer firmware",
    (0x054c, 0x06e5): "Xunlong (RTL‑SDR) – USB‑3.0 adapter",
    # Add more pairs if you encounter a dongle that isn’t listed.
}

# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #
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


def describe_device(dev: usb.core.Device) -> Dict[str, str]:
    """
    Return a dictionary with the most useful information about a device.
    """
    vid, pid = dev.idVendor, dev.idProduct
    vendor_str = get_string(dev, dev.iManufacturer)
    product_str = get_string(dev, dev.iProduct)
    serial_str = get_string(dev, dev.iSerialNumber)

    # Try to find a friendly name for the dongle
    friendly = RTL_IDS.get((vid, pid), f"Unknown VID:PID 0x{vid:04x}:0x{pid:04x}")

    return {
        "VID": f"0x{vid:04x}",
        "PID": f"0x{pid:04x}",
        "Friendly": friendly,
        "Manufacturer": vendor_str,
        "Product": product_str,
        "Serial": serial_str,
        "Bus": dev.bus,
        "Address": dev.address,
    }


def list_rtlsdr_devices() -> List[Dict[str, str]]:
    """
    Enumerate all USB devices and return a list of dicts for those that match
    the known RTL‑SDR IDs.
    """
    devices = usb.core.find(find_all=True)  # type: ignore
    rtlsdr_list = []

    for dev in devices:
        if (dev.idVendor, dev.idProduct) in RTL_IDS:
            rtlsdr_list.append(describe_device(dev))

    return rtlsdr_list


def list_all_usb_devices() -> List[Dict[str, str]]:
    """
    Enumerate all USB devices and return a list of dicts describing each one.
    Useful for debugging if your dongle isn’t showing up.
    """
    devices = usb.core.find(find_all=True)  # type: ignore
    all_list = []

    for dev in devices:
        all_list.append(describe_device(dev))

    return all_list


# --------------------------------------------------------------------------- #
# CLI entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find all RTL‑SDR USB dongles on the system."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all USB devices, not just RTL‑SDR dongles."
    )
    args = parser.parse_args()

    if args.all:
        devices = list_all_usb_devices()
        title = "All USB devices detected:"
    else:
        devices = list_rtlsdr_devices()
        title = "RTL‑SDR USB dongles detected:"

    if not devices:
        print(f"{title} None found.")
        return

    print(title)
    print("-" * len(title))
    for i, dev in enumerate(devices, start=1):
        print(f"[{i}] VID:PID {dev['VID']}:{dev['PID']}  {dev['Friendly']}")
        if dev["Manufacturer"]:
            print(f"     Manufacturer: {dev['Manufacturer']}")
        if dev["Product"]:
            print(f"     Product:      {dev['Product']}")
        if dev["Serial"]:
            print(f"     Serial:       {dev['Serial']}")
        print(f"     Bus {dev['Bus']} Address {dev['Address']}")
        print()

# --------------------------------------------------------------------------- #
# Execute the script
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    main()
