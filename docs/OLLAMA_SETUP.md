# Hassarr + Ollama Integration Setup

## The Issue with Custom LLM APIs

After thorough research of the [official Home Assistant LLM API documentation](https://developers.home-assistant.io/docs/core/llm/), the **Ollama integration does NOT support custom LLM APIs**. 

**Why custom LLM APIs don't work with Ollama:**
- Ollama integration only supports the built-in Home Assistant Assist API
- It has no options flow to select custom LLM APIs
- Custom LLM APIs require conversation agents to explicitly support them
- Only conversation integrations like OpenAI Conversation implement custom LLM API support

**Future Possibility:** If Ollama integration adds support for custom LLM APIs in the future, Hassarr could provide native LLM tools directly to conversation agents. This would eliminate the need for script entity wrappers.

## The Correct Solution: Script Entities

For **Ollama setups**, use **script entities** that expose Hassarr functionality:

### Step 1: Add Scripts Configuration

Add this line to your `configuration.yaml`:

```yaml
script: !include scripts_for_ollama.yaml
```

### Step 2: Copy Scripts File

Copy the `scripts_for_ollama.yaml` file to your Home Assistant config directory.

### Step 3: Restart Home Assistant

After restarting, you'll have these script entities:
- `script.hassarr_add_media`
- `script.hassarr_check_status`
- `script.hassarr_search_media`
- `script.hassarr_get_downloads`
- `script.hassarr_remove_media`
- `script.hassarr_test_connection`

### Step 4: Expose Scripts to Assist

1. Go to **Settings > Voice assistants > Expose**
2. Find your script entities (search for "hassarr")
3. Toggle them **ON** to expose them to your Ollama conversation agent

### Step 5: Enable Ollama Control

In your Ollama integration:
1. Go to **Settings > Devices & Services > Ollama**
2. Click **Configure**
3. Enable **"Control Home Assistant"**
4. Save the configuration

## How It Works

Your Ollama LLM will now see these as available tools:

- **"Add Media to Library"** - For adding movies/TV shows
- **"Check Media Status"** - For checking download progress
- **"Search for Media"** - For finding available content
- **"Get Active Downloads"** - For current download status
- **"Remove Media from Library"** - For removing content
- **"Test Overseerr Connection"** - For system diagnostics

## Testing

### Test Individual Scripts
Go to **Developer Tools > Services** and test:

```yaml
service: script.hassarr_add_media
data:
  title: "The Dark Knight"
```

### Test with Ollama
Ask your Ollama assistant:
- "Add Inception to my library"
- "What's the status of The Matrix?"
- "What's currently downloading?"
- "Search for action movies"

## Why This Works

1. **Scripts create entities** that Ollama can see and interact with
2. **Scripts support response_variable** which provides structured data back to the LLM
3. **Works with any conversation agent** (not just Ollama)
4. **No custom LLM API support required** from the conversation agent

## Development Note

The custom LLM API implementation has been removed from Hassarr since it's incompatible with current conversation agents like Ollama. The script entity approach provides the same functionality with broader compatibility.

## References

- [Home Assistant LLM API Documentation](https://developers.home-assistant.io/docs/core/llm/)
- [Ollama Integration Documentation](https://www.home-assistant.io/integrations/ollama/)
- [Exposing Entities to Assist](https://www.home-assistant.io/voice_control/voice_remote_expose_devices/) 