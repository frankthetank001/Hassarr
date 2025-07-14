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
    
    async def delete_media(self, media_id: int) -> Optional[Dict]:
        """Delete media from Overseerr by media ID."""
        endpoint = f"api/v1/media/{media_id}/file"
        return await self._make_request(endpoint, method="DELETE")

class LLMResponseBuilder:
    """Build structured responses for LLM consumption."""
    
    @staticmethod
    def build_status_response(
        action: str,
        title: str = None,
        search_result: Dict = None,
        media_details: Dict = None,
        requests_data: Dict = None,
        message: str = None,
        error_details: str = None
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
                "error_details": error_details,
                "searched_title": title,
                "message": "Connection error - check Overseerr configuration and server status",
                "troubleshooting": [
                    "Verify Overseerr server is running",
                    "Check URL and API key configuration", 
                    "Confirm network connectivity",
                    "Check Home Assistant logs for details"
                ]
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
        message: str = None,
        error_details: str = None
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
                "error_details": error_details,
                "searched_title": title,
                "message": "Connection error - check Overseerr configuration and server status",
                "troubleshooting": [
                    "Verify Overseerr server is running",
                    "Check URL and API key configuration", 
                    "Confirm network connectivity",
                    "Check Home Assistant logs for details"
                ]
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
                    "genres": [genre["name"] for genre in media_details.get("genres", [])][:2] if media_details else [],
                    "watch_url": search_result.get('mediaInfo', {}).get('mediaUrl')
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
                    "year": LLMResponseBuilder._extract_year(search_result),
                    "rating": search_result.get("voteAverage", 0),
                    "overview_short": media_details.get("overview", "")[:150] + "..." if media_details and len(media_details.get("overview", "")) > 150 else media_details.get("overview", "") if media_details else "",
                    "genres": [genre["name"] for genre in media_details.get("genres", [])][:2] if media_details else []
                },
                "next_steps": {
                    "suggestion": "Would you like me to check the status of this media request?",
                    "action_prompt": f"Ask me: 'What's the status of {search_result.get('title') or search_result.get('name', title)}?'",
                    "typical_workflow": [
                        "Request submitted to Overseerr",
                        "Admin approval (if required)",
                        "Download begins",
                        "Media available in library"
                    ]
                },
                "message": f"{search_result.get('mediaType', 'Media').title()} successfully added to Overseerr"
            }
        
        if action == "media_add_failed":
            return {
                "action": "media_add_failed",
                "error": "Media could not be added to Overseerr",
                "error_details": error_details,
                "searched_title": title,
                "message": "Media request failed - check Overseerr configuration and permissions",
                "troubleshooting": [
                    "Check if user has permission to make requests",
                    "Verify media is available on configured indexers",
                    "Confirm Overseerr quality profiles are set up",
                    "Check Overseerr logs for specific errors"
                ]
            }
        
        return {
            "action": "error",
            "message": "Unexpected error occurred"
        }
    
    @staticmethod
    def build_search_response(
        action: str,
        query: str = None,
        search_data: Dict = None,
        error_details: str = None
    ) -> Dict:
        """Build a structured search response for LLM."""
        
        if action == "missing_query":
            return {
                "action": "missing_query",
                "error": "No search query provided",
                "message": "Please provide a search term to look for movies or TV shows"
            }
        
        if action == "connection_error":
            return {
                "action": "connection_error",
                "error": "Failed to connect to Overseerr server",
                "error_details": error_details,
                "searched_query": query,
                "message": "Connection error - check Overseerr configuration and server status",
                "troubleshooting": [
                    "Verify Overseerr server is running",
                    "Check URL and API key configuration",
                    "Confirm network connectivity",
                    "Check Home Assistant logs for details"
                ]
            }
        
        if action == "no_results":
            return {
                "action": "no_results",
                "searched_query": query,
                "total_results": 0,
                "message": f"No movies or TV shows found matching '{query}'"
            }
        
        if action == "search_results" and search_data:
            results = search_data.get("results", [])
            total_results = search_data.get("totalResults", len(results))
            
            # Process each result for LLM consumption
            processed_results = []
            for result in results[:10]:  # Limit to first 10 results
                processed_result = {
                    "title": result.get("title") or result.get("name", "Unknown"),
                    "media_type": result.get("mediaType", "unknown"),
                    "tmdb_id": result.get("id", 0),
                    "year": LLMResponseBuilder._extract_year(result),
                    "rating": result.get("voteAverage", 0),
                    "overview_short": result.get("overview", "")[:200] + "..." if result.get("overview", "") and len(result.get("overview", "")) > 200 else result.get("overview", "No overview available"),
                    "poster_path": result.get("posterPath"),
                    "backdrop_path": result.get("backdropPath"),
                    "popularity": result.get("popularity", 0),
                    "adult": result.get("adult", False),
                    "original_language": result.get("originalLanguage", "en"),
                    "status_in_overseerr": {
                        "available": result.get("mediaInfo") is not None,
                        "status": result.get("mediaInfo", {}).get("status") if result.get("mediaInfo") else None,
                        "status_text": LLMResponseBuilder._get_status_text(result.get("mediaInfo", {}).get("status")) if result.get("mediaInfo") else "Not in library"
                    }
                }
                
                # Add media-specific info
                if result.get("mediaType") == "tv":
                    processed_result["tv_info"] = {
                        "first_air_date": result.get("firstAirDate"),
                        "origin_country": result.get("originCountry", [])
                    }
                else:
                    processed_result["movie_info"] = {
                        "release_date": result.get("releaseDate"),
                        "original_title": result.get("originalTitle")
                    }
                
                processed_results.append(processed_result)
            
            return {
                "action": "search_results",
                "searched_query": query,
                "total_results": total_results,
                "results_shown": len(processed_results),
                "results": processed_results,
                "llm_instructions": "Present the search results to the user in a clear, organized way. Focus on title, year, type, and rating. Mention if any are already in their library. Ask which one they'd like more information about or want to add.",
                "suggested_followups": [
                    f"Tell me more about [specific title]",
                    f"Add [specific title] to my library",
                    f"What's the status of [specific title]?"
                ],
                "message": f"Found {total_results} results for '{query}'. Showing top {len(processed_results)} matches."
            }
        
        return {
            "action": "error",
            "message": "Unexpected error occurred in search"
        }
    
    @staticmethod
    def build_remove_media_response(
        action: str,
        title: str = None,
        media_id: str = None,
        search_result: Dict = None,
        error_details: str = None
    ) -> Dict:
        """Build a structured remove media response for LLM."""
        
        if action == "missing_params":
            return {
                "action": "missing_params",
                "error": "No title or media_id provided",
                "message": "Please provide either a title to search for or a specific media_id to remove"
            }
        
        if action == "connection_error":
            return {
                "action": "connection_error",
                "error": "Failed to connect to Overseerr server",
                "error_details": error_details,
                "searched_title": title,
                "media_id": media_id,
                "message": "Connection error - check Overseerr configuration and server status",
                "troubleshooting": [
                    "Verify Overseerr server is running",
                    "Check URL and API key configuration",
                    "Confirm network connectivity",
                    "Check Home Assistant logs for details"
                ]
            }
        
        if action == "media_not_found":
            return {
                "action": "media_not_found",
                "searched_title": title,
                "message": f"Could not find '{title}' in your Overseerr library to remove"
            }
        
        if action == "not_in_library":
            return {
                "action": "not_in_library", 
                "searched_title": title,
                "media": {
                    "title": search_result.get("title") or search_result.get("name", "Unknown"),
                    "tmdb_id": search_result.get("id", 0),
                    "year": LLMResponseBuilder._extract_year(search_result),
                    "rating": search_result.get("voteAverage", 0)
                } if search_result else None,
                "message": f"'{title}' is not in your Overseerr library, so it cannot be removed"
            }
        
        if action == "no_media_id":
            return {
                "action": "no_media_id",
                "searched_title": title,
                "media": {
                    "title": search_result.get("title") or search_result.get("name", "Unknown"),
                    "tmdb_id": search_result.get("id", 0),
                    "year": LLMResponseBuilder._extract_year(search_result),
                    "status_text": LLMResponseBuilder._get_status_text(search_result.get("mediaInfo", {}).get("status")) if search_result.get("mediaInfo") else "Unknown"
                } if search_result else None,
                "message": f"Found '{title}' but couldn't get the media ID needed for removal",
                "troubleshooting": [
                    "Try using check_media_status to get more details",
                    "Media might be in an unusual state",
                    "Check Overseerr web interface for status"
                ]
            }
        
        if action == "removal_failed":
            return {
                "action": "removal_failed",
                "media_id": media_id,
                "searched_title": title,
                "error": "Failed to remove media from Overseerr",
                "error_details": error_details,
                "message": f"Could not remove media ID {media_id} from Overseerr",
                "troubleshooting": [
                    "Check if media ID exists and is valid",
                    "Verify user has permission to delete media",
                    "Check if media is currently downloading",
                    "Look at Overseerr server logs for details"
                ]
            }
        
        if action == "media_removed":
            return {
                "action": "media_removed",
                "media_id": media_id,
                "searched_title": title,
                "media": {
                    "title": search_result.get("title") or search_result.get("name", "Unknown"),
                    "tmdb_id": search_result.get("id", 0),
                    "year": LLMResponseBuilder._extract_year(search_result),
                    "media_type": search_result.get("mediaType", "unknown")
                } if search_result else None,
                "message": f"Successfully removed {search_result.get('title') or search_result.get('name', title) if search_result else title} from Overseerr",
                "next_steps": {
                    "suggestion": "The media has been removed from your download queue and library.",
                    "note": "If files were already downloaded, you may need to manually delete them from your media server."
                }
            }
        
        return {
            "action": "error",
            "message": "Unexpected error occurred in remove media operation"
        }