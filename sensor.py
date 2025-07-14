"""Sensor platform for Hassarr integration."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    SENSOR_ACTIVE_DOWNLOADS,
    SENSOR_MEDIA_STATUS,
    SENSOR_QUEUE_STATUS,
    SENSOR_SEARCH_RESULTS,
    UPDATE_INTERVAL,
    STATUS_UPDATE_INTERVAL,
)
from .services import OverseerrAPI

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hassarr sensors from a config entry."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    
    # Create sensors
    sensors = [
        HassarrActiveDownloadsSensor(coordinator),
        HassarrQueueStatusSensor(coordinator),
        HassarrOverseerrOnlineSensor(coordinator),
    ]
    
    async_add_entities(sensors)

class HassarrActiveDownloadsSensor(SensorEntity):
    """Sensor for active downloads count."""
    
    def __init__(self, coordinator: DataUpdateCoordinator):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_name = "Active Downloads"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_ACTIVE_DOWNLOADS}"
        self._attr_native_unit_of_measurement = "downloads"
        self._attr_icon = "mdi:download-multiple"
        
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success
        
    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("active_downloads", 0)
        return 0
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        if not self.coordinator.data:
            return {}
            
        processing_requests = self.coordinator.data.get("processing_requests", [])
        attributes = {
            "total_requests": self.coordinator.data.get("total_requests", 0),
            "last_update": self.coordinator.data.get("last_update"),
        }
        
        # Add download details
        if processing_requests:
            download_details = []
            for req in processing_requests[:5]:  # Limit to first 5
                media = req.get("media", {})
                downloads = media.get("downloadStatus", [])
                if downloads:
                    download_info = {
                        "title": media.get("title", "Unknown"),
                        "type": req.get("type", "unknown"),
                        "downloads": len(downloads),
                        "progress": []
                    }
                    
                    for download in downloads[:3]:  # Limit to first 3 downloads
                        progress = round(((download.get("size", 0) - download.get("sizeLeft", 0)) / download.get("size", 1)) * 100, 1) if download.get("size", 0) > 0 else 0
                        download_info["progress"].append({
                            "title": download.get("title", "Unknown"),
                            "progress_percent": progress,
                            "time_left": download.get("timeLeft", "Unknown"),
                            "size_gb": round(download.get("size", 0) / 1024 / 1024 / 1024, 2)
                        })
                    
                    download_details.append(download_info)
            
            attributes["download_details"] = download_details
            
        return attributes
        
    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.coordinator.async_add_listener(self.async_write_ha_state)

class HassarrQueueStatusSensor(SensorEntity):
    """Sensor for queue status."""
    
    def __init__(self, coordinator: DataUpdateCoordinator):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_name = "Download Queue Status"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_QUEUE_STATUS}"
        self._attr_icon = "mdi:playlist-play"
        
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success
        
    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return "Unknown"
            
        active_downloads = self.coordinator.data.get("active_downloads", 0)
        total_requests = self.coordinator.data.get("total_requests", 0)
        
        if active_downloads > 0:
            return f"{active_downloads} active, {total_requests} total"
        elif total_requests > 0:
            return f"{total_requests} pending"
        else:
            return "Empty"
            
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        if not self.coordinator.data:
            return {}
            
        return {
            "active_downloads": self.coordinator.data.get("active_downloads", 0),
            "total_requests": self.coordinator.data.get("total_requests", 0),
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }

class HassarrOverseerrOnlineSensor(SensorEntity):
    """Sensor for Overseerr connection status."""
    
    def __init__(self, coordinator: DataUpdateCoordinator):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_name = "Overseerr Online"
        self._attr_unique_id = f"{DOMAIN}_overseerr_online"
        self._attr_icon = "mdi:server-network"
        
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success
        
    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return "Unknown"
            
        return "Online" if self.coordinator.data.get("overseerr_online", False) else "Offline"
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        if not self.coordinator.data:
            return {}
            
        return {
            "last_update": self.coordinator.data.get("last_update"),
            "connection_status": "connected" if self.coordinator.data.get("overseerr_online", False) else "disconnected",
        } 