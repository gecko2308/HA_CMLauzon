"""Coordinateur : interroge le portail à intervalle régulier pour tous les capteurs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import CannotConnect, CMLauzonClient, InvalidAuth, Slot
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
    EVENT_NEW_AVAILABILITY,
    KIND_EMERGENCY,
    KIND_REGULAR,
)

_LOGGER = logging.getLogger(__name__)

type CMLauzonConfigEntry = ConfigEntry[CMLauzonCoordinator]


@dataclass(slots=True)
class CMLauzonData:
    """Résultat d'une interrogation du portail."""

    slots: dict[str, list[Slot]] = field(default_factory=dict)

    def get(self, kind: str) -> list[Slot]:
        return self.slots.get(kind, [])


class CMLauzonCoordinator(DataUpdateCoordinator[CMLauzonData]):
    """Récupère les disponibilités régulières et d'urgence."""

    config_entry: CMLauzonConfigEntry

    def __init__(self, hass: HomeAssistant, entry: CMLauzonConfigEntry, client: CMLauzonClient) -> None:
        minutes = entry.options.get(CONF_SCAN_INTERVAL_MIN, DEFAULT_SCAN_INTERVAL_MIN)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
        )
        self.client = client
        self._known: dict[str, set[str]] | None = None

    def _opt(self, key: str, default):
        return self.config_entry.options.get(key, default)

    @property
    def include_emergency(self) -> bool:
        return self._opt(CONF_INCLUDE_EMERGENCY, DEFAULT_INCLUDE_EMERGENCY)

    async def _async_update_data(self) -> CMLauzonData:
        tz = dt_util.get_default_time_zone()
        now = dt_util.now()
        horizon = now + timedelta(days=self._opt(CONF_DAYS_AHEAD, DEFAULT_DAYS_AHEAD))
        common = {
            "professional_id": self._opt(CONF_PROFESSIONAL_ID, DEFAULT_PROFESSIONAL_ID),
            "clinic_site_id": self._opt(CONF_CLINIC_SITE_ID, DEFAULT_CLINIC_SITE_ID),
            "start": now.date(),
            "tz": tz,
        }
        kinds = {KIND_REGULAR: self._opt(CONF_APPOINTMENT_TYPE_ID, DEFAULT_APPOINTMENT_TYPE_ID)}
        if self.include_emergency:
            kinds[KIND_EMERGENCY] = self._opt(CONF_EMERGENCY_TYPE_ID, DEFAULT_EMERGENCY_TYPE_ID)

        data = CMLauzonData()
        try:
            for kind, type_id in kinds.items():
                slots = await self.client.async_get_slots(
                    appointment_type_id=type_id, emergency=kind == KIND_EMERGENCY, **common
                )
                data.slots[kind] = [s for s in slots if now <= s.start <= horizon]
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed("Identifiants refusés par le portail CM Lauzon") from err
        except CannotConnect as err:
            raise UpdateFailed(f"Portail CM Lauzon injoignable : {err}") from err

        self._fire_new_slot_events(data)
        return data

    def _fire_new_slot_events(self, data: CMLauzonData) -> None:
        """Émet un événement pour chaque plage apparue depuis la dernière interrogation."""
        current = {kind: {s.start.isoformat() for s in slots} for kind, slots in data.slots.items()}
        if self._known is not None:
            for kind, slots in data.slots.items():
                for slot in slots:
                    if slot.start.isoformat() not in self._known.get(kind, set()):
                        self.hass.bus.async_fire(
                            EVENT_NEW_AVAILABILITY,
                            {"type": kind, "debut": slot.start.isoformat(), "duree": slot.duration},
                        )
        self._known = current
