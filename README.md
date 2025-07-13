# Hassarr Integration

Hassarr is a custom Home Assistant integration to add movies and TV shows to Radarr, Sonarr and Overseerr with advanced LLM (Large Language Model) integration for natural language interactions.

## Features

### Core Functionality
- Add movies to Radarr
- Add TV shows to Sonarr  
- Add movies and TV shows to Overseerr
- **NEW**: LLM-optimized responses for natural language processing
- **NEW**: Comprehensive media status checking
- **NEW**: Download progress tracking
- **NEW**: Media removal capabilities
- **NEW**: Advanced search functionality

### LLM Integration Features
- **Structured JSON responses** optimized for LLM consumption
- **Comprehensive error handling** with specific error types
- **Download progress tracking** with detailed metrics
- **Media status mapping** (pending, downloading, available, etc.)
- **Rich metadata extraction** (genres, ratings, runtime, etc.)
- **Episode-level tracking** for TV shows
- **Request history and user tracking**

## Requirements

* You must have Home Assistant OS or Home Assistant Core installed (I only tested it on Home Assistant Core)
* HACS installed on Home Assistant (instructions below for Home Assistant Core in Docker)

## Installation

### Installing HACS on Home Assistant Core in Docker
1) SSH into your server (if you have one)
2) SSH into your homeassistant docker container
`docker exec -it <your_container_name> bash`
3) Run the following command to install HACS
`wget -O - https://get.hacs.xyz | bash -`
4) Exit from the docker container
`exit`
4) Restart the docker container
`docker-compose restart <your_container_name>`
5) Add the HACS integration by going to <your_hass_ip>:<your_hass_port>/config/integrations/dashboard on the browser
6) Press "+ Add Integration"
7) Look up "HACS"
8) Read and check all the boxes and Add

Now you should have the HACS button showing on the left menu, which should bring you to the HACS dashboard

### Install Hassarr on HACS
1) Press the button to add this custom repo to HACS
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=frankthetank001&repository=Hassarr&category=Integration)
2) Now look up "Hassarr" in the HACS Store search bar and download it
3) Restart your home assistant again for Hassarr to be properly added: `docker-compose restart <your_container_name>`
4) Add Hassarr to your Home Assistant integrations: <your_hass_ip>:<your_hass_port>/config/integrations/dashboard
5) Press "+ Add Integration"
6) Look up "Hassarr" and select it
7) It should prompt you to pick either Radarr & Sonarr, or Overseerr. Pick whichever service(s) you want to use and follow the instructions.
8a) For Radarr & Sonarr, after filling in the urls and api keys, it will prompt you with the quality profiles you want to use for each service.
8b) For Overseerr, after filling in the urls and api keys, it will prompt you with the Overseerr user you want to use for making requests. 

Now Hassarr should be installed, and you can create an Automation or Intent to have sentences trigger downloads on Sonarr and Radarr.

## Available Services

### Legacy Services (Basic Functionality)
- `hassarr.add_radarr_movie` - Add movies to Radarr
- `hassarr.add_sonarr_tv_show` - Add TV shows to Sonarr
- `hassarr.add_overseerr_movie` - Add movies to Overseerr
- `hassarr.add_overseerr_tv_show` - Add TV shows to Overseerr

### New LLM-Focused Services
- `hassarr.check_media_status` - Check media status with LLM-optimized response
- `hassarr.remove_media` - Remove media from Overseerr
- `hassarr.get_active_requests` - Get all active requests with download progress
- `hassarr.search_media` - Search for movies or TV shows
- `hassarr.get_media_details` - Get detailed media information

## LLM Integration Examples

### Service Response Format
All LLM-focused services return structured JSON responses optimized for natural language processing:

```json
{
  "action": "found_media",
  "llm_instructions": "Focus on request status, who requested it, download progress, and content overview unless asked for specific details.",
  "primary_result": {
    "search_info": {
      "title": "The Matrix",
      "type": "movie",
      "tmdb_id": 603,
      "media_id": 12345,
      "status": 3,
      "status_text": "Processing/Downloading",
      "release_date": "1999-03-31",
      "rating": 8.7,
      "download_info": {
        "active_downloads": 1,
        "current_download": {
          "title": "The Matrix (1999) 1080p",
          "time_left": "2h 15m",
          "estimated_completion": "2024-01-15T14:30:00Z",
          "status": "downloading"
        }
      },
      "request_details": {
        "requested_by": "John Doe",
        "request_date": "2024-01-15T10:00:00Z",
        "request_id": 67890
      }
    },
    "content_details": {
      "overview": "A computer hacker learns from mysterious rebels about the true nature of his reality...",
      "genres": ["Action", "Sci-Fi"],
      "movie_info": {
        "runtime": 136,
        "budget": 63000000,
        "revenue": 463517383,
        "production_companies": "Warner Bros. Pictures"
      }
    }
  },
  "message": "Found detailed information for 'The Matrix'. Focus on request status, who requested it, download progress, and content overview unless asked for specific details."
}
```

### Automation Examples

#### Check Media Status
```yaml
- alias: "Check Movie Status"
  trigger:
    - platform: conversation
      command:
        - "What's the status of {title}"
        - "Check status of {title}"
  action:
    - service: hassarr.check_media_status
      data:
        title: "{{ trigger.slots.title }}"
```

