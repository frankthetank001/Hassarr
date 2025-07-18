# File: const.py
# Note: Keep this filename comment for navigation and organization

DOMAIN = "hassarr"

SERVICE_ADD_RADARR_MOVIE = "add_radarr_movie"
SERVICE_ADD_SONARR_TV_SHOW = "add_sonarr_tv_show"
SERVICE_ADD_OVERSEERR_MOVIE = "add_overseerr_movie"
SERVICE_ADD_OVERSEERR_TV_SHOW = "add_overseerr_tv_show"

# New LLM-focused services
SERVICE_CHECK_MEDIA_STATUS = "check_media_status"
SERVICE_REMOVE_MEDIA = "remove_media"
SERVICE_GET_ACTIVE_REQUESTS = "get_active_requests"
SERVICE_GET_ALL_MEDIA = "get_all_media"
SERVICE_SEARCH_MEDIA = "search_media"
SERVICE_GET_MEDIA_DETAILS = "get_media_details"

# Sensor entities for Home Assistant native approach
SENSOR_ACTIVE_DOWNLOADS = "active_downloads"
SENSOR_MEDIA_STATUS = "media_status"
SENSOR_QUEUE_STATUS = "queue_status"
SENSOR_SEARCH_RESULTS = "search_results"
SENSOR_JOBS_STATUS = "jobs_status"

# New comprehensive sensor suite
SENSOR_TOTAL_REQUESTS = "total_requests"
SENSOR_PENDING_REQUESTS = "pending_requests"
SENSOR_AVAILABLE_REQUESTS = "available_requests"
SENSOR_RECENT_REQUESTS = "recent_requests"
SENSOR_FAILED_REQUESTS = "failed_requests"
SENSOR_MOVIE_REQUESTS = "movie_requests"
SENSOR_TV_REQUESTS = "tv_requests"
SENSOR_TOP_REQUESTER = "top_requester"
SENSOR_SYSTEM_HEALTH = "system_health"
SENSOR_NEXT_JOB = "next_job"
SENSOR_API_RESPONSE_TIME = "api_response_time"

# Binary sensors for state tracking
BINARY_SENSOR_OVERSEERR_ONLINE = "overseerr_online"
BINARY_SENSOR_DOWNLOADS_ACTIVE = "downloads_active"

# Service categories for organization
SERVICE_CATEGORIES = {
    "add": [SERVICE_ADD_RADARR_MOVIE, SERVICE_ADD_SONARR_TV_SHOW, SERVICE_ADD_OVERSEERR_MOVIE, SERVICE_ADD_OVERSEERR_TV_SHOW],
    "status": [SERVICE_CHECK_MEDIA_STATUS, SERVICE_GET_ACTIVE_REQUESTS],
    "manage": [SERVICE_REMOVE_MEDIA, SERVICE_SEARCH_MEDIA, SERVICE_GET_MEDIA_DETAILS]
}

# Update intervals
UPDATE_INTERVAL = 30  # seconds
STATUS_UPDATE_INTERVAL = 60  # seconds