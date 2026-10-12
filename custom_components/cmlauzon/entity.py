"""Base commune des entités CM Lauzon."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PORTAL_URL
from .coordinator import CMLauzonCoordinator


class CMLauzonEntity(CoordinatorEntity[CMLauzonCoordinator]):
    """Entité rattachée à l'appareil « Clinique médicale Lévis-Lauzon »."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CMLauzonCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Clinique médicale Lévis-Lauzon",
            manufacturer="Medfar",
            model="Portail patient",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=PORTAL_URL,
        )
