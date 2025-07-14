# Project Context: Hassarr Home Assistant Integration

## Overview

Hassarr is a custom Home Assistant integration designed to bridge the gap between Home Assistant and media management services (Radarr, Sonarr, Overseerr/Jellyseerr) with a focus on **LLM (Large Language Model) agentic integration** for natural language interactions.

## Primary Goals

### 1. **LLM Agentic Integration** (Primary Focus)
- **Natural Language Processing**: Enable LLMs to interact with media services through structured JSON responses
- **Flexible Commands**: Move away from rigid conversation triggers to natural, contextual interactions
- **Rich Responses**: Provide comprehensive, structured data that LLMs can interpret and respond to naturally
- **Context Awareness**: Allow LLMs to maintain conversation context and provide intelligent follow-ups

### 2. **Home Assistant Native Integration**
- **Sensor Entities**: Automatic updates for download status, queue information, and connection monitoring
- **Binary Sensors**: State-based triggers for reactive automations
- **Data Coordinators**: Efficient API polling with configurable intervals
- **Rich Attributes**: Detailed information accessible without service calls

### 3. **Media Management Automation**
- **Add Media**: Movies and TV shows to Radarr, Sonarr, and Overseerr
- **Status Checking**: Real-time media status with download progress tracking
- **Queue Management**: Active download monitoring with detailed progress metrics
- **Media Removal**: Remove unwanted media from download queues

## Architecture

### Core Components

```
Hassarr Integration
├── Configuration Flow (config_flow.py)
│   ├── Radarr & Sonarr Setup
│   └── Overseerr Setup
├── Services Layer (services.py)
│   ├── OverseerrAPI Client
│   ├── LLMResponseBuilder
│   └── Service Handlers
├── Entity Platforms
│   ├── Sensors (sensor.py)
│   └── Binary Sensors (binary_sensor.py)
└── Integration Core (__init__.py)
    ├── Service Registration
    └── Platform Setup
```

### Service Architecture

#### Legacy Services (Basic Functionality)
- `add_radarr_movie` - Add movies to Radarr
- `add_sonarr_tv_show` - Add TV shows to Sonarr
- `add_overseerr_movie` - Add movies to Overseerr
- `add_overseerr_tv_show` - Add TV shows to Overseerr

#### LLM-Focused Services (New)
- `check_media_status` - Comprehensive media status with LLM-optimized responses
- `get_active_requests` - Download queue with progress tracking
- `remove_media` - Remove media from Overseerr
- `search_media` - Search for movies/TV shows
- `get_media_details` - Detailed media information

#### Sensor Entities (Home Assistant Native)
- `sensor.hassarr_active_downloads` - Number of active downloads
- `sensor.hassarr_download_queue_status` - Queue status overview
- `binary_sensor.hassarr_downloads_active` - Download activity state
- `binary_sensor.hassarr_overseerr_online` - Connection status

## LLM Integration Design

### Response Format
All LLM-focused services return structured JSON with:

```json
{
  "action": "found_media|not_found|connection_error|...",
  "llm_instructions": "Guidance for LLM response focus",
  "primary_result": {
    "search_info": { /* Core media information */ },
    "content_details": { /* Rich metadata */ }
  },
  "message": "Human-readable summary"
}
```

### Action Types
- **Status Actions**: `found_media`, `not_found`, `connection_error`, `missing_title`
- **Request Actions**: `active_requests_found`, `no_active_requests`, `media_removed`, `removal_failed`
- **Search Actions**: `search_results`, `details_found`

### LLM Workflow Example
```
User: "What's the status of The Matrix?"
├── LLM calls: hassarr.check_media_status(title="The Matrix")
├── Service returns: Structured JSON with status, progress, metadata
└── LLM responds: Natural language interpretation of the data
```

## Current State & Issues

### Recent Problem Solved
**Issue**: Service registration error - `handle_get_active_requests_service() missing 1 required positional argument: 'call'`

**Root Cause**: Services were being registered in `async_setup()` but called before proper integration setup

