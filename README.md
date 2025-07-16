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
- **📺 Intelligent Season Requests**: Natural language season support - "add season two", "remaining seasons", "next season".
- **🧠 Smart Suggestions**: Automatically suggests missing seasons when adding existing TV shows.
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
    *   **User Mapping**: Map each Home Assistant user to their corresponding Overseerr user account.
3.  **User Mapping Interface**
    *   **Automatic Detection**: The integration automatically detects all active Home Assistant users and Overseerr users.
    *   **Friendly Names**: Home Assistant users are displayed with their friendly names (name, username, or shortened ID).
    *   **Simple Mapping**: For each Home Assistant user, select which Overseerr user account they should use.
    *   **Clear Descriptions**: Each field is clearly labeled with the user's friendly name for easy identification.
    *   **Automatic Default**: The first mapped user is automatically set as the default for system operations.
    *   **Error Handling**: If Overseerr is unreachable or has no users, clear error messages guide you to fix the issue.
    *   **Reconfiguration**: You can update user mappings later through the integration's configure option.

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

## User Permissions & Access Control

Hassarr implements a user mapping system to control who can make media requests:

### **User Mapping System**
- **Setup**: During integration configuration, you map each Home Assistant user to an Overseerr user
- **Default User**: One Overseerr user is selected as the default for the integration
- **Access Control**: Only mapped users can perform write operations
- **Simple Mapping**: Enter a Home Assistant username and select the corresponding Overseerr user
- **Multiple Mappings**: Add one mapping at a time until all needed users are mapped
- **Flexible Configuration**: When finished adding mappings, leave both fields empty and click Submit

### **Operation Permissions**

| Operation | Mapped Users | Unmapped Users | Description |
|-----------|-------------|----------------|-------------|
| **Add Media** | ✅ Allowed | ❌ Blocked | Add movies/TV shows to Overseerr |
| **Remove Media** | ✅ Allowed | ❌ Blocked | Remove media from library |
| **Run Jobs** | ✅ Allowed | ❌ Blocked | Trigger maintenance jobs |
| **Search Media** | ✅ Allowed | ✅ Allowed | Search for movies/TV shows |
| **Check Status** | ✅ Allowed | ✅ Allowed | Check media download status |
| **View Requests** | ✅ Allowed | ✅ Allowed | View active downloads |

### **Error Messages**
When an unmapped user tries to perform a restricted operation, they'll receive a clear error message:
> "Sorry [username], you're not registered to make media requests through this system. Contact your system administrator to add your account to the media request system."

### **Managing User Access**
To add or modify user mappings:
1. Go to **Settings > Devices & Services > Hassarr**
2. Click **Configure** on the Hassarr integration
3. Navigate to the **User Mapping** section
4. Enter Home Assistant usernames and select corresponding Overseerr users
5. Save the configuration

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

#### Adding Specific TV Show Seasons
**User:** "Add season 3 of Stranger Things"

**Ollama:** "I'll add season 3 of Stranger Things to your library."
*[Calls `script.hassarr_add_media` with `title: "Stranger Things"` and `season: 3`]*

**Ollama:** "Perfect! I've successfully added Stranger Things season 3 to your Overseerr library. The request is now pending approval. Season 3 specifically has been requested as you asked."

**User:** "Add Breaking Bad"

**Ollama:** "I'll add Breaking Bad to your library."
*[Calls `script.hassarr_add_media` with `title: "Breaking Bad"`]*

**Ollama:** "Great! I've successfully added Breaking Bad to your Overseerr library. Since you didn't specify a season, I defaulted to season 1. The request is now pending approval."

#### Natural Language Season Requests
**User:** "Add season two of The Office"

**Ollama:** "I'll add season 2 of The Office to your library."
*[Calls `script.hassarr_add_media` with `title: "The Office"` and `season: "season two"`]*

**Ollama:** "Perfect! I've successfully added The Office season 2 to your Overseerr library. The request is now pending approval."

**User:** "Add the remaining seasons of Game of Thrones"

**Ollama:** "Let me check what seasons you already have and add the missing ones."
*[Calls `script.hassarr_add_media` with `title: "Game of Thrones"` and `season: "remaining seasons"`]*

**Ollama:** "You already have Game of Thrones in your library! Seasons 1-3 are available, season 4 is downloading. I can add seasons 5-8 if you'd like. Should I request the remaining 4 seasons?"

**User:** "Add seasons 1 to 5 of Breaking Bad"

**Ollama:** "I'll add seasons 1 through 5 of Breaking Bad to your library."
*[Calls `script.hassarr_add_media` with `title: "Breaking Bad"` and `season: "seasons 1 to 5"`]*

**Ollama:** "Perfect! I've successfully added Breaking Bad seasons 1, 2, 3, 4, 5 to your Overseerr library. The request is now pending approval."

**User:** "Add seasons 1, 3, and 5 of The Office"

**Ollama:** "I'll add seasons 1, 3, and 5 of The Office to your library."
*[Calls `script.hassarr_add_media` with `title: "The Office"` and `season: "1, 3, 5"`]*

**Ollama:** "Great! I've successfully added The Office seasons 1, 3, 5 to your Overseerr library. The request is now pending approval."

