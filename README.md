# Hassarr Integration

> **Smart Media Management with LLM Integration**

Hassarr is a Home Assistant integration that connects your media management services (Radarr, Sonarr, Overseerr/Jellyseerr) with advanced LLM (Large Language Model) support for natural language interactions. It's a custom version of the original Hassarr integration, extended to provide rich, structured responses that are perfect for chat assistants.

## Requirements

* You must have Home Assistant OS or Home Assistant Core installed
* HACS installed on Home Assistant

## Installation

### Install Hassarr on HACS
1) Press the button to add this custom repo to HACS
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=frankthetank001&repository=Hassarr-ExtendedAI&category=Integration)
2) Now look up "Hassarr" in the HACS Store search bar and download it
3) Restart your home assistant again for Hassarr to be properly added
4) Add Hassarr to your Home Assistant integrations by navigating to Settings > Devices & Services > Add Integration
5) Look up "Hassarr" and select it
6) It should prompt you to pick either Radarr & Sonarr, or Overseerr. Pick whichever service(s) you want to use and follow the instructions.

## Key Features

- **🤖 LLM-First Design**: Built for natural language interactions with ChatGPT, Claude, and other LLMs.
- **📱 Smart Media Management**: Add, remove, and track movies/TV shows.
- **📊 Real-time Monitoring**: Live sensors for downloads, queue status, and system health.
- **🔄 Automatic Updates**: Background sync with your media services.
- **🛠️ Easy Setup**: Simple configuration flow.

## Supported Services

| Service     | Movies | TV Shows | Status Tracking | Download Progress |
|-------------|:------:|:--------:|:---------------:|:-----------------:|
| **Overseerr** |   ✅   |    ✅    |        ✅       |         ✅        |
| **Radarr**    |   ✅   |    ❌    |     ⚠️ Basic     |         ❌         |
| **Sonarr**    |   ❌   |    ✅    |     ⚠️ Basic     |         ❌         |

> **Recommendation**: Use Overseerr for the best experience with full LLM integration.

---

## Configuration

### Overseerr Setup (Recommended)

**Note on Jellyseerr vs. Overseerr:** This integration has been primarily tested with **Jellyseerr**. While the APIs are very similar to Overseerr, some features may differ. For example, the `remove_media` service is designed to remove media from the library, a feature fully supported by Jellyseerr. This may not work on Overseerr. For Overseerr, deleting the request via the endpoint `api/v1/media/{mediaId}` would be the correct approach, and a future update may implement this distinction.

1.  **Requirements**
    *   An Overseerr or Jellyseerr server running.
    *   API key from your Overseerr settings.
    *   Network access from Home Assistant to your Overseerr instance.
2.  **Configuration Steps**
    *   Choose "Overseerr" as the integration type during setup.
    *   Enter your Overseerr URL (e.g., `http://192.168.1.100:5055`).
    *   Enter your API key.
    *   Select a user for making requests.

### Radarr & Sonarr Setup

**Note on Radarr/Sonarr Mode:** This mode currently has limited functionality and only supports adding media. The primary focus of this integration is on the rich, interactive experience provided by the Overseerr/Jellyseerr mode, which acts as a single, powerful entry point for all media management. The direct Radarr/Sonarr service calls have not been fully developed yet.

1.  **Requirements**
    *   Radarr and Sonarr servers running.
    *   API keys from both services.
    *   Quality profiles configured in both Radarr and Sonarr.
2.  **Configuration Steps**
    *   Choose "Radarr & Sonarr" as the integration type.
    *   Enter the URLs and API keys for both services.
    *   Select the desired quality profiles for each service.

---

## LLM & Chat Assistant Integration

Hassarr is designed for **LLM agentic integration**, allowing chat assistants like Ollama to call services directly and interpret structured JSON responses for natural, conversational interactions.

### The Correct Solution: Script Entities

For **Ollama setups**, use **script entities** that expose Hassarr functionality:

#### Step 1: Add Scripts Configuration

