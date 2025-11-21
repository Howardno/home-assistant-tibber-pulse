from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, PLATFORMS, CONF_TOPIC
from .mqtt_listener import TibberPulseMQTTListener

_LOGGER = logging.getLogger(__name__)


@dataclass
class TibberPulseData:
    """Container for decoded Tibber Pulse data."""
    values: dict[str, Any]


class TibberPulseDataCoordinator(DataUpdateCoordinator[TibberPulseData]):
    """Coordinator for push-based Tibber Pulse data."""

    def __init__(self, hass: HomeAssistant, topic: str) -> None:
        # IKKE gi update_method/update_interval når data pushes. :contentReference[oaicite:1]{index=1}
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=DOMAIN,
        )
        self.topic = topic
        self.listener = TibberPulseMQTTListener(hass, topic, self._handle_data)

    async def async_start(self) -> None:
        _LOGGER.debug("Starting MQTT listener on topic %s", self.topic)
        await self.listener.start()

    async def async_stop(self) -> None:
        _LOGGER.debug("Stopping MQTT listener")
        self.listener.stop()

    def _handle_data(self, decoded: dict[str, Any]) -> None:
        """Called by listener when new data arrives."""
        _LOGGER.debug("New decoded data received: %s", decoded)
        self.async_set_updated_data(TibberPulseData(values=decoded))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    topic = entry.data[CONF_TOPIC]

    coordinator = TibberPulseDataCoordinator(hass, topic)
    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: TibberPulseDataCoordinator = hass.data[DOMAIN].pop(entry.entry_id)

    await coordinator.async_stop()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
