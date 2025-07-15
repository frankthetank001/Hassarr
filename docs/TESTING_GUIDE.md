# Hassarr Testing Guide

## Testing Script Entities with Ollama

This guide covers how to test Hassarr functionality with Ollama conversation agents.

## Prerequisites

1. **Hassarr integration installed and configured** with Overseerr
2. **Script entities set up** (see `OLLAMA_SETUP.md`)
3. **Ollama integration configured** with "Control Home Assistant" enabled
4. **Scripts exposed to Assist** in Settings > Voice assistants > Expose

## Method 1: Test Services Directly

Test the underlying Hassarr services in **Developer Tools > Services**:

### Test Connection
```yaml
service: hassarr.test_connection
```

### Add Media
```yaml
service: hassarr.add_media
data:
  title: "The Dark Knight"
```

### Check Media Status
```yaml
service: hassarr.check_media_status
data:
  title: "Inception"
```

### Search Media
```yaml
service: hassarr.search_media
data:
  query: "action movies"
```

### Get Active Downloads
```yaml
service: hassarr.get_active_requests
```

## Method 2: Test Script Entities

Test the script wrappers in **Developer Tools > Services**:

### Add Media Script
```yaml
service: script.hassarr_add_media
data:
  title: "The Matrix"
```

### Check Status Script
```yaml
service: script.hassarr_check_status
data:
  title: "The Matrix"
```

### Search Media Script
```yaml
service: script.hassarr_search_media
data:
  query: "Christopher Nolan"
```

### Get Downloads Script
```yaml
service: script.hassarr_get_downloads
```

### Remove Media Script
```yaml
service: script.hassarr_remove_media
data:
  title: "Old Movie"
```

### Test Connection Script
```yaml
service: script.hassarr_test_connection
```

## Method 3: Test with Ollama Chat

Test by chatting with your Ollama assistant:

### Adding Media
- "Add Inception to my library"
- "Download The Dark Knight for me"
- "Can you add the movie Interstellar?"

### Checking Status
- "What's the status of The Matrix?"
- "Is Inception downloading?"
- "Check if Dune is available"

### Searching
- "Search for Christopher Nolan movies"
- "Find action movies from 2023"
- "Look for sci-fi TV shows"

### Getting Downloads
- "What's currently downloading?"
- "Show me active downloads"
- "What's in the download queue?"

### System Status
- "Test my media server connection"
- "How is Overseerr doing?"
- "Check system status"

## Expected Behavior

### Successful Interactions
Your Ollama assistant should:
1. **Recognize the intent** from natural language
2. **Call the appropriate script** with correct parameters
3. **Receive structured response data** from the script
4. **Provide natural language response** based on the data

### Example Interaction
```
User: "Add The Dark Knight to my library"

Ollama: "I'll add The Dark Knight to your media library for you."
[Calls script.hassarr_add_media with title="The Dark Knight"]

Ollama: "Great! I've successfully added The Dark Knight (2008) to your Overseerr library. 
It has a 9.0/10 rating and the request is now pending approval. 
Would you like me to check the status of this request?"
```

## Troubleshooting

### Scripts Not Available to Ollama
1. Check **Settings > Voice assistants > Expose**
2. Ensure all `script.hassarr_*` entities are toggled **ON**
3. Verify **"Control Home Assistant"** is enabled in Ollama integration
4. Restart Home Assistant if needed

### Ollama Not Calling Scripts
1. Test scripts manually first (Method 2 above)
2. Check Ollama model supports function calling
3. Try more explicit requests: "Use the Add Media to Library function to add Inception"
4. Check Home Assistant logs for any script execution errors

### Scripts Failing
1. Test underlying services first (Method 1 above)
2. Check Overseerr connectivity with `script.hassarr_test_connection`
3. Verify API key and URL configuration
4. Check Home Assistant logs for detailed error messages

### Empty Responses
1. Ensure `response_variable` is working (check in service call response)
2. Verify script has `stop:` action with `response_variable`
3. Test that underlying Hassarr services return data

## Validation Checklist

✅ **Services Work**: All `hassarr.*` services execute successfully  
✅ **Scripts Work**: All `script.hassarr_*` scripts execute successfully  
✅ **Scripts Exposed**: All scripts visible in Voice assistants > Expose  
✅ **Ollama Control**: "Control Home Assistant" enabled in Ollama  
✅ **Natural Language**: Ollama responds to conversational requests  
✅ **Structured Data**: Ollama receives and interprets response data  
✅ **Error Handling**: Graceful responses to connection/API errors  

## Development Testing

### Adding New Functionality
1. **Add service** to Hassarr with `supports_response=True`
2. **Create script wrapper** that calls the service
3. **Test script manually** with specific parameters
4. **Expose script** to Assist
5. **Test with Ollama** using natural language

### Debugging Issues
1. **Enable debug logging**:
   ```yaml
   logger:
     logs:
       custom_components.hassarr: debug
   ```
2. **Check service responses** in Developer Tools
3. **Monitor Home Assistant logs** during script execution
4. **Test incrementally** (service → script → Ollama)

## Future Enhancements

When conversation agents add support for custom LLM APIs, Hassarr could provide:
- **Direct tool access** without script wrappers
- **Parameter validation** at the LLM API level  
- **Improved performance** with fewer intermediate steps
- **Enhanced metadata** for better LLM understanding

Until then, the script entity approach provides excellent functionality and broad compatibility. 