Add this line to your `configuration.yaml`:

```yaml
script: !include hassarr_scripts.yaml
```

#### Step 2: Create a Scripts File

You can name this file anything you like (e.g., `hassarr_scripts.yaml`) and place it in your Home Assistant config folder, or a subfolder like `auxiliary/`. Create the file and add the following content:

```yaml
hassarr_check_media_status:
  alias: "Check Media Status in Overseerr"
  description: "Check the status of a movie or TV show in Overseerr."
  mode: single
  fields:
    title:
      description: "Movie or TV show title to search for"
      required: true
      selector:
        text:
  sequence:
    - service: hassarr.check_media_status
      data:
        title: "{{ title }}"
      response_variable: status_result
    - stop: ""
      response_variable: status_result

hassarr_add_media:
  alias: "Add Media to Overseerr"
  description: "Add a movie or TV show to Overseerr for download."
  mode: single
  fields:
    title:
      description: "Movie or TV show title to add"
      required: true
      selector:
        text:
  sequence:
    - service: hassarr.add_media
      data:
        title: "{{ title }}"
      response_variable: add_result
    - stop: ""
      response_variable: add_result
```
*(Add other scripts for `search_media`, `remove_media`, etc. They are in the [hassarr_scripts.yaml](/auxiliary/hassarr_scripts.yaml) file)*

#### Step 3: Configure Ollama conversation agent

1.  Go to **Settings > Devices & Services > Ollama**.
2.  Add/Configure your Ollama instance.
3.  Enable **Assist** for home assistant control.

#### Step 4: Expose your scripts to Home Assist
1. Go to **Settings > Home Assistant**.
2. CLick on **Entities**
3. Find and add the script entities you created in step 2.

> Note: The services can be tested directly in **Settings > Developer Options > Actions**. Here you may find the service, send parameters and observe the response.
If any errors, check the home assistant logs.

#### How the LLM Integration Works

The magic of this integration lies in how it communicates back to the chat assistant. Here's the process:

1.  You speak or type a command to your assistant (e.g., Ollama).
2.  The assistant matches your command to one of the exposed scripts (e.g., `script.hassarr_add_media`).
3.  The script calls the corresponding Hassarr service.
4.  The Hassarr service does its job (e.g., talks to the Overseerr API) and builds a detailed, structured JSON response.
5.  This JSON response is passed back to the script's `response_variable`.
6.  **Crucially, the entire `response_variable` is then sent back to the LLM.**
7.  The LLM uses this rich, structured data to formulate a helpful, natural-sounding response to you, rather than just saying "OK, I've run the script."

This script-based approach is an elegant workaround for a Home Assistant limitation, which is explained in the "Limitations" section below.

### Example Conversations

Here are a few examples of how you can interact with your chat assistant once Hassarr is set up.

#### Adding New Media
**User:** "Add The Dark Knight to my library"

**Ollama:** "I'll add The Dark Knight to your media library for you."
*[Calls `script.hassarr_add_media` with `title: "The Dark Knight"`]*

**Ollama:** "Great! I've successfully added The Dark Knight (2008) to your Overseerr library. It has a 9.0/10 rating and the request is now pending approval. **Would you like me to check the status of this request?**"

*Self-Correction and Follow-ups:* Notice how the assistant offers a natural next step. This "suggested prompt" comes directly from the rich JSON response provided by Hassarr. The LLM is able to guide the conversation based on the context of the action just performed.

#### Checking Active Downloads
**User:** "What's currently downloading?"

**Ollama:** "Let me check your active downloads."
*[Calls `script.hassarr_get_active_requests`]*

**Ollama:** "You have 2 items currently downloading. 'The Godfather' is at 75% with about 15 minutes remaining. 'The Matrix' is at 50% with about 30 minutes remaining. You also have 3 other items pending approval."

#### Checking the Status of a Specific Movie
**User:** "What's the status of The Godfather?"

**Ollama:** "Let me check that for you."
*[Calls `script.hassarr_check_media_status` with `title: "The Godfather"`]*

