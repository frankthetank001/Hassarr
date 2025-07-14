# File: services.py
# Note: Keep this filename comment for navigation and organization

import logging
import aiohttp
import json
from urllib.parse import urljoin, urlparse, quote
from typing import Dict, Any, Optional
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class OverseerrAPI:
    """Simple Overseerr API client."""
    
    def __init__(self, url: str, api_key: str, session: aiohttp.ClientSession):
        self.base_url = url
        self.api_key = api_key
        self.headers = {'X-Api-Key': api_key}
        self.session = session
        
        # Ensure URL has scheme
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            self.base_url = f"https://{url}"
    
    async def _make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Optional[Dict]:
        """Make async HTTP request to Overseerr API."""
        url = urljoin(self.base_url, endpoint)
        try:
            async with self.session.request(method, url, headers=self.headers, json=data) as response:
                if response.status in [200, 201, 204]:
                    content = await response.text()
                    if not content.strip():
                        # Empty response (common for DELETE requests with 204)
                        return {}
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as json_err:
                        _LOGGER.error(f"Invalid JSON response from {url}: {json_err}")
                        _LOGGER.debug(f"Response content: {content[:200]}...")
                        return None
                else:
                    _LOGGER.error(f"API request failed: {response.status} - {await response.text()}")
                    return None
        except Exception as e:
            _LOGGER.error(f"Request failed: {e}")
            return None
    
    async def get_requests(self) -> Optional[Dict]:
        """Get all active requests."""
        endpoint = "api/v1/request"
        return await self._make_request(endpoint)
    
    async def search_media(self, query: str) -> Optional[Dict]:
        """Search for media in Overseerr."""
        encoded_query = quote(query)
        endpoint = f"api/v1/search?query={encoded_query}"
        return await self._make_request(endpoint)
    
    async def get_media_details(self, media_type: str, tmdb_id: int) -> Optional[Dict]:
        """Get detailed media information from TMDB."""
        endpoint = f"api/v1/{media_type}/{tmdb_id}"
        return await self._make_request(endpoint)
    
    async def add_media_request(self, media_type: str, tmdb_id: int, user_id: int = None) -> Optional[Dict]:
        """Add a media request to Overseerr."""
        endpoint = "api/v1/request"
        data = {
            "mediaType": media_type,
            "mediaId": tmdb_id
        }
        if user_id:
            data["userId"] = user_id
        return await self._make_request(endpoint, method="POST", data=data)

