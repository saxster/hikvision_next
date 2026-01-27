"Integration actions."

from httpx import HTTPStatusError
import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError

from .const import (
    ACTION_ISAPI_REQUEST,
    ACTION_REBOOT,
    ACTION_START_TWO_WAY_AUDIO,
    ACTION_STOP_TWO_WAY_AUDIO,
    ACTION_PTZ_GOTO_PRESET,
    ACTION_PTZ_SET_PATROL,
    ACTION_REBOOT,
    ATTR_CONFIG_ENTRY_ID,
    DOMAIN,
)
from .isapi import ISAPIForbiddenError, ISAPIUnauthorizedError

ACTION_ISAPI_REQUEST_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required("method"): str,
        vol.Required("path"): str,
        vol.Optional("payload"): str,
    }
)

ACTION_TWO_WAY_AUDIO_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Optional("channel_id", default=1): int,
ACTION_PTZ_GOTO_PRESET_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required("channel_id"): vol.Coerce(int),
        vol.Required("preset_id"): vol.Coerce(int),
    }
)

ACTION_PTZ_SET_PATROL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required("channel_id"): vol.Coerce(int),
        vol.Required("patrol_id"): vol.Coerce(int),
        vol.Required("enabled"): bool,
    }
)


def setup_services(hass: HomeAssistant) -> None:
    """Set up the services for the Hikvision component."""

    async def handle_reboot(call: ServiceCall):
        """Handle the reboot action call."""
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        entry = hass.config_entries.async_get_entry(entry_id)
        device = entry.runtime_data
        try:
            await device.reboot()
        except (HTTPStatusError, ISAPIForbiddenError, ISAPIUnauthorizedError) as ex:
            raise HomeAssistantError(ex.response.content) from ex

    async def handle_isapi_request(call: ServiceCall) -> ServiceResponse:
        """Handle the custom ISAPI request action call."""
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        entry = hass.config_entries.async_get_entry(entry_id)
        device = entry.runtime_data
        method = call.data.get("method", "POST")
        path = call.data["path"].strip("/")
        payload = call.data.get("payload")
        try:
            response = await device.request(method, path, present="xml", data=payload)
        except (HTTPStatusError, ISAPIForbiddenError, ISAPIUnauthorizedError) as ex:
            if isinstance(ex.response.content, bytes):
                response = ex.response.content.decode("utf-8")
            else:
                response = ex.response.content
        return {"data": response.replace("\r", "")}

    async def handle_start_two_way_audio(call: ServiceCall):
        """Handle the start two-way audio action call."""
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        entry = hass.config_entries.async_get_entry(entry_id)
        device = entry.runtime_data
        channel_id = call.data.get("channel_id", 1)

        if not device.capabilities.support_two_way_audio:
            raise HomeAssistantError("Device does not support two-way audio")

        try:
            await device.start_two_way_audio(channel_id)
        except (HTTPStatusError, ISAPIForbiddenError, ISAPIUnauthorizedError) as ex:
            raise HomeAssistantError(ex.response.content) from ex

    async def handle_stop_two_way_audio(call: ServiceCall):
        """Handle the stop two-way audio action call."""
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        entry = hass.config_entries.async_get_entry(entry_id)
        device = entry.runtime_data
        channel_id = call.data.get("channel_id", 1)

        if not device.capabilities.support_two_way_audio:
            raise HomeAssistantError("Device does not support two-way audio")

        try:
            await device.stop_two_way_audio(channel_id)
    async def handle_ptz_goto_preset(call: ServiceCall):
        """Handle the PTZ go to preset action call."""
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        entry = hass.config_entries.async_get_entry(entry_id)
        device = entry.runtime_data
        channel_id = call.data["channel_id"]
        preset_id = call.data["preset_id"]
        try:
            await device.ptz_goto_preset(channel_id, preset_id)
        except (HTTPStatusError, ISAPIForbiddenError, ISAPIUnauthorizedError) as ex:
            raise HomeAssistantError(ex.response.content) from ex

    async def handle_ptz_set_patrol(call: ServiceCall):
        """Handle the PTZ set patrol action call."""
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        entry = hass.config_entries.async_get_entry(entry_id)
        device = entry.runtime_data
        channel_id = call.data["channel_id"]
        patrol_id = call.data["patrol_id"]
        enabled = call.data["enabled"]
        try:
            await device.ptz_set_patrol(channel_id, patrol_id, enabled)
        except (HTTPStatusError, ISAPIForbiddenError, ISAPIUnauthorizedError) as ex:
            raise HomeAssistantError(ex.response.content) from ex

    hass.services.async_register(
        DOMAIN,
        ACTION_REBOOT,
        handle_reboot,
    )
    hass.services.async_register(
        DOMAIN,
        ACTION_ISAPI_REQUEST,
        handle_isapi_request,
        schema=ACTION_ISAPI_REQUEST_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        ACTION_START_TWO_WAY_AUDIO,
        handle_start_two_way_audio,
        schema=ACTION_TWO_WAY_AUDIO_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        ACTION_STOP_TWO_WAY_AUDIO,
        handle_stop_two_way_audio,
        schema=ACTION_TWO_WAY_AUDIO_SCHEMA,
        ACTION_PTZ_GOTO_PRESET,
        handle_ptz_goto_preset,
        schema=ACTION_PTZ_GOTO_PRESET_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        ACTION_PTZ_SET_PATROL,
        handle_ptz_set_patrol,
        schema=ACTION_PTZ_SET_PATROL_SCHEMA,
    )
