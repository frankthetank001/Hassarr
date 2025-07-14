# File: sensor.py
# Note: Keep this filename comment for navigation and organization

import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, SENSOR_ACTIVE_DOWNLOADS, SENSOR_QUEUE_STATUS, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hassarr sensors from config entry."""
    _LOGGER.info("Setting up Hassarr sensors")
    
    # Get the API client from the main integration
    api = hass.data[DOMAIN]["api"]
    
    # Create coordinator for periodic updates
    coordinator = HassarrDataUpdateCoordinator(hass, api)
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Create sensor entities
    entities = [
        HassarrActiveDownloadsSensor(coordinator),
        HassarrQueueStatusSensor(coordinator),
    ]
    
    async_add_entities(entities, True)
    _LOGGER.info(f"Added {len(entities)} Hassarr sensors")


class HassarrDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from Overseerr API."""

    def __init__(self, hass: HomeAssistant, api) -> None:
        """Initialize the coordinator."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self):
        """Fetch data from Overseerr API."""
        try:
            _LOGGER.debug("Fetching data from Overseerr...")
            requests_data = await self.api.get_requests()
            
            if requests_data is None:
                _LOGGER.warning("Failed to fetch data from Overseerr")
                return {
                    "overseerr_online": False,
                    "total_requests": 0,
                    "active_downloads": 0,
                    "requests": []
                }
            
            results = requests_data.get("results", [])
            
            # Count active downloads (status 3 = Processing/Downloading)
            active_downloads = len([r for r in results if r.get("media", {}).get("status") == 3])
            
            data = {
                "overseerr_online": True,
                "total_requests": len(results),
                "active_downloads": active_downloads,
                "requests": results,
                "last_update": self.hass.loop.time(),
            }
            
            _LOGGER.debug(f"Updated data: {active_downloads} active downloads, {len(results)} total requests")
            return data
            
        except Exception as err:
            _LOGGER.error(f"Error fetching data: {err}")
            raise UpdateFailed(f"Error communicating with Overseerr: {err}")


class HassarrActiveDownloadsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for active downloads count."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Active Downloads"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_ACTIVE_DOWNLOADS}"
        self._attr_icon = "mdi:download"
        self._attr_native_unit_of_measurement = "downloads"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("active_downloads", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "total_requests": self.coordinator.data.get("total_requests", 0),
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrQueueStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor for queue status overview."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Queue Status"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_QUEUE_STATUS}"
        self._attr_icon = "mdi:playlist-check"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        active = self.coordinator.data.get("active_downloads", 0)
        total = self.coordinator.data.get("total_requests", 0)
        
        if not self.coordinator.data.get("overseerr_online", False):
            return "Offline"
        elif active == 0:
            return f"Idle ({total} queued)" if total > 0 else "Empty"
        else:
            return f"{active} downloading ({total} total)"

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "active_downloads": self.coordinator.data.get("active_downloads", 0),
            "total_requests": self.coordinator.data.get("total_requests", 0),
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        } 