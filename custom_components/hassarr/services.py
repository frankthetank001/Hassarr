# File: services.py
# Note: Keep this filename comment for navigation and organization

import logging
import aiohttp
import json
from urllib.parse import urljoin, urlparse, quote, quote_plus
from typing import Dict, Any, Optional
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class OverseerrStatusMaps:
    """Centralized status mappings for Overseerr API responses."""
    
    # Media Status (mediaInfo.status and mediaInfo.status4k) - Based on observed behavior
    # Used for overall media status in search results and download progress
    MEDIA_STATUS = {
        1: "unknown",
        2: "pending", 
        3: "processing",        # ⭐ OBSERVED: The Godfather downloading
        4: "partially_available",
        5: "available",         # ⭐ OBSERVED: Ice Road completed  
        7: "failed"
    }
    
    # Request Status (request.status and season.status) - Used for request approval status
    # Status 2 = Approved (which means downloading/processing)
    REQUEST_STATUS = {
        1: "pending",
        2: "approved",          # ⭐ APPROVED = Currently downloading/processing
        3: "declined",
        4: "failed",
        5: "available"          # ⭐ OBSERVED: Ice Road completed
    }
    
    # Human-readable text for media status
    MEDIA_STATUS_TEXT = {
        1: "Unknown",
        2: "Pending Approval",
        3: "Processing/Downloading",    # ⭐ CORRECTED: Active downloads
        4: "Partially Available",
        5: "Available in Library",      # ⭐ CORRECTED: Completed  
        7: "Failed/Unavailable"
    }
    
    # Human-readable text for request status
    REQUEST_STATUS_TEXT = {
        1: "Pending Approval",
        2: "Approved & Downloading",  # ⭐ APPROVED = Currently downloading/processing
        3: "Declined", 
        4: "Failed",
        5: "Available"          # ⭐ ADDED: Missing status
    }
    
    @staticmethod
    def get_media_status(status_code: int) -> str:
        """Get media status string from code."""
        return OverseerrStatusMaps.MEDIA_STATUS.get(status_code, "unknown")
    
    @staticmethod
    def get_media_status_text(status_code: int) -> str:
        """Get human-readable media status text from code."""
        return OverseerrStatusMaps.MEDIA_STATUS_TEXT.get(status_code, f"Status {status_code}")
    
    @staticmethod
    def get_request_status(status_code: int) -> str:
        """Get request status string from code."""
        return OverseerrStatusMaps.REQUEST_STATUS.get(status_code, "unknown")
    
    @staticmethod
    def get_request_status_text(status_code: int) -> str:
        """Get human-readable request status text from code."""
        return OverseerrStatusMaps.REQUEST_STATUS_TEXT.get(status_code, f"Status {status_code}")
    
    @staticmethod
    def is_actively_processing(media_status: int) -> bool:
        """Check if media is actively downloading/processing."""
        return media_status == 3  # PROCESSING status (corrected)
    
    @staticmethod
    def is_available(media_status: int) -> bool:
        """Check if media is available in library."""
        return media_status == 5  # AVAILABLE status (corrected)

