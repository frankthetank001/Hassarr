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

from .services import OverseerrAPI, LLMResponseBuilder
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
    
    # Set up sensor platform
    await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor"])
    
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

    async def handle_check_media_status_service(call: ServiceCall) -> dict:
        """Check media status with LLM-optimized response."""
        try:
            title = call.data.get("title", "").strip()
            
            if not title:
                result = LLMResponseBuilder.build_status_response("missing_title")
                hass.data[DOMAIN]["last_status_check"] = result
                return result
            
            _LOGGER.info(f"Checking media status for: {title}")
            api = hass.data[DOMAIN]["api"]
            
            # Search for the media
            search_data = await api.search_media(title)
            if not search_data:
                result = LLMResponseBuilder.build_status_response("connection_error", title)
                hass.data[DOMAIN]["last_status_check"] = result
                return result
            
            # Check if any results found
            results = search_data.get("results", [])
            if not results:
                result = LLMResponseBuilder.build_status_response("not_found", title)
                hass.data[DOMAIN]["last_status_check"] = result
                return result
            
            # Get the first result (most relevant)
            first_result = results[0]
            
            # Get additional media details
            media_details = None
            try:
                media_type = first_result.get("mediaType", "movie")
                tmdb_id = first_result.get("id")
                if tmdb_id:
                    media_details = await api.get_media_details(media_type, tmdb_id)
            except Exception as e:
                _LOGGER.warning(f"Failed to get media details: {e}")
            
            # Get current requests to check status
            requests_data = None
            try:
                requests_data = await api.get_requests()
            except Exception as e:
                _LOGGER.warning(f"Failed to get requests data: {e}")
            
            # Build structured LLM response
            result = LLMResponseBuilder.build_status_response(
                "found_media",
                title=title,
                search_result=first_result,
                media_details=media_details,
                requests_data=requests_data
            )
            
            hass.data[DOMAIN]["last_status_check"] = result
            _LOGGER.info(f"Media status check completed for '{title}': {result['action']}")
            return result
            
        except Exception as e:
            _LOGGER.error(f"Error checking media status: {e}")
            result = LLMResponseBuilder.build_status_response("connection_error", title)
            hass.data[DOMAIN]["last_status_check"] = result
            return result

    # Register the test service
    hass.services.async_register(
        DOMAIN, 
        "test_connection", 
        handle_test_connection_service, 
        schema=vol.Schema({}),
        supports_response=True
    )
    
    # Register the check media status service
    hass.services.async_register(
        DOMAIN, 
        "check_media_status", 
        handle_check_media_status_service, 
        schema=vol.Schema({
            vol.Required("title"): str,
        }),
        supports_response=True
    )
    
    _LOGGER.info("Hassarr services registered successfully (test_connection, check_media_status)")
    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, ["sensor"])
    
    # Remove services
    hass.services.async_remove(DOMAIN, "test_connection")
    hass.services.async_remove(DOMAIN, "check_media_status")
    
    # Clean up data
    if unload_ok:
        hass.data.pop(DOMAIN, None)
    
    return unload_ok

async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)