# File: llm_api.py
# Home Assistant LLM API implementation for Hassarr

import logging
import voluptuous as vol
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.util.json import JsonObjectType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class HassarrAddMediaTool(llm.Tool):
    """Tool to add media to Overseerr."""
    
    name = "hassarr_add_media"
    description = "Add a movie or TV show to Overseerr for download. Automatically detects whether it's a movie or TV show."
    
    parameters = vol.Schema({
        vol.Required("title", description="The title of the movie or TV show to add"): str,
    })
    
    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> JsonObjectType:
        """Add media to Overseerr."""
        try:
            title = tool_input.tool_args["title"]
            _LOGGER.info(f"LLM Tool: Adding media '{title}'")
            
            # Call the service directly
            result = await hass.services.async_call(
                DOMAIN,
                "add_media",
                {"title": title},
                blocking=True,
                return_response=True,
                context=llm_context.context
            )
            
            return result.get("response", {})
            
        except Exception as e:
            _LOGGER.error(f"Error in HassarrAddMedia tool: {e}")
            return {
                "action": "error",
                "message": f"Failed to add media: {str(e)}"
            }


class HassarrCheckStatusTool(llm.Tool):
    """Tool to check media status in Overseerr."""
    
    name = "hassarr_check_status"
    description = "Check the status of a movie or TV show in Overseerr including download progress, who requested it, and detailed information."
    
    parameters = vol.Schema({
        vol.Required("title", description="The title of the movie or TV show to check"): str,
    })
    
    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> JsonObjectType:
        """Check media status."""
        try:
            title = tool_input.tool_args["title"]
            _LOGGER.info(f"LLM Tool: Checking status for '{title}'")
            
            result = await hass.services.async_call(
                DOMAIN,
                "check_media_status",
                {"title": title},
                blocking=True,
                return_response=True,
                context=llm_context.context
            )
            
            return result.get("response", {})
            
        except Exception as e:
            _LOGGER.error(f"Error in HassarrCheckStatus tool: {e}")
            return {
                "action": "error",
                "message": f"Failed to check status: {str(e)}"
            }


class HassarrSearchMediaTool(llm.Tool):
    """Tool to search for movies and TV shows."""
    
    name = "hassarr_search_media"
    description = "Search for movies and TV shows with detailed results including ratings, overviews, and library status."
    
    parameters = vol.Schema({
        vol.Required("query", description="Search query for movies or TV shows"): str,
    })
    
    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> JsonObjectType:
        """Search for media."""
        try:
            query = tool_input.tool_args["query"]
            _LOGGER.info(f"LLM Tool: Searching for '{query}'")
            
            result = await hass.services.async_call(
                DOMAIN,
                "search_media",
                {"query": query},
                blocking=True,
                return_response=True,
                context=llm_context.context
            )
            
            return result.get("response", {})
            
        except Exception as e:
            _LOGGER.error(f"Error in HassarrSearchMedia tool: {e}")
            return {
                "action": "error",
                "message": f"Failed to search media: {str(e)}"
            }


class HassarrGetActiveDownloadsTool(llm.Tool):
    """Tool to get currently active downloads and requests."""
    
    name = "hassarr_get_active_downloads"
    description = "Get information about currently active downloads and pending requests, prioritizing items that are actively downloading."
    
    parameters = vol.Schema({})
    
    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> JsonObjectType:
        """Get active downloads."""
        try:
            _LOGGER.info("LLM Tool: Getting active downloads")
            
            result = await hass.services.async_call(
                DOMAIN,
                "get_active_requests",
                {},
                blocking=True,
                return_response=True,
                context=llm_context.context
            )
            
            return result.get("response", {})
            
        except Exception as e:
            _LOGGER.error(f"Error in HassarrGetActiveDownloads tool: {e}")
            return {
                "action": "error",
                "message": f"Failed to get active downloads: {str(e)}"
            }


class HassarrAPI(llm.API):
    """Hassarr API for LLM integration."""
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the API."""
        super().__init__(
            hass=hass,
            id=f"hassarr-{entry.entry_id}",
            name="Hassarr Media Management"
        )
        self.entry = entry
    
    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        """Return the instance of the API."""
        return llm.APIInstance(
            api=self,
            api_prompt="Use these tools to manage your media library through Overseerr. You can add movies and TV shows, check their status, search for content, and get active downloads.",
            llm_context=llm_context,
            tools=[
                HassarrAddMediaTool(),
                HassarrCheckStatusTool(),
                HassarrSearchMediaTool(),
                HassarrGetActiveDownloadsTool(),
            ]
        )


async def async_setup_llm_api(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Set up the LLM API for Hassarr."""
    _LOGGER.info("Setting up Hassarr LLM API...")
    
    try:
        # Create and register the API
        api = HassarrAPI(hass, config_entry)
        unregister_func = llm.async_register_api(hass, api)
        
        # Store unregister function for cleanup
        hass.data[DOMAIN]["unregister_llm_api"] = unregister_func
        config_entry.async_on_unload(unregister_func)
        
        _LOGGER.info(f"Successfully registered Hassarr LLM API: {api.name}")
        
    except Exception as e:
        _LOGGER.error(f"Failed to setup LLM API: {e}")
        raise


async def async_unload_llm_api(hass: HomeAssistant) -> None:
    """Unload the LLM API for Hassarr."""
    if DOMAIN in hass.data and "unregister_llm_api" in hass.data[DOMAIN]:
        unregister_func = hass.data[DOMAIN].pop("unregister_llm_api")
        unregister_func()
        _LOGGER.info("Hassarr LLM API unregistered")