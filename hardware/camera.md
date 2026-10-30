# Installed solar camera

## Investigation result

The repository confirms an installed, solar-powered, weatherproof camera with
infrared night vision and a rotating head. It does not identify the camera's
manufacturer, model, hardware revision, companion app, or firmware version.
The original `assets/images/security-camera.jpg` and the lower-resolution copy
`frontend/site/img/solar-camera.jpg` contain no EXIF camera make or model. The
README and progress log describe its features but do not name a vendor or
protocol.

RTSP, ONVIF, a vendor API, and motion-snapshot support therefore remain
unverified. There is no stream URL or snapshot URL that can be safely recorded
from the repository evidence. This note records the limit of the remote
investigation; it does not mark issue #18 complete.

## Details needed to finish issue #18

When the camera can be inspected, record only these non-secret details:

| Detail | Where to find it |
| --- | --- |
| Manufacturer and exact model | Label on the camera, packaging, or purchase record |
| Hardware revision | Camera label or app device information |
| Companion app name | App used to view the camera |
| Firmware version | App's device information page |
| RTSP / ONVIF setting or vendor API reference | App settings or documentation for the exact model |
| Motion snapshot or webhook capability | App event settings or documentation for the exact model |

Do not add Wi-Fi passwords, cloud passwords, device serial numbers, or
authenticated stream URLs to this repository. If credentials are required,
keep them in deployment secrets and publish only a credential-free browser
endpoint.

## Integration choices after identification

- **RTSP or ONVIF available:** document the camera's supported stream and
  authentication mode, then restream it with go2rtc or MediaMTX to a
  browser-compatible format for the dashboard. Connect motion events through
  the model's documented API or an event bridge; publish the snapshot URL on
  `greenloop/camera-1/event` with event type `motion`.
- **Cloud-only with a usable vendor API:** document the API's event and
  snapshot support, terms, and subscription or hosting costs before adding an
  integration. Do not assume a cloud viewing app exposes an API.
- **Cloud-only without a usable API:** compare the cost of replacing the camera
  with a model that documents local RTSP/ONVIF and motion events against the
  cost of keeping the installed camera as a standalone device. No replacement
  price is listed until the required stream, connectivity, and power features
  are known.

Software restreamers do not require a camera subscription, but they still need
a host on the farm network. That host's hardware, power, storage, and remote
access costs depend on the installation and are not priced here.
