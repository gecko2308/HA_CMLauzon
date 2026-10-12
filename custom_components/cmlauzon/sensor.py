"""Capteurs : prochaine plage disponible et nombre de plages."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import KIND_EMERGENCY, KIND_REGULAR, MAX_SLOTS_IN_ATTRIBUTES
from .coordinator import CMLauzonConfigEntry, CMLauzonCoordinator
from .entity import CMLauzonEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: CMLauzonConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    kinds = [KIND_REGULAR] + ([KIND_EMERGENCY] if coordinator.include_emergency else [])
    entities: list[SensorEntity] = []
    for kind in kinds:
        entities.append(NextSlotSensor(coordinator, kind))
        entities.append(SlotCountSensor(coordinator, kind))
    async_add_entities(entities)


class NextSlotSensor(CMLauzonEntity, SensorEntity):
    """Date et heure de la prochaine plage disponible."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: CMLauzonCoordinator, kind: str) -> None:
        super().__init__(coordinator, f"next_{kind}")
        self._kind = kind
        self._attr_icon = "mdi:calendar-clock" if kind == KIND_REGULAR else "mdi:calendar-alert"

    @property
    def native_value(self) -> datetime | None:
        slots = self.coordinator.data.get(self._kind)
        return slots[0].start if slots else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        slots = self.coordinator.data.get(self._kind)
        return {
            "duree": slots[0].duration if slots else None,
            "nombre": len(slots),
            "plages": [s.as_dict() for s in slots[:MAX_SLOTS_IN_ATTRIBUTES]],
        }


class SlotCountSensor(CMLauzonEntity, SensorEntity):
    """Nombre de plages disponibles dans l'horizon de recherche."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "plages"

    def __init__(self, coordinator: CMLauzonCoordinator, kind: str) -> None:
        super().__init__(coordinator, f"count_{kind}")
        self._kind = kind
        self._attr_icon = "mdi:calendar-multiple-check"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get(self._kind))