#### Smart Suggestions for Existing Shows
**User:** "Add Two and a Half Men"

**Ollama:** "I'll add Two and a Half Men to your library."
*[Calls `script.hassarr_add_media` with `title: "Two and a Half Men"`]*

**Ollama:** "Two and a Half Men already exists in your Overseerr library! Season 1 is currently downloading. The show has 12 total seasons. Would you like me to add the remaining seasons (2-12)?"

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

#### Enhanced Season Information for TV Shows
**User:** "What's the status of Two and a Half Men?"

**Ollama:** "Let me check the status for you."
*[Calls `script.hassarr_check_media_status` with `title: "Two and a Half Men"`]*

**Ollama:** "Two and a Half Men has Season 2 currently downloading. I can see 10 episodes are actively downloading, including Episode 24 'Does This Smell Funny to You?' which is 75% complete. The season should be ready in about 21 hours. This was requested by the homeassistant user. The show has 12 total seasons, with seasons 1, 3-12 not yet requested. Would you like me to add the remaining seasons?"

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

---

## Future Enhancements & Roadmap

### Completed Features ✅
- **Enhanced Natural Language Processing**: Support for season parsing with complex requests like "seasons 1 to 5", "seasons 1, 3, 5", or "all seasons"
- **Bulk Season Operations**: Requesting multiple non-consecutive seasons in a single command
- **User Mapping System**: Mapping Home Assistant users to Overseerr accounts with permission control
- **Smart Season Suggestions**: Automatic suggestions for missing seasons when adding existing TV shows
- **Detailed Season Information**: Rich season-specific status details including which seasons are downloading, available, or pending
- **Episode-level Information**: Detailed progress tracking for individual episodes within seasons
- **4K Movie Support**: Request movies in 4K quality with a simple parameter

### Upcoming Enhancements 🚀
- **Radarr/Sonarr Feature Parity**: Update the direct Radarr/Sonarr mode to have the same rich service calls and sensor support as the Overseerr/Jellyseerr mode
- **Smarter Status Checks**: Enhance the `check_media_status` service to query Radarr/Sonarr directly if a movie is not found or is stuck in a non-downloading state in Overseerr
- **Availability Sync**: Improve the status check to poll Radarr/Sonarr directly if a request is 100% downloaded in the client but not yet marked as "Available" in Overseerr
- **Post-Action Sync**: Add a post-action hook to the `add_media` and `remove_media` services to automatically trigger the media availability and download sync jobs in Overseerr, ensuring the UI reflects changes almost instantly
- **Quality Profile Support**: Add support for specifying quality profiles (e.g., "in 1080p", "in highest quality") for both movies and TV shows
- **Extended LLM Integration**: Improved compatibility with OpenAI and other conversation agents beyond Ollama
- **Improved Error Handling**: More graceful recovery from API errors and better feedback to users
- **Enhanced Monitoring**: Additional sensors for system performance and request history analytics

Have a feature suggestion? Open an issue on GitHub and let us know what you'd like to see next!

---

## Acknowledgments

This project was originally forked from [TegridyTate/Hassarr](https://github.com/TegridyTate/Hassarr). A big thank you to TegridyTate for the original work that provided the foundation for this extended, LLM-focused version.

---

## Troubleshooting

### LLM Parameter Parsing Issues

If you notice searches like `query=two%20and%20a%20half%20men%20season%202` in your logs instead of just the show name, it means your LLM isn't separating the title and season parameters properly. This is completely normal and expected behavior!

**What's happening:**
- You say: "add season 2 of Two and a Half Men"
- LLM passes: `title: "season 2 of Two and a Half Men"` and `season: ""`
- Hassarr automatically parses this to extract: `title: "Two and a Half Men"` and `season: 2`

**To verify this is working:**
1. Check your Home Assistant logs for a message like: `Extracted season 2 from title 'season 2 of Two and a Half Men' -> cleaned title: 'Two and a Half Men'`
2. The subsequent search should be for just the show name: `query=two%20and%20a%20half%20men`

**Enhanced Season Information:**
The system now provides rich season details in responses:
- **Specific requested seasons**: Shows exactly which seasons were requested (e.g., "Season 2")
- **Multiple season requests**: Support for ranges ("seasons 1 to 5"), multiple seasons ("1, 2, 3"), and "all seasons"
- **Total seasons available**: Shows how many seasons the show has in total
- **Missing seasons**: Lists seasons that haven't been requested yet
- **Episode-level download info**: Includes individual episode titles, progress, and air dates
- **Season status breakdown**: Available, downloading, or pending for each season
- **Smart suggestions**: Automatically suggests missing seasons when appropriate

**If parsing isn't working:**
1. Make sure you're using the updated integration code with title parsing
2. Restart Home Assistant after updating
3. Check the logs for any parsing errors

**What you'll see in enhanced responses:**
- "Season 2 is downloading (Episode 24: Does This Smell Funny to You?, 75% complete)"
- "Seasons 1-3 available, Season 4 downloading"
- "Would you like me to add the remaining seasons (5-12)?"

### Debug Logging

Enable debug logging for detailed troubleshooting by adding this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.hassarr: debug
```