"""Capteurs binaires : « au moins une plage disponible » (pratique pour les automatisations)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import KIND_EMERGENCY, KIND_REGULAR
from .coordinator import CMLauzonConfigEntry, CMLauzonCoordinator
from .entity import CMLauzonEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: CMLauzonConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    kinds = [KIND_REGULAR] + ([KIND_EMERGENCY] if coordinator.include_emergency else [])
    async_add_entities(AvailableBinarySensor(coordinator, kind) for kind in kinds)


class AvailableBinarySensor(CMLauzonEntity, BinarySensorEntity):
    """Vrai dès qu'une plage est disponible."""

    def __init__(self, coordinator: CMLauzonCoordinator, kind: str) -> None:
        super().__init__(coordinator, f"available_{kind}")
        self._kind = kind
        self._attr_icon = "mdi:calendar-check" if kind == KIND_REGULAR else "mdi:hospital-box"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get(self._kind))
