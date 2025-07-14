# Migration Guide

How to upgrade from legacy YAML scripts to the integrated Hassarr component.

## Overview

The new Hassarr integration replaces complex YAML-based scripts with a clean, integrated component featuring:

- **90% reduction** in configuration complexity
- **LLM-optimized responses** for natural language interactions
- **Better error handling** with specific error types
- **Improved performance** through dedicated API client
- **Real-time sensors** for monitoring

## Quick Migration

### ✅ What to Do

1. **Install New Integration**
   - Install via HACS or manually
   - Go to Settings > Devices & Services > Add Integration
   - Search "Hassarr" and configure

2. **Add Script Support (for Chat Assistants)**
   ```yaml
   # configuration.yaml
   script: !include auxiliary/scripts.yaml
   ```

3. **Update Automations**
   ```yaml
   # OLD (complex script call)
   - service: script.check_movie_status_in_overseerr
     data:
       title: "{{ title }}"
   
   # NEW (simple service call)
   - service: hassarr.check_media_status
     data:
       title: "{{ title }}"
   ```

### ❌ What to Remove

Remove these sections from your `configuration.yaml`:

```yaml
# REMOVE: Old REST commands
rest_command:
  search_overseerr_movie: ...
  get_overseerr_requests: ...
  delete_overseerr_media: ...
  get_media_details: ...

# REMOVE: Input text helpers
input_text:
  last_movie_result: ...
  last_show_request_status: ...
  last_media_details: ...
  current_request_context: ...

# REMOVE: Old script includes
script: !include scripts.yaml  # Only if it contains old Hassarr scripts
```

## Service Migration

### Old → New Service Mapping

| Old Script/Service | New Service | Notes |
|-------------------|-------------|-------|
| `script.check_movie_status_in_overseerr` | `hassarr.check_media_status` | Now handles movies & TV |
| `script.smart_add_media_to_overseerr_unified_llm_guided` | `hassarr.add_media` | Auto-detects media type |
| `script.get_active_overseerr_requests_llm_guided` | `hassarr.get_active_requests` | Simplified response |
| `script.remove_media_from_overseerr_llm_guided` | `hassarr.remove_media` | Better error handling |
| Manual REST calls | `hassarr.search_media` | New search service |
| N/A | `hassarr.run_job` | New job management |
| N/A | `hassarr.test_connection` | New diagnostics |

### Response Format Changes

**Old Response (YAML template):**
```yaml
variables:
  llm_response:
    action: found_media
    searched_title: "{{ title }}"
    primary_result:
      search_info:
        title: "{{ first_result.title }}"
        # ... complex template logic
```

**New Response (Structured JSON):**
```json
{
  "action": "found_media",
  "searched_title": "The Matrix",
  "primary_result": {
    "search_info": {
      "title": "The Matrix",
      "status_text": "Processing/Downloading"
    }
  },
  "user_context": {
    "username": "John Doe",
    "is_admin": true
  }
}
```

## Automation Updates

### Before (Legacy)
```yaml
automation:
  - alias: "Add Movie Request"
    trigger:
      - platform: state
        entity_id: input_text.movie_request
    action:
      - service: script.smart_add_media_to_overseerr_unified_llm_guided
        data:
          title: "{{ states('input_text.movie_request') }}"
      - service: input_text.set_value
        data:
          entity_id: input_text.movie_request
          value: ""
      - service: persistent_notification.create
        data:
          title: "Movie Request"
          message: "Request submitted for {{ states('input_text.movie_request') }}"
```

### After (New Integration)
```yaml
automation:
  - alias: "Add Movie Request"
    trigger:
      - platform: state
        entity_id: input_text.movie_request
    action:
      - service: hassarr.add_media
        data:
          title: "{{ states('input_text.movie_request') }}"
        response_variable: add_result
      - service: input_text.set_value
        data:
          entity_id: input_text.movie_request
          value: ""
      - service: persistent_notification.create
        data:
          title: "Media Request"
          message: "{{ add_result.message }}"
```

## New Features Available

### Real-time Sensors
```yaml
# Monitor download progress
sensor.hassarr_active_downloads: 3
sensor.hassarr_queue_status: "3 downloading (45 total)"
sensor.hassarr_system_health: "Healthy - Operating normally"

# Binary sensors for automations
binary_sensor.hassarr_overseerr_online: on
binary_sensor.hassarr_downloads_active: on
```

### User Context Tracking
```json
{
  "user_context": {
    "username": "John Doe",
    "is_admin": true,
    "user_id": "abc123"
  }
}
```

### Enhanced Error Handling
```json
{
  "action": "connection_error",
  "troubleshooting": [
    "Verify Overseerr server is running",
    "Check URL and API key configuration"
  ]
}
```

## Verification Steps

After migration, verify everything works:

1. **Test Basic Connectivity**
   ```yaml
   service: hassarr.test_connection
   ```

2. **Test Media Search**
   ```yaml
   service: hassarr.search_media
   data:
     query: "popular movie"
   ```

3. **Check Sensors**
   - Go to Developer Tools > States
   - Search for `hassarr` entities
   - Verify sensors are updating

4. **Test Automations**
   - Run existing automations with new service calls
   - Check for errors in Home Assistant logs

## Troubleshooting

### Common Issues

**Services Not Found**
- Restart Home Assistant after installation
- Check integration is loaded: Settings > Devices & Services

**Sensors Not Updating**
- Verify Overseerr connectivity with `hassarr.test_connection`
- Check logs for API errors
- Ensure API key has correct permissions

**Old Scripts Still Running**
- Remove old script files
- Clear automation YAML caches
- Restart Home Assistant

### Getting Help

1. **Enable Debug Logging**
   ```yaml
   logger:
     logs:
       custom_components.hassarr: debug
   ```

2. **Check Common Issues**
   - [GitHub Issues](https://github.com/yourusername/Hassarr/issues)
   - [User Guide Troubleshooting](USER_GUIDE.md#troubleshooting)

3. **Community Support**
   - [Home Assistant Community Forum](https://community.home-assistant.io/)

---

**Questions?** See the [User Guide](USER_GUIDE.md) for complete documentation. 