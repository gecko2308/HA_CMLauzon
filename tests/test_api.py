"""Tests du client contre un faux portail local (aucun accès réseau externe).

Lancer : python -m pytest tests -q   (ou : python tests/test_api.py)
"""

import asyncio
from datetime import date, timezone, timedelta
import importlib.util
import pathlib
import sys

import aiohttp
from aiohttp import web
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "cmlauzon"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"cmlauzon.{name}", ROOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# const + api n'importent rien de Home Assistant : on les charge seuls.
pkg = type(sys)("cmlauzon"); pkg.__path__ = [str(ROOT)]; sys.modules["cmlauzon"] = pkg
const = _load("const")
api = _load("api")

TZ = timezone(timedelta(hours=-4))
GOOD = ("moi@exemple.ca", "bon-mdp")


def make_app(state):
    async def auth(req):
        form = await req.post()
        if (form.get("UserName"), form.get("Password")) != GOOD:
            return web.Response(status=401)
        resp = web.Response(text="ok")
        resp.set_cookie("mp-auth", "jeton")
        state["logins"] += 1
        return resp

    async def search(req):
        if req.cookies.get("mp-auth") != "jeton" or state.pop("expire_once", False):
            return web.Response(text="<html>connexion</html>", content_type="text/html")
        state["last_params"] = dict(req.query)
        return web.json_response({
            "Count": 3,
            "Availabilities": [
                {"LocalStartDate": "2026-10-15T14:30:00", "DurationDisplay": "15 min"},
                {"StartDate": "2026-10-14T13:00:00Z", "DurationDisplay": "15 min"},
                {"LocalStartDate": "pas une date"},
            ],
        })

    app = web.Application()
    app.router.add_post("/auth/credentials", auth)
    app.router.add_get("/fr/p/0/availability/search", search)
    return app


async def run():
    state = {"logins": 0}
    runner = web.AppRunner(make_app(state)); await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0); await site.start()
    port = site._server.sockets[0].getsockname()[1]
    api.BASE_URL = f"http://127.0.0.1:{port}"

    args = dict(appointment_type_id="T", professional_id="P", clinic_site_id="C", emergency=False, start=date(2026, 10, 12), tz=TZ)
    try:
        # 1. Mauvais mot de passe -> InvalidAuth
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as s:
            try:
                await api.CMLauzonClient(s, "moi@exemple.ca", "faux").authenticate()
                raise AssertionError("InvalidAuth attendu")
            except api.InvalidAuth:
                pass

        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as s:
            c = api.CMLauzonClient(s, *GOOD)
            # 2. Connexion implicite + tri + date illisible ignorée + fuseau appliqué aux dates naïves
            slots = await c.async_get_slots(**args)
            assert [x.start.isoformat() for x in slots] == ["2026-10-14T13:00:00+00:00", "2026-10-15T14:30:00-04:00"], slots
            assert state["last_params"]["startDate"] == "2026-10-12" and state["last_params"]["isEmergency"] == "false"
            assert state["logins"] == 1
            # 3. Session expirée (page HTML) -> reconnexion automatique, une seule fois
            state["expire_once"] = True
            slots = await c.async_get_slots(**args)
            assert len(slots) == 2 and state["logins"] == 2

        # 4. Portail injoignable -> CannotConnect
        api.BASE_URL = "http://127.0.0.1:1"
        async with aiohttp.ClientSession() as s:
            try:
                await api.CMLauzonClient(s, *GOOD).authenticate()
                raise AssertionError("CannotConnect attendu")
            except api.CannotConnect:
                pass

        # 5. Formats tolérés
        assert api.parse_slots(None, TZ) == []
        assert api.parse_slots({"availabilities": [{"startDate": "/Date(1791820800000)/"}]}, TZ)[0].start.year == 2026
    finally:
        await runner.cleanup()
    print("TOUS LES TESTS PASSENT")


@pytest.mark.enable_socket
async def test_api(socket_enabled):
    await run()


if __name__ == "__main__":
    asyncio.run(run())
