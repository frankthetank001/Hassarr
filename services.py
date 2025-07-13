import logging
import aiohttp
import json
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Dict, Any, Optional, List
from .const import DOMAIN
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

class OverseerrAPI:
    """Overseerr API client with LLM-optimized responses."""
    
    def __init__(self, url: str, api_key: str):
        self.base_url = url
        self.api_key = api_key
        self.headers = {'X-Api-Key': api_key}
        
        # Ensure URL has scheme
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            self.base_url = f"https://{url}"
    
    async def _make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Optional[Dict]:
        """Make async HTTP request to Overseerr API."""
        url = urljoin(self.base_url, endpoint)
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url, headers=self.headers) as response:
                        if response.status in [200, 201, 204]:
                            content = await response.text()
                            return json.loads(content) if content else {}
                        else:
                            _LOGGER.error(f"API request failed: {response.status} - {await response.text()}")
                            return None
                elif method == "POST":
                    async with session.post(url, headers=self.headers, json=data) as response:
                        if response.status in [200, 201, 204]:
                            content = await response.text()
                            return json.loads(content) if content else {}
                        else:
                            _LOGGER.error(f"API request failed: {response.status} - {await response.text()}")
                            return None
                elif method == "DELETE":
                    async with session.delete(url, headers=self.headers) as response:
                        if response.status in [200, 201, 204]:
                            content = await response.text()
                            return json.loads(content) if content else {}
                        else:
                            _LOGGER.error(f"API request failed: {response.status} - {await response.text()}")
                            return None
                else:
                    _LOGGER.error(f"Unsupported HTTP method: {method}")
                    return None
        except Exception as e:
            _LOGGER.error(f"Request failed: {e}")
            return None
    
    async def search_media(self, query: str) -> Optional[Dict]:
        """Search for media in Overseerr."""
        endpoint = f"api/v1/search?query={query}"
        return await self._make_request(endpoint)
    
    async def get_requests(self) -> Optional[Dict]:
        """Get all active requests."""
        endpoint = "api/v1/request"
        return await self._make_request(endpoint)
    
    async def get_media_details(self, media_type: str, tmdb_id: int) -> Optional[Dict]:
        """Get detailed media information."""
        endpoint = f"api/v1/{media_type}/{tmdb_id}"
        return await self._make_request(endpoint)
    
    async def delete_media(self, media_id: int) -> bool:
        """Delete media from Overseerr."""
        endpoint = f"api/v1/media/{media_id}"
        result = await self._make_request(endpoint, method="DELETE")
        return result is not None
    
    async def create_request(self, payload: Dict) -> Optional[Dict]:
        """Create a new media request."""
        endpoint = "api/v1/request"
        return await self._make_request(endpoint, method="POST", data=payload)

