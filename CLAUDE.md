# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hassarr is a Home Assistant integration that connects media management services (Radarr, Sonarr, Overseerr/Jellyseerr) with LLM support for natural language interactions. This is a custom extended version focused on rich, structured responses for chat assistants.

## Key Architecture

### Core Components

- **Integration Entry Point**: `custom_components/hassarr/__init__.py` - Main integration setup, service registration, and user management
- **API Client**: `custom_components/hassarr/services.py` - OverseerrAPI class and LLMResponseBuilder for structured responses
- **Configuration**: `custom_components/hassarr/config_flow.py` - Setup flow for Overseerr/Radarr/Sonarr configuration
- **Sensors**: `custom_components/hassarr/sensor.py` - Real-time monitoring sensors for downloads and system status
- **LLM Scripts**: `auxiliary/scripts.yaml` - Script entities that wrap services for chat assistant integration

### Service Architecture

The integration provides 7 main services, all designed for LLM interaction:

1. **hassarr.add_media** - Add movies/TV shows with natural language season parsing
2. **hassarr.check_media_status** - Check status with detailed download progress
3. **hassarr.search_media** - Search for multiple media results
4. **hassarr.remove_media** - Remove media from library
5. **hassarr.get_active_requests** - Get current downloads and pending requests
6. **hassarr.run_job** - Trigger Overseerr maintenance jobs
7. **hassarr.test_connection** - Test API connectivity

All services return structured JSON responses optimized for LLM interpretation and support `response_variable` for script integration.

### User Permission System

- **User Mapping**: Maps Home Assistant users to Overseerr users during setup
- **Access Control**: Read operations allowed for all users, write operations require mapping
- **Context Tracking**: All service calls include user context for logging and permissions

## Development Commands

This is a Home Assistant custom component - there are no traditional build/test commands. Development workflow:

1. **Install in Home Assistant**: Copy `custom_components/hassarr/` to HA config directory
2. **Configuration**: Set up through HA UI (Settings > Devices & Services > Add Integration)
3. **Testing**: Use Developer Tools > Actions to test services directly
4. **Debugging**: Enable debug logging in `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.hassarr: debug
   ```

## Important Implementation Details

### Natural Language Processing

The `_parse_season_request()` function in `__init__.py` handles complex season parsing:
- Word numbers ("season two" → 2)
- Ranges ("seasons 1 to 5" → [1,2,3,4,5])
- Multiple seasons ("1, 3, 5" → [1,3,5])
- All seasons ("all seasons" → entire series)
- Remaining seasons ("missing seasons" → based on analysis)

### LLM Response Structure

The `LLMResponseBuilder` class in `services.py` creates structured responses with:
- Action status and human-readable messages
- Detailed media information (ratings, overviews, cast)
- Download progress and user context
- Smart suggestions for follow-up actions

### Script Integration Pattern

The integration uses a script wrapper pattern (`auxiliary/scripts.yaml`) to expose services as entities for chat assistants, working around Home Assistant's limitation where conversation agents can only call entities, not services directly.

## Configuration Requirements

### Required Environment
- Home Assistant OS or Core
- HACS (Home Assistant Community Store)
- Overseerr/Jellyseerr OR Radarr/Sonarr setup
- API keys for chosen services

### User Mapping Setup
During integration setup, map Home Assistant users to Overseerr users for permission control. The first mapped user becomes the default for system operations.

## File Structure Notes

- `manifest.json` - Integration metadata and dependencies
- `const.py` - Domain constants and configuration
- `services.yaml` - Service definitions for Home Assistant
- `translations/en.json` - UI text translations
- `hacs.json` - HACS repository configuration

## Testing and Debugging

- Use HA Developer Tools > Actions to test services
- Check HA logs for detailed error messages
- Use `hassarr.test_connection` service to verify API connectivity
- Enable debug logging for detailed service call traces