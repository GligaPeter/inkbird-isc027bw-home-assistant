# Attribution and scope

The Inkbird ISC-027BW custom integration in `custom_components/inkbird_ble` is
based on [777Timo/inkbird-ble-ha](https://github.com/777Timo/inkbird-ble-ha),
copyright Timo Prager, and redistributed under the MIT License included in this
repository.

This kit adds:

- reliable confirmation and retry behavior for probe alarm-temperature writes;
- unavailable states instead of artificial zero readings while disconnected;
- predictive dashboard and Home Assistant helper configuration;
- a reusable repeating critical-notification blueprint.

This is an unofficial community project and is not affiliated with Inkbird.
