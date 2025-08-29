from db import load_devices, save_devices
from models import Device

def get_devices():
    return load_devices()

def add_device(device: Device):
    devices = load_devices()
    devices.append(device.dict())
    save_devices(devices)
    return device
