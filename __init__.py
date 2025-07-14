import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from datetime import timedelta
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)
from .services import (
    OverseerrAPI,
    handle_get_active_requests,
    # Comment out imports for functions we commented out
    # handle_check_media_status,
    # handle_remove_media,
    # handle_search_media,
    # handle_get_media_details
)
from .const import (
    DOMAIN, 
    UPDATE_INTERVAL,
    SERVICE_CHECK_MEDIA_STATUS,
    SERVICE_REMOVE_MEDIA,
    SERVICE_GET_ACTIVE_REQUESTS,
    SERVICE_SEARCH_MEDIA,
    SERVICE_GET_MEDIA_DETAILS
)

# Service schemas
CHECK_MEDIA_STATUS_SCHEMA = vol.Schema({
    vol.Required("title"): cv.string,
})

REMOVE_MEDIA_SCHEMA = vol.Schema({
    vol.Required("media_id"): cv.string,
})

GET_ACTIVE_REQUESTS_SCHEMA = vol.Schema({})

SEARCH_MEDIA_SCHEMA = vol.Schema({
    vol.Required("query"): cv.string,
})

GET_MEDIA_DETAILS_SCHEMA = vol.Schema({
    vol.Required("media_type"): cv.string,
    vol.Required("tmdb_id"): cv.string,
})