#### Get Active Downloads
```yaml
- alias: "Check Active Downloads"
  trigger:
    - platform: conversation
      command:
        - "What's downloading"
        - "Show active downloads"
        - "What's in the queue"
  action:
    - service: hassarr.get_active_requests
```

#### Remove Media
```yaml
- alias: "Remove Media"
  trigger:
    - platform: conversation
      command:
        - "Remove {media_id} from overseerr"
        - "Delete media {media_id}"
  action:
    - service: hassarr.remove_media
      data:
        media_id: "{{ trigger.slots.media_id }}"
```

## How do I add an Automation, and what is an Automation (for noobies)?

Good question! I'm not even sure entirely what Automations are capable of precisely, but with Hassarr you're able to map a sentence to a Hassarr action, like Add Movie or Add TV Show.

You can set something up like "Add {some_title} to Radarr for me please" and this will trigger it to download your title on Radarr.

There's two ways of adding this, through the UI or directly into your automations.yaml file.

### Adding Automations in the UI
1) In Home Assistant, go to Settings > Automations & Scenes > + Create Automation > Create New Automation
2) + Add Trigger > Sentence, and fill in something like this `Download {title} for me on radar`. It's important to write `radar` instead of `radarr` as your speech-to-text will always transcribe the spoken word `radar` to `radar`, and not with `rr`. Add multiple sentences if you want multiple phrases to trigger it to add a movie to Radarr. Same applies to Sonarr or Overseerr.
3) + Add Action > Type in `Hassarr` > Select `Hassarr: add_movie` > Press the three vertical dots > `Edit in YAML` > and fill in the following into the YAML editor
    ```
    action: hassarr.add_radarr_movie
    metadata: {}
    data:
      title: "{{ trigger.slots.title }}"
    ```
4) Hit Save, give it a name like `Add Movie to Radarr`
5) Repeat steps 1-4 for Sonarr (or do it for Overseerr for movies and tv shows, if you prefer)

Now you should be able to add a movie or TV show to Radarr and Sonarr using the sentences you setup!

### Adding Automations in YAML
1) Open the `automations.yaml` in your home assistant's `config` directory, or wherever you mount your home assistant's docker container
2) Paste in the following
```
- id: '1734867354703'
  alias: Add movie using Assist
  description: ''
  triggers:
  - trigger: conversation
    command:
    - (Download|Add|Send) movie {title} [on|to]  [radarr|radar]
    - (Baixa|Adiciona|Envia)[r] [o] filme {title} [no|ao|para o|para] [radarr|radar]
  conditions: []
  actions:
  - action: hassarr.add_radarr_movie
    metadata: {}
      data:
        title: ""{{ trigger.slots.title }}""
  mode: single
```
You can change the sentences in `command: ` to whatever sentences you like, add more etc.
3) Save the file, and you're good to go.
4) Make a copy of this for Sonarr (or for Overseerr, one for movies and one for tv shows, if you so prefer)

### Advanced LLM Integration Examples

#### Comprehensive Status Check
```yaml
- alias: "Smart Media Status Check"
  trigger:
    - platform: conversation
      command:
        - "What's the status of {title}"
        - "Check {title}"
        - "Is {title} downloading"
  action:
    - service: hassarr.check_media_status
      data:
        title: "{{ trigger.slots.title }}"
    - service: persistent_notification.create
      data:
        title: "Media Status"
        message: |
          {% set result = states('input_text.last_status_check') %}
          {% if result %}
            {{ result }}
          {% else %}
            Status check completed. Check logs for details.
          {% endif %}
```

#### Queue Management
```yaml
- alias: "Queue Management"
  trigger:
    - platform: conversation
      command:
        - "What's in the queue"
        - "Show downloads"
        - "What's downloading"
  action:
    - service: hassarr.get_active_requests
    - service: persistent_notification.create
      data:
        title: "Download Queue"
        message: |
          {% set result = states('input_text.last_requests') %}
          {% if result %}
            {{ result }}
          {% else %}
            Queue check completed. Check logs for details.
          {% endif %}
```

## Service Response Actions

The LLM-focused services return specific action types that can be used for conditional logic:

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

## Configuration

The integration stores results in `hass.data[f"{DOMAIN}_results"]` for potential use by other components:

- `last_status_check` - Result of last status check
- `last_removal` - Result of last media removal
- `last_requests` - Result of last active requests check
- `last_search` - Result of last media search
- `last_details` - Result of last media details retrieval

## Troubleshooting

### Common Issues

1. **Connection Errors**: Ensure your Overseerr URL and API key are correct
2. **No Results**: Check that the media title is spelled correctly
3. **Permission Errors**: Verify your Overseerr user has appropriate permissions
4. **Service Not Found**: Restart Home Assistant after installation

### Debugging

Enable debug logging by adding to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.hassarr: debug
```

## Contributing

This integration is designed to work with both Overseerr and Jellyseerr (they share the same API). If you encounter issues or have feature requests, please open an issue on the GitHub repository.

Shoutout to the [repo by Github user Avraham](https://github.com/avraham/hass_radarr_sonarr_search_by_voice) for trying this some time ago, but unfortunately I had difficulties trying to get this to work.

Make sure to check the [Template sentence syntax](https://developers.home-assistant.io/docs/voice/intent-recognition/template-sentence-syntax/) to understand how to change the activation commands.
