"""Tests d'intégration Home Assistant : assistant, entités, événement, réauthentification, options.

Lancer depuis la racine du dépôt :  python -m pytest tests -q
"""

from datetime import timedelta
from unittest.mock import patch

import pytest

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.cmlauzon import api
from custom_components.cmlauzon.const import DOMAIN


class FakePortal:
    def __init__(self):
        self.fail = False
        self.extra = False
        self.now = dt_util.now().replace(microsecond=0)

    async def auth(self, client):
        if self.fail:
            raise api.InvalidAuth

    async def slots(self, client, *, emergency, **kw):
        if self.fail:
            raise api.InvalidAuth
        now = self.now
        if emergency:
            return [api.Slot(now + timedelta(hours=3), "15 min", {})]
        out = [api.Slot(now + timedelta(days=1, hours=2), "15 min", {}), api.Slot(now + timedelta(days=60), "15 min", {})]
        if self.extra:
            out.append(api.Slot(now + timedelta(hours=20), "15 min", {}))
        return sorted(out, key=lambda s: s.start)


@pytest.fixture
def portal():
    p = FakePortal()
    with patch.object(api.CMLauzonClient, "authenticate", lambda self: p.auth(self)), patch.object(
        api.CMLauzonClient, "async_get_slots", lambda self, **kw: p.slots(self, **kw)
    ):
        yield p


async def _setup(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: " Moi@Exemple.ca ", CONF_PASSWORD: "secret"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    await hass.async_block_till_done()
    return hass.config_entries.async_entries(DOMAIN)[0]


def _entities(hass, entry):
    return {e.translation_key: e.entity_id for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)}


async def test_setup_and_entities(hass: HomeAssistant, portal) -> None:
    entry = await _setup(hass)
    assert entry.unique_id == "moi@exemple.ca"
    assert entry.state is config_entries.ConfigEntryState.LOADED
    ents = _entities(hass, entry)
    assert set(ents) == {
        "next_regular", "count_regular", "available_regular",
        "next_emergency", "count_emergency", "available_emergency",
    }
    nxt = hass.states.get(ents["next_regular"])
    assert nxt.attributes["nombre"] == 1  # la plage à +60 j dépasse l'horizon de 30 j
    assert nxt.attributes["plages"][0]["duree"] == "15 min"
    assert hass.states.get(ents["count_regular"]).state == "1"
    assert hass.states.get(ents["available_emergency"]).state == "on"
    print("\nEntités créées :", sorted(ents.values()))


async def test_invalid_credentials(hass: HomeAssistant, portal) -> None:
    portal.fail = True
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_USERNAME: "a@b.c", CONF_PASSWORD: "x"})
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "invalid_auth"}


async def test_duplicate_account(hass: HomeAssistant, portal) -> None:
    await _setup(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_USERNAME: "moi@exemple.ca", CONF_PASSWORD: "x"})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"


async def test_new_slot_event(hass: HomeAssistant, portal) -> None:
    entry = await _setup(hass)
    events = []
    hass.bus.async_listen("cmlauzon_new_availability", lambda e: events.append(e.data))
    portal.extra = True
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert len(events) == 1 and events[0]["type"] == "regular"
    assert hass.states.get(_entities(hass, entry)["count_regular"]).state == "2"


async def test_reauth_and_options(hass: HomeAssistant, portal) -> None:
    entry = await _setup(hass)
    portal.fail = True
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    flows = [f for f in hass.config_entries.flow.async_progress() if f["context"].get("source") == "reauth"]
    assert flows, "une demande de réauthentification est attendue"

    portal.fail = False
    result = await hass.config_entries.flow.async_configure(flows[0]["flow_id"], {CONF_PASSWORD: "nouveau"})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "nouveau"
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    defaults = {k.schema: k.default() for k in result["data_schema"].schema}
    defaults["include_emergency"] = False
    result = await hass.config_entries.options.async_configure(result["flow_id"], defaults)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.state is config_entries.ConfigEntryState.LOADED
    assert "emergency" not in entry.runtime_data.data.slots