async def _async_update_data(hass: HomeAssistant) -> dict:
    """Update data via the Overseerr API."""
    api = hass.data[DOMAIN].get("api")
    if not api:
        raise UpdateFailed("API client not initialized")

    try:
        requests_data = await api.get_requests()
        if not requests_data:
            return {
                "active_downloads": 0,
                "total_requests": 0,
                "processing_requests": [],
                "overseerr_online": False,
                "last_update": dt_util.utcnow().isoformat()
            }
        
        all_requests = requests_data.get("results", [])
        processing_requests = [
            req for req in all_requests 
            if req.get("media", {}).get("status") == 3 and req.get("media", {}).get("downloadStatus")
        ]
        
        return {
            "active_downloads": len(processing_requests),
            "total_requests": len(all_requests),
            "processing_requests": processing_requests,
            "overseerr_online": True,
            "last_update": dt_util.utcnow().isoformat()
        }
    except Exception as err:
        _LOGGER.error("Error communicating with API: %s", err)
        raise UpdateFailed(f"Error communicating with API: {err}")

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Hassarr integration."""
    # Services will be registered in async_setup_entry when config entry is loaded
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Hassarr from a config entry."""
    _LOGGER.info("Setting up Hassarr integration from config entry")
    
    hass.data.setdefault(DOMAIN, {})
    
    # Create a single aiohttp.ClientSession for the integration
    session = async_get_clientsession(hass)
    
    # Initialize API client
    api = OverseerrAPI(config_entry.data.get("overseerr_url"), config_entry.data.get("overseerr_api_key"), session)
    
    # Create DataUpdateCoordinator
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_coordinator",
        update_method=lambda: _async_update_data(hass),
        update_interval=timedelta(seconds=UPDATE_INTERVAL),
    )
    
    # Store instances in hass.data
    hass.data[DOMAIN] = {
        "api": api,
        "coordinator": coordinator,
        **config_entry.data
    }

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    _LOGGER.info("Registering Hassarr services...")

    # Comment out unused service handlers for now
    # async def handle_check_media_status_service(call: ServiceCall) -> None:
    #     """Handle checking media status with LLM-optimized response."""
    #     try:
    #         result = await handle_check_media_status(hass, call)
    #         # Store result in hass.data for potential use by other components
    #         hass.data.setdefault(f"{DOMAIN}_results", {})
    #         hass.data[f"{DOMAIN}_results"]["last_status_check"] = result
    #         _LOGGER.info(f"Media status check result: {result}")
    #     except Exception as e:
    #         _LOGGER.error(f"Error in handle_check_media_status_service: {e}")
    #         error_result = {
    #             "action": "error",
    #             "error": str(e),
    #             "message": f"Service call failed: {e}"
    #         }
    #         hass.data.setdefault(f"{DOMAIN}_results", {})
    #         hass.data[f"{DOMAIN}_results"]["last_status_check"] = error_result

    # async def handle_remove_media_service(call: ServiceCall) -> None:
    #     """Handle removing media with LLM-optimized response."""
    #     try:
    #         result = await handle_remove_media(hass, call)
    #         hass.data.setdefault(f"{DOMAIN}_results", {})
    #         hass.data[f"{DOMAIN}_results"]["last_removal"] = result
    #         _LOGGER.info(f"Media removal result: {result}")
    #     except Exception as e:
    #         _LOGGER.error(f"Error in handle_remove_media_service: {e}")
    #         error_result = {
    #             "action": "error",
    #             "error": str(e),
    #             "message": f"Service call failed: {e}"
    #         }
    #         hass.data.setdefault(f"{DOMAIN}_results", {})
    #         hass.data[f"{DOMAIN}_results"]["last_removal"] = error_result

    async def handle_get_active_requests_service(call: ServiceCall) -> None:
        """Handle getting active requests with LLM-optimized response."""
        _LOGGER.info(f"handle_get_active_requests_service called with call: {call}")
        _LOGGER.info(f"Call data: {call.data if call else 'No call data'}")
        _LOGGER.info(f"Call type: {type(call) if call else 'No call'}")
        
        try:
            if not call:
                _LOGGER.error("Service called without call parameter")
                error_result = {
                    "action": "error",
                    "error": "Service called without call parameter",
                    "message": "Service call failed: Missing call parameter"
                }
                hass.data.setdefault(f"{DOMAIN}_results", {})
                hass.data[f"{DOMAIN}_results"]["last_requests"] = error_result
                return
                
            result = await handle_get_active_requests(hass, call)
            hass.data.setdefault(f"{DOMAIN}_results", {})
            hass.data[f"{DOMAIN}_results"]["last_requests"] = result
            _LOGGER.info(f"Active requests result: {result}")
        except Exception as e:
            _LOGGER.error(f"Error in handle_get_active_requests_service: {e}")
            _LOGGER.error(f"Exception type: {type(e)}")
            import traceback
            _LOGGER.error(f"Traceback: {traceback.format_exc()}")
            # Store error result
            error_result = {
                "action": "error",
                "error": str(e),
                "message": f"Service call failed: {e}"
            }
            hass.data.setdefault(f"{DOMAIN}_results", {})
            hass.data[f"{DOMAIN}_results"]["last_requests"] = error_result

    # async def handle_search_media_service(call: ServiceCall) -> None:
    #     """Handle searching for media."""
    #     try:
    #         result = await handle_search_media(hass, call)
    #         hass.data.setdefault(f"{DOMAIN}_results", {})
    #         hass.data[f"{DOMAIN}_results"]["last_search"] = result
    #         _LOGGER.info(f"Media search result: {result}")
    #     except Exception as e:
    #         _LOGGER.error(f"Error in handle_search_media_service: {e}")
    #         error_result = {
    #             "action": "error",
    #             "error": str(e),
    #             "message": f"Service call failed: {e}"
    #         }
    #         hass.data.setdefault(f"{DOMAIN}_results", {})
    #         hass.data[f"{DOMAIN}_results"]["last_search"] = error_result

    # async def handle_get_media_details_service(call: ServiceCall) -> None:
    #     """Handle getting detailed media information."""
    #     try:
    #         result = await handle_get_media_details(hass, call)
    #         hass.data.setdefault(f"{DOMAIN}_results", {})
    #         hass.data[f"{DOMAIN}_results"]["last_details"] = result
    #         _LOGGER.info(f"Media details result: {result}")
    #     except Exception as e:
    #         _LOGGER.error(f"Error in handle_get_media_details_service: {e}")
    #         error_result = {
    #             "action": "error",
    #             "error": str(e),
    #             "message": f"Service call failed: {e}"
    #         }
    #         hass.data.setdefault(f"{DOMAIN}_results", {})
    #         hass.data[f"{DOMAIN}_results"]["last_details"] = error_result

    async def handle_test_service(call: ServiceCall) -> None:
        """Simple test service to verify service registration is working."""
        _LOGGER.info(f"Test service called with data: {call.data}")
        hass.data.setdefault(f"{DOMAIN}_results", {})
        hass.data[f"{DOMAIN}_results"]["test_result"] = {
            "action": "test_success",
            "message": "Test service called successfully",
            "data": call.data
        }

    async def handle_simple_test_service(call: ServiceCall) -> None:
        """Simple test service that just logs when called."""
        _LOGGER.info("Simple test service called successfully!")
        _LOGGER.info(f"Call object: {call}")
        _LOGGER.info(f"Call data: {call.data if call else 'No data'}")
        hass.data.setdefault(f"{DOMAIN}_results", {})
        hass.data[f"{DOMAIN}_results"]["simple_test"] = "Success"
    
    # Register test service first (for debugging)
    hass.services.async_register(DOMAIN, "test_service", handle_test_service, schema=vol.Schema({}))
    hass.services.async_register(DOMAIN, "simple_test", handle_simple_test_service, schema=vol.Schema({}))
    
    # Register ONLY the get_active_requests service for testing
    hass.services.async_register(DOMAIN, SERVICE_GET_ACTIVE_REQUESTS, handle_get_active_requests_service, schema=GET_ACTIVE_REQUESTS_SCHEMA)
    
    # Comment out other services until we get the first one working
    # hass.services.async_register(DOMAIN, SERVICE_CHECK_MEDIA_STATUS, handle_check_media_status_service, schema=CHECK_MEDIA_STATUS_SCHEMA)
    # hass.services.async_register(DOMAIN, SERVICE_REMOVE_MEDIA, handle_remove_media_service, schema=REMOVE_MEDIA_SCHEMA)
    # hass.services.async_register(DOMAIN, SERVICE_SEARCH_MEDIA, handle_search_media_service, schema=SEARCH_MEDIA_SCHEMA)
    # hass.services.async_register(DOMAIN, SERVICE_GET_MEDIA_DETAILS, handle_get_media_details_service, schema=GET_MEDIA_DETAILS_SCHEMA)

    # Verify service registration
    _LOGGER.info("Verifying service registration...")
    try:
        # Check if the service is registered
        service_name = f"{DOMAIN}.{SERVICE_GET_ACTIVE_REQUESTS}"
        if hass.services.has_service(DOMAIN, SERVICE_GET_ACTIVE_REQUESTS):
            _LOGGER.info(f"Service {service_name} is registered successfully")
        else:
            _LOGGER.error(f"Service {service_name} is NOT registered!")
    except Exception as e:
        _LOGGER.error(f"Error verifying service registration: {e}")

    _LOGGER.info("Hassarr services registered successfully")

    # Forward the config entry to sensor and binary_sensor platforms
    _LOGGER.info("Setting up sensor and binary_sensor platforms...")
    await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor", "binary_sensor"])

    # Register update listener
    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    _LOGGER.info("Hassarr integration setup completed successfully")
    return True

async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)