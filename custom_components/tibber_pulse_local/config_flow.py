from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_TOPIC, DEFAULT_TOPIC


class TibberPulseLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        if user_input is not None:
            topic = user_input[CONF_TOPIC].strip()

            # Enkelt unikt ID pr topic for å unngå duplikater
            await self.async_set_unique_id(topic)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Tibber Pulse ({topic})",
                data={CONF_TOPIC: topic},
            )

        schema = vol.Schema(
            {vol.Required(CONF_TOPIC, default=DEFAULT_TOPIC): str}
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