class OverseerrAPI:
    """Simple Overseerr API client."""
    
    def __init__(self, url: str, api_key: str, session: aiohttp.ClientSession):
        self.base_url = url
        self.api_key = api_key
        self.headers = {'X-Api-Key': api_key}
        self.session = session
        self.last_error = None  # Store last API error for detailed error reporting
        
        # Ensure URL has scheme
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            self.base_url = f"https://{url}"
    
    @staticmethod
    def _encode_query_param(query: str) -> str:
        """Encode query parameters for Overseerr API with aggressive URL encoding."""
        # Replace colons manually before encoding
        query = str(query).replace(':', ' ')
        # Use quote() instead of quote_plus() to get %20 for spaces
        return quote(query, safe='')
    
    @staticmethod
    def _encode_path_param(param: str) -> str:
        """Encode path parameters for Overseerr API."""
        # Encode all characters except alphanumeric
        return quote(str(param), safe='')
    
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
                        error_text = f"Invalid JSON response from {url}: {json_err}"
                        _LOGGER.error(error_text)
                        _LOGGER.debug(f"Response content: {content[:200]}...")
                        # Store the error for caller to access
                        self.last_error = error_text
                        return None
                else:
                    error_text = await response.text()
                    full_error = f"API request failed: {response.status} - {error_text}"
                    _LOGGER.error(full_error)
                    # Store the detailed error for caller to access
                    self.last_error = error_text
                    return None
        except Exception as e:
            error_text = f"Request failed: {e}"
            _LOGGER.error(error_text)
            # Store the error for caller to access
            self.last_error = error_text
            return None
    
    async def get_requests(self, filter_type: str = "all", take: int = 100, skip: int = 0) -> Optional[Dict]:
        """Get requests with optional filtering and pagination.
        
        Args:
            filter_type: Filter type (all, available, partial, allavailable, processing, pending, deleted)
            take: Number of results to return (page size)
            skip: Number of results to skip (for pagination)
        """
        endpoint = f"api/v1/request?take={take}&skip={skip}"
        
        # Get requests with pagination
        result = await self._make_request(endpoint)
        
        # Apply filtering if needed
        if result and filter_type != "all":
            result = self._filter_requests(result, filter_type)
        
        return result
    
    async def get_media(self, filter_type: str = "all", take: int = 20, skip: int = 0, sort: str = "mediaAdded") -> Optional[Dict]:
        """Get media from Overseerr using the /api/v1/media endpoint.
        
        Args:
            filter_type: Filter type (all, available, partial, allavailable, processing, pending, deleted)
            take: Number of results to return (page size)
            skip: Number of results to skip (for pagination)
            sort: Sort order (mediaAdded, title, etc.)
        """
        # Validate filter type
        valid_filters = ["all", "available", "partial", "allavailable", "processing", "pending", "deleted"]
        if filter_type not in valid_filters:
            _LOGGER.warning(f"Invalid filter type '{filter_type}', defaulting to 'all'")
            filter_type = "all"
        
        endpoint = f"api/v1/media?filter={filter_type}&take={take}&skip={skip}&sort={sort}"
        return await self._make_request(endpoint)
    
    def _filter_requests(self, requests_data: Dict, filter_type: str) -> Dict:
        """Filter requests client-side based on media status.
        
        Args:
            requests_data: Raw requests data from API
            filter_type: Filter type to apply
        """
        if not requests_data or not requests_data.get("results"):
            return requests_data
        
        filtered_results = []
        
        for request in requests_data["results"]:
            media = request.get("media", {})
            media_status = media.get("status", 1)
            
            # Apply filter based on media status
            include_request = False
            
            if filter_type == "pending":
                include_request = media_status == 2
            elif filter_type == "processing":
                include_request = media_status == 3
            elif filter_type == "partial":
                include_request = media_status == 4
            elif filter_type == "available":
                include_request = media_status == 5
            elif filter_type == "allavailable":
                include_request = media_status in [4, 5]  # Partial or fully available
            elif filter_type == "deleted":
                include_request = media_status == 7
            else:
                include_request = True  # "all" or unknown filter
            
            if include_request:
                filtered_results.append(request)
        
        # Update the results and counts
        filtered_data = requests_data.copy()
        filtered_data["results"] = filtered_results
        filtered_data["totalResults"] = len(filtered_results)
        filtered_data["pageInfo"] = {
            "page": 1,
            "pages": 1,
            "pageSize": len(filtered_results),
            "results": len(filtered_results)
        }
        
        return filtered_data
    
    async def search_media(self, query: str) -> Optional[Dict]:
        """Search for media in Overseerr."""
        encoded_query = self._encode_query_param(query)
        endpoint = f"api/v1/search?query={encoded_query}"
        full_url = urljoin(self.base_url, endpoint)
        _LOGGER.info(f"Overseerr search: '{query}' -> encoded: '{encoded_query}' -> full URL: '{full_url}'")
        return await self._make_request(endpoint)
    
    async def get_media_details(self, media_type: str, tmdb_id: int) -> Optional[Dict]:
        """Get detailed media information from TMDB."""
        # Encode path parameters
        encoded_media_type = self._encode_path_param(str(media_type))
        encoded_tmdb_id = self._encode_path_param(str(tmdb_id))
        endpoint = f"api/v1/{encoded_media_type}/{encoded_tmdb_id}"
        return await self._make_request(endpoint)
    
    async def add_media_request(self, media_type: str, tmdb_id: int, user_id: int = None, seasons: list = None, is4k: bool = False) -> Optional[Dict]:
        """Add a media request to Overseerr."""
        endpoint = "api/v1/request"
        
        # First, check if this media already exists in Overseerr to get configuration
        existing_request = None
        if media_type == "tv":
            try:
                requests_data = await self.get_requests()
                if requests_data and requests_data.get("results"):
                    for request in requests_data["results"]:
                        media = request.get("media", {})
                        if media.get("tmdbId") == tmdb_id and media.get("mediaType") == "tv":
                            existing_request = request
                            _LOGGER.debug(f"Found existing request for TMDB ID {tmdb_id}: {request.get('id')}")
                            break
            except Exception as e:
                _LOGGER.warning(f"Failed to check existing requests: {e}")
        
        # Build the request data
        data = {
            "mediaType": str(media_type),
            "mediaId": int(tmdb_id)
        }
        
        # Add 4K flag for movies if requested
        if media_type == "movie" and is4k:
            data["is4k"] = True
            _LOGGER.debug(f"Requesting movie in 4K: {data}")
        
        # If we found an existing request, use its configuration
        if existing_request:
            # Copy configuration from existing request
            # data.update({
            #     "tvdbId": existing_request.get("media", {}).get("tvdbId"),
            #     "serverId": existing_request.get("serverId", 0),
            #     "profileId": existing_request.get("profileId"),
            #     "rootFolder": existing_request.get("rootFolder"),
            #     "tags": existing_request.get("tags", [])
            # })
            _LOGGER.debug(f"Using existing request configuration: serverId={data.get('serverId')}, profileId={data.get('profileId')}, rootFolder={data.get('rootFolder')}")
        else:
            # For new requests, use default values
            # data.update({
            #     "serverId": 0,
            #     "tags": []
            # })
            _LOGGER.debug(f"Using default configuration for new request")
        
        # Add user ID
        if user_id:
            data["userId"] = int(user_id)
        
        # For TV shows, add seasons parameter with better validation
        if media_type == "tv":
            # Handle None, empty strings, and empty lists
            if seasons is None or (isinstance(seasons, str) and not seasons.strip()) or (isinstance(seasons, list) and not seasons):
                # Default to season 1 if no seasons specified
                data["seasons"] = [1]
                _LOGGER.debug(f"No seasons specified for TV show, defaulting to season 1")
            else:
                # Use specified seasons (ensure they're integers and valid)
                valid_seasons = []
                for season in seasons:
                    try:
                        season_int = int(season)
                        if season_int >= 1:  # Only accept positive season numbers
                            valid_seasons.append(season_int)
                    except (ValueError, TypeError):
                        _LOGGER.warning(f"Invalid season number: {season}, skipping")
                        continue
                
                # If no valid seasons provided, default to season 1
                if not valid_seasons:
                    _LOGGER.warning(f"No valid seasons found in {seasons}, defaulting to season 1")
                    data["seasons"] = [1]
                else:
                    data["seasons"] = valid_seasons
                    _LOGGER.debug(f"Requesting TV show seasons: {valid_seasons}")
        
        _LOGGER.debug(f"Sending request to Overseerr: {data}")
        result = await self._make_request(endpoint, method="POST", data=data)
        
        # If we get a 500 error and we're requesting seasons, try without seasons as fallback
        if result is None and self.last_error and "500" in str(self.last_error) and media_type == "tv" and "seasons" in data:
            _LOGGER.warning(f"Request with seasons failed (500 error), trying without seasons parameter")
            # Try again without seasons parameter (request entire series)
            fallback_data = {
                "mediaType": str(media_type),
                "mediaId": int(tmdb_id)
            }
            if user_id:
                fallback_data["userId"] = int(user_id)
            
            _LOGGER.debug(f"Fallback request to Overseerr: {fallback_data}")
            result = await self._make_request(endpoint, method="POST", data=fallback_data)
            
            if result is not None:
                _LOGGER.info(f"Fallback request succeeded - requested entire series instead of specific seasons")
        
        return result
    
    async def delete_media(self, media_id: int) -> Optional[Dict]:
        """Delete media from Overseerr by media ID."""
        # Encode path parameter
        encoded_media_id = self._encode_path_param(str(media_id))
        
        # First delete the files
        file_endpoint = f"api/v1/media/{encoded_media_id}/file"
        file_result = await self._make_request(file_endpoint, method="DELETE")
        
        # Delete the media record
        if file_result is not None:
            media_endpoint = f"api/v1/media/{encoded_media_id}"
            media_result = await self._make_request(media_endpoint, method="DELETE")
            
            return {
                "file_deleted": True, 
                "record_deleted": media_result is not None
            }
        
        return None
    
    async def get_jobs(self) -> Optional[Dict]:
        """Get all available jobs from Overseerr."""
        endpoint = "api/v1/settings/jobs"
        return await self._make_request(endpoint)
    
    async def run_job(self, job_id: str) -> Optional[Dict]:
        """Run a specific job by ID."""
        encoded_job_id = self._encode_path_param(job_id)
        endpoint = f"api/v1/settings/jobs/{encoded_job_id}/run"
        _LOGGER.debug(f"Run job: '{job_id}' -> encoded: '{encoded_job_id}' -> endpoint: '{endpoint}'")
        return await self._make_request(endpoint, method="POST")

    async def get_tv_season_analysis(self, tmdb_id: int) -> Optional[Dict]:
        """Analyze existing seasons for a TV show and provide recommendations."""
        try:
            # Get detailed TV show information
            tv_details = await self.get_media_details("tv", tmdb_id)
            if not tv_details:
                return None
            
            total_seasons = tv_details.get("numberOfSeasons", 0)
            if total_seasons == 0:
                return None
            
            # Get current requests to see what seasons are already requested
            requests_data = await self.get_requests()
            if not requests_data:
                return {"total_seasons": total_seasons, "requested_seasons": [], "available_seasons": []}
            
            # Find requests for this specific TV show
            requested_seasons = []
            available_seasons = []
            processing_seasons = []
            
            for request in requests_data.get("results", []):
                media = request.get("media", {})
                if media.get("tmdbId") == tmdb_id and media.get("mediaType") == "tv":
                    # Extract season information from the request
                    seasons = request.get("seasons", [])
                    for season_info in seasons:
                        season_num = season_info.get("seasonNumber")
                        season_status = season_info.get("status")
                        
                        if season_num:
                            requested_seasons.append(season_num)
                            
                            # Categorize by status
                            if season_status == 5:  # Available
                                available_seasons.append(season_num)
                            elif season_status in [2, 3]:  # Pending or Processing
                                processing_seasons.append(season_num)
            
            # Calculate missing seasons
            all_seasons = list(range(1, total_seasons + 1))
            missing_seasons = [s for s in all_seasons if s not in requested_seasons]
            
            return {
                "total_seasons": total_seasons,
                "all_seasons": all_seasons,
                "requested_seasons": sorted(requested_seasons),
                "available_seasons": sorted(available_seasons),
                "processing_seasons": sorted(processing_seasons),
                "missing_seasons": sorted(missing_seasons),
                "tv_details": {
                    "title": tv_details.get("name", "Unknown"),
                    "status": tv_details.get("status", "Unknown"),
                    "air_date": tv_details.get("firstAirDate", "Unknown")
                }
            }
            
        except Exception as e:
            _LOGGER.error(f"Error analyzing TV seasons for {tmdb_id}: {e}")
            return None

