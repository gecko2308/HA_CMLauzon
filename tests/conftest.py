"""Fixtures communes (pytest-homeassistant-custom-component)."""

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Autorise le chargement de custom_components/cmlauzon dans chaque test."""
    yield
