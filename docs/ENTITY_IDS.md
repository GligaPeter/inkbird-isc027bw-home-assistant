# Entity ID mapping

The dashboard and prediction package assume the entity IDs created by a clean,
English Home Assistant installation:

| Function | Expected entity ID |
|---|---|
| Grill temperature | `sensor.inkbird_isc_027bw_internal_temperature` |
| Probe 1 | `sensor.inkbird_isc_027bw_probe_1` |
| Probe 2 | `sensor.inkbird_isc_027bw_probe_2` |
| Probe 3 | `sensor.inkbird_isc_027bw_probe_3` |
| Fan speed | `sensor.inkbird_isc_027bw_fan_speed` |
| Fan switch | `switch.inkbird_isc_027bw_fan` |
| Grill target | `number.inkbird_isc_027bw_grill_target_temperature` |
| Probe 1 target | `number.inkbird_isc_027bw_probe_1_alarm_temperature` |
| Probe 2 target | `number.inkbird_isc_027bw_probe_2_alarm_temperature` |
| Probe 3 target | `number.inkbird_isc_027bw_probe_3_alarm_temperature` |

Home Assistant may append `_2`, `_3`, and so on when an older entity with the
same ID already exists. Either rename the entities in **Settings → Devices &
services → Entities**, or replace the IDs in both YAML files.
