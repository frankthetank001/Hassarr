# Hassarr Chat Assistant Usage Guide

This guide explains how to use Hassarr with Home Assistant's chat assistant functionality, including the new user context awareness and script-based entity exposure.

## Overview

Hassarr now provides **two complementary approaches** for LLM integration:

1. **Direct Service Calls** - For automations and advanced integrations
2. **Script Entities** - For chat assistant interactions (what users will primarily use)

## User Context Awareness

### What's New
Every Hassarr operation now includes information about **who** is performing the action:

```json
{
  "action": "found_media",
  "user_context": {
    "user_id": "abc123",
    "username": "John Doe", 
    "is_admin": true,
    "is_active": true
  },
  "primary_result": { ... }
}
```

### Benefits
- **Audit Trail**: Know who requested what media
- **Personalization**: LLM can respond with user-specific language
- **Security**: Track admin vs regular user actions
- **Logging**: All actions are logged with user information

## Chat Assistant Integration

### Available Scripts

The chat assistant can execute these Hassarr scripts as entities:

#### Core Media Management
- `script.hassarr_check_media_status` - Check status of specific media
- `script.hassarr_search_media` - Search for movies/TV shows
- `script.hassarr_add_media` - Add media to Overseerr
- `script.hassarr_remove_media` - Remove media from Overseerr
- `script.hassarr_get_active_requests` - Get current downloads/queue

#### System Management
- `script.hassarr_test_connection` - Test Overseerr connectivity
- `script.hassarr_run_job` - Run Overseerr maintenance jobs

#### Advanced Reports
- `script.hassarr_quick_status_check` - System overview
- `script.hassarr_media_library_report` - Comprehensive library report
- `script.hassarr_system_diagnostics` - Troubleshooting diagnostics

## Example Chat Interactions

### 1. Checking Media Status

**User:** "What's the status of The Matrix?"

**Chat Assistant Action:**
```yaml
# Calls: script.hassarr_check_media_status
# Parameters: title: "The Matrix"
```

**Response Data:**
```json
{
  "action": "found_media",
  "user_context": {
    "username": "John Doe",
    "is_admin": true
  },
  "primary_result": {
    "search_info": {
      "title": "The Matrix",
      "status_text": "Processing/Downloading",
      "request_details": {
        "requested_by": "Jane Smith",
        "request_date": "2024-01-15T10:00:00Z"
      }
    }
  },
  "message": "Found detailed information for 'The Matrix'..."
}
```

**LLM Response:** "The Matrix is currently downloading. It was requested by Jane Smith on January 15th and should be available soon."

### 2. Adding New Media

**User:** "Add Inception to my library"

**Chat Assistant Action:**
```yaml
# Calls: script.hassarr_add_media  
# Parameters: title: "Inception"
```

**Response Data:**
```json
{
  "action": "media_added_successfully",
  "user_context": {
    "username": "John Doe"
  },
  "media": {
    "title": "Inception",
    "year": "2010",
    "rating": 8.8
  },
  "next_steps": {
    "suggestion": "Would you like me to check the status of this media request?",
    "action_prompt": "Ask me: 'What's the status of Inception?'"
  }
}
```

**LLM Response:** "I've successfully added Inception (2010) to your Overseerr library. It has an 8.8/10 rating. The request is now pending approval. Would you like me to check its status?"

### 3. System Status Check

**User:** "How is my media server doing?"

**Chat Assistant Action:**
```yaml
# Calls: script.hassarr_quick_status_check
# Parameters: none
```

**Response Data:**
```json
{
  "summary": {
    "overseerr_online": true,
    "total_requests": 45,
    "active_downloads": 3,
    "pending_requests": 2
  },
  "message": "System Status: ✅ Online - 3 downloading, 2 pending"
}
```

**LLM Response:** "Your media server is running perfectly! You have 3 items currently downloading and 2 requests pending approval out of 45 total requests."

## User Permission Levels

