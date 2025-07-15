# File: llm_api.py
# Note: Keep this filename comment for navigation and organization

import logging
import voluptuous as vol
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.util.json import JsonObjectType
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .services import LLMResponseBuilder

_LOGGER = logging.getLogger(__name__)

class HassarrAddMediaTool(llm.Tool):
    """Tool to add media to Overseerr."""
    
    name = "HassarrAddMedia"
    description = "Add a movie or TV show to Overseerr for download. Automatically detects whether it's a movie or TV show."
    
    parameters = vol.Schema({
        vol.Required("title"): str,
    })
    
    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> JsonObjectType:
        """Add media to Overseerr."""
        try:
            title = tool_input.tool_args["title"]
            _LOGGER.info(f"HassarrAddMedia called by LLM: {title}")
            
            # Get the API from stored data
            if DOMAIN not in hass.data:
                raise HomeAssistantError("Hassarr integration not loaded")
            
            api = hass.data[DOMAIN]["api"]
            
            # Search for the media
            search_data = await api.search_media(title)
            if not search_data:
                error_details = api.last_error or "Failed to connect to Overseerr"
                return LLMResponseBuilder.build_add_media_response("connection_error", title, error_details=error_details)
            
            results = search_data.get("results", [])
            if not results:
                return LLMResponseBuilder.build_add_media_response("not_found", title)
            
            first_result = results[0]
            media_type = first_result.get("mediaType", "movie")
            tmdb_id = first_result.get("id")
            
            # Check if already exists
            if first_result.get("mediaInfo"):
                try:
                    media_details = await api.get_media_details(media_type, tmdb_id)
                except Exception:
                    media_details = None
                
                return LLMResponseBuilder.build_add_media_response(
                    "media_already_exists",
                    title=title,
                    search_result=first_result,
                    media_details=media_details
                )
            
            # Add to Overseerr
            overseerr_user_id = hass.data[DOMAIN].get("overseerr_user_id")
            add_result = await api.add_media_request(media_type, tmdb_id, overseerr_user_id)
            
            if add_result:
                try:
                    media_details = await api.get_media_details(media_type, tmdb_id)
                except Exception:
                    media_details = None
                
                return LLMResponseBuilder.build_add_media_response(
                    "media_added_successfully",
                    title=title,
                    search_result=first_result,
                    media_details=media_details,
                    add_result=add_result
                )
            else:
                return LLMResponseBuilder.build_add_media_response("media_add_failed", title)
            
        except Exception as e:
            _LOGGER.error(f"Error in HassarrAddMedia: {e}")
            raise HomeAssistantError(f"Failed to add media: {e}")


class HassarrCheckStatusTool(llm.Tool):
    """Tool to check media status in Overseerr."""
    
    name = "HassarrCheckStatus"
    description = "Check the status of a movie or TV show in Overseerr including download progress, who requested it, and detailed information."
    
    parameters = vol.Schema({
        vol.Required("title"): str,
    })
    
    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> JsonObjectType:
        """Check media status."""
        try:
            title = tool_input.tool_args["title"]
            _LOGGER.info(f"HassarrCheckStatus called by LLM: {title}")
            
            if DOMAIN not in hass.data:
                raise HomeAssistantError("Hassarr integration not loaded")
            
            api = hass.data[DOMAIN]["api"]
            
            # Search for the media
            search_data = await api.search_media(title)
            if not search_data:
                error_details = api.last_error or "Failed to connect to Overseerr"
                return LLMResponseBuilder.build_status_response("connection_error", title, error_details=error_details)
            
            results = search_data.get("results", [])
            if not results:
                return LLMResponseBuilder.build_status_response("not_found", title)
            
            first_result = results[0]
            
            # Get additional details
            try:
                media_type = first_result.get("mediaType", "movie")
                tmdb_id = first_result.get("id")
                media_details = await api.get_media_details(media_type, tmdb_id) if tmdb_id else None
            except Exception:
                media_details = None
            
            # Get requests data for context
            try:
                requests_data = await api.get_requests()
            except Exception:
                requests_data = None
            
            return LLMResponseBuilder.build_status_response(
                "found_media",
                title=title,
                search_result=first_result,
                media_details=media_details,
                requests_data=requests_data
            )
            
        except Exception as e:
            _LOGGER.error(f"Error in HassarrCheckStatus: {e}")
            raise HomeAssistantError(f"Failed to check status: {e}")


