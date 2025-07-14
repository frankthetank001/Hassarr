# File: services.py
# Note: Keep this filename comment for navigation and organization

import logging
import aiohttp
import json
from urllib.parse import urljoin, urlparse, quote
from typing import Dict, Any, Optional
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class OverseerrAPI:
    """Simple Overseerr API client."""
    
    def __init__(self, url: str, api_key: str, session: aiohttp.ClientSession):
        self.base_url = url
        self.api_key = api_key
        self.headers = {'X-Api-Key': api_key}
        self.session = session
        
        # Ensure URL has scheme
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            self.base_url = f"https://{url}"
    
    async def _make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Optional[Dict]:
        """Make async HTTP request to Overseerr API."""
        url = urljoin(self.base_url, endpoint)
        try:
            async with self.session.request(method, url, headers=self.headers, json=data) as response:
                if response.status in [200, 201, 204]:
                    content = await response.text()
                    if not content.strip():
                        # Empty response (common for DELETE requests with 204)
                        return {}
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as json_err:
                        _LOGGER.error(f"Invalid JSON response from {url}: {json_err}")
                        _LOGGER.debug(f"Response content: {content[:200]}...")
                        return None
                else:
                    _LOGGER.error(f"API request failed: {response.status} - {await response.text()}")
                    return None
        except Exception as e:
            _LOGGER.error(f"Request failed: {e}")
            return None
    
    async def get_requests(self) -> Optional[Dict]:
        """Get all active requests."""
        endpoint = "api/v1/request"
        return await self._make_request(endpoint)
    
    async def search_media(self, query: str) -> Optional[Dict]:
        """Search for media in Overseerr."""
        encoded_query = quote(query)
        endpoint = f"api/v1/search?query={encoded_query}"
        return await self._make_request(endpoint)