class LLMResponseBuilder:
    """Build structured responses for LLM consumption."""
    
    @staticmethod
    def build_status_response(
        action: str,
        title: str = None,
        search_result: Dict = None,
        media_details: Dict = None,
        requests_data: Dict = None,
        message: str = None
    ) -> Dict:
        """Build a structured status check response for LLM."""
        
        if action == "missing_title":
            return {
                "action": "missing_title",
                "error": "No search title provided",
                "message": "Please provide a movie or TV show title to search for"
            }
        
        if action == "connection_error":
            return {
                "action": "connection_error",
                "error": "Failed to connect to Overseerr server",
                "searched_title": title,
                "message": "Connection error - check Overseerr configuration and server status"
            }
        
        if action == "not_found":
            return {
                "action": "not_found",
                "searched_title": title,
                "message": f"No movies or TV shows found matching '{title}'"
            }
        
        if action == "found_media" and search_result:
            # Find matching request in active requests
            matching_request = None
            if requests_data and requests_data.get("results"):
                for req in requests_data["results"]:
                    if req.get("media", {}).get("tmdbId") == search_result.get("id"):
                        matching_request = req
                        break
            
            # Build the structured response
            response = {
                "action": "found_media",
                "llm_instructions": "Focus on request status, who requested it, download progress, and content overview unless asked for specific details.",
                "searched_title": title,
                "primary_result": {
                    "search_info": {
                        "title": search_result.get("title") or search_result.get("name", "Unknown"),
                        "type": search_result.get("mediaType", "unknown"),
                        "tmdb_id": search_result.get("id", 0),
                        "media_id": search_result.get("mediaInfo", {}).get("id") if search_result.get("mediaInfo") else None,
                        "status": search_result.get("mediaInfo", {}).get("status") if search_result.get("mediaInfo") else None,
                        "status_text": LLMResponseBuilder._get_status_text(search_result.get("mediaInfo", {}).get("status")) if search_result.get("mediaInfo") else "Not Requested",
                        "release_date": search_result.get("releaseDate") or search_result.get("firstAirDate", "Unknown"),
                        "rating": search_result.get("voteAverage", 0),
                        "request_details": LLMResponseBuilder._build_request_details(matching_request)
                    },
                    "content_details": {
                        "overview": media_details.get("overview", "Overview not available")[:300] if media_details else "Overview not available",
                        "genres": [genre["name"] for genre in media_details.get("genres", [])][:3] if media_details else [],
                        "media_specific": LLMResponseBuilder._build_media_specific_info(search_result, media_details)
                    }
                },
                "message": f"Found detailed information for '{search_result.get('title') or search_result.get('name')}'. Focus on request status, who requested it, download progress, and content overview unless asked for specific details."
            }
            
            return response
        
        return {
            "action": "error",
            "message": "Unexpected error occurred"
        }
    
    @staticmethod
    def _get_status_text(status_code: int) -> str:
        """Convert status code to human-readable text."""
        status_map = {
            1: "Unknown",
            2: "Pending Approval", 
            3: "Processing/Downloading",
            4: "Partially Available",
            5: "Available in Library"
        }
        return status_map.get(status_code, f"Status {status_code}")
    
    @staticmethod
    def _build_request_details(matching_request: Dict) -> Dict:
        """Build request details from matching request data."""
        if not matching_request:
            return {
                "requested_by": "Information not available",
                "request_date": "Unknown",
                "request_id": None
            }
        
        return {
            "requested_by": matching_request.get("requestedBy", {}).get("displayName") or 
                           matching_request.get("requestedBy", {}).get("username", "Unknown User"),
            "request_date": matching_request.get("createdAt", "Unknown"),
            "request_id": matching_request.get("id")
        }
    
    @staticmethod
    def _build_media_specific_info(search_result: Dict, media_details: Dict) -> Dict:
        """Build media type specific information."""
        media_type = search_result.get("mediaType", "unknown")
        
        if media_type == "tv" and media_details:
            return {
                "seasons": media_details.get("numberOfSeasons", 0),
                "episodes": media_details.get("numberOfEpisodes", 0),
                "episode_runtime": media_details.get("episodeRunTime", [None])[0],
                "series_status": media_details.get("status", "Unknown"),
                "networks": media_details.get("networks", [{}])[0].get("name", "Unknown") if media_details.get("networks") else "Unknown"
            }
        elif media_type == "movie" and media_details:
            return {
                "runtime": media_details.get("runtime", 0),
                "budget": media_details.get("budget", 0),
                "revenue": media_details.get("revenue", 0),
                "production_companies": media_details.get("productionCompanies", [{}])[0].get("name", "Unknown") if media_details.get("productionCompanies") else "Unknown"
            }
        
        return {}
    
    @staticmethod
    def _extract_year(search_result: Dict) -> str:
        """Extract year from release date."""
        release_date = search_result.get("releaseDate") or search_result.get("firstAirDate")
        if release_date and len(release_date) >= 4:
            return release_date[:4]
        return "Unknown"
    
    @staticmethod
    def build_add_media_response(
        action: str,
        title: str = None,
        search_result: Dict = None,
        media_details: Dict = None,
        add_result: Dict = None,
        message: str = None
    ) -> Dict:
        """Build a structured add media response for LLM."""
        
        if action == "missing_title":
            return {
                "action": "missing_title",
                "error": "No search title provided",
                "message": "Please provide a movie or TV show title to search for"
            }
        
        if action == "connection_error":
            return {
                "action": "connection_error",
                "error": "Failed to connect to Overseerr server",
                "searched_title": title,
                "message": "Connection error - check Overseerr configuration and server status"
            }
        
        if action == "not_found":
            return {
                "action": "not_found",
                "searched_title": title,
                "message": f"No movies or TV shows found matching '{title}'"
            }
        
        if action == "media_already_exists" and search_result:
            return {
                "action": "media_already_exists",
                "media_type": search_result.get("mediaType", "unknown"),
                "searched_title": title,
                "media": {
                    "title": search_result.get("title") or search_result.get("name", "Unknown"),
                    "tmdb_id": search_result.get("id", 0),
                    "status": search_result.get("mediaInfo", {}).get("status") if search_result.get("mediaInfo") else None,
                    "status_text": LLMResponseBuilder._get_status_text(search_result.get("mediaInfo", {}).get("status")) if search_result.get("mediaInfo") else "Not Requested",
                    "year": LLMResponseBuilder._extract_year(search_result),
                    "rating": search_result.get("voteAverage", 0),
                    "overview_short": media_details.get("overview", "")[:150] + "..." if media_details and len(media_details.get("overview", "")) > 150 else media_details.get("overview", "") if media_details else "",
                    "genres": [genre["name"] for genre in media_details.get("genres", [])][:2] if media_details else []
                },
                "message": f"{search_result.get('mediaType', 'Media').title()} already exists in Overseerr"
            }
        
        if action == "media_added_successfully" and search_result:
            return {
                "action": "media_added_successfully",
                "media_type": search_result.get("mediaType", "unknown"),
                "searched_title": title,
                "media": {
                    "title": search_result.get("title") or search_result.get("name", "Unknown"),
                    "tmdb_id": search_result.get("id", 0),
                    "status": 2,  # Newly added items are typically "Pending Approval"
                    "status_text": "Pending Approval",
                    "year": LLMResponseBuilder._extract_year(search_result),
                    "rating": search_result.get("voteAverage", 0),
                    "overview_short": media_details.get("overview", "")[:150] + "..." if media_details and len(media_details.get("overview", "")) > 150 else media_details.get("overview", "") if media_details else "",
                    "genres": [genre["name"] for genre in media_details.get("genres", [])][:2] if media_details else []
                },
                "message": f"{search_result.get('mediaType', 'Media').title()} successfully added to Overseerr"
            }
        
        if action == "media_add_failed":
            return {
                "action": "media_add_failed",
                "error": "Media could not be added to Overseerr",
                "searched_title": title,
                "message": "Media request failed - check Overseerr configuration and permissions"
            }
        
        return {
            "action": "error",
            "message": "Unexpected error occurred"
        }