**Solution**: 
- Moved service registration to `async_setup_entry()`
- Added comprehensive error handling and logging
- Created wrapper functions for better error recovery
- Added test services for debugging

### Implementation Status

#### ✅ Completed
- ✅ Configuration flow for Radarr/Sonarr and Overseerr
- ✅ Basic media addition services
- ✅ LLM-focused services with structured responses
- ✅ Sensor entities with rich attributes
- ✅ Data coordinator for automatic updates
- ✅ Comprehensive error handling
- ✅ Service registration fix

#### 🚧 In Progress
- 🚧 Service reliability testing
- 🚧 Error handling validation
- 🚧 Integration stability improvements

#### 📋 Planned
- 📋 Advanced filtering and search capabilities
- 📋 User preference management
- 📋 Integration with additional media services
- 📋 Performance optimizations

## Technical Specifications

### Dependencies
- `aiohttp` - Async HTTP client for API communications
- Home Assistant Core 2024.12.5+

### API Integrations
- **Overseerr/Jellyseerr API** - Primary media management interface
- **Radarr API** - Movie management (legacy support)
- **Sonarr API** - TV show management (legacy support)

### Data Flow
```
Home Assistant → Hassarr Services → Media APIs → Structured Responses → LLM Processing
                      ↓
              Sensor Updates ← Data Coordinator ← API Polling
```

## Usage Patterns

### 1. LLM Agentic Approach (Recommended)
```yaml
# LLM receives user query and calls services directly
# No rigid conversation triggers needed
# Natural language interpretation of structured responses
```

### 2. Sensor-Based Monitoring
```yaml
# Automatic updates every 30 seconds
# Rich attributes for detailed information
# State-based automation triggers
```

### 3. Traditional Service Calls
```yaml
# Direct service calls from automations
# Structured responses for processing
# Legacy conversation trigger support
```

## Development Philosophy

### Design Principles
1. **LLM-First**: All new features designed with LLM interaction in mind
2. **Home Assistant Native**: Follow HA patterns and conventions
3. **Structured Data**: Consistent, parseable response formats
4. **Error Resilience**: Comprehensive error handling and recovery
5. **Performance Focused**: Efficient API usage and caching

### Code Organization
- **Separation of Concerns**: Clear boundaries between API, services, and entities
- **Async Architecture**: Non-blocking operations throughout
- **Comprehensive Logging**: Detailed debugging and monitoring
- **Type Safety**: Strong typing where possible

## Migration Strategy

### From Legacy Scripts
The integration replaces complex YAML scripts (200+ lines) with simple service calls:

**Before** (Legacy):
```yaml
# Complex 200+ line script with manual REST commands
check_movie_status_in_overseerr:
  sequence:
    - action: rest_command.search_overseerr_movie
    # ... hundreds more lines
```

**After** (New):
```yaml
# Simple service call
- service: hassarr.check_media_status
  data:
    title: "{{ title }}"
```

### Benefits
- **90% reduction** in configuration complexity
- **Improved performance** through dedicated API client
- **Better error handling** with specific error types
- **Rich metadata** extraction and processing
- **LLM optimization** for natural language interactions

## Future Vision

### Short Term (Next Release)
- Service stability and reliability improvements
- Enhanced error reporting and recovery
- Integration testing and validation

### Medium Term
- Advanced search and filtering capabilities
- User preference management
- Multi-user support improvements
- Performance optimizations

### Long Term
- AI-driven media recommendations
- Predictive download management
- Advanced analytics and reporting
- Integration with additional media services

## Contributing

### Development Setup
1. Clone repository to Home Assistant custom_components
2. Configure Overseerr/Jellyseerr connection
3. Enable debug logging: `custom_components.hassarr: debug`
4. Test services through Developer Tools

### Testing Priorities
1. Service registration and calling
2. LLM response format consistency
3. Error handling and recovery
4. Sensor update reliability
5. Configuration flow stability

This integration represents a significant evolution in Home Assistant media management, moving from rigid automation patterns to flexible, AI-driven interactions while maintaining the reliability and performance expected from Home Assistant integrations. 