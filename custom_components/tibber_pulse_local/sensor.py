from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    EntityCategory,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from . import TibberPulseDataCoordinator


@dataclass(frozen=True, kw_only=True)
class TibberPulseSensorDescription(SensorEntityDescription):
    key: str
    suggested_display_precision: int | None = None


SENSOR_TYPES: tuple[TibberPulseSensorDescription, ...] = (
    TibberPulseSensorDescription(
        key="active_power_import",
        name="Active Power Import",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash",
    ),
    TibberPulseSensorDescription(
        key="voltage_l1",
        name="Voltage L1",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    TibberPulseSensorDescription(
        key="voltage_l2",
        name="Voltage L2",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    TibberPulseSensorDescription(
        key="voltage_l3",
        name="Voltage L3",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    TibberPulseSensorDescription(
        key="current_l1",
        name="Current L1",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    TibberPulseSensorDescription(
        key="current_l2",
        name="Current L2",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    TibberPulseSensorDescription(
        key="current_l3",
        name="Current L3",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    TibberPulseSensorDescription(
        key="active_import_total",
        name="Cumulative Active Import Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:counter",
        suggested_display_precision=3,
    ),
    TibberPulseSensorDescription(
        key="meter_id",
        name="Meter ID",
        icon="mdi:barcode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    TibberPulseSensorDescription(
        key="meter_model",
        name="Meter Model",
        icon="mdi:gauge",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TibberPulseDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        TibberPulseSensor(coordinator, entry, description)
        for description in SENSOR_TYPES
    ]
    async_add_entities(sensors)


class TibberPulseSensor(CoordinatorEntity[TibberPulseDataCoordinator], SensorEntity):
    def __init__(
        self,
        coordinator: TibberPulseDataCoordinator,
        entry: ConfigEntry,
        description: TibberPulseSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = description.name

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data
        if not data:
            return None

        val = data.values.get(self.entity_description.key)
        if val is None:
            return None

        prec = self.entity_description.suggested_display_precision
        if prec is not None and isinstance(val, (int, float)):
            return round(val, prec)

        return val
