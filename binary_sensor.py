"""Binary sensor platform for Hassarr integration."""
import logging
from typing import Any, Dict

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    BINARY_SENSOR_OVERSEERR_ONLINE,
    BINARY_SENSOR_DOWNLOADS_ACTIVE,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hassarr binary sensors from a config entry."""
    coordinator = hass.data[DOMAIN].get("coordinator")
    
    if not coordinator:
        _LOGGER.warning("Coordinator not found, skipping binary sensor setup")
        return
    
    # Create binary sensors
    binary_sensors = [
        HassarrDownloadsActiveBinarySensor(coordinator),
        HassarrOverseerrOnlineBinarySensor(coordinator),
    ]
    
    async_add_entities(binary_sensors)

class HassarrDownloadsActiveBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for active downloads."""
    
    def __init__(self, coordinator):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_name = "Downloads Active"
        self._attr_unique_id = f"{DOMAIN}_{BINARY_SENSOR_DOWNLOADS_ACTIVE}"
        self._attr_icon = "mdi:download"
        
    @property
    def is_on(self) -> bool:
        """Return True if downloads are active."""
        if self.coordinator.data:
            return self.coordinator.data.get("active_downloads", 0) > 0
        return False
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        if not self.coordinator.data:
            return {}
            
        return {
            "active_downloads": self.coordinator.data.get("active_downloads", 0),
            "total_requests": self.coordinator.data.get("total_requests", 0),
            "last_update": self.coordinator.data.get("last_update"),
        }

class HassarrOverseerrOnlineBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for Overseerr online status."""
    
    def __init__(self, coordinator):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_name = "Overseerr Online"
        self._attr_unique_id = f"{DOMAIN}_{BINARY_SENSOR_OVERSEERR_ONLINE}"
        self._attr_icon = "mdi:server-network"
        
    @property
    def is_on(self) -> bool:
        """Return True if Overseerr is online."""
        if self.coordinator.data:
            return self.coordinator.data.get("overseerr_online", False)
        return False
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        if not self.coordinator.data:
            return {}
            
        return {
            "last_update": self.coordinator.data.get("last_update"),
            "connection_status": "connected" if self.is_on else "disconnected",
        } 