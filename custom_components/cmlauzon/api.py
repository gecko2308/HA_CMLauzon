"""Client asynchrone pour le portail Medfar de la Clinique médicale Lévis-Lauzon."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, tzinfo
import logging
from typing import Any

import aiohttp

from .const import BASE_URL, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)

AUTH_COOKIE = "mp-auth"


class CMLauzonError(Exception):
    """Erreur générique du portail."""


class CannotConnect(CMLauzonError):
    """Le portail est injoignable ou a répondu de façon inattendue."""


class InvalidAuth(CMLauzonError):
    """Identifiants refusés par le portail."""


@dataclass(frozen=True, slots=True)
class Slot:
    """Une plage de rendez-vous disponible."""

    start: datetime
    duration: str | None
    raw: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"debut": self.start.isoformat(), "duree": self.duration}


class CMLauzonClient:
    """Accès au portail : authentification par cookie puis recherche de disponibilités."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        self._authenticated = False

    async def authenticate(self) -> None:
        """Ouvre une session. Lève InvalidAuth ou CannotConnect."""
        payload = {
            "UseTokenCookie": "True",
            "RememberMe": "True",
            "Continue": "/fr/p/0/",
            "UserName": self._username,
            "Password": self._password,
        }
        try:
            async with self._session.post(
                f"{BASE_URL}/auth/credentials", data=payload, timeout=self._timeout, allow_redirects=False
            ) as resp:
                if resp.status in (401, 403):
                    raise InvalidAuth
                if resp.status >= 500:
                    raise CannotConnect(f"HTTP {resp.status}")
                await resp.read()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CannotConnect(str(err)) from err

        # Le cookie est conservé dans le cookie jar de la session.
        if not any(c.key == AUTH_COOKIE for c in self._session.cookie_jar):
            raise InvalidAuth
        self._authenticated = True
        _LOGGER.debug("Session ouverte sur le portail CM Lauzon")

    async def async_get_slots(
        self,
        *,
        appointment_type_id: str,
        professional_id: str,
        clinic_site_id: str,
        emergency: bool,
        start: date,
        tz: tzinfo,
    ) -> list[Slot]:
        """Retourne les plages disponibles, triées par date. Se reconnecte une fois si la session a expiré."""
        params = {
            "appointmentTypeId": appointment_type_id,
            "professionalId": professional_id,
            "clinicSiteId": clinic_site_id,
            "isEmergency": "true" if emergency else "false",
            "startDate": start.isoformat(),
        }
        if not self._authenticated:
            await self.authenticate()
        data = await self._search(params)
        if data is None:  # session expirée
            self._authenticated = False
            await self.authenticate()
            data = await self._search(params)
            if data is None:
                raise InvalidAuth
        return parse_slots(data, tz)

    async def _search(self, params: dict[str, str]) -> dict[str, Any] | None:
        try:
            async with self._session.get(
                f"{BASE_URL}/fr/p/0/availability/search",
                params=params,
                timeout=self._timeout,
                allow_redirects=False,
                headers={"Accept": "application/json"},
            ) as resp:
                if resp.status in (401, 403) or 300 <= resp.status < 400:
                    return None
                if resp.status != 200:
                    raise CannotConnect(f"HTTP {resp.status}")
                if "json" not in (resp.content_type or ""):
                    # Le portail renvoie la page de connexion en HTML quand la session n'est plus valide.
                    return None
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise CannotConnect(str(err)) from err


def _parse_dt(value: Any, tz: tzinfo) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    # Format .NET « /Date(1716900000000) »
    if text.startswith("/Date("):
        try:
            ms = int(text[6:].split(")")[0].split("+")[0].split("-")[0])
            return datetime.fromtimestamp(ms / 1000, tz)
        except ValueError:
            return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=tz)


def parse_slots(data: dict[str, Any] | None, tz: tzinfo) -> list[Slot]:
    """Convertit la réponse du portail en plages triées. Tolérant aux variations de format."""
    if not isinstance(data, dict):
        return []
    items = data.get("Availabilities") or data.get("availabilities") or []
    slots: list[Slot] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        start = None
        for key in ("StartDate", "UtcStartDate", "LocalStartDate", "startDate", "localStartDate"):
            start = _parse_dt(item.get(key), tz)
            if start:
                break
        if start is None:
            _LOGGER.debug("Plage ignorée, date illisible : %s", item)
            continue
        duration = item.get("DurationDisplay") or item.get("durationDisplay")
        slots.append(Slot(start=start, duration=duration, raw=item))
    slots.sort(key=lambda s: s.start)
    return slots
