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
        # First delete the files
        file_endpoint = f"api/v1/media/{media_id}/file"
        file_result = await self._make_request(file_endpoint, method="DELETE")
        
        # Only delete the media record if file deletion was successful
        # This prevents orphaned files with no tracking record
        if file_result is not None:
            media_endpoint = f"api/v1/media/{media_id}"
            media_result = await self._make_request(media_endpoint, method="DELETE")
            
            return {
                "file_deleted": True, 
                "record_deleted": media_result is not None
            }
        
        # File deletion failed, don't touch the record
        return None
    
    async def get_jobs(self) -> Optional[Dict]:
        """Get all available jobs from Overseerr."""
        endpoint = "api/v1/settings/jobs"
        return await self._make_request(endpoint)
    
    async def run_job(self, job_id: str) -> Optional[Dict]:
        """Run a specific job by ID."""
        endpoint = f"api/v1/settings/jobs/{job_id}/run"
        return await self._make_request(endpoint, method="POST")

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
            5: "Available in Library",
            7: "Deleted"
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

    @staticmethod
    def build_active_requests_response(
        action: str,
        requests_data: Dict = None,
        error_details: str = None
    ) -> Dict:
        """Build LLM-optimized response for active requests."""
        
        if action == "connection_error":
            return {
                "action": "connection_error",
                "message": "Could not connect to Overseerr to get active requests",
                "error_details": error_details,
                "troubleshooting": [
                    "Check Overseerr server connectivity",
                    "Verify API key and URL configuration",
                    "Ensure Overseerr service is running"
                ],
                "next_steps": {
                    "suggestion": "Try running test_connection service first to verify setup"
                }
            }
        
        if action == "requests_found":
            results = requests_data.get("results", [])
            
            # Categorize ALL requests by status (corrected mapping)
            pending_requests = []       # Status 2: Pending Approval
            processing_requests = []    # Status 3: Processing/Downloading  
            partially_available = []    # Status 4: Partially Available
            available_requests = []     # Status 5: Available in Library
            failed_requests = []        # Status 7: Deleted/Failed
            other_requests = []         # Status 1: Unknown and other codes
            
            for request in results:
                status = request.get("status", 0)
                if status == 1:
                    other_requests.append(request)  # Unknown status
                elif status == 2:
                    pending_requests.append(request)  # Pending Approval
                elif status == 3:
                    processing_requests.append(request)  # Processing/Downloading
                elif status == 4:
                    partially_available.append(request)  # Partially Available
                elif status == 5:
                    available_requests.append(request)  # Available in Library
                elif status == 7:
                    failed_requests.append(request)  # Deleted
                else:
                    other_requests.append(request)
            
            # Sort each category by createdAt date (most recent first)
            for request_list in [processing_requests, pending_requests, available_requests, 
                               partially_available, failed_requests, other_requests]:
                request_list.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
            
            # Build response prioritizing active requests (processing + pending)
            active_requests = []
            resolved_requests = []
            
            # Add processing requests first (highest priority)
            for request in processing_requests:
                active_requests.append(LLMResponseBuilder._build_request_info(request))
            
            # Add pending requests 
            for request in pending_requests:
                if len(active_requests) < 10:
                    active_requests.append(LLMResponseBuilder._build_request_info(request))
            
            # Add a few resolved/completed requests for context
            for request in available_requests[:3]:  # Show up to 3 recent completed
                resolved_requests.append(LLMResponseBuilder._build_request_info(request))
            
            # Count totals
            total_requests = len(results)
            processing_count = len(processing_requests)
            pending_count = len(pending_requests)
            available_count = len(available_requests)
            failed_count = len(failed_requests)
            partially_available_count = len(partially_available)
            other_count = len(other_requests)
            
            # Build status breakdown message
            status_breakdown = []
            if processing_count > 0:
                status_breakdown.append(f"{processing_count} downloading")
            if pending_count > 0:
                status_breakdown.append(f"{pending_count} pending approval")
            if available_count > 0:
                status_breakdown.append(f"{available_count} completed")
            if failed_count > 0:
                status_breakdown.append(f"{failed_count} failed")
            if partially_available_count > 0:
                status_breakdown.append(f"{partially_available_count} partially available")
            if other_count > 0:
                status_breakdown.append(f"{other_count} other status")
            
            breakdown_text = ", ".join(status_breakdown) if status_breakdown else "no requests"
            
            return {
                "action": "requests_found",
                "total_requests": total_requests,
                "status_breakdown": {
                    "processing_count": processing_count,
                    "pending_count": pending_count, 
                    "available_count": available_count,
                    "failed_count": failed_count,
                    "partially_available_count": partially_available_count,
                    "other_count": other_count
                },
                "active_requests": active_requests,
                "recent_completed": resolved_requests,
                "message": f"Found {total_requests} total requests ({breakdown_text})",
                "llm_instructions": {
                    "response_guidance": "Focus on active requests (downloading/pending) but mention the status breakdown to explain all request counts",
                    "priority_note": "Processing requests are shown first, then pending requests",
                    "status_meanings": {
                        "processing": "Currently downloading or being processed", 
                        "pending": "Waiting for approval",
                        "available": "Completed and available in library",
                        "failed": "Failed to download or unavailable",
                        "partially_available": "Some content available, some missing"
                    },
                    "completed_note": "Recent completed requests are included for context"
                },
                "next_steps": {
                    "suggestion": "Use check_media_status with a specific title for detailed progress information",
                    "note": "Processing requests are actively downloading and will complete automatically"
                }
            }
        
        if action == "no_requests":
            return {
                "action": "no_requests",
                "message": "No requests found in Overseerr",
                "total_requests": 0,
                "status_breakdown": {
                    "processing_count": 0,
                    "pending_count": 0,
                    "available_count": 0, 
                    "failed_count": 0,
                    "partially_available_count": 0,
                    "other_count": 0
                },
                "active_requests": [],
                "recent_completed": [],
                "next_steps": {
                    "suggestion": "Add media using the add_media service to start new downloads",
                    "note": "This is good - it means your request history is empty!"
                }
            }
        
        return {
            "action": "error",
            "message": "Unexpected error occurred in get active requests operation"
        }

    @staticmethod
    def _build_request_info(request: Dict) -> Dict:
        """Build formatted request information for LLM consumption."""
        media = request.get("media", {})
        
        # Determine media type and title
        media_type = "movie" if request.get("type") == "movie" else "tv"
        title = media.get("title") or media.get("name", "Unknown Title")
        
        # Format release date/year
        release_date = media.get("releaseDate") or media.get("firstAirDate", "")
        year = release_date[:4] if release_date else "Unknown"
        
        # Status mapping (corrected)
        status_map = {
            1: "unknown",
            2: "pending", 
            3: "processing",
            4: "partially_available",
            5: "available",
            7: "unavailable"
        }
        
        status = status_map.get(request.get("status", 1), "unknown")
        
        # Format creation date
        created_at = request.get("createdAt", "")
        if created_at:
            # Convert ISO date to human readable
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_date = dt.strftime("%Y-%m-%d %H:%M")
            except:
                created_date = created_at
        else:
            created_date = "Unknown"
        
        return {
            "title": title,
            "year": year,
            "media_type": media_type,
            "status": status,
            "tmdb_id": media.get("tmdbId", 0),
            "media_id": media.get("id", 0),
            "request_id": request.get("id", 0),
            "requested_date": created_date,
            "requested_by": request.get("requestedBy", {}).get("displayName", "Unknown User"),
            "overview": media.get("overview", "")[:200] + "..." if len(media.get("overview", "")) > 200 else media.get("overview", "")
        }

    @staticmethod
    def build_run_job_response(
        action: str,
        job_id: str = None,
        job_name: str = None,
        error_details: str = None
    ) -> Dict:
        """Build LLM-optimized response for running jobs."""
        
        if action == "connection_error":
            return {
                "action": "connection_error",
                "job_id": job_id,
                "message": "Could not connect to Overseerr to run job",
                "error_details": error_details,
                "troubleshooting": [
                    "Check Overseerr server connectivity",
                    "Verify API key and URL configuration",
                    "Ensure Overseerr service is running"
                ],
                "next_steps": {
                    "suggestion": "Try running test_connection service first to verify setup"
                }
            }
        
        if action == "job_not_found":
            return {
                "action": "job_not_found",
                "job_id": job_id,
                "message": f"Job '{job_id}' not found in Overseerr",
                "error_details": error_details,
                "troubleshooting": [
                    "Check if the job ID is spelled correctly",
                    "Use the get_active_requests service to see available jobs",
                    "Verify the job exists in Overseerr settings"
                ],
                "next_steps": {
                    "suggestion": "Check the Jobs Status sensor for available job IDs"
                }
            }
        
        if action == "job_started":
            return {
                "action": "job_started",
                "job_id": job_id,
                "job_name": job_name,
                "message": f"Successfully triggered job: {job_name or job_id}",
                "next_steps": {
                    "suggestion": "Monitor the Jobs Status sensor to see when the job completes",
                    "note": "The job is now running in the background on your Overseerr server"
                }
            }
        
        if action == "job_run_failed":
            return {
                "action": "job_run_failed",
                "job_id": job_id,
                "message": f"Failed to run job '{job_id}'",
                "error_details": error_details,
                "troubleshooting": [
                    "Job may already be running",
                    "Check Overseerr server logs for details",
                    "Verify user permissions for running jobs"
                ],
                "next_steps": {
                    "suggestion": "Wait a moment and check the Jobs Status sensor to see if the job is running"
                }
            }
        
        return {
            "action": "error",
            "message": "Unexpected error occurred in run job operation"
        }