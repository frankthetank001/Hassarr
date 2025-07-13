"""Binary sensor platform for Hassarr integration."""
import logging
from typing import Any, Dict

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    BINARY_SENSOR_OVerseerr_ONLINE,
    BINARY_SENSOR_DOWNLOADS_ACTIVE,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hassarr binary sensors from a config entry."""
    # Get coordinator from hass.data
    coordinator = hass.data.get(DOMAIN, {}).get("coordinator")
    
    if not coordinator:
        _LOGGER.warning("Coordinator not found, skipping binary sensor setup")
        return
    
    # Create binary sensors
    binary_sensors = [
        HassarrDownloadsActiveBinarySensor(coordinator),
        HassarrOverseerrOnlineBinarySensor(coordinator),
    ]
    
    async_add_entities(binary_sensors)

class HassarrDownloadsActiveBinarySensor(BinarySensorEntity):
    """Binary sensor for active downloads."""
    
    def __init__(self, coordinator):
        """Initialize the binary sensor."""
        self.coordinator = coordinator
        self._attr_name = "Downloads Active"
        self._attr_unique_id = f"{DOMAIN}_{BINARY_SENSOR_DOWNLOADS_ACTIVE}"
        self._attr_icon = "mdi:download"
        
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success
        
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
        
    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.coordinator.async_add_listener(self.async_write_ha_state)

class HassarrOverseerrOnlineBinarySensor(BinarySensorEntity):
    """Binary sensor for Overseerr online status."""
    
    def __init__(self, coordinator):
        """Initialize the binary sensor."""
        self.coordinator = coordinator
        self._attr_name = "Overseerr Online"
        self._attr_unique_id = f"{DOMAIN}_{BINARY_SENSOR_OVerseerr_ONLINE}"
        self._attr_icon = "mdi:server-network"
        
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success
        
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
            "connection_status": "connected" if self.coordinator.data.get("overseerr_online", False) else "disconnected",
        }
        
    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.coordinator.async_add_listener(self.async_write_ha_state) 