class LLMResponseBuilder:
    """Build structured responses for LLM consumption."""
    
    @staticmethod
    def _build_download_info(media_info: Dict) -> Dict:
        """Extract and format download information from mediaInfo."""
        if not media_info:
            return None
            
        download_status = media_info.get("downloadStatus", [])
        download_status_4k = media_info.get("downloadStatus4k", [])
        
        # Combine regular and 4K downloads
        all_downloads = download_status + download_status_4k
        
        if not all_downloads:
            return None
        
        # Process each download
        processed_downloads = []
        total_size = 0
        total_remaining = 0
        
        # Episode-level information extraction
        episodes_info = []
        seasons_downloading = set()
        
        for download in all_downloads:
            size = download.get("size", 0)
            size_left = download.get("sizeLeft", 0)
            
            # Calculate progress
            if size > 0:
                progress_percent = round(((size - size_left) / size) * 100, 1)
                size_downloaded = size - size_left
            else:
                progress_percent = 0
                size_downloaded = 0
            
            # Convert bytes to more readable units
            size_gb = round(size / (1024 ** 3), 2) if size > 0 else 0
            size_left_gb = round(size_left / (1024 ** 3), 2) if size_left > 0 else 0
            downloaded_gb = round(size_downloaded / (1024 ** 3), 2) if size_downloaded > 0 else 0
            
            processed_download = {
                "title": download.get("title", "Unknown"),
                "status": download.get("status", "unknown"),
                "progress_percent": progress_percent,
                "time_left": download.get("timeLeft", "Unknown"),
                "estimated_completion": download.get("estimatedCompletionTime", "Unknown"),
                "size_total_gb": size_gb,
                "size_remaining_gb": size_left_gb,
                "size_downloaded_gb": downloaded_gb,
                "download_id": download.get("downloadId", ""),
                "external_id": download.get("externalId", ""),
                "media_type": download.get("mediaType", "unknown")
            }
            
            # Extract episode information if available
            episode = download.get("episode", {})
            if episode:
                season_number = episode.get("seasonNumber")
                episode_number = episode.get("episodeNumber")
                episode_title = episode.get("title", "Unknown Episode")
                
                if season_number:
                    seasons_downloading.add(season_number)
                
                episode_info = {
                    "season_number": season_number,
                    "episode_number": episode_number,
                    "episode_title": episode_title,
                    "air_date": episode.get("airDate", "Unknown"),
                    "runtime": episode.get("runtime", 0),
                    "overview": episode.get("overview", "")[:100] + "..." if len(episode.get("overview", "")) > 100 else episode.get("overview", ""),
                    "download_progress": progress_percent,
                    "time_left": download.get("timeLeft", "Unknown")
                }
                episodes_info.append(episode_info)
                processed_download["episode_info"] = episode_info
            
            processed_downloads.append(processed_download)
            total_size += size
            total_remaining += size_left
        
        # Calculate overall progress
        if total_size > 0:
            overall_progress = round(((total_size - total_remaining) / total_size) * 100, 1)
        else:
            overall_progress = 0
        
        # Find the download with the least time remaining for "primary" download
        primary_download = None
        if processed_downloads:
            # Try to find one with actual time data, fallback to first
            for download in processed_downloads:
                if download["time_left"] != "Unknown" and download["time_left"]:
                    primary_download = download
                    break
            if not primary_download:
                primary_download = processed_downloads[0]
        
        return {
            "active_downloads": len(all_downloads),
            "overall_progress_percent": overall_progress,
            "total_size_gb": round(total_size / (1024 ** 3), 2) if total_size > 0 else 0,
            "total_remaining_gb": round(total_remaining / (1024 ** 3), 2) if total_remaining > 0 else 0,
            "primary_download": primary_download,
            "all_downloads": processed_downloads,
            "has_4k_downloads": len(download_status_4k) > 0,
            "episodes_downloading": episodes_info,
            "seasons_downloading": sorted(list(seasons_downloading)),
            "episode_count": len(episodes_info)
        }
    
    @staticmethod
    def _extract_season_details_from_request(matching_request: Dict, media_details: Dict = None) -> Dict:
        """Extract detailed season information from request data with comprehensive season context."""
        if not matching_request:
            return None
        
        seasons = matching_request.get("seasons", [])
        if not seasons:
            return None
        
        # Process each season in the request
        season_details = []
        requested_seasons = []
        
        for season in seasons:
            season_number = season.get("seasonNumber")
            season_status = season.get("status")
            created_at = season.get("createdAt", "")
            updated_at = season.get("updatedAt", "")
            
            if season_number:
                requested_seasons.append(season_number)
                
                # Convert season status to human readable
                # Season status uses REQUEST_STATUS mapping, not MEDIA_STATUS
                status_text = OverseerrStatusMaps.get_request_status_text(season_status)
                
                season_info = {
                    "season_number": season_number,
                    "status": season_status,
                    "status_text": status_text,
                    "requested_date": created_at,
                    "updated_date": updated_at,
                    "is_available": season_status == 5,
                    "is_downloading": season_status == 2,  # Status 2 = Approved (which means downloading)
                    "is_pending": season_status == 1
                }
                season_details.append(season_info)
        
        # Get total seasons information from media_details if available
        total_seasons = 0
        all_seasons = []
        missing_seasons = []
        
        if media_details:
            total_seasons = media_details.get("numberOfSeasons", 0)
            if total_seasons > 0:
                all_seasons = list(range(1, total_seasons + 1))
                missing_seasons = [s for s in all_seasons if s not in requested_seasons]
        
        # Calculate season statistics
        downloading_seasons = [s["season_number"] for s in season_details if s["is_downloading"]]
        available_seasons = [s["season_number"] for s in season_details if s["is_available"]]
        pending_seasons = [s["season_number"] for s in season_details if s["is_pending"]]
        
        return {
            "requested_seasons": sorted(requested_seasons),
            "season_count": len(requested_seasons),
            "season_details": season_details,
            "has_multiple_seasons": len(requested_seasons) > 1,
            # Enhanced season information
            "total_seasons": total_seasons,
            "all_seasons": all_seasons,
            "missing_seasons": sorted(missing_seasons),
            "downloading_seasons": sorted(downloading_seasons),
            "available_seasons": sorted(available_seasons),
            "pending_seasons": sorted(pending_seasons),
            "season_summary": {
                "requested": len(requested_seasons),
                "total_available": total_seasons,
                "missing": len(missing_seasons),
                "downloading": len(downloading_seasons),
                "available": len(available_seasons),
                "pending": len(pending_seasons)
            }
        }
    
    @staticmethod
    def _extract_season_details_from_media(media_data: Dict, media_details: Dict = None) -> Dict:
        """Extract detailed season information from media data (/api/v1/media endpoint)."""
        if not media_data:
            return None
        
        seasons = media_data.get("seasons", [])
        if not seasons:
            return None
        
        # Process each season in the media data
        season_details = []
        requested_seasons = []
        
        for season in seasons:
            season_number = season.get("seasonNumber")
            season_status = season.get("status")
            created_at = season.get("createdAt", "")
            updated_at = season.get("updatedAt", "")
            
            if season_number:
                requested_seasons.append(season_number)
                
                # Convert season status to human readable
                # Season status uses MEDIA_STATUS mapping for /media endpoint
                status_text = OverseerrStatusMaps.get_media_status_text(season_status)
                
                season_info = {
                    "season_number": season_number,
                    "status": season_status,
                    "status_text": status_text,
                    "requested_date": created_at,
                    "updated_date": updated_at,
                    "is_available": season_status == 5,
                    "is_downloading": season_status == 3,  # Status 3 = Processing (downloading)
                    "is_pending": season_status == 2
                }
                season_details.append(season_info)
        
        # Get total seasons information from media_details if available
        total_seasons = 0
        all_seasons = []
        missing_seasons = []
        
        if media_details:
            total_seasons = media_details.get("numberOfSeasons", 0)
            if total_seasons > 0:
                all_seasons = list(range(1, total_seasons + 1))
                missing_seasons = [s for s in all_seasons if s not in requested_seasons]
        
        # Calculate season statistics
        downloading_seasons = [s["season_number"] for s in season_details if s["is_downloading"]]
        available_seasons = [s["season_number"] for s in season_details if s["is_available"]]
        pending_seasons = [s["season_number"] for s in season_details if s["is_pending"]]
        
        return {
            "requested_seasons": sorted(requested_seasons),
            "season_count": len(requested_seasons),
            "season_details": season_details,
            "has_multiple_seasons": len(requested_seasons) > 1,
            # Enhanced season information
            "total_seasons": total_seasons,
            "all_seasons": all_seasons,
            "missing_seasons": sorted(missing_seasons),
            "downloading_seasons": sorted(downloading_seasons),
            "available_seasons": sorted(available_seasons),
            "pending_seasons": sorted(pending_seasons),
            "season_summary": {
                "requested": len(requested_seasons),
                "total_available": total_seasons,
                "missing": len(missing_seasons),
                "downloading": len(downloading_seasons),
                "available": len(available_seasons),
                "pending": len(pending_seasons)
            }
        }
    
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
            
            # Extract season details from request data with media context
            season_details = LLMResponseBuilder._extract_season_details_from_request(matching_request, media_details)
            
            # Build the structured response
            response = {
                "action": "found_media",
                "llm_instructions": "Focus on requested seasons, download progress, and who requested it. Include information about total seasons available and missing seasons when relevant for TV shows.",
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
                        "download_info": LLMResponseBuilder._build_download_info(search_result.get("mediaInfo")),
                        "request_details": LLMResponseBuilder._build_request_details(matching_request),
                        "season_info": season_details
                    },
                    "content_details": {
                        "overview": media_details.get("overview", "Overview not available")[:300] if media_details else "Overview not available",
                        "genres": [genre["name"] for genre in media_details.get("genres", [])][:3] if media_details else [],
                        "media_specific": LLMResponseBuilder._build_media_specific_info(search_result, media_details, season_details)
                    }
                },
                "message": f"Found detailed information for '{search_result.get('title') or search_result.get('name')}'. Includes requested seasons, download progress, total seasons available, and missing seasons information."
            }
            
            return response
        
        return {
            "action": "error",
            "message": "Unexpected error occurred"
        }
    
    @staticmethod
    def _get_status_text(status_code: int) -> str:
        """Convert media status code to human-readable text."""
        return OverseerrStatusMaps.get_media_status_text(status_code)
    
    @staticmethod
    def _build_request_details(matching_request: Dict) -> Dict:
        """Build request details from matching request data."""
        if not matching_request:
            return {
                "requested_by": "Information not available",
                "request_date": "Unknown",
                "request_id": None,
                "season_count": 0,
                "requested_seasons": []
            }
        
        # Extract season information
        seasons = matching_request.get("seasons", [])
        requested_seasons = [s.get("seasonNumber") for s in seasons if s.get("seasonNumber")]
        
        return {
            "requested_by": matching_request.get("requestedBy", {}).get("displayName") or 
                           matching_request.get("requestedBy", {}).get("username", "Unknown User"),
            "request_date": matching_request.get("createdAt", "Unknown"),
            "request_id": matching_request.get("id"),
            "season_count": len(requested_seasons),
            "requested_seasons": sorted(requested_seasons),
            "is_4k_request": matching_request.get("is4k", False)
        }
    
    @staticmethod
    def _build_media_specific_info(search_result: Dict, media_details: Dict, season_details: Dict = None) -> Dict:
        """Build media type specific information with season context."""
        media_type = search_result.get("mediaType", "unknown")
        
        if media_type == "tv":
            # For TV shows, include basic series info without duplicating season details
            if season_details:
                # Include basic series info, season details are already in season_info
                return {
                    "episode_runtime": media_details.get("episodeRunTime", [None])[0] if media_details and media_details.get("episodeRunTime") else None,
                    "series_status": media_details.get("status", "Unknown") if media_details else "Unknown",
                    "networks": media_details.get("networks", [{}])[0].get("name", "Unknown") if media_details and media_details.get("networks") else "Unknown",
                    "note": "Season details available in season_info section"
                }
            elif media_details:
                # Fallback to total seasons only if no request data available
                episode_runtime_list = media_details.get("episodeRunTime", [])
                episode_runtime = episode_runtime_list[0] if episode_runtime_list else None
                
                networks_list = media_details.get("networks", [])
                network_name = networks_list[0].get("name", "Unknown") if networks_list else "Unknown"
                
                return {
                    "total_seasons": media_details.get("numberOfSeasons", 0),
                    "total_episodes": media_details.get("numberOfEpisodes", 0),
                    "episode_runtime": episode_runtime,
                    "series_status": media_details.get("status", "Unknown"),
                    "networks": network_name,
                    "note": "No specific seasons requested yet"
                }
            else:
                return {"note": "TV show information not available"}
        
        elif media_type == "movie" and media_details:
            # Safe array access with bounds checking
            production_companies_list = media_details.get("productionCompanies", [])
            production_company = production_companies_list[0].get("name", "Unknown") if production_companies_list else "Unknown"
            
            return {
                "runtime": media_details.get("runtime", 0),
                "budget": media_details.get("budget", 0),
                "revenue": media_details.get("revenue", 0),
                "production_companies": production_company
            }
        
        return {}

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
                    },
                    "download_info": LLMResponseBuilder._build_download_info(result.get("mediaInfo"))
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
                    "note": f"If files were being downloaded at the time of removal, they may need to be manually removed from your media library, link here: {search_result.get('mediaInfo', {}).get('serviceUrl', 'N/A')}"
                }
            }
        
        if action == "user_not_mapped":
            return {
                "action": "user_not_mapped",
                "error": "User not registered for media operations",
                "error_details": error_details,
                "searched_title": title,
                "message": "Sorry, you're not registered to perform media operations through this system.",
                "explanation": "Your Home Assistant user account needs to be mapped to an Overseerr user account to remove media.",
                "next_steps": {
                    "suggestion": "Contact your system administrator to add your account to the media request system",
                    "admin_instructions": [
                        "Go to Settings > Devices & Services > Hassarr",
                        "Click 'Configure' on the Hassarr integration",
                        "Add your Home Assistant user to the user mapping section",
                        "Map your account to the appropriate Overseerr user"
                    ]
                },
                "llm_instructions": "Be polite but firm. Explain they need admin help to get access. Don't offer to help them bypass this restriction."
            }
        
        return {
            "action": "error",
            "message": "Unexpected error occurred in remove media operation"
        }

    @staticmethod
    async def build_active_requests_response(
        action: str,
        requests_data: Dict = None,
        error_details: str = None,
        api = None,
        use_media_endpoint: bool = False,
        take_limit: int = None
    ) -> Dict:
        """Build LLM-optimized response for active requests.
        
        Args:
            action: Action type
            requests_data: Data from requests or media endpoint
            error_details: Error details if any
            api: API client instance
            use_media_endpoint: Whether the data comes from /api/v1/media endpoint (for get_all_media service)
            take_limit: Maximum number of results to include in response
        """
        
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
            
            # Categorize ALL requests by status (using corrected observed mappings)
            # Prioritize media status over request status for accuracy
            pending_requests = []       # Media Status 2: Pending Approval
            processing_requests = []    # Media Status 3: Processing/Downloading ⭐ CORRECTED
            partially_available = []    # Media Status 4: Partially Available
            available_requests = []     # Media Status 5: Available in Library ⭐ CORRECTED
            failed_requests = []        # Media Status 7: Failed
            other_requests = []         # Media Status 1: Unknown and other codes
            
            for request in results:
                if use_media_endpoint:
                    # Data comes from /api/v1/media endpoint
                    media_status = request.get("status")
                    if media_status is not None:
                        status = media_status
                    else:
                        status = 1
                    
                    # Check for active downloads - if there are downloads happening, it's processing
                    download_status = request.get("downloadStatus", [])
                    download_status_4k = request.get("downloadStatus4k", [])
                    has_active_downloads = len(download_status) > 0 or len(download_status_4k) > 0
                else:
                    # Data comes from /api/v1/request endpoint - original logic
                    media = request.get("media", {})
                    media_status = media.get("status")
                    if media_status is not None:
                        status = media_status
                    else:
                        # If no media status, we can't properly categorize, so treat as other
                        status = 1
                    
                    # Check for active downloads - if there are downloads happening, it's processing
                    download_status = media.get("downloadStatus", [])
                    download_status_4k = media.get("downloadStatus4k", [])
                    has_active_downloads = len(download_status) > 0 or len(download_status_4k) > 0
                
                # If there are active downloads, prioritize as processing regardless of status
                if has_active_downloads:
                    processing_requests.append(request)  # Active downloads = processing
                elif status == 1:
                    other_requests.append(request)  # Unknown status
                elif status == 2:
                    pending_requests.append(request)  # Pending Approval
                elif status == 3:
                    processing_requests.append(request)  # Processing/Downloading ⭐ CORRECTED
                elif status == 4:
                    partially_available.append(request)  # Partially Available
                elif status == 5:
                    available_requests.append(request)  # Available in Library ⭐ CORRECTED
                elif status == 7:
                    failed_requests.append(request)  # Failed
                else:
                    other_requests.append(request)
            
            # Sort each category by createdAt date (most recent first)
            for request_list in [processing_requests, pending_requests, available_requests, 
                               partially_available, failed_requests, other_requests]:
                request_list.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
            
            # Build response with all requests, prioritizing active ones first
            active_requests = []
            all_other_requests = []
            requests_added = 0
            max_requests = take_limit or len(results)
            
            # Add processing requests first (highest priority)
            for request in processing_requests:
                if requests_added < max_requests:
                    media_details = await LLMResponseBuilder._fetch_media_details_for_request(request, api, use_media_endpoint)
                    active_requests.append(LLMResponseBuilder._build_request_info(request, media_details, use_media_endpoint))
                    requests_added += 1
            
            # Add pending requests to active requests
            for request in pending_requests:
                if requests_added < max_requests:
                    media_details = await LLMResponseBuilder._fetch_media_details_for_request(request, api, use_media_endpoint)
                    active_requests.append(LLMResponseBuilder._build_request_info(request, media_details, use_media_endpoint))
                    requests_added += 1
            
            # Add all other requests (available, failed, partial, etc.)
            for request_list in [available_requests, partially_available, failed_requests, other_requests]:
                for request in request_list:
                    if requests_added < max_requests:
                        media_details = await LLMResponseBuilder._fetch_media_details_for_request(request, api, use_media_endpoint)
                        all_other_requests.append(LLMResponseBuilder._build_request_info(request, media_details, use_media_endpoint))
                        requests_added += 1
            
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
                "returned_requests": requests_added,
                "status_breakdown": {
                    "processing_count": processing_count,
                    "pending_count": pending_count, 
                    "available_count": available_count,
                    "failed_count": failed_count,
                    "partially_available_count": partially_available_count,
                    "other_count": other_count
                },
                "active_requests": active_requests,
                "other_requests": all_other_requests,
                "message": f"Found {total_requests} total requests, showing {requests_added} ({breakdown_text})",
                "llm_instructions": {
                    "response_guidance": "Focus on active requests (downloading/pending) first, then show other requests. Include specific season information for TV shows.",
                    "priority_note": "Active requests (processing/pending) are shown first, followed by all other requests",
                    "status_meanings": {
                        "processing": "Currently downloading or being processed", 
                        "pending": "Waiting for approval",
                        "available": "Completed and available in library",
                        "failed": "Failed to download or unavailable",
                        "partially_available": "Some content available, some missing"
                    },
                    "season_info_note": "For TV shows, season-specific details are included showing which specific seasons are downloading, available, or pending",
                    "episode_info_note": "Download progress includes individual episode information when available",
                    "structure_note": "Results are limited by the take parameter. Active requests are prioritized first."
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
    async def _fetch_media_details_for_request(request: Dict, api, is_media_endpoint: bool = False) -> Dict:
        """Fetch media details for a request using the TMDB ID.
        
        Args:
            request: Request data (from /request endpoint) or media data (from /media endpoint)
            api: API client instance
            is_media_endpoint: True if request comes from /api/v1/media endpoint
        """
        try:
            if is_media_endpoint:
                # Data comes from /api/v1/media endpoint - structure is different
                media_type = request.get("mediaType", "movie")
                tmdb_id = request.get("tmdbId")
            else:
                # Data comes from /api/v1/request endpoint - original structure
                media = request.get("media", {})
                media_type = media.get("mediaType", "movie")
                tmdb_id = media.get("tmdbId")
            
            if tmdb_id:
                details = await api.get_media_details(media_type, tmdb_id)
                return details or {}
            return {}
        except Exception:
            return {}
    
    @staticmethod
    def _build_request_info(request: Dict, media_details: Dict = None, is_media_endpoint: bool = False) -> Dict:
        """Build formatted request information for LLM consumption.
        
        Args:
            request: Request data (from /request endpoint) or media data (from /media endpoint)
            media_details: Additional media details from TMDB
            is_media_endpoint: True if request comes from /api/v1/media endpoint
        """
        if is_media_endpoint:
            # Data comes from /api/v1/media endpoint - structure is different
            media_type = request.get("mediaType", "movie")
            
            # Get title from media_details if available, otherwise fallback to request object
            if media_details:
                title = media_details.get("title") or media_details.get("name", "Unknown Title")
            else:
                title = "Unknown Title"  # /media endpoint doesn't include title directly
        else:
            # Data comes from /api/v1/request endpoint - original structure
            media = request.get("media", {})
            
            # Determine media type and title
            media_type = "movie" if request.get("type") == "movie" else "tv"
            
            # Get title from media_details if available, otherwise fallback to media object
            if media_details:
                title = media_details.get("title") or media_details.get("name", "Unknown Title")
            else:
                title = media.get("title") or media.get("name", "Unknown Title")
        
        if is_media_endpoint:
            # Data comes from /api/v1/media endpoint
            # Format release date/year from media_details
            if media_details:
                release_date = media_details.get("releaseDate") or media_details.get("firstAirDate", "")
            else:
                release_date = ""
            year = release_date[:4] if release_date else "Unknown"
            
            # Use media status directly (more accurate for download state)
            media_status = request.get("status")
            status = OverseerrStatusMaps.get_media_status(media_status) if media_status is not None else "unknown"
            
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
            
            # Get overview from media_details (primary source for /media endpoint)
            if media_details:
                overview = media_details.get("overview", "")
            else:
                overview = ""
            
            # Truncate overview if too long
            if len(overview) > 200:
                overview = overview[:200] + "..."
            
            # Extract download information if available
            download_info = LLMResponseBuilder._build_download_info(request)  # request is actually media data
        else:
            # Data comes from /api/v1/request endpoint - original logic
            media = request.get("media", {})
            
            # Format release date/year
            release_date = media.get("releaseDate") or media.get("firstAirDate", "")
            year = release_date[:4] if release_date else "Unknown"
            
            # Prioritize media status over request status when available
            # This fixes inconsistency where request might be "pending" but media is "processing"
            media_status = media.get("status")
            if media_status is not None:
                # Use media status (more accurate for download state)
                status = OverseerrStatusMaps.get_media_status(media_status)
            else:
                # Fallback to request status if media status not available
                status = OverseerrStatusMaps.get_request_status(request.get("status", 1))
            
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
            
            # Get overview from media_details if available (more accurate)
            if media_details:
                overview = media_details.get("overview", "")
            else:
                overview = media.get("overview", "")
            
            # Truncate overview if too long
            if len(overview) > 200:
                overview = overview[:200] + "..."
            
            # Extract download information if available
            download_info = LLMResponseBuilder._build_download_info(media)
        
        # Extract detailed season information for TV shows
        season_info = None
        if media_type == "tv":
            if is_media_endpoint:
                # For /media endpoint, season info is in seasons array
                season_info = LLMResponseBuilder._extract_season_details_from_media(request, media_details)
            else:
                # For /request endpoint, use original method
                season_info = LLMResponseBuilder._extract_season_details_from_request(request, media_details)
        
        if is_media_endpoint:
            result = {
                "title": title,
                "year": year,
                "media_type": media_type,
                "status": status,
                "tmdb_id": request.get("tmdbId", 0),
                "media_id": request.get("id", 0),
                "request_id": None,  # /media endpoint doesn't have request ID
                "requested_date": created_date,
                "requested_by": "System",  # /media endpoint doesn't have requestedBy
                "overview": overview,
                "download_info": download_info
            }
        else:
            result = {
                "title": title,
                "year": year,
                "media_type": media_type,
                "status": status,
                "tmdb_id": media.get("tmdbId", 0),
                "media_id": media.get("id", 0),
                "request_id": request.get("id", 0),
                "requested_date": created_date,
                "requested_by": request.get("requestedBy", {}).get("displayName", "Unknown User"),
                "overview": overview,
                "download_info": download_info
            }
        
        # Add season information for TV shows
        if season_info:
            result["season_info"] = season_info
            result["requested_seasons"] = season_info["requested_seasons"]
            result["season_count"] = season_info["season_count"]
            
            # Add season-specific status summary for TV shows
            downloading_seasons = [s["season_number"] for s in season_info["season_details"] if s["is_downloading"]]
            available_seasons = [s["season_number"] for s in season_info["season_details"] if s["is_available"]]
            pending_seasons = [s["season_number"] for s in season_info["season_details"] if s["is_pending"]]
            
            season_status_parts = []
            if downloading_seasons:
                if len(downloading_seasons) == 1:
                    season_status_parts.append(f"Season {downloading_seasons[0]} downloading")
                else:
                    season_status_parts.append(f"Seasons {', '.join(map(str, downloading_seasons))} downloading")
            
            if available_seasons:
                if len(available_seasons) == 1:
                    season_status_parts.append(f"Season {available_seasons[0]} available")
                else:
                    season_status_parts.append(f"Seasons {', '.join(map(str, available_seasons))} available")
            
            if pending_seasons:
                if len(pending_seasons) == 1:
                    season_status_parts.append(f"Season {pending_seasons[0]} pending")
                else:
                    season_status_parts.append(f"Seasons {', '.join(map(str, pending_seasons))} pending")
            
            result["season_status_summary"] = "; ".join(season_status_parts) if season_status_parts else "Season status unknown"
        
        return result

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
        
        if action == "user_not_mapped":
            return {
                "action": "user_not_mapped",
                "error": "User not registered for job operations",
                "error_details": error_details,
                "job_id": job_id,
                "message": f"Sorry, you're not registered to run jobs through this system.",
                "explanation": "Your Home Assistant user account needs to be mapped to an Overseerr user account to run maintenance jobs.",
                "next_steps": {
                    "suggestion": "Contact your system administrator to add your account to the media request system",
                    "admin_instructions": [
                        "Go to Settings > Devices & Services > Hassarr",
                        "Click 'Configure' on the Hassarr integration",
                        "Add your Home Assistant user to the user mapping section",
                        "Map your account to the appropriate Overseerr user"
                    ]
                },
                "llm_instructions": "Be polite but firm. Explain they need admin help to get access. Don't offer to help them bypass this restriction."
            }
        
        return {
            "action": "error",
            "message": "Unexpected error occurred in run job operation"
        }

    @staticmethod
    def _extract_year(search_result: Dict) -> str:
        """Extract year from release date."""
        release_date = search_result.get("releaseDate") or search_result.get("firstAirDate")
        if release_date and len(release_date) >= 4:
            return release_date[:4]
        return "Unknown"
    
    @staticmethod
    async def build_add_media_response(
        action: str,
        title: str = None,
        search_result: Dict = None,
        media_details: Dict = None,
        add_result: Dict = None,
        message: str = None,
        error_details: str = None,
        season: int = None,
        season_analysis: Dict = None,
        parse_type: str = None,
        seasons_list: list = None,
        is4k: bool = False,
        api = None
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
            response = {
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
                    "watch_url": search_result.get('mediaInfo', {}).get('mediaUrl'),
                    "download_info": LLMResponseBuilder._build_download_info(search_result.get("mediaInfo"))
                },
                "message": f"{search_result.get('mediaType', 'Media').title()} already exists in Overseerr"
            }
            
            # Add 4K information for movies
            if search_result.get("mediaType") == "movie" and is4k:
                response["media"]["requested_4k"] = True
                response["message"] = f"Movie already exists in Overseerr (4K version was requested)"
            
            # Add season context for TV shows with intelligent suggestions
            if search_result.get("mediaType") == "tv":
                if season_analysis:
                    # Build intelligent season suggestions
                    suggestions = []
                    missing_seasons = season_analysis.get("missing_seasons", [])
                    processing_seasons = season_analysis.get("processing_seasons", [])
                    available_seasons = season_analysis.get("available_seasons", [])
                    total_seasons = season_analysis.get("total_seasons", 0)
                    
                    # Create status summary
                    status_parts = []
                    if available_seasons:
                        if len(available_seasons) == 1:
                            status_parts.append(f"Season {available_seasons[0]} is available")
                        else:
                            status_parts.append(f"Seasons {', '.join(map(str, available_seasons))} are available")
                    
                    if processing_seasons:
                        if len(processing_seasons) == 1:
                            status_parts.append(f"Season {processing_seasons[0]} is downloading")
                        else:
                            status_parts.append(f"Seasons {', '.join(map(str, processing_seasons))} are downloading")
                    
                    status_summary = "; ".join(status_parts) if status_parts else "No seasons available yet"
                    
                    # Generate suggestions
                    if missing_seasons:
                        if len(missing_seasons) == 1:
                            suggestions.append(f"Request season {missing_seasons[0]}")
                        elif len(missing_seasons) <= 3:
                            suggestions.append(f"Request seasons {', '.join(map(str, missing_seasons))}")
                        else:
                            suggestions.append(f"Request remaining {len(missing_seasons)} seasons ({missing_seasons[0]}-{missing_seasons[-1]})")
                    
                    response["season_analysis"] = {
                        "total_seasons": total_seasons,
                        "status_summary": status_summary,
                        "available_seasons": available_seasons,
                        "processing_seasons": processing_seasons,
                        "missing_seasons": missing_seasons,
                        "requested_season": season,
                        "suggestions": suggestions
                    }
                    
                    # Update message with season context
                    if season is not None:
                        if season in available_seasons:
                            response["message"] = f"TV show already exists - Season {season} is available in your library"
                        elif season in processing_seasons:
                            response["message"] = f"TV show already exists - Season {season} is currently downloading"
                        else:
                            response["message"] = f"TV show already exists - Season {season} is not yet requested"
                    else:
                        response["message"] = f"TV show already exists in Overseerr ({status_summary})"
                    
                    # Add LLM instructions for natural conversation
                    response["llm_suggestions"] = {
                        "conversation_starters": [
                            "Would you like me to add the missing seasons?",
                            "Should I request the remaining episodes?",
                            f"I can add seasons {', '.join(map(str, missing_seasons[:3]))} if you'd like"
                        ] if missing_seasons else [
                            "All seasons are already requested or available",
                            "You have the complete series"
                        ]
                    }
                else:
                    # Fallback for when season analysis isn't available
                    if season is not None:
                        response["season_context"] = {
                            "requested_season": season,
                            "note": f"You requested season {season}, but the series is already in your library"
                        }
                        response["message"] = f"TV show already exists in Overseerr (you requested season {season})"
                
            return response
        
        if action == "media_added_successfully" and search_result:
            response = {
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
            
            # Add 4K information for movies
            if search_result.get("mediaType") == "movie" and is4k:
                response["media"]["requested_4k"] = True
                response["message"] = f"Movie successfully added to Overseerr in 4K quality"
            
            # Add season context for TV shows
            if search_result.get("mediaType") == "tv":
                if parse_type == "all":
                    response["season_context"] = {
                        "requested_season": "all",
                        "note": "Requested entire series (all seasons)"
                    }
                    response["message"] = "TV show successfully added to Overseerr (entire series requested)"
                elif season is not None:
                    # Check if we have multiple seasons in the seasons_list
                    if seasons_list and len(seasons_list) > 1:
                        seasons_str = ", ".join(map(str, seasons_list))
                        response["season_context"] = {
                            "requested_season": seasons_list,
                            "note": f"Requested seasons {seasons_str}"
                        }
                        response["message"] = f"TV show successfully added to Overseerr (seasons {seasons_str} requested)"
                    else:
                        response["season_context"] = {
                            "requested_season": season,
                            "note": f"Requested season {season} specifically"
                        }
                        response["message"] = f"TV show successfully added to Overseerr (season {season} requested)"
                else:
                    response["season_context"] = {
                        "requested_season": 1,
                        "note": "No season specified, defaulted to season 1"
                    }
                    response["message"] = "TV show successfully added to Overseerr (defaulted to season 1)"
            
            return response
        
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
        
        if action == "user_not_mapped":
            return {
                "action": "user_not_mapped",
                "error": "User not registered for media requests",
                "error_details": error_details,
                "searched_title": title,
                "message": f"Sorry, you're not registered to make media requests through this system.",
                "explanation": "Your Home Assistant user account needs to be mapped to an Overseerr user account to make requests.",
                "next_steps": {
                    "suggestion": "Contact your system administrator to add your account to the media request system",
                    "admin_instructions": [
                        "Go to Settings > Devices & Services > Hassarr",
                        "Click 'Configure' on the Hassarr integration",
                        "Add your Home Assistant user to the user mapping section",
                        "Map your account to the appropriate Overseerr user"
                    ]
                },
                "llm_instructions": "Be polite but firm. Explain they need admin help to get access. Don't offer to help them bypass this restriction."
            }
        
        return {
            "action": "error",
            "message": "Unexpected error occurred"
        }