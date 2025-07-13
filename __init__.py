import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)
from .services import (
    handle_add_media, 
    handle_add_overseerr_media,
    handle_check_media_status,
    handle_remove_media,
    handle_get_active_requests,
    handle_search_media,
    handle_get_media_details
)
from .const import (
    DOMAIN, 
    SERVICE_ADD_RADARR_MOVIE, 
    SERVICE_ADD_SONARR_TV_SHOW, 
    SERVICE_ADD_OVERSEERR_MOVIE, 
    SERVICE_ADD_OVERSEERR_TV_SHOW,
    SERVICE_CHECK_MEDIA_STATUS,
    SERVICE_REMOVE_MEDIA,
    SERVICE_GET_ACTIVE_REQUESTS,
    SERVICE_SEARCH_MEDIA,
    SERVICE_GET_MEDIA_DETAILS
)

# Service schemas
ADD_RADARR_MOVIE_SCHEMA = vol.Schema({
    vol.Required("title"): cv.string,
})

ADD_SONARR_TV_SHOW_SCHEMA = vol.Schema({
    vol.Required("title"): cv.string,
})

ADD_OVERSEERR_MOVIE_SCHEMA = vol.Schema({
    vol.Required("title"): cv.string,
})

ADD_OVERSEERR_TV_SHOW_SCHEMA = vol.Schema({
    vol.Required("title"): cv.string,
})

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

