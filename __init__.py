# File: __init__.py
# Note: Keep this filename comment for navigation and organization

import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

from .services import OverseerrAPI
from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Hassarr integration."""
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Hassarr from a config entry."""
    _LOGGER.info("Setting up Hassarr integration from config entry")
    
    hass.data.setdefault(DOMAIN, {})
    
    # Store config data (like the old version)
    hass.data[DOMAIN] = config_entry.data.copy()
    
    # Create a simple API client for Overseerr
    session = async_get_clientsession(hass)
    api = OverseerrAPI(
        config_entry.data.get("overseerr_url", ""), 
        config_entry.data.get("overseerr_api_key", ""), 
        session
    )
    hass.data[DOMAIN]["api"] = api
    
    _LOGGER.info("Registering basic test service...")
    
    async def handle_test_connection_service(call: ServiceCall) -> dict:
        """Test the Overseerr connection."""
        try:
            _LOGGER.info("Testing Overseerr connection...")
            api = hass.data[DOMAIN]["api"]
            requests_data = await api.get_requests()
            
            if requests_data:
                result = {
                    "status": "success",
                    "message": f"Connected to Overseerr successfully. Found {len(requests_data.get('results', []))} requests.",
                    "total_requests": len(requests_data.get('results', []))
                }
                _LOGGER.info(f"Connection test successful: {result}")
            else:
                result = {
                    "status": "failed",
                    "message": "Failed to connect to Overseerr",
                    "total_requests": 0
                }
                _LOGGER.error(f"Connection test failed: {result}")
                
            # Store result for inspection
            hass.data[DOMAIN]["last_test_result"] = result
            
            # Return the result for response_variable support
            return result
            
        except Exception as e:
            _LOGGER.error(f"Error testing connection: {e}")
            result = {
                "status": "error",
                "message": f"Error: {e}",
                "total_requests": 0
            }
            hass.data[DOMAIN]["last_test_result"] = result
            return result

    # Register the test service
    hass.services.async_register(
        DOMAIN, 
        "test_connection", 
        handle_test_connection_service, 
        schema=vol.Schema({}),
        supports_response=True
    )
    
    _LOGGER.info("Hassarr test service registered successfully")
    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Remove services
    hass.services.async_remove(DOMAIN, "test_connection")
    
    # Clean up data
    hass.data.pop(DOMAIN, None)
    
    return True

async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)