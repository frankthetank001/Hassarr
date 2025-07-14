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
        
        # New comprehensive sensors
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
            requests_data = await self.api.get_requests()
            
            # Fetch jobs data
            jobs_data = await self.api.get_jobs()
            
            # Calculate API response time
            api_response_time = (datetime.now() - start_time).total_seconds()
            
            if requests_data is None:
                _LOGGER.warning("Failed to fetch requests data from Overseerr")
                requests_data = {"results": []}
            
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
            
            results = requests_data.get("results", [])
            
            # Calculate comprehensive metrics
            metrics = self._calculate_comprehensive_metrics(results, jobs_list)
            
            data = {
                "overseerr_online": True,
                "requests": results,
                "jobs": jobs_list,
                "api_response_time": api_response_time,
                "last_update": self.hass.loop.time(),
                **metrics
            }
            
            _LOGGER.debug(f"Updated comprehensive data: {len(results)} requests, {len(jobs_list)} jobs, {api_response_time:.2f}s response time")
            return data
            
        except Exception as err:
            _LOGGER.error(f"Error fetching data: {err}")
            raise UpdateFailed(f"Error communicating with Overseerr: {err}")
    
    def _calculate_comprehensive_metrics(self, requests: list, jobs: list) -> dict:
        """Calculate comprehensive metrics from raw API data."""
        # Initialize counters
        status_counts = Counter()
        type_counts = Counter()
        user_counts = Counter()
        recent_count = 0
        
        # Get current time for recent requests calculation
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)
        
        # Process each request
        for request in requests:
            # Count by status
            status = request.get("status", 1)
            status_counts[status] += 1
            
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
        
        # Calculate job metrics
        running_jobs = len([j for j in jobs if j.get("running", False)])
        total_jobs = len(jobs)
        
        # Find next scheduled job
        next_job_info = self._find_next_scheduled_job(jobs)
        
        # Determine system health
        system_health = self._calculate_system_health(requests, jobs, status_counts)
        
        # Get top requester
        top_requester = user_counts.most_common(1)[0] if user_counts else ("No requests", 0)
        
        return {
            # Request counts by status (corrected mapping)
            "total_requests": len(requests),
            "pending_requests": status_counts.get(2, 0),  # 2 = Pending Approval
            "active_downloads": status_counts.get(3, 0),  # 3 = Processing/Downloading
            "available_requests": status_counts.get(5, 0),  # 5 = Available in Library
            "failed_requests": status_counts.get(7, 0),  # 7 = Deleted
            
            # Request counts by type
            "movie_requests": type_counts.get("movie", 0),
            "tv_requests": type_counts.get("tv", 0),
            
            # Time-based metrics
            "recent_requests": recent_count,
            
            # User metrics
            "top_requester": top_requester[0],
            "top_requester_count": top_requester[1],
            
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
    
    def _calculate_system_health(self, requests: list, jobs: list, status_counts: Counter) -> str:
        """Calculate overall system health status."""
        failed_requests = status_counts.get(7, 0)  # Status 7 = Deleted/Failed
        total_requests = len(requests)
        running_jobs = len([j for j in jobs if j.get("running", False)])
        
        # Calculate health score
        if total_requests == 0:
            return "Healthy - No activity"
        
        failure_rate = failed_requests / total_requests if total_requests > 0 else 0
        
        if failure_rate > 0.2:  # More than 20% failed
            return "Degraded - High failure rate"
        elif failure_rate > 0.1:  # More than 10% failed
            return "Warning - Some failures detected"
        elif running_jobs > 3:  # Too many jobs running
            return "Busy - Multiple jobs running"
        else:
            return "Healthy - Operating normally"


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