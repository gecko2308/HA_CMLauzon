"""Constantes de l'intégration CM Lauzon."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "cmlauzon"

BASE_URL: Final = "https://cmlevislauzon.portail.medfarsolutions.com"
PORTAL_URL: Final = f"{BASE_URL}/fr/p/0/"

# Options (modifiables après l'installation)
CONF_PROFESSIONAL_ID: Final = "professional_id"
CONF_CLINIC_SITE_ID: Final = "clinic_site_id"
CONF_APPOINTMENT_TYPE_ID: Final = "appointment_type_id"
CONF_EMERGENCY_TYPE_ID: Final = "emergency_type_id"
CONF_INCLUDE_EMERGENCY: Final = "include_emergency"
CONF_SCAN_INTERVAL_MIN: Final = "scan_interval_minutes"
CONF_DAYS_AHEAD: Final = "days_ahead"

# Valeurs par défaut reprises de la version 1.x
DEFAULT_PROFESSIONAL_ID: Final = "ac1e4218-72bb-594f-a031-e4fd742ce65a"
DEFAULT_CLINIC_SITE_ID: Final = "95a922d2-a721-50fe-9c50-ef48705f7374"
DEFAULT_APPOINTMENT_TYPE_ID: Final = "7be85490-a07c-5374-9b67-44a9f3cbf298"
DEFAULT_EMERGENCY_TYPE_ID: Final = "3b3a40d4-ba18-5640-a957-87eba806f607"
DEFAULT_INCLUDE_EMERGENCY: Final = True
DEFAULT_SCAN_INTERVAL_MIN: Final = 15
MIN_SCAN_INTERVAL_MIN: Final = 5
DEFAULT_DAYS_AHEAD: Final = 30

REQUEST_TIMEOUT: Final = 30
MAX_SLOTS_IN_ATTRIBUTES: Final = 20

KIND_REGULAR: Final = "regular"
KIND_EMERGENCY: Final = "emergency"

# Événement émis lorsqu'une nouvelle plage apparaît (pratique pour les notifications)
EVENT_NEW_AVAILABILITY: Final = "cmlauzon_new_availability"

DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MIN)