class LLMResponseBuilder:
    """Build LLM-optimized responses."""
    
    @staticmethod
    def build_status_response(media_data: Dict, requests_data: Dict, details_data: Dict) -> Dict:
        """Build comprehensive status response for LLM."""
        if not media_data or not media_data.get("results"):
            return {
                "action": "not_found",
                "message": "No media found matching the search criteria"
            }
        
        result = media_data["results"][0]
        media_info = result.get("mediaInfo", {})
        
        # Build status text
        status = media_info.get("status", 0)
        status_text = {
            1: "Unknown",
            2: "Pending Approval", 
            3: "Processing/Downloading",
            4: "Partially Available",
            5: "Available in Library"
        }.get(status, f"Status {status}")
        
        # Build download info
        download_info = None
        if media_info.get("downloadStatus"):
            downloads = media_info["downloadStatus"]
            download_info = {
                "active_downloads": len(downloads),
                "current_download": {
                    "title": downloads[0].get("title", "Unknown"),
                    "time_left": downloads[0].get("timeLeft", "Unknown"),
                    "estimated_completion": downloads[0].get("estimatedCompletionTime", "Unknown"),
                    "status": downloads[0].get("status", "unknown")
                },
                "all_downloads": downloads
            }
        
        # Build request details
        request_details = {
            "requested_by": "Information not available",
            "request_date": "Unknown",
            "request_id": None
        }
        
        if requests_data and requests_data.get("results"):
            for req in requests_data["results"]:
                if req.get("media", {}).get("tmdbId") == result.get("id"):
                    request_details = {
                        "requested_by": req.get("requestedBy", {}).get("displayName", "Unknown User"),
                        "request_date": req.get("createdAt", "Unknown"),
                        "request_id": req.get("id")
                    }
                    break
        
        # Build content details
        content_details = {
            "overview": "Overview not available",
            "genres": []
        }
        
        if details_data:
            content_details["overview"] = details_data.get("overview", "Overview not available")
            content_details["genres"] = [g.get("name") for g in details_data.get("genres", [])[:3]]
            
            if result.get("mediaType") == "tv":
                content_details["tv_info"] = {
                    "seasons": details_data.get("numberOfSeasons", 0),
                    "episodes": details_data.get("numberOfEpisodes", 0),
                    "episode_runtime": details_data.get("episodeRunTime", [None])[0],
                    "series_status": details_data.get("status", "Unknown"),
                    "networks": details_data.get("networks", [{}])[0].get("name", "Unknown") if details_data.get("networks") else "Unknown"
                }
            else:
                content_details["movie_info"] = {
                    "runtime": details_data.get("runtime", 0),
                    "budget": details_data.get("budget", 0),
                    "revenue": details_data.get("revenue", 0),
                    "production_companies": details_data.get("productionCompanies", [{}])[0].get("name", "Unknown") if details_data.get("productionCompanies") else "Unknown"
                }
        
        return {
            "action": "found_media",
            "llm_instructions": "Focus on request status, who requested it, download progress, and content overview unless asked for specific details.",
            "primary_result": {
                "search_info": {
                    "title": result.get("title") or result.get("name", "Unknown"),
                    "type": result.get("mediaType", "unknown"),
                    "tmdb_id": result.get("id", 0),
                    "media_id": media_info.get("id"),
                    "status": status,
                    "status_text": status_text,
                    "release_date": result.get("releaseDate") or result.get("firstAirDate", "Unknown"),
                    "rating": result.get("voteAverage", 0),
                    "download_info": download_info,
                    "request_details": request_details
                },
                "content_details": content_details
            },
            "message": f"Found detailed information for '{result.get('title') or result.get('name', 'Unknown')}'. Focus on request status, who requested it, download progress, and content overview unless asked for specific details."
        }
    
    @staticmethod
    def build_requests_response(requests_data: Dict) -> Dict:
        """Build active requests response for LLM."""
        if not requests_data or not requests_data.get("results"):
            return {
                "action": "no_active_requests",
                "total_requests": 0,
                "message": "No active requests found - your Overseerr queue is empty"
            }
        
        all_requests = requests_data["results"]
        processing_requests = [
            req for req in all_requests 
            if req.get("media", {}).get("status") == 3 and req.get("media", {}).get("downloadStatus")
        ]
        
        return {
            "action": "active_requests_found",
            "llm_instructions": "Focus on currently processing downloads unless specifically asked for all requests or other details.",
            "total_requests": len(all_requests),
            "currently_processing": {
                "count": len(processing_requests),
                "requests": [
                    {
                        "request_id": req.get("id"),
                        "media_id": req.get("media", {}).get("id"),
                        "tmdb_id": req.get("media", {}).get("tmdbId"),
                        "type": req.get("type"),
                        "title": req.get("media", {}).get("title", "Unknown Title"),
                        "requested_by": req.get("requestedBy", {}).get("displayName", "Unknown"),
                        "created_at": req.get("createdAt"),
                        "active_downloads": len(req.get("media", {}).get("downloadStatus", [])),
                        "download_progress": [
                            {
                                "file_title": download.get("title"),
                                "status": download.get("status"),
                                "progress_percent": round(((download.get("size", 0) - download.get("sizeLeft", 0)) / download.get("size", 1)) * 100, 1) if download.get("size", 0) > 0 else 0,
                                "time_left": download.get("timeLeft"),
                                "estimated_completion": download.get("estimatedCompletionTime"),
                                "size_total_gb": round(download.get("size", 0) / 1024 / 1024 / 1024, 2),
                                "size_remaining_gb": round(download.get("sizeLeft", 0) / 1024 / 1024 / 1024, 2),
                                "size_downloaded_gb": round((download.get("size", 0) - download.get("sizeLeft", 0)) / 1024 / 1024 / 1024, 2),
                                "episode_info": {
                                    "season": download.get("episode", {}).get("seasonNumber"),
                                    "episode": download.get("episode", {}).get("episodeNumber"),
                                    "title": download.get("episode", {}).get("title"),
                                    "air_date": download.get("episode", {}).get("airDate"),
                                    "runtime": download.get("episode", {}).get("runtime"),
                                    "is_finale": download.get("episode", {}).get("finaleType", False)
                                } if download.get("episode") else None
                            }
                            for download in req.get("media", {}).get("downloadStatus", [])
                        ]
                    }
                    for req in processing_requests
                ]
            },
            "message": f"Found {len(all_requests)} total request(s) with {len(processing_requests)} actively downloading. Focus on currently processing downloads unless asked for other details."
        }

