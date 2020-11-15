# Huawei HG659 Router Integration in Home Assistant
Component to integrate the Huawei HG659 router (tested on model HG659). Also works on Eir F2000 router (an ISP branded HG659).

## Features
- Publish the huawei_hg659.reboot service to reboot the router.
- Provides a device_tracker to monitor the connection status of devices.

## Example usage

```
# Setup the platform huawei_hg_659
huawei_hg659:
  host: 192.168.0.1
  username: admin
  password: !secret router_password

# Enable and customize the tracker's parameters
device_tracker:
- platform: huawei_hg659
  interval_seconds: 60
  consider_home: 180
  new_device_defaults:
    track_new_devices: false
```
