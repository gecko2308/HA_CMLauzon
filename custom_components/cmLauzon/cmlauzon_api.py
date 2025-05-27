import aiohttp
import logging

_LOGGER = logging.getLogger(__name__)

class CMLauzonClient:
    def __init__(self, username, password, session: aiohttp.ClientSession):
        self.session = session
        self.username = username
        self.password = password
        self.base_url = "https://cmlevislauzon.portail.medfarsolutions.com"
        self.cookies = None

    async def authenticate(self) -> bool:
        _LOGGER.debug("Authenticating with CM Lauzon as %s", self.username)
        url = f"{self.base_url}/auth/credentials"
        payload = {
            "UseTokenCookie": "True",
            "RememberMe": "False",
            "Continue": "/fr/p/0/",
            "UserName": self.username,
            "Password": self.password
        }

        async with self.session.post(url, data=payload) as response:
            if response.status != 200:
                _LOGGER.error("Authentication failed, status code %s", response.status)
                return False

            self.cookies = response.cookies
            if "mp-auth" in self.cookies:
                _LOGGER.debug("Authentication successful")
                return True
            else:
                _LOGGER.warning("No mp-auth cookie received")
                return False

    async def get_availabilities(self, emergency=False):
        _LOGGER.debug("Fetching appointments (emergency=%s)", emergency)
        url = f"{self.base_url}/fr/p/0/availability/search"
        params = {
            "appointmentTypeId": "3b3a40d4-ba18-5640-a957-87eba806f607" if emergency else "7be85490-a07c-5374-9b67-44a9f3cbf298",
            "professionalId": "ac1e4218-72bb-594f-a031-e4fd742ce65a",
            "clinicSiteId": "95a