# Legacy functions for backward compatibility
async def fetch_data(url: str, headers: dict) -> dict | None:
    """Fetch data from the given URL with headers."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    return json.loads(content) if content else None
                else:
                    _LOGGER.error(f"Failed to fetch data from {url}: {await response.text()}")
                    return None
    except Exception as e:
        _LOGGER.error(f"Request failed: {e}")
        return None

async def get_root_folder_path(url: str, headers: dict) -> str | None:
    """Get root folder path from the given URL."""
    data = await fetch_data(url, headers)
    if data:
        return data[0].get("path")
    return None

async def handle_add_media(hass: HomeAssistant, call: ServiceCall, media_type: str, service_name: str) -> None:
    """Handle the service action to add a media (movie or TV show)."""
    _LOGGER.info(f"Received call data: {call.data}")
    title = call.data.get("title")

    if not title:
        _LOGGER.error("Title is missing in the service call data")
        return

    _LOGGER.info(f"Title received: {title}")

    # Access stored configuration data
    config_data = hass.data[DOMAIN]

    url = config_data.get(f"{service_name}_url")
    api_key = config_data.get(f"{service_name}_api_key")
    quality_profile_id = config_data.get(f"{service_name}_quality_profile_id")

    if not url or not api_key:
        _LOGGER.error(f"{service_name.capitalize()} URL or API key is missing")
        return

    headers = {'X-Api-Key': api_key}

    # Fetch media list
    search_url = urljoin(url, f"api/v3/{media_type}/lookup?term={title}")
    _LOGGER.info(f"Fetching media list from URL: {search_url}")
    media_list = await fetch_data(search_url, headers)

    if media_list:
        media_data = media_list[0]

        # Get root folder path
        root_folder_url = urljoin(url, "api/v3/rootfolder")
        root_folder_path = await get_root_folder_path(root_folder_url, headers)
        if not root_folder_path:
            return

        # Prepare payload
        payload = {
            'title': media_data['title'],
            'titleSlug': media_data['titleSlug'],
            'images': media_data['images'],
            'year': media_data['year'],
            'rootFolderPath': root_folder_path,
            'addOptions': {
                'searchForMovie' if media_type == 'movie' else 'searchForMissingEpisodes': True
            },
            'qualityProfileId': quality_profile_id,
        }
        if media_type == 'movie':
            payload['tmdbId'] = media_data['tmdbId']
        else:
            payload['tvdbId'] = media_data['tvdbId']

        # Add media
        add_url = urljoin(url, f"api/v3/{media_type}")
        _LOGGER.info(f"Adding media to URL: {add_url} with payload: {payload}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(add_url, json=payload, headers=headers) as response:
                    if response.status == 201:
                        _LOGGER.info(f"Successfully added {media_type} '{title}' to {service_name.capitalize()}")
                    else:
                        _LOGGER.error(f"Failed to add {media_type} '{title}' to {service_name.capitalize()}: {await response.text()}")
        except Exception as e:
            _LOGGER.error(f"Request failed: {e}")
    else:
        _LOGGER.info(f"No results found for {media_type} '{title}'")

async def handle_add_overseerr_media(hass: HomeAssistant, call: ServiceCall, media_type: str) -> None:
    """Handle the service action to add a media (movie or TV show) using Overseerr."""
    _LOGGER.info(f"Received call data: {call.data}")
    title = call.data.get("title")

    if not title:
        _LOGGER.error("Title is missing in the service call data")
        return

    _LOGGER.info(f"Title received: {title}")

    # Access stored configuration data
    config_data = hass.data[DOMAIN]

    url = config_data.get("overseerr_url")
    api_key = config_data.get("overseerr_api_key")

    if not url or not api_key:
        _LOGGER.error("Overseerr URL or API key is missing")
        return

    api = OverseerrAPI(url, api_key)
    search_results = await api.search_media(title)

    if search_results and search_results.get("results"):
        media_data = search_results["results"][0]
        _LOGGER.info(f"Media data: {media_data}")

        # Prepare payload
        payload = {
            "mediaType": media_type,
            "mediaId": media_data["id"],
            "is4k": False,
            "serverId": 0,
            "profileId": 0,
            "rootFolder": "",
            "languageProfileId": 0,
            "userId": config_data.get("overseerr_user_id"),
            "seasons": "all" if media_type == "tv" else []
        }
        if media_type == "tv":
            tvdb_id = media_data.get("tvdbId")
            if tvdb_id is not None:
                payload["tvdbId"] = tvdb_id

        # Create request
        request_result = await api.create_request(payload)

        if request_result:
            _LOGGER.info(f"Successfully created request for {media_type} '{title}' in Overseerr")
        else:
            _LOGGER.error(f"Failed to create request for {media_type} '{title}' in Overseerr")
    else:
        _LOGGER.info(f"No results found for {media_type} '{title}'")

# New LLM-focused service handlers
async def handle_check_media_status(hass: HomeAssistant, call: ServiceCall) -> Dict[str, Any]:
    """Handle checking media status with LLM-optimized response."""
    title = call.data.get("title")
    
    if not title:
        return {
            "action": "missing_title",
            "error": "No search title provided",
            "message": "Please provide a movie or TV show title to search for"
        }
    
    config_data = hass.data[DOMAIN]
    url = config_data.get("overseerr_url")
    api_key = config_data.get("overseerr_api_key")
    
    if not url or not api_key:
        return {
            "action": "connection_error",
            "error": "Overseerr configuration missing",
            "message": "Overseerr URL or API key is not configured"
        }
    
    api = OverseerrAPI(url, api_key)
    
    # Search for media
    search_results = await api.search_media(title)
    if not search_results or not search_results.get("results"):
        return {
            "action": "not_found",
            "searched_title": title,
            "message": f"No movies or TV shows found matching '{title}'"
        }
    
    result = search_results["results"][0]
    
    # Get media details and requests
    details_data = await api.get_media_details(result.get("mediaType", "movie"), result.get("id"))
    requests_data = await api.get_requests()
    
    return LLMResponseBuilder.build_status_response(search_results, requests_data, details_data)

async def handle_remove_media(hass: HomeAssistant, call: ServiceCall) -> Dict[str, Any]:
    """Handle removing media with LLM-optimized response."""
    media_id = call.data.get("media_id")
    
    if not media_id:
        return {
            "action": "missing_media_id",
            "error": "No media ID provided",
            "message": "Please provide a media ID to remove"
        }
    
    config_data = hass.data[DOMAIN]
    url = config_data.get("overseerr_url")
    api_key = config_data.get("overseerr_api_key")
    
    if not url or not api_key:
        return {
            "action": "connection_error",
            "error": "Overseerr configuration missing",
            "message": "Overseerr URL or API key is not configured"
        }
    
    api = OverseerrAPI(url, api_key)
    success = await api.delete_media(int(media_id))
    
    if success:
        return {
            "action": "media_removed",
            "media_id": media_id,
            "message": f"Media ID {media_id} has been successfully removed from Overseerr"
        }
    else:
        return {
            "action": "removal_failed",
            "media_id": media_id,
            "error": "Failed to remove media from Overseerr",
            "message": f"Could not remove media ID {media_id} - check permissions, media status, or if ID exists"
        }

async def handle_get_active_requests(hass: HomeAssistant, call: ServiceCall) -> Dict[str, Any]:
    """Handle getting active requests with LLM-optimized response."""
    config_data = hass.data[DOMAIN]
    url = config_data.get("overseerr_url")
    api_key = config_data.get("overseerr_api_key")
    
    if not url or not api_key:
        return {
            "action": "connection_error",
            "error": "Overseerr configuration missing",
            "message": "Overseerr URL or API key is not configured"
        }
    
    api = OverseerrAPI(url, api_key)
    requests_data = await api.get_requests()
    
    if not requests_data:
        return {
            "action": "connection_error",
            "error": "Failed to connect to Overseerr server",
            "message": "Connection error - check Overseerr configuration and server status"
        }
    
    return LLMResponseBuilder.build_requests_response(requests_data)

async def handle_search_media(hass: HomeAssistant, call: ServiceCall) -> Dict[str, Any]:
    """Handle searching for media."""
    query = call.data.get("query")
    
    if not query:
        return {
            "action": "missing_query",
            "error": "No search query provided",
            "message": "Please provide a search query"
        }
    
    config_data = hass.data[DOMAIN]
    url = config_data.get("overseerr_url")
    api_key = config_data.get("overseerr_api_key")
    
    if not url or not api_key:
        return {
            "action": "connection_error",
            "error": "Overseerr configuration missing",
            "message": "Overseerr URL or API key is not configured"
        }
    
    api = OverseerrAPI(url, api_key)
    search_results = await api.search_media(query)
    
    if not search_results or not search_results.get("results"):
        return {
            "action": "not_found",
            "searched_query": query,
            "message": f"No results found for '{query}'"
        }
    
    return {
        "action": "search_results",
        "query": query,
        "results": search_results["results"][:10],  # Limit to first 10 results
        "total_results": len(search_results["results"]),
        "message": f"Found {len(search_results['results'])} results for '{query}'"
    }

async def handle_get_media_details(hass: HomeAssistant, call: ServiceCall) -> Dict[str, Any]:
    """Handle getting detailed media information."""
    media_type = call.data.get("media_type")
    tmdb_id = call.data.get("tmdb_id")
    
    if not media_type or not tmdb_id:
        return {
            "action": "missing_parameters",
            "error": "Missing media_type or tmdb_id",
            "message": "Please provide both media_type and tmdb_id"
        }
    
    config_data = hass.data[DOMAIN]
    url = config_data.get("overseerr_url")
    api_key = config_data.get("overseerr_api_key")
    
    if not url or not api_key:
        return {
            "action": "connection_error",
            "error": "Overseerr configuration missing",
            "message": "Overseerr URL or API key is not configured"
        }
    
    api = OverseerrAPI(url, api_key)
    details = await api.get_media_details(media_type, int(tmdb_id))
    
    if not details:
        return {
            "action": "not_found",
            "media_type": media_type,
            "tmdb_id": tmdb_id,
            "message": f"Could not find details for {media_type} with TMDB ID {tmdb_id}"
        }
    
    return {
        "action": "details_found",
        "media_type": media_type,
        "tmdb_id": tmdb_id,
        "details": details,
        "message": f"Found details for {media_type} with TMDB ID {tmdb_id}"
    }