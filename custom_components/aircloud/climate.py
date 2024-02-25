from __future__ import annotations

import logging

from aircloudy import HitachiAirCloud, InteriorUnit

from homeassistant import config_entries
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_EMAIL,
    CONF_PASSWORD,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import const

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entry."""
    ac = HitachiAirCloud(entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    await ac.connect()
    entities_by_id = {iu.id: HitachiAcUnit(ac, iu) for iu in ac.interior_units}
    ac.on_change = lambda changes: handle_changes(changes, entities_by_id)
    async_add_entities(list(entities_by_id.values()))


def handle_changes(
    changes: dict[int, tuple[InteriorUnit | None, InteriorUnit | None]],
    entities_by_id: dict[int, HitachiAcUnit],
) -> None:
    for id, (old, new) in changes:
        if old is None:
            _LOGGER.warning("Unit %d disapeared", id)
            pass
        elif new is None:
            _LOGGER.warning("Unit %d appeared", id)
            pass
        else:
            entities_by_id[id].handle_update(new)


class HitachiAcUnit(ClimateEntity):
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    _ac: HitachiAirCloud
    _interior_unit: InteriorUnit

    def __init__(self, ac: HitachiAirCloud, interior_unit: InteriorUnit) -> None:
        self._ac = ac
        self._interior_unit = interior_unit
        self._attr_has_entity_name = True
        self._attr_should_poll = False
        # self._attr_name = self._interior_unit.name
        self._attr_unique_id = f"climate.{self._interior_unit.id}"
        # self._attr_device_info =

    def handle_update(self, interior_unit: InteriorUnit) -> None:
        if interior_unit.id != self._interior_unit.id:
            raise Exception("Update must come from the same unit")
        self._interior_unit = interior_unit
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        return self._interior_unit.name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(const.DOMAIN, self.unique_id)},
            name=self.name,
            manufacturer=self._interior_unit.vendor,
            model=self._interior_unit.model_id,
            via_device=(const.DOMAIN, self._ac._connection_info.user_profile.email),
        )

    @property
    def available(self) -> bool:
        "Indicate if Home Assistant is able to read the state and control the underlying device."
        return self._interior_unit.online

    @property
    def current_humidity(self) -> int | None:
        "None	The current humidity."
        return None

    @property
    def current_temperature(self) -> float | None:
        "None	The current temperature."
        return self._interior_unit.room_temperature

    @property
    def fan_mode(self) -> str | None:
        "Required by SUPPORT_FAN_MODE	The current fan mode."
        return self._interior_unit.fan_speed

    @property
    def fan_modes(self) -> list[str] | None:
        "Required by SUPPORT_FAN_MODE	The list of available fan modes."
        return ["AUTO", "LV1", "LV2", "LV3", "LV4", "LV5"]

    @property
    def hvac_action(self) -> HVACAction | None:
        "None	The current HVAC action (heating, cooling)"
        return None

    @property
    def hvac_mode(self) -> HVACMode | None:
        "Required	The current operation (e.g. heat, cool, idle). Used to determine state."
        match self._interior_unit.mode:
            case "AUTO":
                return HVACMode.HEAT_COOL
            case "COOLING":
                return HVACMode.COOL
            case "DE_HUMIDIFY":
                return HVACMode.DRY
            case "FAN":
                return HVACMode.FAN_ONLY
            case "HEATING":
                return HVACMode.HEAT
            case _:
                raise Exception(f"Unexpected mode {self._interior_unit.mode}")

    @property
    def hvac_modes(self) -> list[HVACMode]:
        "Required	List of available operation modes. See below."
        return [
            HVACMode.HEAT_COOL,
            HVACMode.COOL,
            HVACMode.DRY,
            HVACMode.FAN_ONLY,
            HVACMode.HEAT,
        ]

    # @property
    # def is_aux_heat(self)->	int | None:
    #     "Required by SUPPORT_AUX_HEAT	True if an auxiliary heater is on."

    # @property
    # def max_humidity(self)->	int:
    #     "DEFAULT_MAX_HUMIDITY (value == 99)	The maximum humidity."

    # @property
    # def max_temp(self)->	float:
    #     "DEFAULT_MAX_TEMP (value == 35 °C)	The maximum temperature in temperature_unit."

    # @property
    # def min_humidity(self)->	int:
    #     "DEFAULT_MIN_HUMIDITY (value == 30)	The minimum humidity."

    # @property
    # def min_temp(self)->	float:
    #     "DEFAULT_MIN_TEMP (value == 7 °C)	The minimum temperature in temperature_unit."

    # @property
    # def precision(self)->	float:
    #     "According to temperature_unit	The precision of the temperature in the system. Defaults to tenths for TEMP_CELSIUS, whole number otherwise."
    #     return 0.1

    # @property
    # def preset_mode(self)->	str | None:
    #     "Required by SUPPORT_PRESET_MODE	The current active preset."
    #     return None

    # @property
    # def preset_modes(self)->list[str] | None:
    #     "Required by SUPPORT_PRESET_MODE	The available presets."
    #     return None

    @property
    def swing_mode(self) -> str | None:
        "Required by SUPPORT_SWING_MODE	The swing setting."
        return self._interior_unit.fan_swing

    @property
    def swing_modes(self) -> list[str] | None:
        "Required by SUPPORT_SWING_MODE	Returns the list of available swing modes."
        return ["OFF", "VERTICAL", "HORIZONTAL", "BOTH", "AUTO"]

    # @property
    # def target_humidity(self)->	int | None:
    #     "The target humidity the device is trying to reach."
    #     return None

    @property
    def target_temperature(self) -> float | None:
        "The temperature currently set to be reached."
        return self._interior_unit.requested_temperature

    @property
    def target_temperature_high(self) -> float:
        "Required by TARGET_TEMPERATURE_RANGE	The upper bound target temperature"
        return 32

    @property
    def target_temperature_low(self) -> float:
        "Required by TARGET_TEMPERATURE_RANGE	The lower bound target temperature"
        return 16

    @property
    def target_temperature_step(self) -> float:
        return 1

    @property
    def temperature_unit(self) -> str:
        "Required	The unit of temperature measurement for the system (TEMP_CELSIUS or TEMP_FAHRENHEIT)."
        match self._ac.temperature_unit:
            case "CELSIUS":
                return UnitOfTemperature.CELSIUS
            case "FAHRENHEIT":
                return UnitOfTemperature.FAHRENHEIT
            case _:
                raise Exception(
                    f"Unexpected temperature_unit {self._ac.temperature_unit}"
                )

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        match hvac_mode:
            case HVACMode.HEAT_COOL:
                await self._ac.set(self._interior_unit.id, operating_mode="AUTO")
            case HVACMode.COOL:
                await self._ac.set(self._interior_unit.id, operating_mode="COOLING")
            case HVACMode.DRY:
                await self._ac.set(self._interior_unit.id, operating_mode="DE_HUMIDIFY")
            case HVACMode.FAN_ONLY:
                await self._ac.set(self._interior_unit.id, operating_mode="FAN")
            case HVACMode.HEAT:
                await self._ac.set(self._interior_unit.id, operating_mode="HEATING")
            case _:
                raise Exception(f"Unmanaged hvac_mode {hvac_mode}")

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        await self._ac.set(self._interior_unit.id, fan_speed=fan_mode)

    async def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        await self._ac.set(self._interior_unit.id, fan_swing=swing_mode)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            raise Exception(f"Temperature attr is expected in {kwargs}")
        await self._ac.set(self._interior_unit.id, requested_temperature=temperature)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self._ac.set(self._interior_unit.id, power="OFF")

    async def async_turn_on(self) -> None:
        """Turn the entity off."""
        await self._ac.set(self._interior_unit.id, power="ON")
