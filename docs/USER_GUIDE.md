# Hassarr User Guide

Complete guide for setting up and using Hassarr with Home Assistant.

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Services](#services)
4. [Sensors](#sensors)
5. [Troubleshooting](#troubleshooting)

## Installation

### Via HACS (Recommended)

1. **Add Custom Repository**
   - Go to HACS > Integrations > ⋮ > Custom repositories
   - Repository: `https://github.com/yourusername/Hassarr`
   - Category: `Integration`

2. **Install Integration**
   - Search for "Hassarr" in HACS
   - Click "Download" and restart Home Assistant

3. **Add Integration**
   - Settings > Devices & Services > Add Integration
   - Search "Hassarr" and follow the setup wizard

### Manual Installation

1. Copy the `hassarr` folder to `custom_components/`
2. Restart Home Assistant
3. Add the integration via Settings > Devices & Services

## Configuration

### Overseerr Setup (Recommended)

1. **Requirements**
   - Overseerr/Jellyseerr server running
   - API key from Overseerr settings
   - Network access from Home Assistant

2. **Configuration Steps**
   - Choose "Overseerr" integration type
   - Enter your Overseerr URL (e.g., `http://192.168.1.100:5055`)
   - Enter your API key
   - Select a user for requests

### Radarr & Sonarr Setup

1. **Requirements**
   - Radarr and Sonarr servers running
   - API keys from both services
   - Quality profiles configured

2. **Configuration Steps**
   - Choose "Radarr & Sonarr" integration type
   - Enter URLs and API keys for both services
   - Select quality profiles for each service

## Services

### Core Services

#### `hassarr.add_media`
Add movies or TV shows automatically.

```yaml
service: hassarr.add_media
data:
  title: "The Dark Knight"
```

**Response Structure:**
```json
{
  "action": "media_added_successfully",
  "media_type": "movie",
  "media": {
    "title": "The Dark Knight",
    "year": "2008",
    "rating": 9.0
  },
  "next_steps": {
    "suggestion": "Check the status of this request"
  }
}
```

#### `hassarr.check_media_status`
Check the status of specific media.

```yaml
service: hassarr.check_media_status
data:
  title: "Inception"
```

**Response Types:**
- `found_media` - Media found with detailed status
- `not_found` - No results found
- `connection_error` - Server connectivity issues

#### `hassarr.get_active_requests`
Get current downloads and pending requests.

```yaml
service: hassarr.get_active_requests
```

**Returns:** List of active downloads with progress information.

#### `hassarr.search_media`
Search for multiple media results.

```yaml
service: hassarr.search_media
data:
  query: "action movies 2023"
```

#### `hassarr.remove_media`
Remove media from your library.

```yaml
# By title (searches automatically)
service: hassarr.remove_media
data:
  title: "Old Movie"

# By media ID (direct removal)
service: hassarr.remove_media
data:
  media_id: "12345"
```

#### `hassarr.run_job`
Trigger Overseerr maintenance jobs.

```yaml
service: hassarr.run_job
data:
  job_id: "plex-sync"
```

#### `hassarr.test_connection`
Test connectivity to your media services.

```yaml
service: hassarr.test_connection
```

### Legacy Services (Radarr/Sonarr)

These services are available but provide basic functionality:

- `hassarr.add_radarr_movie`
- `hassarr.add_sonarr_tv_show`
- `hassarr.add_overseerr_movie`
- `hassarr.add_overseerr_tv_show`

> **Tip:** Use `hassarr.add_media` instead - it auto-detects media type.

## Sensors

Hassarr provides comprehensive monitoring sensors that update automatically.

### Primary Sensors

| Sensor | Description | Example Value |
|--------|-------------|---------------|
| `sensor.hassarr_active_downloads` | Number of actively downloading items | `3` |
| `sensor.hassarr_queue_status` | Human-readable queue status | `"3 downloading (45 total)"` |
| `sensor.hassarr_total_requests` | Total number of requests | `45` |
| `sensor.hassarr_pending_requests` | Requests awaiting approval | `2` |
| `sensor.hassarr_available_requests` | Ready to download | `5` |
| `sensor.hassarr_system_health` | Overall system status | `"Healthy - Operating normally"` |

### Extended Sensors

| Sensor | Description |
|--------|-------------|
| `sensor.hassarr_recent_requests` | Requests from last 7 days |
| `sensor.hassarr_failed_requests` | Failed/unavailable requests |
| `sensor.hassarr_movie_requests` | Movie-specific requests |
| `sensor.hassarr_tv_requests` | TV show requests |
| `sensor.hassarr_top_requester` | Most active user |
| `sensor.hassarr_jobs_status` | Overseerr jobs status |
| `sensor.hassarr_api_response_time` | API performance metric |

### Binary Sensors

| Sensor | States |
|--------|--------|
| `binary_sensor.hassarr_overseerr_online` | `on` (connected) / `off` (disconnected) |
| `binary_sensor.hassarr_downloads_active` | `on` (downloading) / `off` (idle) |

### Using Sensors in Automations

```yaml
automation:
  - alias: "Download Complete Notification"
    trigger:
      - platform: state
        entity_id: sensor.hassarr_active_downloads
        to: "0"
    condition:
      - condition: numeric_state
        entity_id: sensor.hassarr_total_requests
        above: 0
    action:
      - service: notify.mobile_app
        data:
          title: "Downloads Complete!"
          message: "All media downloads have finished"

  - alias: "Connection Lost Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.hassarr_overseerr_online
        to: "off"
        for: "00:02:00"
    action:
      - service: persistent_notification.create
        data:
          title: "Overseerr Offline"
          message: "Lost connection to Overseerr server"
```

## Automation Examples

### Basic Media Addition

```yaml
automation:
  - alias: "Add Movie via Input"
    trigger:
      - platform: state
        entity_id: input_text.movie_to_add
    action:
      - service: hassarr.add_media
        data:
          title: "{{ states('input_text.movie_to_add') }}"
        response_variable: add_result
      - service: input_text.set_value
        data:
          entity_id: input_text.movie_to_add
          value: ""
      - service: persistent_notification.create
        data:
          title: "Media Request"
          message: "{{ add_result.message }}"
```

### Download Progress Monitoring

```yaml
automation:
  - alias: "Download Progress Update"
    trigger:
      - platform: time_pattern
        minutes: "/5"  # Every 5 minutes
    action:
      - service: hassarr.get_active_requests
        response_variable: active_downloads
      - condition: template
        value_template: "{{ active_downloads.processing_count > 0 }}"
      - service: notify.family
        data:
          title: "Download Progress"
          message: >
            Currently downloading {{ active_downloads.processing_count }} items.
            {{ active_downloads.pending_count }} waiting for approval.
```

## Troubleshooting

### Common Issues

#### "Service not found" Error
1. Verify integration is installed and loaded
2. Check Home Assistant logs for errors
3. Restart Home Assistant
4. Verify YAML syntax in automations

#### Connection Errors
1. **Test Connectivity**
   ```yaml
   service: hassarr.test_connection
   ```

2. **Common Causes:**
   - Incorrect URL or API key
   - Network connectivity issues
   - Overseerr server down
   - Firewall blocking access

#### Sensors Not Updating
1. Check if `binary_sensor.hassarr_overseerr_online` is `on`
2. Verify API permissions in Overseerr
3. Check Home Assistant logs for update errors
4. Restart the integration: Settings > Devices & Services > Hassarr > Reload

### Debug Logging

Enable debug logging for detailed troubleshooting:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.hassarr: debug
```

### Manual Testing

Test services individually in Developer Tools > Services:

1. **Test Connection**
   - Service: `hassarr.test_connection`
   - Check response for errors

2. **Search Test**
   - Service: `hassarr.search_media`
   - Data: `query: "test"`

3. **Status Check**
   - Service: `hassarr.check_media_status`
   - Data: `title: "popular movie"`

### Getting Help

1. **Check Logs:** Settings > System > Logs
2. **Search Issues:** [GitHub Issues](https://github.com/yourusername/Hassarr/issues)
3. **Community:** [Home Assistant Community Forum](https://community.home-assistant.io/)

## Best Practices

### Performance
- Use sensors for monitoring instead of frequent service calls
- Set reasonable update intervals (default 30 seconds is usually fine)
- Don't call services in tight loops

### Reliability
- Always check `binary_sensor.hassarr_overseerr_online` before service calls
- Use `continue_on_error: true` for non-critical automations
- Implement retry logic for important operations

### Organization
- Group related automations together
- Use meaningful names for automations and scripts
- Document your automation logic with comments

---

**Need more help?** Check the [Chat Assistant Integration Guide](CHAT_ASSISTANT.md) for LLM-specific features. 