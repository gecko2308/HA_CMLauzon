"""Intégration CM Lauzon : disponibilités de rendez-vous à la Clinique médicale Lévis-Lauzon."""

from __future__ import annotations

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import CMLauzonClient
from .coordinator import CMLauzonConfigEntry, CMLauzonCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: CMLauzonConfigEntry) -> bool:
    """Configure l'intégration à partir d'une entrée de configuration."""
    # Session dédiée : son cookie jar conserve le cookie d'authentification du portail.
    session = async_create_clientsession(hass)
    client = CMLauzonClient(session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    coordinator = CMLauzonCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CMLauzonConfigEntry) -> bool:
    """Décharge l'intégration."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: CMLauzonConfigEntry) -> bool:
    """Migre les entrées de la version 1 (sans identifiant unique)."""
    if entry.version == 1:
        hass.config_entries.async_update_entry(
            entry, unique_id=entry.unique_id or entry.data[CONF_USERNAME].strip().lower(), version=2
        )
    return True


async def _async_reload_on_options(hass: HomeAssistant, entry: CMLauzonConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
