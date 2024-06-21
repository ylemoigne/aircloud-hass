import logging
from datetime import timedelta

from aircloudy import HitachiAirCloud
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

_LOGGER = logging.getLogger(__name__)

class Coordinator(DataUpdateCoordinator):
    aircloud: HitachiAirCloud

    def __init__(self, hass: HomeAssistant, aircloud: HitachiAirCloud):
        super().__init__(
            hass,
            _LOGGER,
            name="Aircloud",
            update_interval=timedelta(seconds=30),
        )
        self.aircloud = aircloud

    async def _async_update_data(self):
        # try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            # async with async_timeout.timeout(10):
                return await self.aircloud.update_all()
        # except ApiAuthError as err:
        #     # Raising ConfigEntryAuthFailed will cancel future updates
        #     # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        #     raise ConfigEntryAuthFailed from err
        # except ApiError as err:
        #     raise UpdateFailed(f"Error communicating with API: {err}")
