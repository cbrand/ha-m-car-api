DOMAIN = "ha_m_car_api"
CONF_DEVICE_KEY = "device_key"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_LOCATION = "location"
CONF_DISTANCE_METERS = "distance_meters"
CONF_TYPE_LIMIT = "type_limit"
CONF_ELECTRIC_ONLY = "electric_only"
CONF_GAS_ONLY = "gas_only"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"

VALID_ENTITY_TYPES = ["zone", "person", "device_tracker"]
VALID_CAR_TYPES = ["S", "M", "L", "X", "P"]

DEFAULT_CONF_SCAN_INTERVAL = 2
DEFAULT_CONF_DISTANCE_METERS = 500
DEFAULT_CONF_ELECTRIC_ONLY = False
DEFAULT_CONF_GAS_ONLY = False
DEFAULT_CONF_TYPE_LIMIT = VALID_CAR_TYPES
