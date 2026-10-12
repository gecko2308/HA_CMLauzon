"""Diagnostics (identifiants masqués)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .coordinator import CMLauzonConfigEntry

TO_REDACT = {CONF_USERNAME, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: CMLauzonConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "last_update_success": coordinator.last_update_success,
        "slots": {kind: [s.as_dict() for s in slots] for kind, slots in (data.slots.items() if data else [])},
        "raw_sample": {kind: slots[0].raw for kind, slots in (data.slots.items() if data else []) if slots},
    }
