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
    ACTION_PLAY_VOICE,
    ACTION_REBOOT,
    ACTION_TRIGGER_SIREN,
    ACTION_TRIGGER_STROBE,
    ACTION_START_TWO_WAY_AUDIO,
    ACTION_STOP_TWO_WAY_AUDIO,
    ACTION_PTZ_GOTO_PRESET,
    ACTION_PTZ_SET_PATROL,
    ATTR_CONFIG_ENTRY_ID,
    DOMAIN,
)
from .isapi import (
    ISAPIActiveDeterrenceNotSupportedError,
    ISAPIForbiddenError,
    ISAPIUnauthorizedError,
)

ACTION_ISAPI_REQUEST_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required("method"): str,
        vol.Required("path"): str,
        vol.Optional("payload"): str,
    }
)

ACTION_TRIGGER_SIREN_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Optional("duration", default=10): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
        vol.Optional("audio_id", default=1): vol.Coerce(int),
        vol.Optional("volume", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional("alarm_times", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
    }
)

ACTION_TRIGGER_STROBE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Optional("channel_id", default=1): vol.Coerce(int),
        vol.Optional("duration", default=10): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
        vol.Optional("frequency", default="medium"): vol.In(["low", "medium", "high", "constant"]),
    }
)

ACTION_PLAY_VOICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Optional("audio_id", default=1): vol.Coerce(int),
        vol.Optional("volume", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional("alarm_times", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
    }
)

ACTION_TWO_WAY_AUDIO_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Optional("channel_id", default=1): int,
    }
)

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

    async def handle_trigger_siren(call: ServiceCall) -> None:
        """Handle the trigger siren action call."""
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        entry = hass.config_entries.async_get_entry(entry_id)
        device = entry.runtime_data
        duration = call.data.get("duration", 10)
        audio_id = call.data.get("audio_id", 1)
        volume = call.data.get("volume", 50)
        alarm_times = call.data.get("alarm_times", 1)
        try:
            await device.trigger_siren(duration=duration, audio_id=audio_id, volume=volume, alarm_times=alarm_times)
        except ISAPIActiveDeterrenceNotSupportedError as ex:
            raise HomeAssistantError(ex.message) from ex
        except (HTTPStatusError, ISAPIForbiddenError, ISAPIUnauthorizedError) as ex:
            raise HomeAssistantError(ex.response.content) from ex

    async def handle_trigger_strobe(call: ServiceCall) -> None:
        """Handle the trigger strobe action call."""
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        entry = hass.config_entries.async_get_entry(entry_id)
        device = entry.runtime_data
        channel_id = call.data.get("channel_id", 1)
        duration = call.data.get("duration", 10)
        frequency = call.data.get("frequency", "medium")