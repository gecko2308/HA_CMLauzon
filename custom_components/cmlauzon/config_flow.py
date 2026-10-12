"""Assistant de configuration de CM Lauzon."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import CannotConnect, CMLauzonClient, InvalidAuth
from .const import (
    CONF_APPOINTMENT_TYPE_ID,
    CONF_CLINIC_SITE_ID,
    CONF_DAYS_AHEAD,
    CONF_EMERGENCY_TYPE_ID,
    CONF_INCLUDE_EMERGENCY,
    CONF_PROFESSIONAL_ID,
    CONF_SCAN_INTERVAL_MIN,
    DEFAULT_APPOINTMENT_TYPE_ID,
    DEFAULT_CLINIC_SITE_ID,
    DEFAULT_DAYS_AHEAD,
    DEFAULT_EMERGENCY_TYPE_ID,
    DEFAULT_INCLUDE_EMERGENCY,
    DEFAULT_PROFESSIONAL_ID,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    MIN_SCAN_INTERVAL_MIN,
)

_LOGGER = logging.getLogger(__name__)

PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password"))
CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")),
        vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
    }
)


async def _validate(hass: HomeAssistant, username: str, password: str) -> dict[str, str]:
    """Teste les identifiants. Retourne un dict d'erreurs (vide si OK)."""
    # Session éphémère propre au test d'identifiants (on ne ferme jamais une session gérée par HA).
    session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())
    try:
        await CMLauzonClient(session, username, password).authenticate()
    except InvalidAuth:
        return {"base": "invalid_auth"}
    except CannotConnect:
        return {"base": "cannot_connect"}
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Erreur inattendue lors de la validation")
        return {"base": "unknown"}
    finally:
        await session.close()
    return {}


class CMLauzonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configuration par l'interface."""

    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()
            errors = await _validate(self.hass, username, user_input[CONF_PASSWORD])
            if not errors:
                return self.async_create_entry(
                    title=f"CM Lauzon ({username})",
                    data={CONF_USERNAME: username, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(CREDENTIALS_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            errors = await _validate(self.hass, entry.data[CONF_USERNAME], user_input[CONF_PASSWORD])
            if not errors:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]})
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR}),
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return CMLauzonOptionsFlow()


class CMLauzonOptionsFlow(OptionsFlow):
    """Options : fréquence, horizon, médecin et types de rendez-vous."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        opts = self.config_entry.options
        text = TextSelector()
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL_MIN, default=opts.get(CONF_SCAN_INTERVAL_MIN, DEFAULT_SCAN_INTERVAL_MIN)): NumberSelector(
                    NumberSelectorConfig(min=MIN_SCAN_INTERVAL_MIN, max=240, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX)
                ),
                vol.Required(CONF_DAYS_AHEAD, default=opts.get(CONF_DAYS_AHEAD, DEFAULT_DAYS_AHEAD)): NumberSelector(
                    NumberSelectorConfig(min=1, max=120, step=1, unit_of_measurement="j", mode=NumberSelectorMode.BOX)
                ),
                vol.Required(CONF_INCLUDE_EMERGENCY, default=opts.get(CONF_INCLUDE_EMERGENCY, DEFAULT_INCLUDE_EMERGENCY)): bool,
                vol.Required(CONF_PROFESSIONAL_ID, default=opts.get(CONF_PROFESSIONAL_ID, DEFAULT_PROFESSIONAL_ID)): text,
                vol.Required(CONF_CLINIC_SITE_ID, default=opts.get(CONF_CLINIC_SITE_ID, DEFAULT_CLINIC_SITE_ID)): text,
                vol.Required(CONF_APPOINTMENT_TYPE_ID, default=opts.get(CONF_APPOINTMENT_TYPE_ID, DEFAULT_APPOINTMENT_TYPE_ID)): text,
                vol.Required(CONF_EMERGENCY_TYPE_ID, default=opts.get(CONF_EMERGENCY_TYPE_ID, DEFAULT_EMERGENCY_TYPE_ID)): text,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
