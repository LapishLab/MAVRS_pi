# MAVRS_pi
 Modular audio and video recording system for rat behavior. Code for Raspberry Pi.

## Live video

Add the following to `~/mavrs_pi_config.yaml` to serve video while an experiment is recording:

```yaml
streaming:
  enable: true
  port: 9000
  queue_size: 16
```

Open `tcp://<pi-address>:9000` in VLC. Only one viewer is supported at a time; the stream contains video only. A slow or disconnected viewer can lose stream frames without stopping the MP4 recording. Allow the chosen TCP port through the Pi's firewall if one is enabled.
