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

def handle_add_movie(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the service action to add a movie to Radarr."""
    handle_add_media(hass, call, "movie", "radarr")

def handle_add_tv_show(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the service action to add a TV show to Sonarr."""
    handle_add_media(hass, call, "series", "sonarr")

def handle_add_overseerr_movie(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the service action to add a movie to Overseerr."""
    handle_add_overseerr_media(hass, call, "movie")

def handle_add_overseerr_tv_show(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the service action to add a TV show to Overseerr."""
    handle_add_overseerr_media(hass, call, "tv")

def handle_check_media_status_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle checking media status with LLM-optimized response."""
    result = handle_check_media_status(hass, call)
    # Store result in hass.data for potential use by other components
    hass.data.setdefault(f"{DOMAIN}_results", {})
    hass.data[f"{DOMAIN}_results"]["last_status_check"] = result
    _LOGGER.info(f"Media status check result: {result}")

def handle_remove_media_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle removing media with LLM-optimized response."""
    result = handle_remove_media(hass, call)
    hass.data.setdefault(f"{DOMAIN}_results", {})
    hass.data[f"{DOMAIN}_results"]["last_removal"] = result
    _LOGGER.info(f"Media removal result: {result}")

def handle_get_active_requests_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle getting active requests with LLM-optimized response."""
    result = handle_get_active_requests(hass, call)
    hass.data.setdefault(f"{DOMAIN}_results", {})
    hass.data[f"{DOMAIN}_results"]["last_requests"] = result
    _LOGGER.info(f"Active requests result: {result}")

def handle_search_media_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle searching for media."""
    result = handle_search_media(hass, call)
    hass.data.setdefault(f"{DOMAIN}_results", {})
    hass.data[f"{DOMAIN}_results"]["last_search"] = result
    _LOGGER.info(f"Media search result: {result}")

def handle_get_media_details_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle getting detailed media information."""
    result = handle_get_media_details(hass, call)
    hass.data.setdefault(f"{DOMAIN}_results", {})
    hass.data[f"{DOMAIN}_results"]["last_details"] = result
    _LOGGER.info(f"Media details result: {result}")

def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Hassarr integration."""
    # Register legacy services
    hass.services.register(DOMAIN, SERVICE_ADD_RADARR_MOVIE, lambda call: handle_add_movie(hass, call), schema=ADD_RADARR_MOVIE_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_ADD_SONARR_TV_SHOW, lambda call: handle_add_tv_show(hass, call), schema=ADD_SONARR_TV_SHOW_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_ADD_OVERSEERR_MOVIE, lambda call: handle_add_overseerr_movie(hass, call), schema=ADD_OVERSEERR_MOVIE_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_ADD_OVERSEERR_TV_SHOW, lambda call: handle_add_overseerr_tv_show(hass, call), schema=ADD_OVERSEERR_TV_SHOW_SCHEMA)
    
    # Register new LLM-focused services
    hass.services.register(DOMAIN, SERVICE_CHECK_MEDIA_STATUS, lambda call: handle_check_media_status_service(hass, call), schema=CHECK_MEDIA_STATUS_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_REMOVE_MEDIA, lambda call: handle_remove_media_service(hass, call), schema=REMOVE_MEDIA_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_GET_ACTIVE_REQUESTS, lambda call: handle_get_active_requests_service(hass, call), schema=GET_ACTIVE_REQUESTS_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_SEARCH_MEDIA, lambda call: handle_search_media_service(hass, call), schema=SEARCH_MEDIA_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_GET_MEDIA_DETAILS, lambda call: handle_get_media_details_service(hass, call), schema=GET_MEDIA_DETAILS_SCHEMA)

    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Hassarr from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].update(config_entry.data)

    # Register legacy services
    hass.services.async_register(DOMAIN, SERVICE_ADD_RADARR_MOVIE, lambda call: handle_add_movie(hass, call), schema=ADD_RADARR_MOVIE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_ADD_SONARR_TV_SHOW, lambda call: handle_add_tv_show(hass, call), schema=ADD_SONARR_TV_SHOW_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_ADD_OVERSEERR_MOVIE, lambda call: handle_add_overseerr_movie(hass, call), schema=ADD_OVERSEERR_MOVIE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_ADD_OVERSEERR_TV_SHOW, lambda call: handle_add_overseerr_tv_show(hass, call), schema=ADD_OVERSEERR_TV_SHOW_SCHEMA)
    
    # Register new LLM-focused services
    hass.services.async_register(DOMAIN, SERVICE_CHECK_MEDIA_STATUS, lambda call: handle_check_media_status_service(hass, call), schema=CHECK_MEDIA_STATUS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_REMOVE_MEDIA, lambda call: handle_remove_media_service(hass, call), schema=REMOVE_MEDIA_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_GET_ACTIVE_REQUESTS, lambda call: handle_get_active_requests_service(hass, call), schema=GET_ACTIVE_REQUESTS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEARCH_MEDIA, lambda call: handle_search_media_service(hass, call), schema=SEARCH_MEDIA_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_GET_MEDIA_DETAILS, lambda call: handle_get_media_details_service(hass, call), schema=GET_MEDIA_DETAILS_SCHEMA)

    # Forward the config entry to sensor and binary_sensor platforms
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "binary_sensor")
    )

    # Register update listener
    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    return True

async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    hass.data[DOMAIN] = config_entry.data