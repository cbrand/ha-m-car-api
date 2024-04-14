from functools import partial
from typing import Awaitable, Callable
from uuid import uuid4

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse
from m_car_api import vehicles_meters_around_location
from m_car_api.api import VehicleQuery

from custom_components.ha_m_car_api.const import (
    CONF_DEVICE_KEY,
    CONF_DISTANCE_METERS,
    CONF_ELECTRIC_ONLY,
    CONF_GAS_ONLY,
    CONF_LATITUDE,
    CONF_LOCATION,
    CONF_LONGITUDE,
    CONF_TYPE_LIMIT,
)
from custom_components.ha_m_car_api.response import format_attrs


def search_vehicles_service(hass: HomeAssistant) -> Callable[[ServiceCall], Awaitable[None]]:

    async def search_vehicles(call: ServiceCall) -> ServiceResponse:
        device_key = call.data.get(CONF_DEVICE_KEY, None)
        if not device_key:
            device_key = str(uuid4())

        latitude = call.data.get(CONF_LATITUDE, None)
        longitude = call.data.get(CONF_LONGITUDE, None)
        location = call.data.get(CONF_LOCATION, None)

        if location:
            location_state = hass.states.get(location)
            if location_state is None:
                raise ValueError("Location not found")

            latitude = location_state.attributes.get("latitude", None)
            longitude = location_state.attributes.get("longitude", None)
            if latitude is None or longitude is None:
                raise ValueError("Location does not have latitude and longitude attributes")

        if latitude is None or longitude is None:
            raise ValueError("Latitude and longitude or a location is required")

        distance_meters = call.data.get(CONF_DISTANCE_METERS, 500)
        type_limit = call.data.get(CONF_TYPE_LIMIT, None)
        query: VehicleQuery | None = None
        if type_limit is not None:
            query = VehicleQuery(
                vehicle_size_filter=type_limit,
            )

        vehicles = await hass.async_add_executor_job(
            partial(
                vehicles_meters_around_location,
                device_key=device_key,
                lat=latitude,
                lon=longitude,
                meters=distance_meters,
                query=query,
            )
        )

        gas_only = call.data.get(CONF_GAS_ONLY, False)
        electric_only = call.data.get(CONF_ELECTRIC_ONLY, False)
        if gas_only:
            vehicles = [vehicle for vehicle in vehicles if not vehicle.electric]
        elif electric_only:
            vehicles = [vehicle for vehicle in vehicles if vehicle.electric]

        return format_attrs(vehicles)

    return search_vehicles
