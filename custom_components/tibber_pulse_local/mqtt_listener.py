from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.components import mqtt

from .decoder import decode_tibber_pulse_message

_LOGGER = logging.getLogger(__name__)


class TibberPulseMQTTListener:
    def __init__(
        self,
        hass: HomeAssistant,
        topic: str,
        on_message: Callable[[dict[str, Any]], None],
    ) -> None:
        self.hass = hass
        self.topic = topic
        self._on_message = on_message
        self._remove = None

    async def start(self) -> None:
        if self._remove is not None:
            return

        async def _message_received(msg: mqtt.ReceiveMessage) -> None:
            _LOGGER.debug("MQTT payload received on %s (%d bytes)", msg.topic, len(msg.payload))

            try:
                decoded = decode_tibber_pulse_message(msg.payload)
            except Exception:
                _LOGGER.exception("Decode failed for payload on %s", msg.topic)
                return

            self._on_message(decoded)

        # encoding=None gir rå bytes
        self._remove = await mqtt.async_subscribe(
            self.hass,
            self.topic,
            _message_received,
            encoding=None,
        )
        _LOGGER.debug("Subscribed to topic %s", self.topic)

    def stop(self) -> None:
        if self._remove:
            self._remove()
            self._remove = None
            _LOGGER.debug("Unsubscribed from topic %s", self.topic)