class HassarrSearchMediaTool(llm.Tool):
    """Tool to search for movies and TV shows."""
    
    name = "HassarrSearchMedia"
    description = "Search for movies and TV shows with detailed results including ratings, overviews, and library status."
    
    parameters = vol.Schema({
        vol.Required("query"): str,
    })
    
    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> JsonObjectType:
        """Search for media."""
        try:
            query = tool_input.tool_args["query"]
            _LOGGER.info(f"HassarrSearchMedia called by LLM: {query}")
            
            if DOMAIN not in hass.data:
                raise HomeAssistantError("Hassarr integration not loaded")
            
            api = hass.data[DOMAIN]["api"]
            
            search_data = await api.search_media(query)
            if not search_data:
                error_details = api.last_error or "Failed to connect to Overseerr"
                return LLMResponseBuilder.build_search_response("connection_error", query, error_details=error_details)
            
            results = search_data.get("results", [])
            if not results:
                return LLMResponseBuilder.build_search_response("no_results", query)
            
            return LLMResponseBuilder.build_search_response("search_results", query, search_data)
            
        except Exception as e:
            _LOGGER.error(f"Error in HassarrSearchMedia: {e}")
            raise HomeAssistantError(f"Failed to search media: {e}")


class HassarrGetActiveDownloadsTool(llm.Tool):
    """Tool to get currently active downloads and requests."""
    
    name = "HassarrGetActiveDownloads"
    description = "Get information about currently active downloads and pending requests, prioritizing items that are actively downloading."
    
    parameters = vol.Schema({})
    
    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> JsonObjectType:
        """Get active downloads."""
        try:
            _LOGGER.info("HassarrGetActiveDownloads called by LLM")
            
            if DOMAIN not in hass.data:
                raise HomeAssistantError("Hassarr integration not loaded")
            
            api = hass.data[DOMAIN]["api"]
            
            requests_data = await api.get_requests()
            if requests_data is None:
                return await LLMResponseBuilder.build_active_requests_response(
                    "connection_error",
                    error_details="Failed to connect to Overseerr"
                )
            
            if not requests_data.get("results"):
                return await LLMResponseBuilder.build_active_requests_response(
                    "no_requests",
                    requests_data=requests_data
                )
            
            return await LLMResponseBuilder.build_active_requests_response(
                "requests_found",
                requests_data=requests_data,
                api=api
            )
            
        except Exception as e:
            _LOGGER.error(f"Error in HassarrGetActiveDownloads: {e}")
            raise HomeAssistantError(f"Failed to get active downloads: {e}")


class HassarrTestConnectionTool(llm.Tool):
    """Tool to test Overseerr connection and get system status."""
    
    name = "HassarrTestConnection"
    description = "Test connection to Overseerr server and get basic system information including total requests count."
    
    parameters = vol.Schema({})
    
    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> JsonObjectType:
        """Test connection."""
        try:
            _LOGGER.info("HassarrTestConnection called by LLM")
            
            if DOMAIN not in hass.data:
                raise HomeAssistantError("Hassarr integration not loaded")
            
            api = hass.data[DOMAIN]["api"]
            
            requests_data = await api.get_requests()
            if requests_data:
                return {
                    "status": "success",
                    "message": f"Connected to Overseerr successfully. Found {len(requests_data.get('results', []))} requests.",
                    "total_requests": len(requests_data.get('results', [])),
                    "overseerr_online": True
                }
            else:
                return {
                    "status": "failed",
                    "message": "Failed to connect to Overseerr",
                    "total_requests": 0,
                    "overseerr_online": False,
                    "error_details": api.last_error
                }
            
        except Exception as e:
            _LOGGER.error(f"Error in HassarrTestConnection: {e}")
            raise HomeAssistantError(f"Failed to test connection: {e}")


class HassarrAPI(llm.API):
    """Hassarr API for LLM interactions."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the Hassarr API."""
        super().__init__(
            hass=hass,
            id=f"{DOMAIN}_llm_api",
            name="Hassarr Media Manager"
        )
    
    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        """Return the API instance."""
        return llm.APIInstance(
            api=self,
            api_prompt="Use these tools to manage media in Overseerr. You can add movies/TV shows, check their status, search for content, and monitor download progress. Always provide helpful context about what you found or what actions were taken.",
            llm_context=llm_context,
            tools=[
                HassarrAddMediaTool(),
                HassarrCheckStatusTool(),
                HassarrSearchMediaTool(),
                HassarrGetActiveDownloadsTool(),
                HassarrTestConnectionTool(),
            ],
        )


async def async_setup_llm_api(hass: HomeAssistant, config_entry) -> None:
    """Set up the LLM API for Hassarr."""
    _LOGGER.info("Setting up Hassarr LLM API")
    
    api = HassarrAPI(hass)
    
    # Register the API with Home Assistant
    unregister_api = llm.async_register_api(hass, api)
    
    # Store the unregister function to call when unloading
    hass.data[DOMAIN]["unregister_llm_api"] = unregister_api
    
    # Ensure it gets unregistered when the config entry is unloaded
    config_entry.async_on_unload(unregister_api)
    
    _LOGGER.info("Hassarr LLM API registered successfully")


async def async_unload_llm_api(hass: HomeAssistant) -> None:
    """Unload the LLM API for Hassarr."""
    if DOMAIN in hass.data and "unregister_llm_api" in hass.data[DOMAIN]:
        unregister_api = hass.data[DOMAIN].pop("unregister_llm_api")
        unregister_api()
        _LOGGER.info("Hassarr LLM API unregistered") 