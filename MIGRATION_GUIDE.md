# Migration Guide: From Deprecated Scripts to Hassarr LLM Integration

This guide helps you migrate from the deprecated YAML-based scripts to the new integrated Hassarr component with LLM capabilities.

## Overview of Changes

### What's New
- **Integrated Component**: All functionality is now part of the Hassarr custom component
- **LLM-Optimized Responses**: Structured JSON responses designed for natural language processing
- **Better Error Handling**: Comprehensive error types and messages
- **Improved API Client**: Robust Overseerr API client with automatic retry logic
- **Service-Based Architecture**: Clean service interfaces instead of complex YAML scripts

### What's Removed
- Complex YAML scripts with hundreds of lines
- Manual REST command configuration
- Input text entities for storing results
- Template-heavy automation logic

## Migration Steps

### Step 1: Install the Updated Hassarr Component

1. Update your Hassarr component to the latest version
2. Restart Home Assistant
3. Verify the new services are available in Developer Tools > Services

### Step 2: Remove Deprecated Configuration

Remove these sections from your `configuration.yaml`:

```yaml
# REMOVE: These REST commands are no longer needed
rest_command:
  search_overseerr_movie:
    url: "https://jellyseerr.shafted.dev/api/v1/search?query={{ query | replace(':', '%3A') | urlencode }}"
    method: GET
    headers:
      X-Api-Key: "your-api-key"
  get_overseerr_requests:
    url: "https://jellyseerr.shafted.dev/api/v1/request"
    method: GET
    headers:
      X-Api-Key: "your-api-key"
  delete_overseerr_media:
    url: "https://jellyseerr.shafted.dev/api/v1/media/{{ media_id }}"
    method: DELETE
    headers:
      X-Api-Key: "your-api-key"
  get_media_details:
    url: "https://jellyseerr.shafted.dev/api/v1/{{ media_type }}/{{ tmdb_id }}"
    method: GET
    headers:
      X-Api-Key: "your-api-key"

# REMOVE: These input_text entities are no longer needed
input_text:
  last_movie_result:
    name: "Last Movie Request Result"
    max: 255
  last_show_request_status:
    name: "Last TV Show Request Status"
    max: 500
  last_media_details:
    name: "Last Media Details"
    max: 1000
  current_request_context:
    name: "Current Request Context"
    max: 255
```

### Step 3: Replace Scripts with Services

#### Old Script: `check_movie_status_in_overseerr`
**Before:**
```yaml
# In scripts.yaml - 200+ lines of complex YAML
check_movie_status_in_overseerr:
  sequence:
  - action: rest_command.search_overseerr_movie
    data:
      query: '{{ title }}'
    response_variable: search_response
    continue_on_error: true
  # ... hundreds more lines
```

**After:**
```yaml
# In automations.yaml - simple service call
- alias: "Check Media Status"
  trigger:
    - platform: conversation
      command:
        - "What's the status of {title}"
  action:
    - service: hassarr.check_media_status
      data:
        title: "{{ trigger.slots.title }}"
```

#### Old Script: `get_active_overseerr_requests_llm_guided`
**Before:**
```yaml
# In scripts.yaml - 300+ lines of complex YAML
get_active_overseerr_requests_llm_guided:
  sequence:
  - action: rest_command.get_overseerr_requests
    response_variable: requests_response
    data: {}
  # ... hundreds more lines
```

**After:**
```yaml
# In automations.yaml - simple service call
- alias: "Get Active Downloads"
  trigger:
    - platform: conversation
      command:
        - "What's downloading"
  action:
    - service: hassarr.get_active_requests
```

#### Old Script: `remove_media_from_overseerr_llm_guided`
**Before:**
```yaml
# In scripts.yaml - 50+ lines
remove_media_from_overseerr_llm_guided:
  sequence:
  - action: rest_command.delete_overseerr_media
    data:
      media_id: '{{ media_id }}'
    response_variable: delete_response
  # ... more lines
```

**After:**
```yaml
# In automations.yaml - simple service call
- alias: "Remove Media"
  trigger:
    - platform: conversation
      command:
        - "Remove media {media_id}"
  action:
    - service: hassarr.remove_media
      data:
        media_id: "{{ trigger.slots.media_id }}"
```

### Step 4: Update Automation Logic

#### Old Pattern: Complex Template Logic
**Before:**
```yaml
- service: persistent_notification.create
  data:
    title: "Media Status"
    message: |
      {% set result = states('input_text.last_status_check') %}
      {% if result %}
        {% set data = result | from_json %}
        {% if data.action == 'found_media' %}
          Title: {{ data.primary_result.search_info.title }}
          Status: {{ data.primary_result.search_info.status_text }}
        {% endif %}
      {% endif %}
```

**After:**
```yaml
- service: hassarr.check_media_status
  data:
    title: "{{ trigger.slots.title }}"
- service: persistent_notification.create
  data:
    title: "Media Status"
    message: |
      {% set result = state_attr('input_text.last_status_check', 'value') %}
      {% if result and result.action == 'found_media' %}
        Title: {{ result.primary_result.search_info.title }}
        Status: {{ result.primary_result.search_info.status_text }}
      {% endif %}
```

### Step 5: Handle Service Responses

The new services return structured data that's automatically stored in `hass.data[f"{DOMAIN}_results"]`. You can access this data in your automations:

```yaml
# Access the last status check result
{% set result = state_attr('input_text.last_status_check', 'value') %}

# Check the action type
{% if result.action == 'found_media' %}
  # Media was found
{% elif result.action == 'not_found' %}
  # No media found
{% elif result.action == 'connection_error' %}
  # Connection failed
{% endif %}
```

## Service Mapping

| Old Script | New Service | Description |
|------------|-------------|-------------|
| `check_movie_status_in_overseerr` | `hassarr.check_media_status` | Check media status with LLM response |
| `get_active_overseerr_requests_llm_guided` | `hassarr.get_active_requests` | Get active downloads with progress |
| `remove_media_from_overseerr_llm_guided` | `hassarr.remove_media` | Remove media from Overseerr |
| `smart_add_media_to_overseerr_unified_llm_guided` | `hassarr.add_overseerr_movie` / `hassarr.add_overseerr_tv_show` | Add media to Overseerr |

## Response Format Changes

### Old Format (YAML Scripts)
```yaml
llm_response:
  action: found_media
  primary_result:
    search_info:
      title: "The Matrix"
      status: 3
      status_text: "Processing/Downloading"
```

### New Format (Services)
```json
{
  "action": "found_media",
  "llm_instructions": "Focus on request status, who requested it, download progress, and content overview unless asked for specific details.",
  "primary_result": {
    "search_info": {
      "title": "The Matrix",
      "status": 3,
      "status_text": "Processing/Downloading"
    }
  }
}
```

## Action Types Reference

### Status Check Actions
- `found_media` - Media found with detailed information
- `not_found` - No media found matching search criteria
- `connection_error` - Failed to connect to Overseerr
- `missing_title` - No search title provided

### Request Management Actions
- `active_requests_found` - Active requests found with download progress
- `no_active_requests` - No active requests in queue
- `media_removed` - Media successfully removed
- `removal_failed` - Failed to remove media

### Search Actions
- `search_results` - Search results found
- `details_found` - Media details retrieved successfully

## Troubleshooting Migration

### Common Issues

1. **Service Not Found**
   - Ensure you've restarted Home Assistant after updating
   - Check that the Hassarr integration is properly configured

2. **Missing Results**
   - Results are now stored in `hass.data[f"{DOMAIN}_results"]`
   - Use `state_attr('input_text.last_status_check', 'value')` to access them

3. **Template Errors**
   - The new response format is JSON, not YAML
   - Use `state_attr()` instead of `states()` for accessing results

4. **Connection Errors**
   - Verify your Overseerr configuration in the Hassarr integration
   - Check that your API key and URL are correct

### Debugging

Enable debug logging to troubleshoot issues:

```yaml
logger:
  default: info
  logs:
    custom_components.hassarr: debug
```

## Benefits of Migration

### Performance
- **Faster Response Times**: Direct API calls instead of complex YAML processing
- **Reduced Memory Usage**: No need for large input_text entities
- **Better Error Handling**: Comprehensive error types and recovery

### Maintainability
- **Cleaner Code**: Simple service calls instead of complex scripts
- **Better Documentation**: Clear service definitions and examples
- **Easier Debugging**: Structured logging and error messages

### Functionality
- **LLM Optimization**: Responses designed for natural language processing
- **Rich Metadata**: Comprehensive media information extraction
- **Download Progress**: Detailed progress tracking with time estimates
- **Request History**: User tracking and request management

## Complete Example Migration

### Before (Old Scripts)
```yaml
# configuration.yaml
rest_command:
  search_overseerr_movie:
    url: "https://jellyseerr.shafted.dev/api/v1/search?query={{ query }}"
    headers:
      X-Api-Key: "your-api-key"

input_text:
  last_movie_result:
    name: "Last Movie Request Result"
    max: 255

# scripts.yaml (200+ lines)
check_movie_status_in_overseerr:
  sequence:
  - action: rest_command.search_overseerr_movie
    data:
      query: '{{ title }}'
    response_variable: search_response
    continue_on_error: true
  # ... hundreds more lines

# automations.yaml
- alias: "Check Status"
  trigger:
    - platform: conversation
      command:
        - "Check {title}"
  action:
    - service: script.check_movie_status_in_overseerr
      data:
        title: "{{ trigger.slots.title }}"
```

### After (New Integration)
```yaml
# configuration.yaml
# No REST commands or input_text needed!

# automations.yaml
- alias: "Check Status"
  trigger:
    - platform: conversation
      command:
        - "Check {title}"
  action:
    - service: hassarr.check_media_status
      data:
        title: "{{ trigger.slots.title }}"
    - service: persistent_notification.create
      data:
        title: "Media Status"
        message: |
          {% set result = state_attr('input_text.last_status_check', 'value') %}
          {% if result and result.action == 'found_media' %}
            **{{ result.primary_result.search_info.title }}**
            Status: {{ result.primary_result.search_info.status_text }}
          {% endif %}
```

## Support

If you encounter issues during migration:

1. Check the [README.md](README.md) for detailed documentation
2. Review the [examples/llm_automations.yaml](examples/llm_automations.yaml) for working examples
3. Enable debug logging to troubleshoot issues
4. Open an issue on the GitHub repository with detailed error information

The new integration provides the same functionality as the deprecated scripts but with improved performance, maintainability, and LLM integration capabilities. 