**Ollama:** "The Godfather is currently downloading. It is 75% complete and should be available in about 15 minutes. It was requested by John."

---

## Services

Hassarr provides a suite of services for media management.

| Service                       | Description                                      |
| ----------------------------- | ------------------------------------------------ |
| `hassarr.add_media`             | Add a movie or TV show (auto-detects type).      |
| `hassarr.check_media_status`    | Check the status of specific media.              |
| `hassarr.get_active_requests`   | Get current downloads and pending requests.      |
| `hassarr.search_media`          | Search for multiple media results.               |
| `hassarr.remove_media`          | Remove media from your library.                  |
| `hassarr.run_job`               | Trigger Overseerr maintenance jobs.              |
| `hassarr.test_connection`       | Test connectivity to your media services.        |

### Legacy Services
These services are still available for basic Radarr/Sonarr functionality:
- `hassarr.add_radarr_movie`
- `hassarr.add_sonarr_tv_show`

---

## Sensors

Hassarr provides comprehensive monitoring sensors that update automatically.

### Primary Sensors

| Sensor                            | Description                                |
| --------------------------------- | ------------------------------------------ |
| `sensor.hassarr_active_downloads`   | Number of actively downloading items.      |
| `sensor.hassarr_queue_status`       | Human-readable queue status.               |
| `sensor.hassarr_system_health`      | Overall system health status.              |
| `binary_sensor.hassarr_overseerr_online` | `on` (connected) / `off` (disconnected). |
| `binary_sensor.hassarr_downloads_active` | `on` (downloading) / `off` (idle).       |


### Using Sensors in Automations

```yaml
automation:
  - alias: "Download Complete Notification"
    trigger:
      - platform: state
        entity_id: sensor.hassarr_active_downloads
        to: "0"
    action:
      - service: notify.mobile_app
        data:
          title: "Downloads Complete!"
          message: "All media downloads have finished."
```

---

## Limitations

*   **LLM Testing**: This integration was developed and tested primarily with the **Ollama** conversation agent. While it should work with other agents that can call script entities, it has not been tested with the official OpenAI or the Extended OpenAI Conversation integrations. Future updates may include specific compatibility for these platforms.

*   **The Script Workaround**: You might wonder why we need to use scripts instead of calling the services directly from the LLM. This is due to a current limitation in Home Assistant: conversation agents **cannot directly call services**. They can only interact with **entities**. By wrapping our services in simple scripts, we create `script` entities that *can* be exposed to assistants like Ollama. This is an elegant and effective workaround that unlocks the full power of the integration for voice and chat control. The Extended OpenAI integration has its own method for handling this using function calls, which may be explored in a future update.

*   **TV Show Requests**: Currently, when requesting a TV show, the entire series is requested by default. There is no support for requesting specific seasons.

---

## Future Enhancements

Here is a list of planned improvements for the integration:

*   **Radarr/Sonarr Feature Parity**: Update the direct Radarr/Sonarr mode to have the same rich service calls and sensor support as the Overseerr/Jellyseerr mode.
*   **Smarter Status Checks**: Enhance the `check_media_status` service to query Radarr/Sonarr directly if a movie is not found or is stuck in a non-downloading state in Overseerr.
*   **Availability Sync**: Improve the status check to poll Radarr/Sonarr directly if a request is 100% downloaded in the client but not yet marked as "Available" in Overseerr.
*   **Post-Action Sync**: Add a post-action hook to the `add_media` and `remove_media` services to automatically trigger the media availability and download sync jobs in Overseerr, ensuring the UI reflects changes almost instantly.
*   **Quality Profile & 4K Support**: Add support for specifying quality profiles (e.g., "in 1080p", "in highest quality") and making 4K requests directly in the service call.
*   **Specific Season Requests**: Allow users to request specific seasons of a TV show instead of the entire series.

---

## Troubleshooting

### Debug Logging

Enable debug logging for detailed troubleshooting by adding this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.hassarr: debug
```