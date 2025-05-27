from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import AddEntitiesCallback
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from .cmlauzon_api import CMLauzonClient
import logging
import aiohttp

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    session = hass.data[DOMAIN][entry.entry_id]["session"]
    client = CMLauzonClient(username, password, session)

    if not await client.authenticate():
        _LOGGER.error("Authentication failed for CM Lauzon")
        await session.close()
        return

    data = await client.get_availabilities()

    sensors = []
    for rdv in data.get("Availabilities", []):
        sensors.append(CMLauzonSensor(rdv))
    async_add_entities(sensors, True)

    # Ne pas fermer la session ici si elle est utilisée plus tard

class CMLauzonSensor(Entity):
    def __init__(self, rdv):
        self._rdv = rdv
        self._attr_name = f"RDV - {rdv.get('LocalStartDate', 'inconnu')}"
        self._attr_native_value = rdv.get("DurationDisplay", "N/A")

    @property
    def name(self):
        return self._attr_name

    @property
    def state(self):
        return self._attr_native_value
