# Chat Assistant Integration Guide

How to integrate Hassarr with LLM chat assistants for natural language media management.

## Overview

Hassarr is designed specifically for **LLM agentic integration**, allowing chat assistants to call services directly and interpret structured responses for natural conversations.

**Implementation Note:** Currently uses script entities for maximum compatibility with conversation agents like Ollama. Future versions may include native LLM API tools if conversation agent support becomes available.

## Key Benefits

- **Natural Language Processing** - No rigid command patterns required
- **Context Awareness** - LLMs can maintain conversation context
- **Structured Responses** - Rich JSON data for intelligent responses
- **User Context** - Tracks who performed each action
- **Error Handling** - Comprehensive error types for appropriate responses

## Quick Setup

### 1. Enable Script Entities

Since chat assistants can only interact with entities (not services directly), Hassarr provides script wrappers:

```yaml
# configuration.yaml
script: !include auxiliary/scripts.yaml
```

### 2. Available Script Entities

| Script Entity | Description |
|---------------|-------------|
| `script.hassarr_check_media_status` | Check status of specific media |
| `script.hassarr_search_media` | Search for movies/TV shows |
| `script.hassarr_add_media` | Add media to Overseerr |
| `script.hassarr_remove_media` | Remove media from Overseerr |
| `script.hassarr_get_active_requests` | Get current downloads/queue |
| `script.hassarr_test_connection` | Test Overseerr connectivity |
| `script.hassarr_run_job` | Run Overseerr maintenance jobs |

### 3. User Context Awareness

Every operation includes information about who performed it:

```json
{
  "action": "media_added_successfully",
  "user_context": {
    "user_id": "abc123",
    "username": "John Doe",
    "is_admin": true,
    "is_active": true
  },
  "media": { ... }
}
```

## Example Interactions

### 1. Checking Media Status

**User:** "What's the status of The Matrix?"

**Chat Assistant Action:**
```yaml
script.hassarr_check_media_status:
  title: "The Matrix"
```

**Response Data:**
```json
{
  "action": "found_media",
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
script.hassarr_add_media:
  title: "Inception"
```

**Response Data:**
```json
{
  "action": "media_added_successfully",
  "media": {
    "title": "Inception",
    "year": "2010",
    "rating": 8.8
  },
  "next_steps": {
    "suggestion": "Would you like me to check the status of this media request?"
  }
}
```

**LLM Response:** "I've successfully added Inception (2010) to your Overseerr library. It has an 8.8/10 rating. The request is now pending approval. Would you like me to check its status?"

### 3. System Status Check

**User:** "How is my media server doing?"

**Chat Assistant Action:**
```yaml
script.hassarr_test_connection: {}
```

**Response Data:**
```json
{
  "status": "success",
  "total_requests": 45,
  "message": "Connected successfully. Found 45 requests."
}
```

**LLM Response:** "Your media server is running perfectly! You have 45 total requests in your system."

## Response Actions

LLMs should handle these response types appropriately:

### Success Actions
- `found_media` - Media found with detailed information
- `media_added_successfully` - Media successfully added to library
- `media_removed` - Media successfully removed
- `requests_found` - Active requests retrieved
- `search_results` - Search completed with results

### Error Actions
- `not_found` - No media found matching search
- `connection_error` - Cannot connect to Overseerr
- `missing_title` / `missing_params` - Required parameters missing
- `media_already_exists` - Media already in library
- `removal_failed` - Could not remove media

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

## Configuration Requirements

### 1. Home Assistant Configuration

```yaml
# configuration.yaml
script: !include auxiliary/scripts.yaml

# Optional: Enable chat assistant access to script entities
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

### 2. Restart Required

After adding scripts configuration, restart Home Assistant for the entities to be available.

## Sensor Integration

Chat assistants can also reference live sensor data:

### Key Sensors for Context
- `sensor.hassarr_active_downloads` - Current download count
- `sensor.hassarr_queue_status` - Overall queue status
- `binary_sensor.hassarr_overseerr_online` - Connection status
- `sensor.hassarr_system_health` - System health summary

### Example Context Usage

**User:** "Are there any downloads running?"

**LLM Response (using sensor):** "Yes, you currently have {{ states('sensor.hassarr_active_downloads') }} items downloading. Your system status is {{ states('sensor.hassarr_system_health') }}."

## Best Practices

### For LLM Integration

1. **Always check response action type** before generating responses
2. **Use structured data** provided in responses rather than guessing
3. **Handle errors gracefully** with helpful suggestions
4. **Leverage user context** for personalized responses
5. **Reference sensor data** for real-time status information

### For Error Handling

```json
// Connection error example
{
  "action": "connection_error",
  "message": "Connection error - check Overseerr configuration",
  "troubleshooting": [
    "Verify Overseerr server is running",
    "Check URL and API key configuration"
  ]
}
```

**LLM Response:** "I'm unable to connect to your media server right now. Please check that Overseerr is running and verify your URL and API key configuration."

### For Follow-up Suggestions

Use the `next_steps` data in responses:

```json
{
  "next_steps": {
    "suggestion": "Would you like me to check the status of this media request?",
    "action_prompt": "Ask me: 'What's the status of Inception?'"
  }
}
```

## Troubleshooting

### Script Entities Not Available
1. Ensure `script: !include auxiliary/scripts.yaml` in configuration.yaml
2. Restart Home Assistant
3. Check Developer Tools > States for `script.hassarr_*` entities

### User Context Missing
- User context is automatically included in all service calls
- Check Home Assistant logs for user information
- Guest users may show as "Unknown User"

### Chat Assistant Not Working
1. Run diagnostic script manually to test functionality
2. Check Overseerr connectivity
3. Verify script entities are available
4. Test individual services in Developer Tools

---

**Need technical details?** See the [User Guide](USER_GUIDE.md) for complete service documentation. 