### Admin Users
- Can add/remove any media
- Can run system jobs
- Can access diagnostic information
- Get full system reports

### Regular Users  
- Can add media (subject to Overseerr permissions)
- Can check status of any media
- Can search for media
- Cannot remove media or run jobs

## Advanced Features

### 1. Comprehensive Library Report

**User:** "Give me a full report on my media library"

**Chat Assistant Action:**
```yaml
# Calls: script.hassarr_media_library_report
```

**Features:**
- Live sensor data integration
- Request statistics
- System health metrics
- User activity summary
- LLM-optimized presentation

### 2. System Diagnostics

**User:** "My media server isn't working properly"

**Chat Assistant Action:**
```yaml
# Calls: script.hassarr_system_diagnostics
```

**Features:**
- Connection testing
- API functionality verification
- Sensor status checks
- Configuration validation
- Troubleshooting recommendations

### 3. Legacy Compatibility

**User:** "Add a movie" (using old automation)

**Legacy Script Handling:**
```yaml
# Old: script.hassarr_add_movie
# Redirects to: script.hassarr_add_media
# Maintains backward compatibility
```

## Configuration Requirements

### 1. Enable Scripts in Chat Assistant

In your Home Assistant configuration, ensure the chat assistant can access script entities:

```yaml
# configuration.yaml
conversation:
  intents:
    HassFindMedia:
      - "What's the status of {title}"
      - "Check {title}"
    HassAddMedia:
      - "Add {title} to my library"
      - "Download {title}"
    HassSystemStatus:
      - "How is my media server"
      - "System status"
```

### 2. Script Loading

Add to your `configuration.yaml`:

```yaml
script: !include scripts.yaml
```

### 3. Restart Required

After adding scripts.yaml, restart Home Assistant for the entities to be available.

## Benefits Over Legacy Approach

### Before (Legacy Scripts)
```yaml
# 200+ lines of complex YAML per script
# Manual REST command configuration  
# Complex template logic
# No user context
# Difficult to maintain
```

### After (New Integration)
```yaml
# Simple script calls
# Automatic user context
# Structured JSON responses
# Easy to maintain
# Rich error handling
```

## Troubleshooting

### Script Not Found
1. Ensure `scripts.yaml` is in your config directory
2. Add `script: !include scripts.yaml` to `configuration.yaml`
3. Restart Home Assistant
4. Check Developer Tools > States for `script.hassarr_*` entities

### User Context Missing
- User context is automatically included in all service calls
- Check Home Assistant logs for user information
- Guest users may show as "Unknown User"

### Chat Assistant Not Working
1. Run `script.hassarr_system_diagnostics` manually
2. Check Overseerr connectivity
3. Verify script entities are available
4. Test individual services in Developer Tools

## Example Automations

### Track User Activity
```yaml
automation:
  - alias: "Log Media Requests"
    trigger:
      - platform: event
        event_type: call_service
        event_data:
          domain: script
          service: hassarr_add_media
    action:
      - service: logbook.log
        data:
          name: "Media Request"
          message: "{{ trigger.event.data.service_data.title }} requested by {{ user }}"
          entity_id: script.hassarr_add_media
```

### Auto-Notifications
```yaml
automation:
  - alias: "Media Added Notification"
    trigger:
      - platform: state
        entity_id: sensor.hassarr_total_requests
    action:
      - service: notify.mobile_app
        data:
          title: "New Media Request"
          message: "Total requests: {{ states('sensor.hassarr_total_requests') }}"
```

## Security Considerations

### User Permissions
- Hassarr respects Home Assistant user permissions
- Admin users get full access
- Regular users have limited capabilities
- All actions are logged with user context

### API Security
- Uses configured Overseerr user for actual requests
- Tracks HA user for audit purposes
- Secure credential storage in integration config

This integration provides a seamless bridge between natural language chat interactions and your media management system, with full user awareness and comprehensive functionality. 