from homeassistant.helpers.entity import Entity
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from .cmlauzon_api import CMLauzonClient
import logging
import aiohttp

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    session = aiohttp.ClientSession()
    client = CMLauzonClient(username, password, session)

    if not await client.authenticate():
        _LOGGER.error("Failed to authenticate with CM Lauzon")
        await session.close()
        return

    data = await client.get_availabilities()

    sensors = []
    for rdv in data.get("Availabilities", []):
        sensors.append(CMLauzonSensor(rdv))
    async_add_entities(sensors, True)

class CMLauzonSensor(Entity):
    def __init__(self, rdv):
        self._data = rdv
        self._name = f"RDV - {rdv['LocalStartDate']}"
        self._state = rdv["DurationDisplay"]

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state
