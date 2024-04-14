"""Test component setup."""

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.ha_m_car_api.const import DOMAIN


async def test_async_setup(hass: HomeAssistant) -> None:
    """Test the component gets setup."""
    assert await async_setup_component(hass, DOMAIN, {}) is True
