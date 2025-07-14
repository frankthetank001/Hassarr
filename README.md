# Hassarr - Home Assistant Media Integration

> **Smart Media Management with LLM Integration**

Hassarr is a Home Assistant integration that connects your media management services (Radarr, Sonarr, Overseerr) with advanced LLM (Large Language Model) support for natural language interactions.

## ✨ Key Features

- **🤖 LLM-First Design**: Built for natural language interactions with ChatGPT, Claude, etc.
- **📱 Smart Media Management**: Add, remove, and track movies/TV shows
- **📊 Real-time Monitoring**: Live sensors for downloads, queue status, and system health  
- **🔄 Automatic Updates**: Background sync with your media services
- **🛠️ Easy Setup**: Simple configuration flow with automatic discovery

## 🚀 Quick Start

1. **Install via HACS** (recommended)
   - Add custom repository: `https://github.com/yourusername/Hassarr`
   - Install "Hassarr" integration

2. **Configure Integration**
   - Go to Settings > Devices & Services > Add Integration
   - Search for "Hassarr" and follow setup wizard

3. **Start Using**
   ```yaml
   # Add to your automations or scripts
   service: hassarr.add_media
   data:
     title: "The Dark Knight"
   ```

## 🎯 Perfect For

- **Chat Assistants**: "Add Inception to my library"
- **Automation**: Trigger downloads based on events
- **Monitoring**: Track download progress and system health
- **Management**: Remove unwanted media, run maintenance jobs

## 📚 Documentation

- **[User Guide](docs/USER_GUIDE.md)** - Complete setup and usage instructions
- **[Chat Assistant Integration](docs/CHAT_ASSISTANT.md)** - LLM integration guide
- **[Migration Guide](docs/MIGRATION.md)** - Upgrading from legacy scripts

## 🔧 Supported Services

| Service | Movies | TV Shows | Status Tracking | Download Progress |
|---------|---------|----------|-----------------|-------------------|
| **Overseerr** | ✅ | ✅ | ✅ | ✅ |
| **Radarr** | ✅ | ❌ | ⚠️ Basic | ❌ |
| **Sonarr** | ❌ | ✅ | ⚠️ Basic | ❌ |

> **Recommendation**: Use Overseerr for the best experience with full LLM integration

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/Hassarr/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/Hassarr/discussions)
- **Discord**: [Home Assistant Community](https://discord.gg/home-assistant)

---

**Made with ❤️ for the Home Assistant community** 