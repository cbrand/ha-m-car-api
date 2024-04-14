import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode

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
    DEFAULT_CONF_TYPE_LIMIT,
    DOMAIN,
    VALID_CAR_TYPES,
    VALID_ENTITY_TYPES,
)

M_CAR_API_DATA_SCHEMA = vol.Schema({vol.Required("")})

_LOGGER = logging.getLogger(__name__)


async def validate_device_key(device_key: str | None) -> str:
    if not device_key:
        device_key = str(uuid4())
    return device_key


async def _validate_location(hass: HomeAssistant, location: str) -> str:
    if not any(location.startswith(f"{entity_type}.") for entity_type in VALID_ENTITY_TYPES):
        raise vol.Invalid("location_invalid")
    location_check = hass.states.get(location)
    if location_check is None:
        raise vol.Invalid("location_not_found")
    return location_check.name


async def _get_valid_locations(hass: HomeAssistant) -> List[str]:
    locations = []
    for entity_type in VALID_ENTITY_TYPES:
        locations.extend(hass.states.async_entity_ids(entity_type))

    locations = sorted(locations, key=_location_sort_key)
    return locations


def _location_sort_key(location: str) -> Tuple[int, str]:
    entity_type, entity_id = location.split(".", 1)
    return VALID_ENTITY_TYPES.index(entity_type), entity_id


def get_unique_id(location: str, data: dict[str, Any]) -> str:
    location = location.replace(".", "_")

    unique_id = f"miles_tracker_{location}"
    if type_limit := data.get(CONF_TYPE_LIMIT, DEFAULT_CONF_TYPE_LIMIT):
        unique_id += f"_{'_'.join(sorted(type_limit))}"

    if data.get(CONF_ELECTRIC_ONLY, DEFAULT_CONF_ELECTRIC_ONLY):
        unique_id += "_electric"
    elif data.get(CONF_GAS_ONLY, DEFAULT_CONF_GAS_ONLY):
        unique_id += "_gas"
    return unique_id


def get_title_of(location_entry: str, data: dict[str, Any]) -> str:
    title = f"M Car API Tracker {location_entry}"
    type_limit = data[CONF_TYPE_LIMIT]
    if type_limit:
        title += f" ({', '.join(type_limit)})"
    if data[CONF_ELECTRIC_ONLY]:
        title += " (Electric)"
    elif data[CONF_GAS_ONLY]:
        title += " (Gas)"

    return title


class OptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        return await self.async_step_menu(user_input)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        return await self.async_step_menu(user_input)

    async def async_step_menu(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        def __get_option(key: str, default: Any) -> Any:
            result = self.config_entry.options.get(key, self.config_entry.data.get(key, default))
            return result

        errors = {}
        if user_input is not None:
            user_input[CONF_DEVICE_KEY] = await validate_device_key(__get_option(CONF_DEVICE_KEY, None))
            user_input[CONF_SCAN_INTERVAL] = __get_option(CONF_SCAN_INTERVAL, DEFAULT_CONF_SCAN_INTERVAL)

            location = __get_option(CONF_LOCATION, "")
            try:
                location = await _validate_location(self.hass, location)
                items = location.split(".", 1)
                location_entry = items[-1]
            except vol.Invalid as error:
                errors[CONF_LOCATION] = error.error_message

            if len(errors) == 0:
                return self.async_create_entry(
                    title=get_title_of(location_entry, user_input),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOCATION, default=__get_option(CONF_LOCATION, None)): SelectSelector(
                        SelectSelectorConfig(
                            options=await _get_valid_locations(self.hass), mode=SelectSelectorMode.DROPDOWN
                        ),
                    ),
                    vol.Required(
                        CONF_DISTANCE_METERS, default=__get_option(CONF_DISTANCE_METERS, DEFAULT_CONF_DISTANCE_METERS)
                    ): cv.positive_int,
                    vol.Required(CONF_DEVICE_KEY, default=__get_option(CONF_DEVICE_KEY, None)): cv.string,
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=__get_option(CONF_SCAN_INTERVAL, DEFAULT_CONF_SCAN_INTERVAL)
                    ): cv.positive_int,
                }
            ),
            errors=errors,
        )


class MCarAPIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}
        if user_input is not None:
            user_input[CONF_DEVICE_KEY] = await validate_device_key(user_input.get(CONF_DEVICE_KEY, None))
            location = user_input.get(CONF_LOCATION, "")
            unique_id = ""
            location_entry = ""
            try:
                location = await _validate_location(self.hass, location)
                items = location.split(".", 1)
                location_entry = items[-1]
                unique_id = get_unique_id(location, user_input)
            except vol.Invalid as error:
                errors[CONF_LOCATION] = error.error_message

            if len(errors) == 0:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                _LOGGER.debug("Initialized new new m car api tracker with ID: {unique_id}")
                return self.async_create_entry(
                    title=get_title_of(location_entry, user_input),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOCATION): SelectSelector(
                        SelectSelectorConfig(
                            options=await _get_valid_locations(self.hass), mode=SelectSelectorMode.DROPDOWN
                        ),
                    ),
                    vol.Required(CONF_DISTANCE_METERS, default=DEFAULT_CONF_DISTANCE_METERS): cv.positive_int,
                    vol.Optional(CONF_DEVICE_KEY): cv.string,
                    vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_CONF_SCAN_INTERVAL): cv.positive_int,
                    vol.Required(CONF_TYPE_LIMIT, default=DEFAULT_CONF_TYPE_LIMIT): cv.multi_select(VALID_CAR_TYPES),
                    vol.Required(CONF_ELECTRIC_ONLY, default=DEFAULT_CONF_ELECTRIC_ONLY): cv.boolean,
                    vol.Required(CONF_GAS_ONLY, default=DEFAULT_CONF_GAS_ONLY): cv.boolean,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)
