from typing import Any

from m_car_api.objects import Vehicle


def format_attrs(vehicles: list[Vehicle]) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "num_electric_cars": len([vehicle for vehicle in vehicles if vehicle.electric]),
        "num_gas_cars": len([vehicle for vehicle in vehicles if not vehicle.electric]),
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

    for vehicle in vehicles:
        car_key = f"number_car_{vehicle.size.lower()}"
        attrs[car_key] += 1
        if vehicle.electric:
            car_key += "_electric"
            attrs[car_key] += 1
        else:
            car_key += "_gas"
            attrs[car_key] += 1

    attrs["vehicles"] = [vehicle.dict() for vehicle in vehicles]
    return attrs
