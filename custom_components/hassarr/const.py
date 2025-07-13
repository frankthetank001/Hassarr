DOMAIN = "hassarr"

SERVICE_ADD_RADARR_MOVIE = "add_radarr_movie"
SERVICE_ADD_SONARR_TV_SHOW = "add_sonarr_tv_show"
SERVICE_ADD_OVERSEERR_MOVIE = "add_overseerr_movie"
SERVICE_ADD_OVERSEERR_TV_SHOW = "add_overseerr_tv_show"

# New LLM-focused services
SERVICE_CHECK_MEDIA_STATUS = "check_media_status"
SERVICE_REMOVE_MEDIA = "remove_media"
SERVICE_GET_ACTIVE_REQUESTS = "get_active_requests"
SERVICE_SEARCH_MEDIA = "search_media"
SERVICE_GET_MEDIA_DETAILS = "get_media_details"

# Sensor entities for Home Assistant native approach
SENSOR_ACTIVE_DOWNLOADS = "active_downloads"
SENSOR_MEDIA_STATUS = "media_status"
SENSOR_QUEUE_STATUS = "queue_status"
SENSOR_SEARCH_RESULTS = "search_results"

# Binary sensors for state tracking
BINARY_SENSOR_OVerseerr_ONLINE = "overseerr_online"
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