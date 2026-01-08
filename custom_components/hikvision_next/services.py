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
    ACTION_PTZ_MOVE,
    ACTION_PTZ_PRESET,
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

ACTION_PTZ_MOVE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required("channel_id"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("pan", default=0): vol.All(vol.Coerce(int), vol.Range(min=-100, max=100)),
        vol.Optional("tilt", default=0): vol.All(vol.Coerce(int), vol.Range(min=-100, max=100)),
        vol.Optional("zoom", default=0): vol.All(vol.Coerce(int), vol.Range(min=-100, max=100)),
    }
)

ACTION_PTZ_PRESET_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required("channel_id"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required("preset_id"): vol.All(vol.Coerce(int), vol.Range(min=1)),
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

    async def handle_ptz_move(call: ServiceCall) -> None:
        """Handle the PTZ move action call."""
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry:
            raise HomeAssistantError(f"Config entry {entry_id} not found")
        device = entry.runtime_data
        channel_id = call.data["channel_id"]
        pan = call.data.get("pan", 0)
        tilt = call.data.get("tilt", 0)
        zoom = call.data.get("zoom", 0)

        camera = device.get_camera_by_id(channel_id)
        if not camera:
            raise HomeAssistantError(f"Camera with channel_id {channel_id} not found")
        if not camera.support_ptz:
            raise HomeAssistantError(f"Camera with channel_id {channel_id} does not support PTZ")

        try:
            await device.ptz_move(channel_id, pan=pan, tilt=tilt, zoom=zoom)
        except (HTTPStatusError, ISAPIForbiddenError, ISAPIUnauthorizedError) as ex:
            raise HomeAssistantError(ex.response.content) from ex

    async def handle_ptz_preset(call: ServiceCall) -> None:
        """Handle the PTZ preset action call."""
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry:
            raise HomeAssistantError(f"Config entry {entry_id} not found")
        device = entry.runtime_data
        channel_id = call.data["channel_id"]
        preset_id = call.data["preset_id"]

        camera = device.get_camera_by_id(channel_id)
        if not camera:
            raise HomeAssistantError(f"Camera with channel_id {channel_id} not found")
        if not camera.support_ptz:
            raise HomeAssistantError(f"Camera with channel_id {channel_id} does not support PTZ")

        try:
            await device.ptz_goto_preset(channel_id, preset_id)
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
        ACTION_PTZ_MOVE,
        handle_ptz_move,
        schema=ACTION_PTZ_MOVE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        ACTION_PTZ_PRESET,
        handle_ptz_preset,
        schema=ACTION_PTZ_PRESET_SCHEMA,
    )
