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
    result = await handle_check_media_status(hass, call)
    # Store result in hass.data for potential use by other components
    hass.data.setdefault(f"{DOMAIN}_results", {})
    hass.data[f"{DOMAIN}_results"]["last_status_check"] = result
    _LOGGER.info(f"Media status check result: {result}")

async def handle_remove_media_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle removing media with LLM-optimized response."""
    result = await handle_remove_media(hass, call)
    hass.data.setdefault(f"{DOMAIN}_results", {})
    hass.data[f"{DOMAIN}_results"]["last_removal"] = result
    _LOGGER.info(f"Media removal result: {result}")

async def handle_get_active_requests_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle getting active requests with LLM-optimized response."""
    result = await handle_get_active_requests(hass, call)
    hass.data.setdefault(f"{DOMAIN}_results", {})
    hass.data[f"{DOMAIN}_results"]["last_requests"] = result
    _LOGGER.info(f"Active requests result: {result}")

async def handle_search_media_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle searching for media."""
    result = await handle_search_media(hass, call)
    hass.data.setdefault(f"{DOMAIN}_results", {})
    hass.data[f"{DOMAIN}_results"]["last_search"] = result
    _LOGGER.info(f"Media search result: {result}")

async def handle_get_media_details_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle getting detailed media information."""
    result = await handle_get_media_details(hass, call)
    hass.data.setdefault(f"{DOMAIN}_results", {})
    hass.data[f"{DOMAIN}_results"]["last_details"] = result
    _LOGGER.info(f"Media details result: {result}")



async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Hassarr from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].update(config_entry.data)

    # Register legacy services
    hass.services.async_register(DOMAIN, SERVICE_ADD_RADARR_MOVIE, handle_add_movie, schema=ADD_RADARR_MOVIE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_ADD_SONARR_TV_SHOW, handle_add_tv_show, schema=ADD_SONARR_TV_SHOW_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_ADD_OVERSEERR_MOVIE, handle_add_overseerr_movie, schema=ADD_OVERSEERR_MOVIE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_ADD_OVERSEERR_TV_SHOW, handle_add_overseerr_tv_show, schema=ADD_OVERSEERR_TV_SHOW_SCHEMA)
    
    # Register new LLM-focused services
    hass.services.async_register(DOMAIN, SERVICE_CHECK_MEDIA_STATUS, handle_check_media_status_service, schema=CHECK_MEDIA_STATUS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_REMOVE_MEDIA, handle_remove_media_service, schema=REMOVE_MEDIA_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_GET_ACTIVE_REQUESTS, handle_get_active_requests_service, schema=GET_ACTIVE_REQUESTS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEARCH_MEDIA, handle_search_media_service, schema=SEARCH_MEDIA_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_GET_MEDIA_DETAILS, handle_get_media_details_service, schema=GET_MEDIA_DETAILS_SCHEMA)

    # Forward the config entry to sensor and binary_sensor platforms
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(config_entry, ["sensor", "binary_sensor"])
    )

    # Register update listener
    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    return True

async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    hass.data[DOMAIN] = config_entry.data