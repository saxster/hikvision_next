"""Tests for Active Deterrence services (siren, strobe, voice)."""

import json
import pytest
import respx
import httpx
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.hikvision_next.const import (
    ACTION_TRIGGER_SIREN,
    ACTION_TRIGGER_STROBE,
    ACTION_PLAY_VOICE,
    ATTR_CONFIG_ENTRY_ID,
    DOMAIN,
)
from custom_components.hikvision_next.isapi import ISAPIActiveDeterrenceNotSupportedError
from tests.conftest import TEST_HOST


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2T86G2-ISU"], indirect=True)
async def test_trigger_siren_action(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test triggering the siren service."""
    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Enable siren support for test
    device.capabilities.support_siren = True

    url = f"{TEST_HOST}/ISAPI/Event/triggers/notifications/AudioAlarm?format=json"

    def check_payload(request, route):
        payload = json.loads(request.content.decode("utf-8"))
        assert "AudioAlarm" in payload
        assert payload["AudioAlarm"]["audioID"] == "1"
        assert payload["AudioAlarm"]["audioVolume"] == "50"
        assert payload["AudioAlarm"]["alarmTimes"] == "1"
        assert payload["AudioAlarm"]["durationTime"] == "10"
        return httpx.Response(200)

    endpoint = respx.put(url).mock(side_effect=check_payload)

    await hass.services.async_call(
        DOMAIN,
        ACTION_TRIGGER_SIREN,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2T86G2-ISU"], indirect=True)
async def test_trigger_siren_with_custom_params(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test triggering siren with custom parameters."""
    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Enable siren support for test
    device.capabilities.support_siren = True

    url = f"{TEST_HOST}/ISAPI/Event/triggers/notifications/AudioAlarm?format=json"

    def check_payload(request, route):
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["AudioAlarm"]["audioID"] == "5"
        assert payload["AudioAlarm"]["audioVolume"] == "80"
        assert payload["AudioAlarm"]["alarmTimes"] == "3"
        assert payload["AudioAlarm"]["durationTime"] == "30"
        return httpx.Response(200)

    endpoint = respx.put(url).mock(side_effect=check_payload)

    await hass.services.async_call(
        DOMAIN,
        ACTION_TRIGGER_SIREN,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "duration": 30,
            "audio_id": 5,
            "volume": 80,
            "alarm_times": 3,
        },
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2T86G2-ISU"], indirect=True)
async def test_trigger_siren_not_supported(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test triggering siren on device that doesn't support it."""
    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Explicitly disable siren support
    device.capabilities.support_siren = False

    with pytest.raises(HomeAssistantError, match="siren"):
        await hass.services.async_call(
            DOMAIN,
            ACTION_TRIGGER_SIREN,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
            blocking=True,
        )


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2T86G2-ISU"], indirect=True)
async def test_trigger_strobe_action(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test triggering the strobe service."""
    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Enable strobe support for test
    device.capabilities.support_strobe = True

    url = f"{TEST_HOST}/ISAPI/Event/triggers/notifications/channels/1/whiteLightAlarm?format=json"

    def check_payload(request, route):
        payload = json.loads(request.content.decode("utf-8"))
        assert "WhiteLightAlarm" in payload
        assert payload["WhiteLightAlarm"]["channelID"] == "1"
        assert payload["WhiteLightAlarm"]["durationTime"] == "10"
        assert payload["WhiteLightAlarm"]["frequency"] == "medium"
        return httpx.Response(200)

    endpoint = respx.put(url).mock(side_effect=check_payload)

    await hass.services.async_call(
        DOMAIN,
        ACTION_TRIGGER_STROBE,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2T86G2-ISU"], indirect=True)
async def test_trigger_strobe_with_custom_params(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test triggering strobe with custom parameters."""
    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Enable strobe support for test
    device.capabilities.support_strobe = True

    url = f"{TEST_HOST}/ISAPI/Event/triggers/notifications/channels/2/whiteLightAlarm?format=json"

    def check_payload(request, route):
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["WhiteLightAlarm"]["channelID"] == "2"
        assert payload["WhiteLightAlarm"]["durationTime"] == "60"
        assert payload["WhiteLightAlarm"]["frequency"] == "high"
        return httpx.Response(200)

    endpoint = respx.put(url).mock(side_effect=check_payload)

    await hass.services.async_call(
        DOMAIN,
        ACTION_TRIGGER_STROBE,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "channel_id": 2,
            "duration": 60,
            "frequency": "high",
        },
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2T86G2-ISU"], indirect=True)
async def test_trigger_strobe_not_supported(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test triggering strobe on device that doesn't support it."""
    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Explicitly disable strobe support
    device.capabilities.support_strobe = False

    with pytest.raises(HomeAssistantError, match="strobe"):
        await hass.services.async_call(
            DOMAIN,
            ACTION_TRIGGER_STROBE,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
            blocking=True,
        )


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2T86G2-ISU"], indirect=True)
async def test_play_voice_action(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test playing a voice message."""
    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Enable voice support for test
    device.capabilities.support_voice = True

    url = f"{TEST_HOST}/ISAPI/Event/triggers/notifications/AudioAlarm?format=json"

    def check_payload(request, route):
        payload = json.loads(request.content.decode("utf-8"))
        assert "AudioAlarm" in payload
        assert payload["AudioAlarm"]["audioID"] == "1"
        assert payload["AudioAlarm"]["audioVolume"] == "50"
        assert payload["AudioAlarm"]["alarmTimes"] == "1"
        assert payload["AudioAlarm"]["audioClass"] == "alertAudio"
        assert payload["AudioAlarm"]["alertAudioID"] == "1"
        return httpx.Response(200)

    endpoint = respx.put(url).mock(side_effect=check_payload)

    await hass.services.async_call(
        DOMAIN,
        ACTION_PLAY_VOICE,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2T86G2-ISU"], indirect=True)
async def test_play_voice_with_custom_params(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test playing voice message with custom parameters."""
    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Enable voice support for test
    device.capabilities.support_voice = True

    url = f"{TEST_HOST}/ISAPI/Event/triggers/notifications/AudioAlarm?format=json"

    def check_payload(request, route):
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["AudioAlarm"]["audioID"] == "3"
        assert payload["AudioAlarm"]["audioVolume"] == "100"
        assert payload["AudioAlarm"]["alarmTimes"] == "5"
        assert payload["AudioAlarm"]["alertAudioID"] == "3"
        return httpx.Response(200)

    endpoint = respx.put(url).mock(side_effect=check_payload)

    await hass.services.async_call(
        DOMAIN,
        ACTION_PLAY_VOICE,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "audio_id": 3,
            "volume": 100,
            "alarm_times": 5,
        },
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2T86G2-ISU"], indirect=True)
async def test_play_voice_not_supported(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test playing voice on device that doesn't support it."""
    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Explicitly disable voice support
    device.capabilities.support_voice = False

    with pytest.raises(HomeAssistantError, match="voice"):
        await hass.services.async_call(
            DOMAIN,
            ACTION_PLAY_VOICE,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
            blocking=True,
        )


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2T86G2-ISU"], indirect=True)
async def test_siren_volume_bounds(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test that siren volume is bounded between 1 and 100."""
    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Enable siren support for test
    device.capabilities.support_siren = True

    url = f"{TEST_HOST}/ISAPI/Event/triggers/notifications/AudioAlarm?format=json"

    def check_payload_max(request, route):
        payload = json.loads(request.content.decode("utf-8"))
        # Volume should be clamped to 100
        assert payload["AudioAlarm"]["audioVolume"] == "100"
        return httpx.Response(200)

    endpoint = respx.put(url).mock(side_effect=check_payload_max)

    await hass.services.async_call(
        DOMAIN,
        ACTION_TRIGGER_SIREN,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "volume": 100,
        },
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2T86G2-ISU"], indirect=True)
async def test_strobe_constant_frequency(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test strobe with constant frequency (solid light)."""
    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Enable strobe support for test
    device.capabilities.support_strobe = True

    url = f"{TEST_HOST}/ISAPI/Event/triggers/notifications/channels/1/whiteLightAlarm?format=json"

    def check_frequency(request, route):
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["WhiteLightAlarm"]["frequency"] == "constant"
        return httpx.Response(200)

    endpoint = respx.put(url).mock(side_effect=check_frequency)

    await hass.services.async_call(
        DOMAIN,
        ACTION_TRIGGER_STROBE,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "frequency": "constant",
        },
        blocking=True,
    )

    assert endpoint.called


class TestActiveDeterrenceCapabilityDetection:
    """Tests for Active Deterrence capability detection."""

    @respx.mock
    async def test_isapi_exception_on_unsupported_siren(self, mock_isapi) -> None:
        """Test that ISAPIActiveDeterrenceNotSupportedError is raised for unsupported siren."""
        isapi = mock_isapi
        isapi.capabilities.support_siren = False

        with pytest.raises(ISAPIActiveDeterrenceNotSupportedError) as exc_info:
            await isapi.trigger_siren()

        assert exc_info.value.feature == "siren"
        assert "siren" in exc_info.value.message

    @respx.mock
    async def test_isapi_exception_on_unsupported_strobe(self, mock_isapi) -> None:
        """Test that ISAPIActiveDeterrenceNotSupportedError is raised for unsupported strobe."""
        isapi = mock_isapi
        isapi.capabilities.support_strobe = False

        with pytest.raises(ISAPIActiveDeterrenceNotSupportedError) as exc_info:
            await isapi.trigger_strobe()

        assert exc_info.value.feature == "strobe"
        assert "strobe" in exc_info.value.message

    @respx.mock
    async def test_isapi_exception_on_unsupported_voice(self, mock_isapi) -> None:
        """Test that ISAPIActiveDeterrenceNotSupportedError is raised for unsupported voice."""
        isapi = mock_isapi
        isapi.capabilities.support_voice = False

        with pytest.raises(ISAPIActiveDeterrenceNotSupportedError) as exc_info:
            await isapi.play_voice()

        assert exc_info.value.feature == "voice"
        assert "voice" in exc_info.value.message


class TestActiveDeterrenceISAPIMethods:
    """Tests for ISAPI Active Deterrence methods."""

    @respx.mock
    async def test_trigger_siren_request(self, mock_isapi) -> None:
        """Test that trigger_siren sends correct ISAPI request."""
        isapi = mock_isapi
        isapi.capabilities.support_siren = True

        url = f"{isapi.host}/ISAPI/Event/triggers/notifications/AudioAlarm?format=json"
        endpoint = respx.put(url).respond(status_code=200)

        await isapi.trigger_siren(duration=15, audio_id=2, volume=75, alarm_times=2)

        assert endpoint.called
        request = endpoint.calls[0].request
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["AudioAlarm"]["durationTime"] == "15"
        assert payload["AudioAlarm"]["audioID"] == "2"
        assert payload["AudioAlarm"]["audioVolume"] == "75"
        assert payload["AudioAlarm"]["alarmTimes"] == "2"

    @respx.mock
    async def test_trigger_strobe_request(self, mock_isapi) -> None:
        """Test that trigger_strobe sends correct ISAPI request."""
        isapi = mock_isapi
        isapi.capabilities.support_strobe = True

        url = f"{isapi.host}/ISAPI/Event/triggers/notifications/channels/1/whiteLightAlarm?format=json"
        endpoint = respx.put(url).respond(status_code=200)

        await isapi.trigger_strobe(channel_id=1, duration=20, frequency="high")

        assert endpoint.called
        request = endpoint.calls[0].request
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["WhiteLightAlarm"]["channelID"] == "1"
        assert payload["WhiteLightAlarm"]["durationTime"] == "20"
        assert payload["WhiteLightAlarm"]["frequency"] == "high"

    @respx.mock
    async def test_play_voice_request(self, mock_isapi) -> None:
        """Test that play_voice sends correct ISAPI request."""
        isapi = mock_isapi
        isapi.capabilities.support_voice = True

        url = f"{isapi.host}/ISAPI/Event/triggers/notifications/AudioAlarm?format=json"
        endpoint = respx.put(url).respond(status_code=200)

        await isapi.play_voice(audio_id=4, volume=60, alarm_times=3)

        assert endpoint.called
        request = endpoint.calls[0].request
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["AudioAlarm"]["audioID"] == "4"
        assert payload["AudioAlarm"]["audioVolume"] == "60"
        assert payload["AudioAlarm"]["alarmTimes"] == "3"
        assert payload["AudioAlarm"]["audioClass"] == "alertAudio"
        assert payload["AudioAlarm"]["alertAudioID"] == "4"

    @respx.mock
    async def test_duration_bounds(self, mock_isapi) -> None:
        """Test that duration is bounded between 1 and 300."""
        isapi = mock_isapi
        isapi.capabilities.support_siren = True

        url = f"{isapi.host}/ISAPI/Event/triggers/notifications/AudioAlarm?format=json"
        endpoint = respx.put(url).respond(status_code=200)

        # Test lower bound (should be clamped to 1)
        await isapi.trigger_siren(duration=0)
        payload = json.loads(endpoint.calls[-1].request.content.decode("utf-8"))
        assert payload["AudioAlarm"]["durationTime"] == "1"

        # Test upper bound (should be clamped to 300)
        await isapi.trigger_siren(duration=500)
        payload = json.loads(endpoint.calls[-1].request.content.decode("utf-8"))
        assert payload["AudioAlarm"]["durationTime"] == "300"

    @respx.mock
    async def test_volume_bounds(self, mock_isapi) -> None:
        """Test that volume is bounded between 1 and 100."""
        isapi = mock_isapi
        isapi.capabilities.support_siren = True

        url = f"{isapi.host}/ISAPI/Event/triggers/notifications/AudioAlarm?format=json"
        endpoint = respx.put(url).respond(status_code=200)

        # Test lower bound (should be clamped to 1)
        await isapi.trigger_siren(volume=0)
        payload = json.loads(endpoint.calls[-1].request.content.decode("utf-8"))
        assert payload["AudioAlarm"]["audioVolume"] == "1"

        # Test upper bound (should be clamped to 100)
        await isapi.trigger_siren(volume=150)
        payload = json.loads(endpoint.calls[-1].request.content.decode("utf-8"))
        assert payload["AudioAlarm"]["audioVolume"] == "100"

    @respx.mock
    async def test_strobe_invalid_frequency_defaults_to_medium(self, mock_isapi) -> None:
        """Test that invalid frequency defaults to medium."""
        isapi = mock_isapi
        isapi.capabilities.support_strobe = True

        url = f"{isapi.host}/ISAPI/Event/triggers/notifications/channels/1/whiteLightAlarm?format=json"
        endpoint = respx.put(url).respond(status_code=200)

        await isapi.trigger_strobe(frequency="invalid")

        payload = json.loads(endpoint.calls[-1].request.content.decode("utf-8"))
        assert payload["WhiteLightAlarm"]["frequency"] == "medium"

    @respx.mock
    async def test_check_siren_support_true(self, mock_isapi) -> None:
        """Test siren support detection when supported."""
        isapi = mock_isapi

        url = f"{isapi.host}/ISAPI/Event/triggers/notifications/AudioAlarm?format=json"
        # ISAPI returns XML which gets parsed to dict, return valid XML response
        respx.get(url).respond(text='<AudioAlarm><enabled>true</enabled></AudioAlarm>')

        result = await isapi._check_siren_support()
        assert result is True

    @respx.mock
    async def test_check_siren_support_false(self, mock_isapi) -> None:
        """Test siren support detection when not supported."""
        isapi = mock_isapi

        url = f"{isapi.host}/ISAPI/Event/triggers/notifications/AudioAlarm?format=json"
        respx.get(url).respond(status_code=404)

        result = await isapi._check_siren_support()
        assert result is False
