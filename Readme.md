# RosTAK (ROS 2)

ROS 2 Jazzy GPS-to-CoT conversion and CoT XML network transport. For this three-repository workspace, see the [suite setup, preview commands, and work log](../README.md).

## Run

After building with Colcon and sourcing the workspace:

```bash
ros2 launch rostak rostak.launch.py cot_url:=udp://127.0.0.1:16969
ros2 topic pub --once /fix sensor_msgs/msg/NavSatFix '{latitude: 39.0, longitude: -77.0, altitude: 100.0}'
```

The default endpoint is the suite's emulator forwarding port, not a TAK Server. The emulator redirect must be established separately; the suite's `scripts/start-preview.sh` does that.

## Interfaces

- `/fix`: `sensor_msgs/msg/NavSatFix`, converted by `roscot_fix` using sensor-data QoS.
- `/tak/tak_tx`: `std_msgs/msg/String` containing CoT XML, sent by `rostak_bridge`.
- `/tak/tak_rx`: received CoT XML as `std_msgs/msg/String`.
- Launch arguments: `cot_url`, `fix_topic`, `cot_params`, and `tak_params`.

PRONTOTak can publish custom CoT directly to `/tak/tak_tx`, bypassing the basic GPS converter.

## Transport and configuration

UDP, TCP, and TLS are implemented with Python's standard library; PyTAK is no longer a runtime dependency. Configure identity in `config/cot.yaml` and transport parameters in `config/tak.yaml`.

For ATAK's direct peer TCP input, use `tcp+direct://HOST:4242`: it sends one
complete CoT event per connection and closes the connection to delimit it.
This is a one-way transport, unlike the persistent `tcp://` TAK Server stream.
The suite's `scripts/connect-phone.sh` creates USB forwarding and a separate
bridge at `tcp+direct://127.0.0.1:14242`, with ROS parameter
`DIRECT_TCP_FLUSH_SECONDS:=0.05` to allow ADB to drain before closing. That
parameter defaults to zero and accepts values from zero to one second.

For TLS, set `cot_url:=tls://HOST:8089` and the `PYTAK_TLS_CLIENT_CERT`, `PYTAK_TLS_CLIENT_KEY`, and `PYTAK_TLS_CLIENT_CAFILE` ROS parameters. The legacy parameter names are retained for compatibility. Paths must be readable by the node (inside the container when applicable). Certificate and hostname verification remain enabled. Never commit private keys.

Local UDP transmission has been tested through ATAK in the emulator. Direct TCP
over USB has been tested on the Galaxy S23 with five HMT casualties and six robot
tracks at 1 Hz each. External TAK Server TLS and inbound server traffic have not
been verified for arbitrary remote deployments. The adjacent `tak-server/`
deployment has now been verified with certificate-authenticated TLS, server
relay, ROS `/fix` publication, and HMT/robot delivery to the S23 over Wi-Fi.
See its [standalone deployment guide](../tak-server/README.md).
