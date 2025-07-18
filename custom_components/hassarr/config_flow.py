# File: config_flow.py
# Note: Keep this filename comment for navigation and organization

from urllib.parse import urljoin
import voluptuous as vol
from homeassistant import config_entries
import aiohttp
import logging
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class HassarrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required("integration_type"): vol.In(["Radarr & Sonarr", "Overseerr"])
                })
            )

        self.integration_type = user_input["integration_type"]
        if self.integration_type == "Radarr & Sonarr":
            return await self.async_step_radarr_sonarr()
        else:
            return await self.async_step_overseerr()
    
    async def async_step_reconfigure(self, user_input=None):
        """Handle reconfiguration of an existing entry."""
        if user_input is not None:
            self.integration_type = user_input["integration_type"]
            if self.integration_type == "Radarr & Sonarr":
                return await self.async_step_reconfigure_radarr_sonarr()
            else:
                return await self.async_step_reconfigure_overseerr()

        # Get existing data to pre-fill the form
        existing_data = self._get_reconfigure_entry().data
        integration_type = existing_data.get("integration_type", "Radarr & Sonarr")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required("integration_type", default=integration_type): vol.In(["Radarr & Sonarr", "Overseerr"]),
            })
        )


    async def async_step_reconfigure_overseerr(self, user_input=None):
        """Handle reconfiguration for Overseerr."""
        if user_input is not None:
            # Update the existing config entry
            data = dict(self._get_reconfigure_entry().data)
            data.update(user_input)
            self.hass.config_entries.async_update_entry(
                self._get_reconfigure_entry(),
                data=data
            )
            return await self.async_step_reconfigure_overseerr_user()

        # Get existing data to pre-fill the form
        existing_data = self._get_reconfigure_entry().data

        return self.async_show_form(
            step_id="reconfigure_overseerr",
            data_schema=vol.Schema({
                vol.Optional("overseerr_url", default=existing_data.get("overseerr_url", ""), description={"suggested_value": existing_data.get("overseerr_url", "")}): str,
                vol.Optional("overseerr_api_key", default=existing_data.get("overseerr_api_key", ""), description={"suggested_value": existing_data.get("overseerr_api_key", "")}): str,
            })
        )

    async def async_step_reconfigure_overseerr_user(self, user_input=None):
        """Handle reconfiguration for Overseerr user selection and mapping."""
        if user_input is None:
            # Get all Overseerr users
            try:
                overseerr_url = self._get_reconfigure_entry().data.get("overseerr_url")
                overseerr_api_key = self._get_reconfigure_entry().data.get("overseerr_api_key")
                overseerr_users = await self._fetch_overseerr_users(overseerr_url, overseerr_api_key)
                if not overseerr_users:
                    return self.async_abort(reason="no_overseerr_users_found")
                
                # Create options with more descriptive labels including user roles if available
                overseerr_options = {}
                for user in overseerr_users:
                    username = user["username"]
                    display_name = user.get("displayName", "")
                    
                    # Add display name if available
                    if display_name and display_name != username:
                        label = f"{username} ({display_name})"
                    else:
                        label = username
                    
                    # Add user permissions if available
                    if user.get("permissions", 0) == 2:
                        label += " [Admin]"
                    
                    overseerr_options[user["id"]] = label
                
                # Get existing data to pre-fill the form
                existing_data = self._get_reconfigure_entry().data
                existing_user_mappings = existing_data.get("user_mappings", {})
                existing_default_user = existing_data.get("overseerr_user_id")
                
                # Create a simple form for manual user mapping
                return self.async_show_form(
                    step_id="reconfigure_overseerr_user",
                    data_schema=vol.Schema({
                        vol.Optional("manual_mapping"): cv.string,
                        vol.Optional("overseerr_user"): vol.In(overseerr_options),
                        vol.Optional("default_overseerr_user", default=existing_default_user): vol.In(overseerr_options)
                    }),
                    description_placeholders={
                        "note": "Enter Home Assistant username and select Overseerr user, then click Submit. Repeat for each user you want to map. When finished, leave the fields empty and click Submit."
                    }
                )
            except Exception as e:
                _LOGGER.error(f"Error fetching Overseerr users during reconfigure: {e}")
                return self.async_abort(reason="failed_to_fetch_overseerr_users")
        
        # Process the form input
        manual_mapping = user_input.get("manual_mapping")
        overseerr_user = user_input.get("overseerr_user")
        default_user_id = user_input.get("default_overseerr_user")
        
        # If both fields are empty, we're done mapping
        if not manual_mapping and not overseerr_user:
            # Get existing mappings from previous submissions
            user_mappings = self.hass.data.get(DOMAIN, {}).get("user_mappings", {})
            
            # Update the existing config entry
            data = dict(self._get_reconfigure_entry().data)
            data.update({
                "overseerr_user_id": default_user_id,
                "user_mappings": user_mappings
            })
            
            self.hass.config_entries.async_update_entry(
                self._get_reconfigure_entry(),
                data=data
            )
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data_updates=data,
            )
        
        # Store the mapping in Home Assistant data
        if manual_mapping and overseerr_user:
            # Get existing mappings
            if DOMAIN not in self.hass.data:
                self.hass.data[DOMAIN] = {}
            if "user_mappings" not in self.hass.data[DOMAIN]:
                self.hass.data[DOMAIN]["user_mappings"] = {}
                
            # Find user ID by name
            users = await self.hass.auth.async_get_users()
            for user in users:
                user_name = self._get_simple_user_name(user, 0)
                if manual_mapping.lower() in user_name.lower():
                    self.hass.data[DOMAIN]["user_mappings"][str(user.id)] = overseerr_user
                    _LOGGER.info(f"Mapped Home Assistant user '{user_name}' to Overseerr user ID {overseerr_user}")
                    break
            
            # Show the form again for the next mapping
            return await self.async_step_reconfigure_overseerr_user()

    async def async_step_reconfigure_radarr_sonarr(self, user_input=None):
        """Handle reconfiguration for Radarr & Sonarr."""
        if user_input is not None:
            # Update the existing config entry
            data = dict(self._get_reconfigure_entry().data)
            data.update(user_input)
            self.hass.config_entries.async_update_entry(
                self._get_reconfigure_entry(),
                data=data
            )
            return await self.async_step_reconfigure_radarr_sonarr_quality_profiles()

        # Get existing data to pre-fill the form
        existing_data = self._get_reconfigure_entry().data

        return self.async_show_form(
            step_id="reconfigure_radarr_sonarr",
            data_schema=vol.Schema({
                vol.Optional("radarr_url", default=existing_data.get("radarr_url", ""), description={"suggested_value": existing_data.get("radarr_url", "")}): str,
                vol.Optional("sonarr_url", default=existing_data.get("sonarr_url", ""), description={"suggested_value": existing_data.get("sonarr_url", "")}): str,
                vol.Optional("radarr_api_key", default=existing_data.get("radarr_api_key", ""), description={"suggested_value": existing_data.get("radarr_api_key", "")}): str,
                vol.Optional("sonarr_api_key", default=existing_data.get("sonarr_api_key", ""), description={"suggested_value": existing_data.get("sonarr_api_key", "")}): str,
            })
        )

    async def async_step_reconfigure_radarr_sonarr_quality_profiles(self, user_input=None):
        """Handle reconfiguration for Radarr & Sonarr quality profiles."""
        if user_input is not None:
            # Update the existing config entry
            data = dict(self._get_reconfigure_entry().data)
            data.update(user_input)
            self.hass.config_entries.async_update_entry(
                self._get_reconfigure_entry(),
                data=data
            )
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data_updates=user_input,
            )

        # Get existing data to pre-fill the form
        existing_data = self._get_reconfigure_entry().data
        radarr_url = existing_data.get("radarr_url")
        radarr_api_key = existing_data.get("radarr_api_key")
        sonarr_url = existing_data.get("sonarr_url")
        sonarr_api_key = existing_data.get("sonarr_api_key")

        # Fetch quality profiles from Radarr and Sonarr APIs
        radarr_profiles = await self._fetch_quality_profiles(radarr_url, radarr_api_key)
        sonarr_profiles = await self._fetch_quality_profiles(sonarr_url, sonarr_api_key)

        radarr_options = {profile["id"]: profile["name"] for profile in radarr_profiles}
        sonarr_options = {profile["id"]: profile["name"] for profile in sonarr_profiles}

        return self.async_show_form(
            step_id="reconfigure_radarr_sonarr_quality_profiles",
            data_schema=vol.Schema({
                vol.Required("radarr_quality_profile_id"): vol.In(radarr_options),
                vol.Required("sonarr_quality_profile_id"): vol.In(sonarr_options),
            })
        )

    async def async_step_radarr_sonarr(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="radarr_sonarr", data_schema=self._get_radarr_sonarr_schema())

        # Validate user input
        errors = {}
        if not user_input.get("radarr_url") or not user_input.get("radarr_api_key"):
            errors["base"] = "missing_radarr_info"
        if not user_input.get("sonarr_url") or not user_input.get("sonarr_api_key"):
            errors["base"] = "missing_sonarr_info"

        if errors:
            return self.async_show_form(step_id="radarr_sonarr", data_schema=self._get_radarr_sonarr_schema(), errors=errors)

        # Save the radarr_url and radarr_api_key and proceed to quality profile selection step
        self.radarr_url = user_input["radarr_url"]
        self.radarr_api_key = user_input["radarr_api_key"]
        self.sonarr_url = user_input["sonarr_url"]
        self.sonarr_api_key = user_input["sonarr_api_key"]
        return await self.async_step_radarr_sonarr_quality_profiles()

    async def async_step_radarr_sonarr_quality_profiles(self, user_input=None):
        if user_input is None:
            # Fetch quality profiles from Radarr and Sonarr APIs
            radarr_profiles = await self._fetch_quality_profiles(self.radarr_url, self.radarr_api_key)
            sonarr_profiles = await self._fetch_quality_profiles(self.sonarr_url, self.sonarr_api_key)

            radarr_options = {profile["id"]: profile["name"] for profile in radarr_profiles}
            sonarr_options = {profile["id"]: profile["name"] for profile in sonarr_profiles}

            return self.async_show_form(
                step_id="radarr_sonarr_quality_profiles",
                data_schema=vol.Schema({
                    vol.Required("radarr_quality_profile_id"): vol.In(radarr_options),
                    vol.Required("sonarr_quality_profile_id"): vol.In(sonarr_options),
                })
            )

        # Create the entry with the selected quality profile IDs
        user_input.update({
            "radarr_url": self.radarr_url,
            "radarr_api_key": self.radarr_api_key,
            "sonarr_url": self.sonarr_url,
            "sonarr_api_key": self.sonarr_api_key
        })
        return self.async_create_entry(title="Hassarr", data=user_input)

    async def async_step_overseerr(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="overseerr", data_schema=self._get_overseerr_schema())

        # Validate user input
        errors = {}
        if not user_input.get("overseerr_url") or not user_input.get("overseerr_api_key"):
            errors["base"] = "missing_overseerr_info"

        if errors:
            return self.async_show_form(step_id="overseerr", data_schema=self._get_overseerr_schema(), errors=errors)

        # Save the overseerr_url and overseerr_api_key and proceed directly to user mapping
        self.overseerr_url = user_input["overseerr_url"]
        self.overseerr_api_key = user_input["overseerr_api_key"]
        return await self.async_step_overseerr_user_mapping()

    async def async_step_overseerr_user_mapping(self, user_input=None):
        """Handle user mapping configuration."""
        if user_input is None:
            # Get all Home Assistant users
            ha_users = []
            try:
                users = await self.hass.auth.async_get_users()
                
                for i, user in enumerate(users):
                    if user.is_active:
                        user_label = self._get_simple_user_name(user, i)
                        _LOGGER.debug(f"Found active user {user.id}, labeling as {user_label}")
                        
                        ha_users.append({
                            "id": user.id,
                            "name": user_label,
                            "index": i
                        })
            except Exception as e:
                _LOGGER.error(f"Error fetching Home Assistant users: {e}")
                return self.async_abort(reason="failed_to_fetch_ha_users")
            
            # Get all Overseerr users
            try:
                overseerr_users = await self._fetch_overseerr_users(self.overseerr_url, self.overseerr_api_key)
                if not overseerr_users:
                    return self.async_abort(reason="no_overseerr_users_found")
                
                # Create options with more descriptive labels including user roles if available
                overseerr_options = {}
                for user in overseerr_users:
                    username = user["username"]
                    display_name = user.get("displayName", "")
                    
                    # Add display name if available
                    if display_name and display_name != username:
                        label = f"{username} ({display_name})"
                    else:
                        label = username
                    
                    # Add user permissions if available
                    if user.get("permissions", 0) == 2:
                        label += " [Admin]"
                    
                    overseerr_options[user["id"]] = label
            except Exception as e:
                _LOGGER.error(f"Error fetching Overseerr users: {e}")
                return self.async_abort(reason="failed_to_fetch_overseerr_users")
            
            # Create a simple form for manual user mapping
            return self.async_show_form(
                step_id="overseerr_user_mapping",
                data_schema=vol.Schema({
                    vol.Optional("manual_mapping"): cv.string,
                    vol.Optional("overseerr_user"): vol.In(overseerr_options),
                    vol.Optional("default_overseerr_user", default=list(overseerr_options.keys())[0] if overseerr_options else None): vol.In(overseerr_options)
                }),
                description_placeholders={
                    "total_ha_users": str(len(ha_users)),
                    "total_overseerr_users": str(len(overseerr_options)),
                    "note": "Enter Home Assistant username and select Overseerr user, then click Submit. Repeat for each user you want to map. When finished, leave the fields empty and click Submit."
                }
            )

        # Process the form input
        manual_mapping = user_input.get("manual_mapping")
        overseerr_user = user_input.get("overseerr_user")
        default_user_id = user_input.get("default_overseerr_user")
        
        # If both fields are empty, we're done mapping
        if not manual_mapping and not overseerr_user:
            # Get existing mappings from previous submissions
            user_mappings = self.hass.data.get(DOMAIN, {}).get("user_mappings", {})
            
            # Create the entry with all the data
            user_input.update({
                "overseerr_url": self.overseerr_url,
                "overseerr_api_key": self.overseerr_api_key,
                "overseerr_user_id": default_user_id,
                "user_mappings": user_mappings
            })
            
            return self.async_create_entry(title="Hassarr", data=user_input)
        
        # Store the mapping in Home Assistant data
        if manual_mapping and overseerr_user:
            # Get existing mappings
            if DOMAIN not in self.hass.data:
                self.hass.data[DOMAIN] = {}
            if "user_mappings" not in self.hass.data[DOMAIN]:
                self.hass.data[DOMAIN]["user_mappings"] = {}
                
            # Find user ID by name
            users = await self.hass.auth.async_get_users()
            for user in users:
                user_name = self._get_simple_user_name(user, 0)
                if manual_mapping.lower() in user_name.lower():
                    self.hass.data[DOMAIN]["user_mappings"][str(user.id)] = overseerr_user
                    _LOGGER.info(f"Mapped Home Assistant user '{user_name}' to Overseerr user ID {overseerr_user}")
                    break
            
            # Show the form again for the next mapping
            return await self.async_step_overseerr_user_mapping()

    def _get_simple_user_name(self, user, index):
        """Get a simple, readable name for a Home Assistant user."""
        try:
            # Try different property names that might exist
            if hasattr(user, 'name') and user.name:
                return user.name
            elif hasattr(user, 'display_name') and user.display_name:
                return user.display_name
            elif hasattr(user, 'username') and user.username:
                return user.username
            elif hasattr(user, 'email') and user.email:
                # Use email as fallback
                return user.email.split('@')[0]  # Just the username part
            else:
                # Last resort: shortened ID
                user_id = str(user.id)
                short_id = user_id[-8:] if len(user_id) > 8 else user_id
                return f"User {index + 1} ({short_id})"
        except Exception as e:
            _LOGGER.warning(f"Error getting friendly name for user {user.id}: {e}")
            # Fallback to shortened ID
            user_id = str(user.id)
            short_id = user_id[-8:] if len(user_id) > 8 else user_id
            return f"User {index + 1} ({short_id})"

    async def _fetch_overseerr_users(self, url, api_key):
        """Fetch users from the Overseerr API."""
        async with aiohttp.ClientSession() as session:
            url = urljoin(url, "api/v1/user")
            async with session.get(url, headers={"X-Api-Key": api_key}) as response:
                response.raise_for_status()
                data = await response.json()
                return data["results"]

    async def _fetch_quality_profiles(self, url, api_key):
        """Fetch quality profiles from the Radarr/Sonarr API."""
        async with aiohttp.ClientSession() as session:
            url = urljoin(url, "api/v3/qualityprofile")
            async with session.get(url, headers={"X-Api-Key": api_key}) as response:
                response.raise_for_status()
                data = await response.json()
                return data

    @staticmethod
    def _get_radarr_sonarr_schema():
        return vol.Schema({
            vol.Required("radarr_url", description={"placeholder": "http://192.168.1.100:7878"}): str,
            vol.Required("radarr_api_key", description={"placeholder": "Your Radarr API Key"}): str,
            vol.Required("sonarr_url", description={"placeholder": "http://192.168.1.100:8989"}): str,
            vol.Required("sonarr_api_key", description={"placeholder": "Your Sonarr API Key"}): str,
        })

    @staticmethod
    def _get_overseerr_schema():
        return vol.Schema({
            vol.Required("overseerr_url", description={"placeholder": "http://192.168.1.100:5055"}): str,
            vol.Required("overseerr_api_key", description={"placeholder": "Your Overseerr API Key"}): str
        })

