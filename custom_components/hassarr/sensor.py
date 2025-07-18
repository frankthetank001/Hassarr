# File: sensor.py
# Note: Keep this filename comment for navigation and organization

import logging
from datetime import timedelta, datetime
from collections import Counter
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN, UPDATE_INTERVAL,
    SENSOR_ACTIVE_DOWNLOADS, SENSOR_QUEUE_STATUS, SENSOR_JOBS_STATUS,
    SENSOR_TOTAL_REQUESTS, SENSOR_PENDING_REQUESTS, SENSOR_AVAILABLE_REQUESTS,
    SENSOR_RECENT_REQUESTS, SENSOR_FAILED_REQUESTS, SENSOR_MOVIE_REQUESTS,
    SENSOR_TV_REQUESTS, SENSOR_TOP_REQUESTER, SENSOR_SYSTEM_HEALTH,
    SENSOR_NEXT_JOB, SENSOR_API_RESPONSE_TIME
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hassarr sensors from config entry."""
    _LOGGER.info("Setting up Hassarr comprehensive sensor suite")
    
    # Get the API client from the main integration
    api = hass.data[DOMAIN]["api"]
    
    # Create coordinator for periodic updates
    coordinator = HassarrDataUpdateCoordinator(hass, api)
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Create comprehensive sensor entities
    entities = [
        # Original sensors
        HassarrActiveDownloadsSensor(coordinator),
        HassarrQueueStatusSensor(coordinator),
        HassarrJobsStatusSensor(coordinator),
        
        # Request-based sensors
        HassarrTotalRequestsSensor(coordinator),
        HassarrPendingRequestsSensor(coordinator),
        HassarrAvailableRequestsSensor(coordinator),
        HassarrRecentRequestsSensor(coordinator),
        HassarrFailedRequestsSensor(coordinator),
        HassarrMovieRequestsSensor(coordinator),
        HassarrTVRequestsSensor(coordinator),
        HassarrTopRequesterSensor(coordinator),
        HassarrSystemHealthSensor(coordinator),
        HassarrNextJobSensor(coordinator),
        HassarrApiResponseTimeSensor(coordinator),
        
        # Media library sensors
        HassarrTotalMediaSensor(coordinator),
        HassarrAvailableMediaSensor(coordinator),
        HassarrProcessingMediaSensor(coordinator),
        
        # Latest request tracking sensors
        HassarrLastMovieRequestSensor(coordinator),
        HassarrLastTVRequestSensor(coordinator),
    ]
    
    async_add_entities(entities, True)
    _LOGGER.info(f"Added {len(entities)} Hassarr sensors")


class HassarrDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from Overseerr API."""

    def __init__(self, hass: HomeAssistant, api) -> None:
        """Initialize the coordinator."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self):
        """Fetch data from Overseerr API."""
        start_time = datetime.now()
        
        try:
            _LOGGER.debug("Fetching comprehensive data from Overseerr...")
            
            # Fetch requests data
            requests_data = await self.api.get_requests(take=500)
            
            # Fetch media data (comprehensive library view)
            media_data = await self.api.get_media(filter_type="all", take=200)
            
            # Fetch jobs data
            jobs_data = await self.api.get_jobs()
            
            # Calculate API response time
            api_response_time = (datetime.now() - start_time).total_seconds()
            
            if requests_data is None:
                _LOGGER.warning("Failed to fetch requests data from Overseerr")
                requests_data = {"results": []}
            
            if media_data is None:
                _LOGGER.warning("Failed to fetch media data from Overseerr")
                media_data = {"results": []}
            
            if jobs_data is None:
                _LOGGER.warning("Failed to fetch jobs data from Overseerr")
                jobs_data = []
            
            # Handle different job data formats
            if isinstance(jobs_data, dict) and "results" in jobs_data:
                jobs_list = jobs_data["results"]
            elif isinstance(jobs_data, list):
                jobs_list = jobs_data
            else:
                jobs_list = []
            
            requests_results = requests_data.get("results", [])
            media_results = media_data.get("results", [])
            
            # Calculate comprehensive metrics using both requests and media data
            metrics = await self._calculate_comprehensive_metrics(requests_results, media_results, jobs_list)
            
            data = {
                "overseerr_online": True,
                "requests": requests_results,
                "media": media_results,
                "jobs": jobs_list,
                "api_response_time": api_response_time,
                "last_update": self.hass.loop.time(),
                **metrics
            }
            
            _LOGGER.debug(f"Updated comprehensive data: {len(requests_results)} requests, {len(media_results)} media, {len(jobs_list)} jobs, {api_response_time:.2f}s response time")
            return data
            
        except Exception as err:
            _LOGGER.error(f"Error fetching data: {err}")
            raise UpdateFailed(f"Error communicating with Overseerr: {err}")
    
    async def _calculate_comprehensive_metrics(self, requests: list, media: list, jobs: list) -> dict:
        """Calculate comprehensive metrics from raw API data."""
        # Initialize counters
        request_status_counts = Counter()
        media_status_counts = Counter()
        type_counts = Counter()
        user_counts = Counter()
        recent_count = 0
        
        # Get current time for recent requests calculation
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)
        
        # Process each request
        for request in requests:
            # Count by status (request-based)
            status = request.get("status", 1)
            request_status_counts[status] += 1
            
            # Count by type
            req_type = request.get("type", "unknown")
            type_counts[req_type] += 1
            
            # Count by user
            user = request.get("requestedBy", {}).get("displayName", "Unknown")
            user_counts[user] += 1
            
            # Count recent requests (last 7 days)
            created_at = request.get("createdAt", "")
            if created_at:
                try:
                    # Parse ISO date string
                    request_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if request_date.replace(tzinfo=None) >= seven_days_ago:
                        recent_count += 1
                except:
                    pass  # Skip if date parsing fails
        
        # Process each media item (comprehensive library view)
        for media_item in media:
            # Count by media status (more accurate than request status)
            media_status = media_item.get("status", 1)
            media_status_counts[media_status] += 1
            
            # Count by media type
            media_type = media_item.get("mediaType", "unknown")
            type_counts[media_type] += 1  # This will combine with request type counts
        
        # Calculate job metrics
        running_jobs = len([j for j in jobs if j.get("running", False)])
        total_jobs = len(jobs)
        
        # Find next scheduled job
        next_job_info = self._find_next_scheduled_job(jobs)
        
        # Determine system health using combined data
        system_health = self._calculate_system_health(requests, media, jobs, request_status_counts, media_status_counts)
        
        # Get top requester
        top_requester = user_counts.most_common(1)[0] if user_counts else ("No requests", 0)
        
        # Find last requested movie and TV show
        last_movie_request = await self._find_last_request_by_type(requests, "movie")
        last_tv_request = await self._find_last_request_by_type(requests, "tv")
        
        return {
            # Request counts by status (from requests endpoint)
            "total_requests": len(requests),
            "pending_requests": request_status_counts.get(2, 0),  # 2 = Pending Approval
            "active_downloads": request_status_counts.get(3, 0),  # 3 = Processing/Downloading
            "available_requests": request_status_counts.get(5, 0),  # 5 = Available in Library
            "failed_requests": request_status_counts.get(7, 0),  # 7 = Deleted
            
            # Media counts by status (from media endpoint - more comprehensive)
            "total_media": len(media),
            "pending_media": media_status_counts.get(2, 0),  # 2 = Pending
            "processing_media": media_status_counts.get(3, 0),  # 3 = Processing/Downloading
            "available_media": media_status_counts.get(5, 0),  # 5 = Available in Library
            "failed_media": media_status_counts.get(7, 0),  # 7 = Failed
            
            # Request counts by type
            "movie_requests": type_counts.get("movie", 0),
            "tv_requests": type_counts.get("tv", 0),
            
            # Time-based metrics
            "recent_requests": recent_count,
            
            # User metrics
            "top_requester": top_requester[0],
            "top_requester_count": top_requester[1],
            
            # Latest request tracking
            "last_movie_request": last_movie_request,
            "last_tv_request": last_tv_request,
            
            # Job metrics
            "running_jobs": running_jobs,
            "total_jobs": total_jobs,
            "next_job": next_job_info,
            
            # System health
            "system_health": system_health
        }
    
    def _find_next_scheduled_job(self, jobs: list) -> dict:
        """Find the next scheduled job to run."""
        next_job = None
        next_time = None
        
        for job in jobs:
            if not job.get("running", False):  # Skip currently running jobs
                job_time_str = job.get("nextExecutionTime", "")
                if job_time_str:
                    try:
                        job_time = datetime.fromisoformat(job_time_str.replace('Z', '+00:00'))
                        if next_time is None or job_time < next_time:
                            next_time = job_time
                            next_job = {
                                "id": job.get("id", "unknown"),
                                "name": job.get("name", "Unknown Job"),
                                "next_execution": job_time_str,
                                "type": job.get("type", "unknown")
                            }
                    except:
                        continue
        
        return next_job or {
            "id": "none",
            "name": "No scheduled jobs",
            "next_execution": "unknown",
            "type": "none"
        }
    
    async def _find_last_request_by_type(self, requests: list, media_type: str) -> dict:
        """Find the most recent request by media type."""
        filtered_requests = [r for r in requests if r.get("type") == media_type]
        
        if not filtered_requests:
            return {
                "title": f"No {media_type} requests",
                "status": 0,
                "status_text": "No requests",
                "requested_by": "N/A",
                "requested_date": "N/A",
                "tmdb_id": 0
            }
        
        # Sort by creation date (most recent first)
        try:
            latest_request = max(filtered_requests, key=lambda x: x.get("createdAt", ""))
        except (ValueError, TypeError):
            latest_request = filtered_requests[0]
        
        # Extract media information
        media = latest_request.get("media", {})
        title = media.get("title") or media.get("name", "Unknown")
        status = media.get("status", 1)
        requested_by = latest_request.get("requestedBy", {}).get("displayName", "Unknown")
        requested_date = latest_request.get("createdAt", "Unknown")
        tmdb_id = media.get("tmdbId", 0)
        
        # If title is unknown but we have a tmdb_id, try to fetch the title
        if title == "Unknown" and tmdb_id > 0:
            try:
                # Fetch media details from TMDB API
                media_details = await self.api.get_media_details(media_type, tmdb_id)
                if media_details:
                    title = media_details.get("title") or media_details.get("name", "Unknown")
                    _LOGGER.debug(f"Fetched title from TMDB for {media_type} {tmdb_id}: {title}")
                else:
                    title = f"Unknown ({media_type.title()} {tmdb_id})"
            except Exception as e:
                _LOGGER.warning(f"Failed to fetch title from TMDB for {media_type} {tmdb_id}: {e}")
                title = f"Unknown ({media_type.title()} {tmdb_id})"
        
        # Format the date
        if requested_date != "Unknown":
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(requested_date.replace('Z', '+00:00'))
                requested_date = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
        
        # Extract download information if available
        download_info = self._extract_download_info(media)
        
        return {
            "title": title,
            "status": status,
            "status_text": self._get_status_text_for_status(status),
            "requested_by": requested_by,
            "requested_date": requested_date,
            "tmdb_id": tmdb_id,
            "download_info": download_info
        }
    
    def _get_status_text_for_status(self, status: int) -> str:
        """Convert status code to human-readable text."""
        status_map = {
            0: "No requests",
            1: "Unknown",
            2: "Pending",
            3: "Processing",
            4: "Partially Available",
            5: "Available",
            7: "Failed"
        }
        return status_map.get(status, f"Status {status}")
    
    def _extract_download_info(self, media: dict) -> dict:
        """Extract download information from media data."""
        if not media:
            return None
        
        download_status = media.get("downloadStatus", [])
        download_status_4k = media.get("downloadStatus4k", [])
        all_downloads = download_status + download_status_4k
        
        if not all_downloads:
            return None
        
        # Process download information
        total_size = 0
        total_remaining = 0
        active_downloads = 0
        download_titles = []
        
        for download in all_downloads:
            if download.get("status") in ["downloading", "queued"]:
                active_downloads += 1
                download_titles.append(download.get("title", "Unknown"))
            
            size = download.get("size", 0)
            size_left = download.get("sizeLeft", 0)
            total_size += size
            total_remaining += size_left
        
        # Calculate overall progress
        if total_size > 0:
            progress_percent = round(((total_size - total_remaining) / total_size) * 100, 1)
        else:
            progress_percent = 0
        
        return {
            "has_downloads": True,
            "active_downloads": active_downloads,
            "total_downloads": len(all_downloads),
            "progress_percent": progress_percent,
            "total_size_gb": round(total_size / (1024 ** 3), 2) if total_size > 0 else 0,
            "remaining_size_gb": round(total_remaining / (1024 ** 3), 2) if total_remaining > 0 else 0,
            "download_titles": download_titles[:3],  # Limit to first 3 titles
            "has_4k_downloads": len(download_status_4k) > 0
        }
    
    def _calculate_system_health(self, requests: list, media: list, jobs: list, request_status_counts: Counter, media_status_counts: Counter) -> str:
        """Calculate overall system health status using combined data."""
        failed_requests = request_status_counts.get(7, 0)  # Status 7 = Deleted/Failed
        failed_media = media_status_counts.get(7, 0)  # Status 7 = Failed
        total_requests = len(requests)
        total_media = len(media)
        running_jobs = len([j for j in jobs if j.get("running", False)])
        
        # Calculate health score using both requests and media data
        if total_requests == 0 and total_media == 0:
            return "Healthy - No activity"
        
        # Use media data for more accurate failure rate if available
        if total_media > 0:
            failure_rate = failed_media / total_media
            total_items = total_media
        else:
            failure_rate = failed_requests / total_requests if total_requests > 0 else 0
            total_items = total_requests
        
        if failure_rate > 0.2:  # More than 20% failed
            return f"Degraded - High failure rate ({int(failure_rate*100)}%)"
        elif failure_rate > 0.1:  # More than 10% failed
            return f"Warning - Some failures detected ({int(failure_rate*100)}%)"
        elif running_jobs > 3:  # Too many jobs running
            return "Busy - Multiple jobs running"
        else:
            return f"Healthy - Operating normally ({total_items} items)"


class HassarrActiveDownloadsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for active downloads count."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Active Downloads"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_ACTIVE_DOWNLOADS}"
        self._attr_icon = "mdi:download"
        self._attr_native_unit_of_measurement = "downloads"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("active_downloads", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "total_requests": self.coordinator.data.get("total_requests", 0),
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrQueueStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor for queue status overview."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Queue Status"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_QUEUE_STATUS}"
        self._attr_icon = "mdi:playlist-check"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        active = self.coordinator.data.get("active_downloads", 0)
        total = self.coordinator.data.get("total_requests", 0)
        
        if not self.coordinator.data.get("overseerr_online", False):
            return "Offline"
        elif active == 0:
            return f"Idle ({total} queued)" if total > 0 else "Empty"
        else:
            return f"{active} downloading ({total} total)"

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "active_downloads": self.coordinator.data.get("active_downloads", 0),
            "total_requests": self.coordinator.data.get("total_requests", 0),
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrJobsStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Overseerr jobs status."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Jobs Status"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_JOBS_STATUS}"
        self._attr_icon = "mdi:cog"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        running = self.coordinator.data.get("running_jobs", 0)
        total = self.coordinator.data.get("total_jobs", 0)
        
        if not self.coordinator.data.get("overseerr_online", False):
            return "Offline"
        elif running == 0:
            return f"Idle ({total} jobs available)"
        else:
            return f"{running} running ({total} total)"

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        jobs = self.coordinator.data.get("jobs", [])
        
        # Format jobs for display
        job_details = []
        running_jobs = []
        
        for job in jobs:
            job_info = {
                "id": job.get("id", "unknown"),
                "name": job.get("name", "Unknown Job"),
                "type": job.get("type", "unknown"),
                "interval": job.get("interval", "unknown"),
                "running": job.get("running", False),
                "next_execution": job.get("nextExecutionTime", "unknown"),
                "cron_schedule": job.get("cronSchedule", "unknown")
            }
            job_details.append(job_info)
            
            if job.get("running", False):
                running_jobs.append(job_info)
        
        return {
            "running_jobs": self.coordinator.data.get("running_jobs", 0),
            "total_jobs": self.coordinator.data.get("total_jobs", 0),
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
            "jobs": job_details,
            "currently_running": running_jobs
        }


class HassarrTotalRequestsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for total requests count."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Total Requests"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_TOTAL_REQUESTS}"
        self._attr_icon = "mdi:file-multiple"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("total_requests", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrPendingRequestsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for pending requests count."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Pending Requests"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_PENDING_REQUESTS}"
        self._attr_icon = "mdi:file-clock"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("pending_requests", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrAvailableRequestsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for available requests count."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Available Requests"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_AVAILABLE_REQUESTS}"
        self._attr_icon = "mdi:file-check"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("available_requests", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrRecentRequestsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for recent requests count."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Recent Requests"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_RECENT_REQUESTS}"
        self._attr_icon = "mdi:file-clock"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("recent_requests", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrFailedRequestsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for failed requests count."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Failed Requests"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_FAILED_REQUESTS}"
        self._attr_icon = "mdi:file-alert"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("failed_requests", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrMovieRequestsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for movie requests count."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Movie Requests"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_MOVIE_REQUESTS}"
        self._attr_icon = "mdi:file-movie"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("movie_requests", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrTVRequestsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for TV requests count."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr TV Requests"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_TV_REQUESTS}"
        self._attr_icon = "mdi:file-tv"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("tv_requests", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrTopRequesterSensor(CoordinatorEntity, SensorEntity):
    """Sensor for top requester."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Top Requester"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_TOP_REQUESTER}"
        self._attr_icon = "mdi:account-group"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self.coordinator.data.get("top_requester", "No requests")

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "top_requester_count": self.coordinator.data.get("top_requester_count", 0),
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrSystemHealthSensor(CoordinatorEntity, SensorEntity):
    """Sensor for system health."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr System Health"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_SYSTEM_HEALTH}"
        self._attr_icon = "mdi:health"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self.coordinator.data.get("system_health", "Unknown")

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrNextJobSensor(CoordinatorEntity, SensorEntity):
    """Sensor for next job."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Next Job"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_NEXT_JOB}"
        self._attr_icon = "mdi:calendar-check"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        next_job = self.coordinator.data.get("next_job", {})
        return f"{next_job.get('name', 'No scheduled job')} ({next_job.get('type', 'unknown')})"

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrApiResponseTimeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for API response time."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr API Response Time"
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_API_RESPONSE_TIME}"
        self._attr_icon = "mdi:clock"
        self._attr_native_unit_of_measurement = "seconds"

    @property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        return self.coordinator.data.get("api_response_time", 0.0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrTotalMediaSensor(CoordinatorEntity, SensorEntity):
    """Sensor for total media count in library."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Total Media"
        self._attr_unique_id = f"{DOMAIN}_total_media"
        self._attr_icon = "mdi:database"
        self._attr_native_unit_of_measurement = "items"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("total_media", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "total_requests": self.coordinator.data.get("total_requests", 0),
            "requests_vs_media": f"{self.coordinator.data.get('total_requests', 0)}/{self.coordinator.data.get('total_media', 0)}",
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrAvailableMediaSensor(CoordinatorEntity, SensorEntity):
    """Sensor for available media count in library."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Available Media"
        self._attr_unique_id = f"{DOMAIN}_available_media"
        self._attr_icon = "mdi:check-circle"
        self._attr_native_unit_of_measurement = "items"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("available_media", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        total_media = self.coordinator.data.get("total_media", 0)
        available_media = self.coordinator.data.get("available_media", 0)
        completion_rate = (available_media / total_media * 100) if total_media > 0 else 0
        
        return {
            "total_media": total_media,
            "completion_rate": f"{completion_rate:.1f}%",
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrProcessingMediaSensor(CoordinatorEntity, SensorEntity):
    """Sensor for processing media count in library."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Processing Media"
        self._attr_unique_id = f"{DOMAIN}_processing_media"
        self._attr_icon = "mdi:progress-download"
        self._attr_native_unit_of_measurement = "items"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data.get("processing_media", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "total_media": self.coordinator.data.get("total_media", 0),
            "active_downloads": self.coordinator.data.get("active_downloads", 0),
            "media_vs_requests": f"{self.coordinator.data.get('processing_media', 0)}/{self.coordinator.data.get('active_downloads', 0)}",
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }


class HassarrLastMovieRequestSensor(CoordinatorEntity, SensorEntity):
    """Sensor for the last requested movie."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Last Movie Request"
        self._attr_unique_id = f"{DOMAIN}_last_movie_request"
        self._attr_icon = "mdi:movie"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        last_movie = self.coordinator.data.get("last_movie_request", {})
        title = last_movie.get("title", "No movie requests")
        status = last_movie.get("status_text", "")
        download_info = last_movie.get("download_info")
        
        if title == "No movie requests":
            return title
        
        # Add download progress if available
        if download_info and download_info.get("has_downloads"):
            progress = download_info.get("progress_percent", 0)
            return f"{title} ({status} - {progress}%)"
        
        return f"{title} ({status})" if status else title

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        last_movie = self.coordinator.data.get("last_movie_request", {})
        download_info = last_movie.get("download_info")
        
        attributes = {
            "title": last_movie.get("title", "No movie requests"),
            "status": last_movie.get("status", 0),
            "status_text": last_movie.get("status_text", "N/A"),
            "requested_by": last_movie.get("requested_by", "N/A"),
            "requested_date": last_movie.get("requested_date", "N/A"),
            "tmdb_id": last_movie.get("tmdb_id", 0),
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }
        
        # Add download information if available
        if download_info:
            attributes.update({
                "has_downloads": download_info.get("has_downloads", False),
                "active_downloads": download_info.get("active_downloads", 0),
                "download_progress": download_info.get("progress_percent", 0),
                "total_size_gb": download_info.get("total_size_gb", 0),
                "remaining_size_gb": download_info.get("remaining_size_gb", 0),
                "download_titles": download_info.get("download_titles", []),
                "has_4k_downloads": download_info.get("has_4k_downloads", False)
            })
        
        return attributes


class HassarrLastTVRequestSensor(CoordinatorEntity, SensorEntity):
    """Sensor for the last requested TV show."""

    def __init__(self, coordinator: HassarrDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Hassarr Last TV Request"
        self._attr_unique_id = f"{DOMAIN}_last_tv_request"
        self._attr_icon = "mdi:television"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        last_tv = self.coordinator.data.get("last_tv_request", {})
        title = last_tv.get("title", "No TV requests")
        status = last_tv.get("status_text", "")
        download_info = last_tv.get("download_info")
        
        if title == "No TV requests":
            return title
        
        # Add download progress if available
        if download_info and download_info.get("has_downloads"):
            progress = download_info.get("progress_percent", 0)
            active_downloads = download_info.get("active_downloads", 0)
            return f"{title} ({status} - {active_downloads} downloading, {progress}%)"
        
        return f"{title} ({status})" if status else title

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        last_tv = self.coordinator.data.get("last_tv_request", {})
        download_info = last_tv.get("download_info")
        
        attributes = {
            "title": last_tv.get("title", "No TV requests"),
            "status": last_tv.get("status", 0),
            "status_text": last_tv.get("status_text", "N/A"),
            "requested_by": last_tv.get("requested_by", "N/A"),
            "requested_date": last_tv.get("requested_date", "N/A"),
            "tmdb_id": last_tv.get("tmdb_id", 0),
            "overseerr_online": self.coordinator.data.get("overseerr_online", False),
            "last_update": self.coordinator.data.get("last_update"),
        }
        
        # Add download information if available
        if download_info:
            attributes.update({
                "has_downloads": download_info.get("has_downloads", False),
                "active_downloads": download_info.get("active_downloads", 0),
                "download_progress": download_info.get("progress_percent", 0),
                "total_size_gb": download_info.get("total_size_gb", 0),
                "remaining_size_gb": download_info.get("remaining_size_gb", 0),
                "download_titles": download_info.get("download_titles", []),
                "has_4k_downloads": download_info.get("has_4k_downloads", False)
            })
        
        return attributes