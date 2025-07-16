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
    
    def _get_user_friendly_name(user):
        """Get a friendly name for a Home Assistant user."""
        try:
            # Try different property names that might exist
            if hasattr(user, 'name') and user.name:
                name = user.name
            elif hasattr(user, 'display_name') and user.display_name:
                name = user.display_name
            elif hasattr(user, 'username') and user.username:
                name = user.username
            elif hasattr(user, 'email') and user.email:
                # Use email as fallback
                name = user.email.split('@')[0]  # Just the username part
            else:
                # Last resort: shortened ID
                user_id = str(user.id)
                short_id = user_id[-8:] if len(user_id) > 8 else user_id
                name = f"User {short_id}"
            
            # Add role suffix if applicable
            is_owner = user.is_owner if hasattr(user, 'is_owner') else False
            is_admin = user.is_admin if hasattr(user, 'is_admin') else False
            
            if is_owner:
                return f"{name} (Owner)"
            elif is_admin:
                return f"{name} (Admin)"
            else:
                return name
                
        except Exception as e:
            _LOGGER.warning(f"Error getting friendly name for user {user.id}: {e}")
            # Fallback to shortened ID
            user_id = str(user.id)
            short_id = user_id[-8:] if len(user_id) > 8 else user_id
            return f"User {short_id}"

    async def _get_user_context(call: ServiceCall) -> dict:
        """Get user context from service call."""
        user_context = {
            "user_id": getattr(call.context, 'user_id', None),
            "is_admin": False,
            "username": "Unknown User"
        }
        
        if call.context and call.context.user_id:
            user = await hass.auth.async_get_user(call.context.user_id)
            if user:
                user_context.update({
                    "is_admin": user.is_admin,
                    "username": _get_user_friendly_name(user),
                    "is_active": user.is_active
                })
        
        return user_context
    
    def _parse_title_for_season_info(title: str) -> dict:
        """Parse title to extract season information if included in the title text.
        This is a fallback for when the LLM doesn't separate parameters properly."""
        import re
        
        original_title = title.strip()
        cleaned_title = original_title
        extracted_season = None
        
        # Only do basic parsing as a fallback - LLM should handle this properly
        # Common patterns for season in titles
        patterns = [
            # "season X of TITLE" or "season X from TITLE"
            r'^season\s+(\d+)\s+(?:of|from)\s+(.+)$',
            # "TITLE season X"
            r'^(.+?)\s+season\s+(\d+)$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, original_title, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # Check which group is the season number and which is the title
                    if groups[0].isdigit():
                        extracted_season = int(groups[0])
                        cleaned_title = groups[1].strip()
                    else:
                        cleaned_title = groups[0].strip()
                        extracted_season = int(groups[1])
                    break
        
        return {
            "original_title": original_title,
            "cleaned_title": cleaned_title,
            "extracted_season": extracted_season,
            "season_found_in_title": extracted_season is not None,
            "parsing_method": "title_parsing" if extracted_season is not None else "no_season_detected"
        }
    
    def _parse_season_request(season_input, season_analysis: dict = None) -> dict:
        """Parse natural language season requests.
        LLM should provide clean parameters, but we handle common cases as fallback."""
        if not season_input:
            return {"seasons": None, "type": "default"}
        
        season_str = str(season_input).lower().strip()
        
        # Handle explicit numbers (most common case)
        if season_str.isdigit():
            return {"seasons": [int(season_str)], "type": "explicit"}
        
        # Handle word numbers ("season two", "season three")
        word_to_num = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
        }
        
        for word, num in word_to_num.items():
            if word in season_str:
                return {"seasons": [num], "type": "word_number"}
        
        # Handle "all seasons" (request entire series)
        if any(term in season_str for term in ["all", "every", "complete"]):
            if season_analysis:
                all_seasons = season_analysis.get("all_seasons", [])
                return {"seasons": all_seasons, "type": "all"} if all_seasons else {"seasons": None, "type": "all_unknown"}
            return {"seasons": None, "type": "all_unknown"}
        
        # Handle range requests like "seasons 1 to 5" or "seasons 1-5"
        range_patterns = [
            r'seasons?\s+(\d+)\s+(?:to|-)\s+(\d+)',  # "seasons 1 to 5" or "seasons 1-5"
            r'(\d+)\s+(?:to|-)\s+(\d+)',  # "1 to 5" or "1-5"
        ]
        
        for pattern in range_patterns:
            match = re.search(pattern, season_str)
            if match:
                start = int(match.group(1))
                end = int(match.group(2))
                if start <= end:
                    seasons = list(range(start, end + 1))
                    return {"seasons": seasons, "type": "range"}
        
        # Handle "remaining seasons" (if we have season analysis)
        if any(term in season_str for term in ["remaining", "missing", "rest", "other"]) and season_analysis:
            missing = season_analysis.get("missing_seasons", [])
            return {"seasons": missing, "type": "remaining"} if missing else {"seasons": None, "type": "none_missing"}
        
        # Handle multiple specific seasons like "seasons 1, 2, and 3" or "seasons 1 2 3"
        # First try comma-separated
        comma_numbers = re.findall(r'(\d+)(?:\s*,\s*(\d+))*', season_str)
        if comma_numbers:
            seasons = []
            for match in comma_numbers:
                for group in match:
                    if group:
                        seasons.append(int(group))
            if seasons:
                return {"seasons": seasons, "type": "multiple"}
        
        # Fallback - try to extract any numbers
        import re
        numbers = re.findall(r'\d+', season_str)
        if numbers:
            return {"seasons": [int(num) for num in numbers], "type": "extracted"}
        
        return {"seasons": None, "type": "unparseable"}
    
    async def handle_test_connection_service(call: ServiceCall) -> dict:
        """Test the Overseerr connection."""
        try:
            user_context = await _get_user_context(call)
            _LOGGER.info(f"Testing Overseerr connection... (called by {user_context['username']})")
            
            api = hass.data[DOMAIN]["api"]
            requests_data = await api.get_requests()
            
            if requests_data:
                result = {
                    "status": "success",
                    "message": f"Connected to Overseerr successfully. Found {len(requests_data.get('results', []))} requests.",
                    "total_requests": len(requests_data.get('results', [])),
                    "user_context": user_context
                }
                _LOGGER.info(f"Connection test successful: {result}")
            else:
                result = {
                    "status": "failed",
                    "message": "Failed to connect to Overseerr",
                    "total_requests": 0,
                    "user_context": user_context
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
                "total_requests": 0,
                "user_context": await _get_user_context(call)
            }
            hass.data[DOMAIN]["last_test_result"] = result
            return result

    async def handle_check_media_status_service(call: ServiceCall) -> dict:
        """Check media status with LLM-optimized response."""
        try:
            title = call.data.get("title", "").strip()
            user_context = await _get_user_context(call)
            
            if not title:
                result = LLMResponseBuilder.build_status_response("missing_title")
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_status_check"] = result
                return result
            
            # Check if user is mapped (for read-only operations, we can be more lenient)
            user_mappings = hass.data[DOMAIN].get("user_mappings", {})
            calling_user_id = user_context.get("user_id")
            
            if calling_user_id and calling_user_id not in user_mappings:
                # For status checks, we can allow unmapped users but log it
                _LOGGER.info(f"Unmapped user {user_context['username']} checking media status - allowing read-only access")
            
            _LOGGER.info(f"Checking media status for: {title} (called by {user_context['username']})")
            api = hass.data[DOMAIN]["api"]
            
            # Search for the media
            search_data = await api.search_media(title)
            if not search_data:
                # Get detailed error from API if available
                error_details = api.last_error if api.last_error else "Failed to get response from Overseerr search API"
                result = LLMResponseBuilder.build_status_response("connection_error", title, error_details=error_details)
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_status_check"] = result
                return result
            
            # Check if any results found
            results = search_data.get("results", [])
            if not results:
                result = LLMResponseBuilder.build_status_response("not_found", title)
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_status_check"] = result
                return result
            
            # Get the first result (most relevant) with bounds checking
            first_result = results[0]
            _LOGGER.debug(f"Found search result for '{title}': {first_result.get('title') or first_result.get('name', 'Unknown')}")
            
            # Get additional media details
            media_details = None
            try:
                media_type = first_result.get("mediaType", "movie")
                tmdb_id = first_result.get("id")
                if tmdb_id:
                    media_details = await api.get_media_details(media_type, tmdb_id)
                    _LOGGER.debug(f"Retrieved media details for TMDB ID {tmdb_id}")
            except Exception as e:
                _LOGGER.warning(f"Failed to get media details for '{title}': {e}")
            
            # Get current requests to check status
            requests_data = None
            try:
                requests_data = await api.get_requests()
                _LOGGER.debug(f"Retrieved requests data: {len(requests_data.get('results', []))} requests")
            except Exception as e:
                _LOGGER.warning(f"Failed to get requests data: {e}")
            
            # Build structured LLM response
            try:
                result = LLMResponseBuilder.build_status_response(
                    "found_media",
                    title=title,
                    search_result=first_result,
                    media_details=media_details,
                    requests_data=requests_data
                )
            except Exception as e:
                _LOGGER.error(f"Error building status response for '{title}': {e}")
                result = LLMResponseBuilder.build_status_response("connection_error", title, error_details=f"Error processing response: {e}")
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_status_check"] = result
                return result
            
            result["user_context"] = user_context
            hass.data[DOMAIN]["last_status_check"] = result
            _LOGGER.info(f"Media status check completed for '{title}': {result['action']}")
            return result
            
        except Exception as e:
            _LOGGER.error(f"Error checking media status: {e}")
            result = LLMResponseBuilder.build_status_response("connection_error", title, error_details=str(e))
            result["user_context"] = await _get_user_context(call)
            hass.data[DOMAIN]["last_status_check"] = result
            return result

    async def handle_add_media_service(call: ServiceCall) -> dict:
        """Add media to Overseerr with LLM-optimized response."""
        try:
            title = call.data.get("title", "").strip()
            season_input = call.data.get("season")  # Optional season parameter
            user_context = await _get_user_context(call)
            
            if not title:
                result = await LLMResponseBuilder.build_add_media_response("missing_title")
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_add_media"] = result
                return result

            season_info = f" (season: {season_input})" if season_input is not None else ""
            _LOGGER.info(f"Adding media to Overseerr: {title}{season_info} (called by {user_context['username']})")
            api = hass.data[DOMAIN]["api"]
            
            # Search for the media first to get media type and tmdb_id
            search_data = await api.search_media(title)
            if not search_data:
                # Get detailed error from API if available
                error_details = api.last_error if api.last_error else "Failed to get response from Overseerr search API"
                result = await LLMResponseBuilder.build_add_media_response("connection_error", title, error_details=error_details)
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_add_media"] = result
                return result
            
            # Check if any results found
            results = search_data.get("results", [])
            if not results:
                result = await LLMResponseBuilder.build_add_media_response("not_found", title)
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_add_media"] = result
                return result
            
            # Get the first result (most relevant)
            first_result = results[0]
            media_type = first_result.get("mediaType", "movie")
            tmdb_id = first_result.get("id")
            
            # For TV shows, perform season analysis before parsing season input
            season_analysis = None
            if media_type == "tv" and season_input is not None:
                try:
                    season_analysis = await api.get_tv_season_analysis(tmdb_id)
                except Exception as e:
                    _LOGGER.warning(f"Failed to get season analysis: {e}")
            
            # Parse season input using natural language processing
            season_parse_result = _parse_season_request(season_input, season_analysis)
            requested_seasons = season_parse_result.get("seasons")
            parse_type = season_parse_result.get("type")
            
            # Handle different season request types
            season = None
            seasons_list = None
            
            if parse_type == "all":
                # "All seasons" - use all available seasons
                if requested_seasons:
                    seasons_list = requested_seasons
                    _LOGGER.info(f"Parsed season request '{season_input}' -> requesting all seasons: {requested_seasons}")
                else:
                    seasons_list = None  # Fallback to API default
                    _LOGGER.info(f"Parsed season request '{season_input}' -> requesting entire series (API default)")
            elif requested_seasons:
                # Multiple seasons requested
                if len(requested_seasons) > 1:
                    seasons_list = requested_seasons
                    _LOGGER.info(f"Parsed season request '{season_input}' -> requesting multiple seasons: {requested_seasons}")
                else:
                    # Single season
                    season = requested_seasons[0]
                    seasons_list = [season]
                    _LOGGER.info(f"Parsed season request '{season_input}' -> requesting season {season}")
                
                # Validate seasons
                try:
                    valid_seasons = []
                    for s in requested_seasons:
                        season_int = int(s)
                        if season_int >= 1:
                            valid_seasons.append(season_int)
                        else:
                            _LOGGER.warning(f"Invalid season number: {s}, skipping")
                    
                    if valid_seasons:
                        seasons_list = valid_seasons
                        if len(valid_seasons) == 1:
                            season = valid_seasons[0]
                    else:
                        # No valid seasons, default to season 1
                        season = 1
                        seasons_list = [1]
                        _LOGGER.warning(f"No valid seasons found, defaulting to season 1")
                        
                except (ValueError, TypeError) as e:
                    _LOGGER.warning(f"Error validating seasons: {e}, defaulting to season 1")
                    season = 1
                    seasons_list = [1]
            else:
                # No season specified - default to season 1
                season = 1
                seasons_list = [1]
                _LOGGER.info(f"No season specified, defaulting to season 1")
            
            # Check if already exists in Overseerr
            if first_result.get("mediaInfo"):
                # For TV shows, check if the specific season is already requested
                if media_type == "tv" and season is not None:
                    try:
                        # Get season analysis to check if this specific season is already requested
                        season_analysis = await api.get_tv_season_analysis(tmdb_id)
                        if season_analysis:
                            requested_seasons = season_analysis.get("requested_seasons", [])
                            if season in requested_seasons:
                                # This specific season is already requested
                                _LOGGER.info(f"Season {season} of '{title}' is already requested in Overseerr")
                                media_details = None
                                try:
                                    if tmdb_id:
                                        media_details = await api.get_media_details(media_type, tmdb_id)
                                except Exception as e:
                                    _LOGGER.warning(f"Failed to get media details: {e}")
                                
                                result = await LLMResponseBuilder.build_add_media_response(
                                    "media_already_exists",
                                    title=title,
                                    search_result=first_result,
                                    media_details=media_details,
                                    season=season,
                                    season_analysis=season_analysis,
                                    api=api
                                )
                                result["user_context"] = user_context
                                hass.data[DOMAIN]["last_add_media"] = result
                                return result
                            else:
                                # Season is not requested yet, proceed with the request
                                _LOGGER.info(f"Season {season} of '{title}' is not yet requested, proceeding with request")
                    except Exception as e:
                        _LOGGER.warning(f"Failed to check season analysis for '{title}': {e}")
                        # If we can't check season analysis, proceed with the request anyway
                
                # For movies or if no specific season requested, check if media exists
                elif media_type == "movie" or season is None:
                    # Media already exists, get details and return
                    media_details = None
                    season_analysis = None
                    
                    try:
                        if tmdb_id:
                            media_details = await api.get_media_details(media_type, tmdb_id)
                            
                            # For TV shows, perform season analysis to provide intelligent suggestions
                            if media_type == "tv":
                                season_analysis = await api.get_tv_season_analysis(tmdb_id)
                                _LOGGER.debug(f"Season analysis for '{title}': {season_analysis}")
                            
                    except Exception as e:
                        _LOGGER.warning(f"Failed to get media details or season analysis: {e}")
                    
                    result = await LLMResponseBuilder.build_add_media_response(
                        "media_already_exists",
                        title=title,
                        search_result=first_result,
                        media_details=media_details,
                        season=season,
                        season_analysis=season_analysis,
                        api=api
                    )
                    result["user_context"] = user_context
                    hass.data[DOMAIN]["last_add_media"] = result
                    _LOGGER.info(f"Media '{title}' already exists in Overseerr")
                    return result
            
            # Media doesn't exist, so add it
            # Get the appropriate Overseerr user ID for this Home Assistant user
            user_mappings = hass.data[DOMAIN].get("user_mappings", {})
            calling_user_id = user_context.get("user_id")
            
            if calling_user_id and calling_user_id in user_mappings:
                overseerr_user_id = user_mappings[calling_user_id]
                _LOGGER.info(f"User {user_context['username']} mapped to Overseerr user ID {overseerr_user_id}")
            else:
                # No mapping found - return error response
                result = await LLMResponseBuilder.build_add_media_response(
                    "user_not_mapped",
                    title=title,
                    error_details=f"User {user_context.get('username')} is not mapped to any Overseerr user"
                )
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_add_media"] = result
                _LOGGER.warning(f"User {user_context['username']} (ID: {calling_user_id}) is not mapped to any Overseerr user")
                return result
            
            # Prepare seasons list for TV shows (seasons_list is already set above)
            if media_type == "tv":
                if seasons_list is not None:
                    _LOGGER.debug(f"Requesting seasons {seasons_list} for TV show '{title}'")
                else:
                    _LOGGER.debug(f"Requesting entire series (all seasons) for TV show '{title}'")
            else:
                _LOGGER.debug(f"Adding movie '{title}' (seasons parameter not applicable)")
            
            add_result = await api.add_media_request(media_type, tmdb_id, overseerr_user_id, seasons_list)
            
            if add_result:
                # Successfully added, get details for response
                media_details = None
                try:
                    if tmdb_id:
                        media_details = await api.get_media_details(media_type, tmdb_id)
                except Exception as e:
                    _LOGGER.warning(f"Failed to get media details: {e}")
                
                # Check if we requested specific seasons but may have fallen back to entire series
                actual_season = season
                fallback_message = ""
                
                # If we requested a specific season but the API had to fall back to entire series
                if media_type == "tv" and season is not None and api.last_error and "500" in str(api.last_error):
                    fallback_message = f" (Note: Season {season} request failed, so the entire series was requested instead)"
                    actual_season = None  # Indicate that entire series was requested
                
                result = await LLMResponseBuilder.build_add_media_response(
                    "media_added_successfully",
                    title=title,
                    search_result=first_result,
                    media_details=media_details,
                    add_result=add_result,
                    season=actual_season,
                    parse_type=parse_type,
                    seasons_list=seasons_list
                )
                
                # Add fallback information if needed
                if fallback_message:
                    result["fallback_info"] = {
                        "original_season_request": season,
                        "actual_request": "entire_series",
                        "reason": "Season-specific request failed on server"
                    }
                    result["message"] = result["message"] + fallback_message
                
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_add_media"] = result
                _LOGGER.info(f"Successfully added '{title}'{season_info} to Overseerr{fallback_message}")
                return result
            else:
                # Failed to add - get detailed error from API
                error_details = api.last_error if api.last_error else "API request returned empty result"
                result = await LLMResponseBuilder.build_add_media_response("media_add_failed", title, error_details=error_details, season=season)
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_add_media"] = result
                _LOGGER.error(f"Failed to add '{title}' to Overseerr: {error_details}")
                return result
            
        except Exception as e:
            _LOGGER.error(f"Error adding media: {e}")
            # Get detailed error from API if available, otherwise use exception
            api = hass.data[DOMAIN].get("api")
            error_details = api.last_error if api and api.last_error else str(e)
            result = await LLMResponseBuilder.build_add_media_response("connection_error", title, error_details=error_details, season=season)
            result["user_context"] = await _get_user_context(call)
            hass.data[DOMAIN]["last_add_media"] = result
            return result

    async def handle_search_media_service(call: ServiceCall) -> dict:
        """Search for media with LLM-optimized response showing multiple results."""
        try:
            query = call.data.get("query", "").strip()
            user_context = await _get_user_context(call)
            
            if not query:
                result = LLMResponseBuilder.build_search_response("missing_query")
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_search"] = result
                return result
            
            # Check if user is mapped (for read-only operations, we can be more lenient)
            user_mappings = hass.data[DOMAIN].get("user_mappings", {})
            calling_user_id = user_context.get("user_id")
            
            if calling_user_id and calling_user_id not in user_mappings:
                # For searches, we can allow unmapped users but log it
                _LOGGER.info(f"Unmapped user {user_context['username']} searching media - allowing read-only access")
            
            _LOGGER.info(f"Searching for media: {query} (called by {user_context['username']})")
            api = hass.data[DOMAIN]["api"]
            
            # Search for the media
            search_data = await api.search_media(query)
            if not search_data:
                # Get detailed error from API if available
                error_details = api.last_error if api.last_error else "Failed to get response from Overseerr search API"
                result = LLMResponseBuilder.build_search_response("connection_error", query, error_details=error_details)
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_search"] = result
                return result
            
            # Check if any results found
            results = search_data.get("results", [])
            if not results:
                result = LLMResponseBuilder.build_search_response("no_results", query)
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_search"] = result
                return result
            
            # Return the search results
            result = LLMResponseBuilder.build_search_response("search_results", query, search_data)
            result["user_context"] = user_context
            hass.data[DOMAIN]["last_search"] = result
            _LOGGER.info(f"Found {len(results)} results for search: {query}")
            return result
            
        except Exception as e:
            _LOGGER.error(f"Error searching for media: {e}")
            result = LLMResponseBuilder.build_search_response("connection_error", query, error_details=str(e))
            result["user_context"] = await _get_user_context(call)
            hass.data[DOMAIN]["last_search"] = result
            return result

    async def handle_remove_media_service(call: ServiceCall) -> dict:
        """Remove media from Overseerr with LLM-optimized response."""
        try:
            title = call.data.get("title", "").strip()
            media_id = call.data.get("media_id", "").strip()
            user_context = await _get_user_context(call)
            
            # Validate input parameters
            if not title and not media_id:
                result = LLMResponseBuilder.build_remove_media_response("missing_params")
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_remove_media"] = result
                return result
            
            _LOGGER.info(f"Remove media request (called by {user_context['username']}): title='{title}', media_id='{media_id}'")
            
            # Check if user is mapped (required for removal operations)
            user_mappings = hass.data[DOMAIN].get("user_mappings", {})
            calling_user_id = user_context.get("user_id")
            
            if calling_user_id and calling_user_id not in user_mappings:
                # No mapping found - return error response
                result = LLMResponseBuilder.build_remove_media_response(
                    "user_not_mapped",
                    title=title,
                    error_details=f"User {user_context.get('username')} is not mapped to any Overseerr user"
                )
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_remove_media"] = result
                _LOGGER.warning(f"User {user_context['username']} (ID: {calling_user_id}) is not mapped to any Overseerr user")
                return result
            
            api = hass.data[DOMAIN]["api"]
            search_result = None
            
            # If title provided, search for media_id
            if title:
                search_data = await api.search_media(title)
                if not search_data:
                    # Get detailed error from API if available
                    error_details = api.last_error if api.last_error else "Failed to get response from Overseerr search API"
                    result = LLMResponseBuilder.build_remove_media_response("connection_error", title, error_details=error_details)
                    result["user_context"] = user_context
                    hass.data[DOMAIN]["last_remove_media"] = result
                    return result
                
                results = search_data.get("results", [])
                if not results:
                    result = LLMResponseBuilder.build_remove_media_response("media_not_found", title)
                    result["user_context"] = user_context
                    hass.data[DOMAIN]["last_remove_media"] = result
                    return result
                
                # Get the first result
                search_result = results[0]
                
                # Check if it's in the library (has mediaInfo)
                if not search_result.get("mediaInfo"):
                    result = LLMResponseBuilder.build_remove_media_response("not_in_library", title, search_result=search_result)
                    result["user_context"] = user_context
                    hass.data[DOMAIN]["last_remove_media"] = result
                    return result
                
                # Extract media_id from mediaInfo
                media_id = search_result.get("mediaInfo", {}).get("id")
                if not media_id:
                    result = LLMResponseBuilder.build_remove_media_response("no_media_id", title, search_result=search_result)
                    result["user_context"] = user_context
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
                result["user_context"] = user_context
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
                result["user_context"] = user_context
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
            result["user_context"] = await _get_user_context(call)
            hass.data[DOMAIN]["last_remove_media"] = result
            return result

    async def handle_get_active_requests_service(call: ServiceCall) -> dict:
        """Handle get active requests service call."""
        try:
            user_context = await _get_user_context(call)
            _LOGGER.info(f"Getting active requests (called by {user_context['username']})")
            
            # Use the existing API client
            api = hass.data[DOMAIN]["api"]
            
            # Get all requests
            requests_data = await api.get_requests()
            
            if requests_data is None:
                result = await LLMResponseBuilder.build_active_requests_response(
                    "connection_error",
                    error_details="Failed to retrieve requests from Overseerr API"
                )
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_active_requests"] = result
                _LOGGER.error("Failed to get active requests - API returned None")
                return result
            
            # Check if we have any requests
            if not requests_data.get("results") or len(requests_data.get("results", [])) == 0:
                result = await LLMResponseBuilder.build_active_requests_response(
                    "no_requests",
                    requests_data=requests_data
                )
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_active_requests"] = result
                _LOGGER.info("No active requests found")
                return result
            
            # We have requests - build the response
            result = await LLMResponseBuilder.build_active_requests_response(
                "requests_found",
                requests_data=requests_data,
                api=api
            )
            result["user_context"] = user_context
            hass.data[DOMAIN]["last_active_requests"] = result
            _LOGGER.info(f"Retrieved {len(requests_data.get('results', []))} requests from Overseerr")
            return result
            
        except Exception as e:
            _LOGGER.error(f"Error getting active requests: {e}")
            result = await LLMResponseBuilder.build_active_requests_response(
                "connection_error",
                error_details=str(e)
            )
            result["user_context"] = await _get_user_context(call)
            hass.data[DOMAIN]["last_active_requests"] = result
            return result

    async def handle_run_job_service(call: ServiceCall) -> dict:
        """Handle run job service call."""
        job_id = call.data.get("job_id")
        user_context = await _get_user_context(call)
        
        try:
            _LOGGER.info(f"Running job {job_id} (called by {user_context['username']})")
            
            # Check if user is mapped (required for job operations)
            user_mappings = hass.data[DOMAIN].get("user_mappings", {})
            calling_user_id = user_context.get("user_id")
            
            if calling_user_id and calling_user_id not in user_mappings:
                # No mapping found - return error response
                result = LLMResponseBuilder.build_run_job_response(
                    "user_not_mapped",
                    job_id=job_id,
                    error_details=f"User {user_context.get('username')} is not mapped to any Overseerr user"
                )
                result["user_context"] = user_context
                hass.data[DOMAIN]["last_run_job"] = result
                _LOGGER.warning(f"User {user_context['username']} (ID: {calling_user_id}) is not mapped to any Overseerr user")
                return result
            
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
                result["user_context"] = user_context
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
                result["user_context"] = user_context
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
                result["user_context"] = user_context
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
                result["user_context"] = user_context
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
            result["user_context"] = await _get_user_context(call)
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
            vol.Optional("season"): vol.Any(int, str),
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