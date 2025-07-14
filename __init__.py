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
                result = LLMResponseBuilder.build_status_response("connection_error", title, error_details="Failed to get response from Overseerr search API")
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
            result = LLMResponseBuilder.build_status_response("connection_error", title, error_details=str(e))
            hass.data[DOMAIN]["last_status_check"] = result
            return result

    async def handle_add_media_service(call: ServiceCall) -> dict:
        """Add media to Overseerr with LLM-optimized response."""
        try:
            title = call.data.get("title", "").strip()
            
            if not title:
                result = LLMResponseBuilder.build_add_media_response("missing_title")
                hass.data[DOMAIN]["last_add_media"] = result
                return result
            
            _LOGGER.info(f"Adding media to Overseerr: {title}")
            api = hass.data[DOMAIN]["api"]
            
            # Search for the media
            search_data = await api.search_media(title)
            if not search_data:
                result = LLMResponseBuilder.build_add_media_response("connection_error", title, error_details="Failed to get response from Overseerr search API")
                hass.data[DOMAIN]["last_add_media"] = result
                return result
            
            # Check if any results found
            results = search_data.get("results", [])
            if not results:
                result = LLMResponseBuilder.build_add_media_response("not_found", title)
                hass.data[DOMAIN]["last_add_media"] = result
                return result
            
            # Get the first result (most relevant)
            first_result = results[0]
            media_type = first_result.get("mediaType", "movie")
            tmdb_id = first_result.get("id")
            
            # Check if already exists in Overseerr
            if first_result.get("mediaInfo"):
                # Media already exists, get details and return
                media_details = None
                try:
                    if tmdb_id:
                        media_details = await api.get_media_details(media_type, tmdb_id)
                except Exception as e:
                    _LOGGER.warning(f"Failed to get media details: {e}")
                
                result = LLMResponseBuilder.build_add_media_response(
                    "media_already_exists",
                    title=title,
                    search_result=first_result,
                    media_details=media_details
                )
                hass.data[DOMAIN]["last_add_media"] = result
                _LOGGER.info(f"Media '{title}' already exists in Overseerr")
                return result
            
            # Media doesn't exist, so add it
            user_id = hass.data[DOMAIN].get("overseerr_user_id")
            add_result = await api.add_media_request(media_type, tmdb_id, user_id)
            
            if add_result:
                # Successfully added, get details for response
                media_details = None
                try:
                    if tmdb_id:
                        media_details = await api.get_media_details(media_type, tmdb_id)
                except Exception as e:
                    _LOGGER.warning(f"Failed to get media details: {e}")
                
                result = LLMResponseBuilder.build_add_media_response(
                    "media_added_successfully",
                    title=title,
                    search_result=first_result,
                    media_details=media_details,
                    add_result=add_result
                )
                hass.data[DOMAIN]["last_add_media"] = result
                _LOGGER.info(f"Successfully added '{title}' to Overseerr")
                return result
            else:
                # Failed to add
                result = LLMResponseBuilder.build_add_media_response("media_add_failed", title, error_details="API request returned empty result")
                hass.data[DOMAIN]["last_add_media"] = result
                _LOGGER.error(f"Failed to add '{title}' to Overseerr")
                return result
            
        except Exception as e:
            _LOGGER.error(f"Error adding media: {e}")
            result = LLMResponseBuilder.build_add_media_response("connection_error", title, error_details=str(e))
            hass.data[DOMAIN]["last_add_media"] = result
            return result

    async def handle_search_media_service(call: ServiceCall) -> dict:
        """Search for media with LLM-optimized response showing multiple results."""
        try:
            query = call.data.get("query", "").strip()
            
            if not query:
                result = LLMResponseBuilder.build_search_response("missing_query")
                hass.data[DOMAIN]["last_search"] = result
                return result
            
            _LOGGER.info(f"Searching for media: {query}")
            api = hass.data[DOMAIN]["api"]
            
            # Search for the media
            search_data = await api.search_media(query)
            if not search_data:
                result = LLMResponseBuilder.build_search_response("connection_error", query, error_details="Failed to get response from Overseerr search API")
                hass.data[DOMAIN]["last_search"] = result
                return result
            
            # Check if any results found
            results = search_data.get("results", [])
            if not results:
                result = LLMResponseBuilder.build_search_response("no_results", query)
                hass.data[DOMAIN]["last_search"] = result
                return result
            
            # Return the search results
            result = LLMResponseBuilder.build_search_response("search_results", query, search_data)
            hass.data[DOMAIN]["last_search"] = result
            _LOGGER.info(f"Found {len(results)} results for search: {query}")
            return result
            
        except Exception as e:
            _LOGGER.error(f"Error searching for media: {e}")
            result = LLMResponseBuilder.build_search_response("connection_error", query, error_details=str(e))
            hass.data[DOMAIN]["last_search"] = result
            return result

    async def handle_remove_media_service(call: ServiceCall) -> dict:
        """Remove media from Overseerr with LLM-optimized response."""
        try:
            title = call.data.get("title", "").strip()
            media_id = call.data.get("media_id", "").strip()
            
            # Validate input parameters
            if not title and not media_id:
                result = LLMResponseBuilder.build_remove_media_response("missing_params")
                hass.data[DOMAIN]["last_remove_media"] = result
                return result
            
            api = hass.data[DOMAIN]["api"]
            search_result = None
            
            # If title provided, search for media_id
            if title:
                _LOGGER.info(f"Searching for media to remove: {title}")
                search_data = await api.search_media(title)
                if not search_data:
                    result = LLMResponseBuilder.build_remove_media_response("connection_error", title, error_details="Failed to get response from Overseerr search API")
                    hass.data[DOMAIN]["last_remove_media"] = result
                    return result
                
                results = search_data.get("results", [])
                if not results:
                    result = LLMResponseBuilder.build_remove_media_response("media_not_found", title)
                    hass.data[DOMAIN]["last_remove_media"] = result
                    return result
                
                # Get the first result
                search_result = results[0]
                
                # Check if it's in the library (has mediaInfo)
                if not search_result.get("mediaInfo"):
                    result = LLMResponseBuilder.build_remove_media_response("not_in_library", title, search_result=search_result)
                    hass.data[DOMAIN]["last_remove_media"] = result
                    return result
                
                # Extract media_id from mediaInfo
                media_id = search_result.get("mediaInfo", {}).get("id")
                if not media_id:
                    result = LLMResponseBuilder.build_remove_media_response("no_media_id", title, search_result=search_result)
                    hass.data[DOMAIN]["last_remove_media"] = result
                    return result
            
            _LOGGER.info(f"Attempting to remove media ID: {media_id}")
            
            # Make the delete request
            delete_result = await api.delete_media(int(media_id))
            
            if delete_result is not None:
                # Success - deletion worked
                result = LLMResponseBuilder.build_remove_media_response(
                    "media_removed",
                    title=title,
                    media_id=media_id,
                    search_result=search_result
                )
                hass.data[DOMAIN]["last_remove_media"] = result
                _LOGGER.info(f"Successfully removed media ID {media_id}")
                return result
            else:
                # Failed to remove
                result = LLMResponseBuilder.build_remove_media_response(
                    "removal_failed",
                    title=title,
                    media_id=media_id,
                    error_details="Delete request returned empty result"
                )
                hass.data[DOMAIN]["last_remove_media"] = result
                _LOGGER.error(f"Failed to remove media ID {media_id}")
                return result
            
        except Exception as e:
            _LOGGER.error(f"Error removing media: {e}")
            result = LLMResponseBuilder.build_remove_media_response(
                "connection_error",
                title=title,
                media_id=media_id,
                error_details=str(e)
            )
            hass.data[DOMAIN]["last_remove_media"] = result
            return result

    async def handle_get_active_requests_service(call: ServiceCall) -> dict:
        """Handle get active requests service call."""
        try:
            # Use the existing API client
            api = hass.data[DOMAIN]["api"]
            
            # Get all requests
            requests_data = await api.get_requests()
            
            if requests_data is None:
                result = LLMResponseBuilder.build_active_requests_response(
                    "connection_error",
                    error_details="Failed to retrieve requests from Overseerr API"
                )
                hass.data[DOMAIN]["last_active_requests"] = result
                _LOGGER.error("Failed to get active requests - API returned None")
                return result
            
            # Check if we have any requests
            if not requests_data.get("results") or len(requests_data.get("results", [])) == 0:
                result = LLMResponseBuilder.build_active_requests_response(
                    "no_requests",
                    requests_data=requests_data
                )
                hass.data[DOMAIN]["last_active_requests"] = result
                _LOGGER.info("No active requests found")
                return result
            
            # We have requests - build the response
            result = LLMResponseBuilder.build_active_requests_response(
                "requests_found",
                requests_data=requests_data
            )
            hass.data[DOMAIN]["last_active_requests"] = result
            _LOGGER.info(f"Retrieved {len(requests_data.get('results', []))} requests from Overseerr")
            return result
            
        except Exception as e:
            _LOGGER.error(f"Error getting active requests: {e}")
            result = LLMResponseBuilder.build_active_requests_response(
                "connection_error",
                error_details=str(e)
            )
            hass.data[DOMAIN]["last_active_requests"] = result
            return result

    async def handle_run_job_service(call: ServiceCall) -> dict:
        """Handle run job service call."""
        job_id = call.data.get("job_id")
        
        try:
            # Use the existing API client
            api = hass.data[DOMAIN]["api"]
            
            # First, get available jobs to validate the job_id and get job name
            jobs_data = await api.get_jobs()
            
            if jobs_data is None:
                result = LLMResponseBuilder.build_run_job_response(
                    "connection_error",
                    job_id=job_id,
                    error_details="Failed to retrieve jobs from Overseerr API"
                )
                hass.data[DOMAIN]["last_run_job"] = result
                _LOGGER.error(f"Failed to get jobs list to validate job_id: {job_id}")
                return result
            
            # Handle different response formats
            if isinstance(jobs_data, dict) and "results" in jobs_data:
                jobs_list = jobs_data["results"]
            elif isinstance(jobs_data, list):
                jobs_list = jobs_data
            else:
                jobs_list = []
            
            # Find the job to get its name
            job_name = None
            job_found = False
            for job in jobs_list:
                if job.get("id") == job_id:
                    job_name = job.get("name", job_id)
                    job_found = True
                    break
            
            if not job_found:
                result = LLMResponseBuilder.build_run_job_response(
                    "job_not_found",
                    job_id=job_id,
                    error_details=f"Job '{job_id}' not found in available jobs list"
                )
                hass.data[DOMAIN]["last_run_job"] = result
                _LOGGER.error(f"Job not found: {job_id}")
                return result
            
            # Run the job
            run_result = await api.run_job(job_id)
            
            if run_result is not None:
                # Success - job was triggered
                result = LLMResponseBuilder.build_run_job_response(
                    "job_started",
                    job_id=job_id,
                    job_name=job_name
                )
                hass.data[DOMAIN]["last_run_job"] = result
                _LOGGER.info(f"Successfully triggered job: {job_name} ({job_id})")
                return result
            else:
                # Failed to run job
                result = LLMResponseBuilder.build_run_job_response(
                    "job_run_failed",
                    job_id=job_id,
                    error_details="Job run request returned empty result"
                )
                hass.data[DOMAIN]["last_run_job"] = result
                _LOGGER.error(f"Failed to run job: {job_id}")
                return result
            
        except Exception as e:
            _LOGGER.error(f"Error running job {job_id}: {e}")
            result = LLMResponseBuilder.build_run_job_response(
                "connection_error",
                job_id=job_id,
                error_details=str(e)
            )
            hass.data[DOMAIN]["last_run_job"] = result
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
    
    # Register the add media service
    hass.services.async_register(
        DOMAIN, 
        "add_media", 
        handle_add_media_service, 
        schema=vol.Schema({
            vol.Required("title"): str,
        }),
        supports_response=True
    )
    
    # Register the search media service
    hass.services.async_register(
        DOMAIN, 
        "search_media", 
        handle_search_media_service, 
        schema=vol.Schema({
            vol.Required("query"): str,
        }),
        supports_response=True
    )
    
    # Register the remove media service
    hass.services.async_register(
        DOMAIN, 
        "remove_media", 
        handle_remove_media_service, 
        schema=vol.Schema({
            vol.Optional("title"): str,
            vol.Optional("media_id"): str,
        }),
        supports_response=True
    )
    
    # Register the get active requests service
    hass.services.async_register(
        DOMAIN, 
        "get_active_requests", 
        handle_get_active_requests_service, 
        schema=vol.Schema({}),
        supports_response=True
    )
    
    # Register the run job service
    hass.services.async_register(
        DOMAIN, 
        "run_job", 
        handle_run_job_service, 
        schema=vol.Schema({
            vol.Required("job_id"): str,
        }),
        supports_response=True
    )
    
    _LOGGER.info("Hassarr services registered successfully (test_connection, check_media_status, add_media, search_media, remove_media, get_active_requests, run_job)")
    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, ["sensor"])
    
    # Remove services
    hass.services.async_remove(DOMAIN, "test_connection")
    hass.services.async_remove(DOMAIN, "check_media_status")
    hass.services.async_remove(DOMAIN, "add_media")
    hass.services.async_remove(DOMAIN, "search_media")
    hass.services.async_remove(DOMAIN, "remove_media")
    hass.services.async_remove(DOMAIN, "get_active_requests")
    hass.services.async_remove(DOMAIN, "run_job")
    
    # Clean up data
    if unload_ok:
        hass.data.pop(DOMAIN, None)
    
    return unload_ok

async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)