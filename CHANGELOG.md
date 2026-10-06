# Changelog

## 1.3.0-community.1

- Preserve requested probe alarm temperatures until the controller confirms
  them, retrying a mismatched write up to three times.
- Requeue pending grill and probe values after a BLE write error.
- Mark disconnected and unplugged temperature sensors unavailable instead of
  publishing zeroes.
- Add the predictive Kamado dashboard and helper package.
- Add a reusable repeating iOS critical-alarm blueprint.
- Add protocol regression tests and English installation documentation.