async def handle_add_movie(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the service action to add a movie to Radarr."""
    await handle_add_media(hass, call, "movie", "radarr")

async def handle_add_tv_show(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the service action to add a TV show to Sonarr."""
    await handle_add_media(hass, call, "series", "sonarr")

async def handle_add_overseerr_movie(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the service action to add a movie to Overseerr."""
    await handle_add_overseerr_media(hass, call, "movie")

async def handle_add_overseerr_tv_show(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the service action to add a TV show to Overseerr."""
    await handle_add_overseerr_media(hass, call, "tv")

async def handle_check_media_status_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle checking media status with LLM-optimized response."""
    try:
        result = await handle_check_media_status(hass, call)
        # Store result in hass.data for potential use by other components
        hass.data.setdefault(f"{DOMAIN}_results", {})
        hass.data[f"{DOMAIN}_results"]["last_status_check"] = result
        _LOGGER.info(f"Media status check result: {result}")
    except Exception as e:
        _LOGGER.error(f"Error in handle_check_media_status_service: {e}")
        error_result = {
            "action": "error",
            "error": str(e),
            "message": f"Service call failed: {e}"
        }
        hass.data.setdefault(f"{DOMAIN}_results", {})
        hass.data[f"{DOMAIN}_results"]["last_status_check"] = error_result

async def handle_remove_media_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle removing media with LLM-optimized response."""
    try:
        result = await handle_remove_media(hass, call)
        hass.data.setdefault(f"{DOMAIN}_results", {})
        hass.data[f"{DOMAIN}_results"]["last_removal"] = result
        _LOGGER.info(f"Media removal result: {result}")
    except Exception as e:
        _LOGGER.error(f"Error in handle_remove_media_service: {e}")
        error_result = {
            "action": "error",
            "error": str(e),
            "message": f"Service call failed: {e}"
        }
        hass.data.setdefault(f"{DOMAIN}_results", {})
        hass.data[f"{DOMAIN}_results"]["last_removal"] = error_result

async def handle_get_active_requests_service(hass: HomeAssistant, call: ServiceCall) -> None:
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

async def handle_search_media_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle searching for media."""
    try:
        result = await handle_search_media(hass, call)
        hass.data.setdefault(f"{DOMAIN}_results", {})
        hass.data[f"{DOMAIN}_results"]["last_search"] = result
        _LOGGER.info(f"Media search result: {result}")
    except Exception as e:
        _LOGGER.error(f"Error in handle_search_media_service: {e}")
        error_result = {
            "action": "error",
            "error": str(e),
            "message": f"Service call failed: {e}"
        }
        hass.data.setdefault(f"{DOMAIN}_results", {})
        hass.data[f"{DOMAIN}_results"]["last_search"] = error_result

async def handle_get_media_details_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle getting detailed media information."""
    try:
        result = await handle_get_media_details(hass, call)
        hass.data.setdefault(f"{DOMAIN}_results", {})
        hass.data[f"{DOMAIN}_results"]["last_details"] = result
        _LOGGER.info(f"Media details result: {result}")
    except Exception as e:
        _LOGGER.error(f"Error in handle_get_media_details_service: {e}")
        error_result = {
            "action": "error",
            "error": str(e),
            "message": f"Service call failed: {e}"
        }
        hass.data.setdefault(f"{DOMAIN}_results", {})
        hass.data[f"{DOMAIN}_results"]["last_details"] = error_result

async def handle_test_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Simple test service to verify service registration is working."""
    _LOGGER.info(f"Test service called with data: {call.data}")
    hass.data.setdefault(f"{DOMAIN}_results", {})
    hass.data[f"{DOMAIN}_results"]["test_result"] = {
        "action": "test_success",
        "message": "Test service called successfully",
        "data": call.data
    }

async def handle_simple_test_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Simple test service that just logs when called."""
    _LOGGER.info("Simple test service called successfully!")
    _LOGGER.info(f"Call object: {call}")
    _LOGGER.info(f"Call data: {call.data if call else 'No data'}")
    hass.data.setdefault(f"{DOMAIN}_results", {})
    hass.data[f"{DOMAIN}_results"]["simple_test"] = "Success"

async def handle_get_active_requests_wrapper(hass: HomeAssistant, call: ServiceCall) -> None:
    """Wrapper for handle_get_active_requests_service with additional error handling."""
    _LOGGER.info("Wrapper called for get_active_requests service")
    try:
        await handle_get_active_requests_service(hass, call)
    except TypeError as e:
        if "missing 1 required positional argument: 'call'" in str(e):
            _LOGGER.error("Service called without call parameter - this indicates a registration issue")
            # Try to create a minimal call object
            from homeassistant.core import ServiceCall
            minimal_call = ServiceCall("hassarr.get_active_requests", {})
            await handle_get_active_requests_service(hass, minimal_call)
        else:
            raise
    except Exception as e:
        _LOGGER.error(f"Unexpected error in wrapper: {e}")
        raise

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Hassarr integration."""
    # Services will be registered in async_setup_entry when config entry is loaded
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Hassarr from a config entry."""
    _LOGGER.info("Setting up Hassarr integration from config entry")
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].update(config_entry.data)

    _LOGGER.info("Registering Hassarr services...")
    
    # Register test service first
    hass.services.async_register(DOMAIN, "test_service", handle_test_service, schema=vol.Schema({}))
    hass.services.async_register(DOMAIN, "simple_test", handle_simple_test_service, schema=vol.Schema({}))
    
    # Register services for legacy support
    hass.services.async_register(DOMAIN, SERVICE_ADD_RADARR_MOVIE, handle_add_movie, schema=ADD_RADARR_MOVIE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_ADD_SONARR_TV_SHOW, handle_add_tv_show, schema=ADD_SONARR_TV_SHOW_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_ADD_OVERSEERR_MOVIE, handle_add_overseerr_movie, schema=ADD_OVERSEERR_MOVIE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_ADD_OVERSEERR_TV_SHOW, handle_add_overseerr_tv_show, schema=ADD_OVERSEERR_TV_SHOW_SCHEMA)
    
    # Register new LLM-focused services
    hass.services.async_register(DOMAIN, SERVICE_CHECK_MEDIA_STATUS, handle_check_media_status_service, schema=CHECK_MEDIA_STATUS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_REMOVE_MEDIA, handle_remove_media_service, schema=REMOVE_MEDIA_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_GET_ACTIVE_REQUESTS, handle_get_active_requests_wrapper, schema=GET_ACTIVE_REQUESTS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEARCH_MEDIA, handle_search_media_service, schema=SEARCH_MEDIA_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_GET_MEDIA_DETAILS, handle_get_media_details_service, schema=GET_MEDIA_DETAILS_SCHEMA)

    # Verify service registration
    _LOGGER.info("Verifying service registration...")
    try:
        # Check if the service is registered
        service_name = f"{DOMAIN}.{SERVICE_GET_ACTIVE_REQUESTS}"
        if service_name in hass.services.async_services():
            _LOGGER.info(f"Service {service_name} is registered successfully")
        else:
            _LOGGER.error(f"Service {service_name} is NOT registered!")
    except Exception as e:
        _LOGGER.error(f"Error verifying service registration: {e}")

    _LOGGER.info("Hassarr services registered successfully")

    # Forward the config entry to sensor and binary_sensor platforms
    _LOGGER.info("Setting up sensor and binary_sensor platforms...")
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(config_entry, ["sensor", "binary_sensor"])
    )

    # Register update listener
    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    _LOGGER.info("Hassarr integration setup completed successfully")
    return True

async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    hass.data[DOMAIN] = config_entry.data