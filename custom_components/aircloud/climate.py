from __future__ import annotations

import logging

from aircloudy import HitachiAirCloud, InteriorUnit, FanSpeed, FanSwing, CommandFailedException
from homeassistant import config_entries
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity
)

from .const import DOMAIN
from .coordinator import Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: config_entries.ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entry."""
    ac = hass.data[DOMAIN][entry.entry_id]
    coordinator = Coordinator(hass, ac)

    entities_by_id = {iu.id: HitachiAcUnit(coordinator, ac, iu) for iu in ac.interior_units}
    async_add_entities(list(entities_by_id.values()))


class HitachiAcUnit(CoordinatorEntity, ClimateEntity):
    _enable_turn_on_off_backwards_compatibility = False
    _attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.SWING_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
    )

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = None
    _attr_swing_modes = ["OFF", "VERTICAL", "HORIZONTAL", "BOTH", "AUTO"]
    _attr_fan_modes = ["AUTO", "LV1", "LV2", "LV3", "LV4", "LV5"]
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT_COOL,
        HVACMode.COOL,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.HEAT,
    ]
    _attr_target_temperature_high = 32
    _attr_target_temperature_low = 16
    _attr_target_temperature_step = 1

    _coordinator: Coordinator
    _ac: HitachiAirCloud
    _interior_unit: InteriorUnit

    def __init__(self, coordinator: Coordinator, ac: HitachiAirCloud, interior_unit: InteriorUnit) -> None:
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._ac = ac
        self._interior_unit = interior_unit
        self._interior_unit.on_changes = lambda _: self.async_write_ha_state()
        self._attr_unique_id = f"climate.{self._interior_unit.id}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=f"HVAC {self._interior_unit.name}",
            manufacturer=self._interior_unit.vendor,
            model=self._interior_unit.model_id,
            via_device=(DOMAIN, self._ac._connection_info.user_profile.email),
        )

    @property
    def available(self) -> bool:
        """Indicate if Home Assistant is able to read the state and control the underlying device."""
        return self._interior_unit.online

    @property
    def current_temperature(self) -> float | None:
        """None	The current temperature."""
        return self._interior_unit.room_temperature

    @property
    def fan_mode(self) -> str | None:
        """Required by SUPPORT_FAN_MODE	The current fan mode."""
        return self._interior_unit.fan_speed

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Required	The current operation (e.g. heat, cool, idle). Used to determine state."""
        if self._interior_unit.power == "OFF":
            return HVACMode.OFF
        match self._interior_unit.operating_mode:
            case "AUTO":
                return HVACMode.HEAT_COOL
            case "COOLING":
                return HVACMode.COOL
            case "DRY":
                return HVACMode.DRY
            case "FAN":
                return HVACMode.FAN_ONLY
            case "HEATING":
                return HVACMode.HEAT
            case _:
                raise Exception(f"Unexpected mode '{self._interior_unit.operating_mode}'")

    # @property
    # def max_temp(self)->	float:
    #     "DEFAULT_MAX_TEMP (value == 35 °C)	The maximum temperature in temperature_unit."

    # @property
    # def min_temp(self)->	float:
    #     "DEFAULT_MIN_TEMP (value == 7 °C)	The minimum temperature in temperature_unit."

    @property
    def swing_mode(self) -> str | None:
        """Required by SUPPORT_SWING_MODE	The swing setting."""
        return self._interior_unit.fan_swing

    @property
    def target_temperature(self) -> float | None:
        """The temperature currently set to be reached."""
        return self._interior_unit.requested_temperature

    @property
    def temperature_unit(self) -> str:
        """Required	The unit of temperature measurement for the system (TEMP_CELSIUS or TEMP_FAHRENHEIT)."""
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
            case HVACMode.OFF:
                await self.async_turn_off()
            case HVACMode.HEAT_COOL:
                try:
                    await self._interior_unit.send_command(mode="AUTO", power="ON")
                except CommandFailedException as e:
                    raise HomeAssistantError(f"Failed to set {self.friendly_name} mode to AUTO") from e
            case HVACMode.COOL:
                try:
                    await self._interior_unit.send_command(mode="COOLING", power="ON")
                except CommandFailedException as e:
                    raise HomeAssistantError(f"Failed to set {self.friendly_name} mode to COOLING") from e
            case HVACMode.DRY:
                try:
                    await self._interior_unit.send_command(mode="DRY", power="ON")
                except CommandFailedException as e:
                    raise HomeAssistantError(f"Failed to set {self.friendly_name} mode to DE_HUMIDIFY") from e
            case HVACMode.FAN_ONLY:
                try:
                    await self._interior_unit.send_command(mode="FAN", power="ON")
                except CommandFailedException as e:
                    raise HomeAssistantError(f"Failed to set {self.friendly_name} mode to FAN_ONLY") from e
            case HVACMode.HEAT:
                try:
                    await self._interior_unit.send_command(mode="HEATING", power="ON")
                except CommandFailedException as e:
                    raise HomeAssistantError(f"Failed to set {self.friendly_name} mode to HEAT") from e
            case _:
                raise Exception(f"Unmanaged hvac_mode {hvac_mode}")

    async def async_set_fan_mode(self, fan_mode: FanSpeed):
        """Set new target fan mode."""
        try:
            await self._interior_unit.send_command(fan_speed=fan_mode)
        except CommandFailedException as e:
            raise HomeAssistantError(f"Failed to set {self.friendly_name} fan mode to {fan_mode}") from e

    async def async_set_swing_mode(self, swing_mode: FanSwing):
        """Set new target swing operation."""
        try:
            await self._interior_unit.send_command(fan_swing=swing_mode)
        except CommandFailedException as e:
            raise HomeAssistantError(f"Failed to set {self.friendly_name} swing mode to {swing_mode}") from e

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            raise Exception(f"Temperature attr is expected in {kwargs}")
        try:
            await self._interior_unit.send_command(requested_temperature=temperature)
        except CommandFailedException as e:
            raise HomeAssistantError(f"Failed to set {self.friendly_name} temperature to {temperature}") from e

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        try:
            await self._interior_unit.send_command(power="OFF")
        except CommandFailedException as e:
            raise HomeAssistantError(f"Failed to turn off {self.friendly_name}") from e

    async def async_turn_on(self) -> None:
        """Turn the entity off."""
        try:
            await self._interior_unit.send_command(power="ON")
        except CommandFailedException as e:
            raise HomeAssistantError(f"Failed to turn on {self.friendly_name}") from e
