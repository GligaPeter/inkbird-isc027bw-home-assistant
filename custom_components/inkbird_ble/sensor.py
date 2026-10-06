"""Inkbird BLE Sensoren: Temperaturen + Lüfterdrehzahl."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, InkbirdCoordinator, InkbirdData


@dataclass(frozen=True, kw_only=True)
class InkbirdSensorDescription(SensorEntityDescription):
    value_fn: Callable[[InkbirdData], float | int | str | None]
    # Wert der gezeigt wird wenn Gerät nicht verbunden ist (None = unknown)
    offline_value: float | int | str | None = None


SENSORS: tuple[InkbirdSensorDescription, ...] = (
    InkbirdSensorDescription(
        key="probe0",
        translation_key="probe0",
        name="Innentemperatur / Sonde 0",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.probe0,
    ),
    InkbirdSensorDescription(
        key="probe1",
        translation_key="probe1",
        name="Sonde 1",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.probe1,
    ),
    InkbirdSensorDescription(
        key="probe2",
        translation_key="probe2",
        name="Sonde 2",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.probe2,
    ),
    InkbirdSensorDescription(
        key="probe3",
        translation_key="probe3",
        name="Sonde 3",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.probe3,
    ),
    InkbirdSensorDescription(
        key="fan_speed",
        translation_key="fan_speed",
        name="Lüfter Ist-Drehzahl",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        value_fn=lambda d: d.fan_speed,
    ),
    InkbirdSensorDescription(
        key="grill_target_actual",
        translation_key="grill_target_actual",
        name="Zieltemperatur (Gerät)",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.grill_target_actual,
        offline_value=None,  # Zieltemp bleibt auf letztem Wert
    ),
    InkbirdSensorDescription(
        key="grill_heating_rate",
        translation_key="grill_heating_rate",
        name="Grill Heating Rate",
        native_unit_of_measurement="°C/min",
        icon="mdi:chart-timeline-variant",
        value_fn=lambda d: d.grill_heating_rate,
    ),
    *(
        InkbirdSensorDescription(
            key=f"probe{index}_heating_rate",
            translation_key=f"probe{index}_heating_rate",
            name=f"Probe {index} Heating Rate",
            native_unit_of_measurement="°C/min",
            icon="mdi:chart-timeline-variant",
            value_fn=lambda d, index=index: getattr(d, f"probe{index}_heating_rate"),
        )
        for index in range(1, 4)
    ),
    *(
        InkbirdSensorDescription(
            key=f"probe{index}_target_eta",
            translation_key=f"probe{index}_target_eta",
            name=f"Probe {index} Target ETA",
            icon="mdi:timer-outline",
            value_fn=lambda d, index=index: getattr(d, f"probe{index}_target_eta"),
        )
        for index in range(1, 4)
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: InkbirdCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        InkbirdSensor(coordinator, entry, description) for description in SENSORS
    )


class InkbirdSensor(SensorEntity):
    entity_description: InkbirdSensorDescription
    _attr_has_entity_name = True


    def __init__(
        self,
        coordinator: InkbirdCoordinator,
        entry: ConfigEntry,
        description: InkbirdSensorDescription,
    ) -> None:
        self.entity_description = description
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Inkbird ISC-027BW",
            manufacturer="Inkbird",
            model="ISC-027BW",
        )

    async def async_added_to_hass(self) -> None:
        self._unregister = self._coordinator.register_listener(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        self._unregister()

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return (
            self._coordinator.data.connected
            and self.entity_description.value_fn(self._coordinator.data) is not None
        )

    @property
    def native_value(self) -> float | int | str | None:
        if not self._coordinator.data.connected:
            return self.entity_description.offline_value
        return self.entity_description.value_fn(self._coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, float] | None:
        if not self.entity_description.key.endswith("_target_eta"):
            return None
        minutes = getattr(
            self._coordinator.data,
            self.entity_description.key.replace("_target_eta", "_eta_minutes"),
        )
        return {"estimated_minutes": minutes} if minutes is not None else None
