import logging
from datetime import timedelta
from functools import partial
from typing import Any, Callable, Dict, Optional

import requests
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType
from m_car_api import MApi
from m_car_api.api import VehicleQuery

from custom_components.ha_m_car_api.const import (
    CONF_DEVICE_KEY,
    CONF_DISTANCE_METERS,
    CONF_ELECTRIC_ONLY,
    CONF_GAS_ONLY,
    CONF_LOCATION,
    CONF_SCAN_INTERVAL,
    CONF_TYPE_LIMIT,
    DEFAULT_CONF_DISTANCE_METERS,
    DEFAULT_CONF_ELECTRIC_ONLY,
    DEFAULT_CONF_GAS_ONLY,
    DEFAULT_CONF_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.ha_m_car_api.response import format_attrs

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

    def __init__(
        self,
        hass: HomeAssistant,
        m_api: MApi,
        data: dict[str, Any],
    ) -> None:
        super().__init__()
        self._api = m_api
        self._hass = hass
        self._location = data[CONF_LOCATION]
        self._distance_meters = data.get(CONF_DISTANCE_METERS, DEFAULT_CONF_DISTANCE_METERS)
        self._scan_interval = data.get(CONF_SCAN_INTERVAL, DEFAULT_CONF_SCAN_INTERVAL)
        self._type_limit = data.get(CONF_TYPE_LIMIT, None)
        self._type_limit = sorted(self._type_limit) if self._type_limit else None
        self._electric_only = bool(data.get(CONF_ELECTRIC_ONLY, DEFAULT_CONF_ELECTRIC_ONLY))
        self._gas_only = bool(data.get(CONF_GAS_ONLY, DEFAULT_CONF_GAS_ONLY))

        default_name = f"Miles cars close to {self._location}"
        if self._type_limit:
            default_name = f"{', '.join(self._type_limit)} {default_name}"
        if self._electric_only:
            default_name += " (electric only)"
        elif self._gas_only:
            default_name += " (gas only)"
        self._name = data.get("name", default_name)
        self._attr_icon = data.get("icon", "mdi:car-search")
        self.attrs: dict[str, Any] = {
            "location": self._location,
            "distance_meters": self._distance_meters,
            "device_key": self._api.device_key,
            "electric_only": self._electric_only,
            "gas_only": self._gas_only,
        }

        if self._type_limit:
            self.attrs["type_limit"] = self._type_limit

        self._available = True

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        location_key, location_entity = self._location.split(".", 1)
        id = f"miles_cars_close_to_{location_key}_{location_entity}"
        if self._type_limit:
            id += f"_{'_'.join(self._type_limit)}"
        if self._gas_only:
            id += "_gas"
        elif self._electric_only:
            id += "_electric"

        return id

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def state(self) -> Optional[int]:
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def _job_parameters(self) -> Dict[str, Any]:
        location = self._hass.states.get(self._location)
        latitude = location.attributes.get("latitude")
        longitude = location.attributes.get("longitude")
        if latitude is None or longitude is None:
            _LOGGER.error("Latitude or longitude is missing for sensor %s.", self.name)
            self._available = False
            return {}

        search_parameters = {
            "lat": latitude,
            "lon": longitude,
            "meters": self._distance_meters,
        }
        query: VehicleQuery | None = None

        if self._type_limit:
            query = VehicleQuery(
                vehicle_size_filter=tuple(self._type_limit),
            )
            search_parameters["query"] = query

        return search_parameters

    async def async_update(self) -> None:
        try:
            # Do something
            self._available = True

            search_parameters = self._job_parameters
            if not search_parameters:
                return

            vehicles = await self.hass.async_add_executor_job(
                partial(self._api.vehicles_meters_around_location, **search_parameters)
            )
            if self._electric_only:
                vehicles = [vehicle for vehicle in vehicles if vehicle.electric]

            if self._gas_only:
                vehicles = [vehicle for vehicle in vehicles if not vehicle.electric]

            self._state = len(vehicles)
            self.attrs.update(format_attrs(vehicles))

        except (ValueError, requests.ConnectionError):
            self._available = False
            _LOGGER.exception("Error retrieving data from Car API for sensor %s.", self.name)
