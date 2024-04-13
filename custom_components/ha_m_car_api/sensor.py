from functools import partial
import logging
from datetime import timedelta
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

import requests
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType
from m_car_api import MApi

from custom_components.ha_m_car_api.const import (
    CONF_DEVICE_KEY,
    CONF_DISTANCE_METERS,
    CONF_LOCATION,
    CONF_SCAN_INTERVAL,
    DEFAULT_CONF_DISTANCE_METERS,
    DEFAULT_CONF_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=DEFAULT_CONF_SCAN_INTERVAL)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigType,
    async_add_entities: Callable,
) -> None:
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Sensor async_setup_entry")
    if entry.options:
        config.update(entry.options)
    _LOGGER.info("Config: %s", config)
    device_key = config.get(CONF_DEVICE_KEY, None)
    if device_key is None:
        _LOGGER.error("Could not get device key from configuration for M Car API initialization")
    else:
        m_api = MApi(device_key)

        sensor = CarApiSensor(hass, m_api, config)
        async_add_entities([sensor], update_before_add=True)


class CarApiSensor(Entity):
    def __init__(self, hass: HomeAssistant, m_api: MApi, data: dict[str, Any]) -> None:
        super().__init__()
        self._api = m_api
        self._hass = hass
        self._location = data[CONF_LOCATION]
        self._distance_meters = data.get(CONF_DISTANCE_METERS, DEFAULT_CONF_DISTANCE_METERS)
        self._scan_interval = data.get(CONF_SCAN_INTERVAL, DEFAULT_CONF_SCAN_INTERVAL)
        self._name = data.get("name", f"Car API Sensor {self._location}")
        self.attrs: dict[str, Any] = {
            "location": self._location,
            "distance_meters": self._distance_meters,
        }

        self._available = True

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        location_key, location_entity = self._location.split(".", 1)
        return f"miles_cars_close_to_{location_key}_{location_entity}"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_update(self) -> None:
        try:
            # Do something
            self._available = True
            location = self._hass.states.get(self._location)
            latitude = location.attributes.get("latitude")
            longitude = location.attributes.get("longitude")
            if latitude is None or longitude is None:
                _LOGGER.error("Latitude or longitude is missing for sensor %s.", self.name)
                self._available = False
                return

            vehicles = await self.hass.async_add_executor_job(
                partial(
                    self._api.vehicles_meters_around_location,
                    lat=latitude,
                    lon=longitude,
                    meters=self._distance_meters,
                )
            )

            self._state = len(vehicles)
            self.attrs["num_electric_cars"] = len([vehicle for vehicle in vehicles if vehicle.electric])
            self.attrs["num_gas_cars"] = len([vehicle for vehicle in vehicles if not vehicle.electric])
            self.attrs.update(
                {
                    "number_car_s": 0,
                    "number_car_s_electric": 0,
                    "number_car_s_gas": 0,
                    "number_car_m": 0,
                    "number_car_m_electric": 0,
                    "number_car_m_gas": 0,
                    "number_car_l": 0,
                    "number_car_l_electric": 0,
                    "number_car_l_gas": 0,
                    "number_car_x": 0,
                    "number_car_x_electric": 0,
                    "number_car_x_gas": 0,
                    "number_car_p": 0,
                    "number_car_p_electric": 0,
                    "number_car_p_gas": 0,
                }
            )

            for vehicle in vehicles:
                car_key = f"number_car_{vehicle.size.lower()}"
                self.attrs[car_key] += 1
                if vehicle.electric:
                    car_key += "_electric"
                    self.attrs[car_key] += 1
                else:
                    car_key += "_gas"
                    self.attrs[car_key] += 1

            self.attrs["vehicles"] = [vehicle.dict() for vehicle in vehicles]

        except (ValueError, requests.ConnectionError):
            self._available = False
            _LOGGER.exception("Error retrieving data from Car API for sensor %s.", self.name)
