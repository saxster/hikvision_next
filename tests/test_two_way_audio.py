"""Tests for two-way audio functionality."""

import pytest
import respx
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.hikvision_next.const import (
    ACTION_START_TWO_WAY_AUDIO,
    ACTION_STOP_TWO_WAY_AUDIO,
    ATTR_CONFIG_ENTRY_ID,
    DOMAIN,
)
from custom_components.hikvision_next.isapi import TwoWayAudioChannelInfo
from tests.conftest import TEST_HOST, mock_endpoint


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_two_way_audio_capability_detection(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that two-way audio capability is detected from voicetalkNums."""

    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # DS-2CD2146G2-ISU has voicetalkNums: "1" in the fixture
    assert device.capabilities.support_two_way_audio is True
    assert device.capabilities.two_way_audio_channels == 1


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
async def test_two_way_audio_not_supported(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that two-way audio is not supported when voicetalkNums is 0."""

    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # DS-2CD2386G2-IU has voicetalkNums: "0" in the fixture
    assert device.capabilities.support_two_way_audio is False
    assert device.capabilities.two_way_audio_channels == 0


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_start_two_way_audio_action(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test starting two-way audio via service action."""

    mock_config_entry = init_integration

    url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/open"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_START_TWO_WAY_AUDIO,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id, "channel_id": 1},
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_stop_two_way_audio_action(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test stopping two-way audio via service action."""

    mock_config_entry = init_integration

    url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/close"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_STOP_TWO_WAY_AUDIO,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id, "channel_id": 1},
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_start_two_way_audio_default_channel(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test starting two-way audio with default channel_id."""

    mock_config_entry = init_integration

    url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/open"
    endpoint = respx.put(url).respond()

    # Call without specifying channel_id to use default
    await hass.services.async_call(
        DOMAIN,
        ACTION_START_TWO_WAY_AUDIO,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
async def test_start_two_way_audio_not_supported(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that starting two-way audio fails when not supported."""

    mock_config_entry = init_integration

    with pytest.raises(HomeAssistantError, match="Device does not support two-way audio"):
        await hass.services.async_call(
            DOMAIN,
            ACTION_START_TWO_WAY_AUDIO,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
            blocking=True,
        )


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
async def test_stop_two_way_audio_not_supported(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that stopping two-way audio fails when not supported."""

    mock_config_entry = init_integration

    with pytest.raises(HomeAssistantError, match="Device does not support two-way audio"):
        await hass.services.async_call(
            DOMAIN,
            ACTION_STOP_TWO_WAY_AUDIO,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
            blocking=True,
        )


@respx.mock
async def test_get_two_way_audio_channels(mock_isapi):
    """Test fetching two-way audio channels."""
    isapi = mock_isapi

    # Mock the two-way audio channels endpoint
    mock_endpoint("System/TwoWayAudio/channels", "channels_list")

    channels = await isapi.get_two_way_audio_channels()

    assert len(channels) == 1
    assert channels[0] == TwoWayAudioChannelInfo(
        id=1,
        enabled=True,
        audio_compression_type="G.711ulaw",
    )


@respx.mock
async def test_get_two_way_audio_channels_empty(mock_isapi):
    """Test fetching two-way audio channels when none exist."""
    isapi = mock_isapi

    # Mock empty response
    mock_endpoint("System/TwoWayAudio/channels", "channels_empty")

    channels = await isapi.get_two_way_audio_channels()

    assert len(channels) == 0


@respx.mock
async def test_start_two_way_audio_method(mock_isapi):
    """Test the ISAPIClient start_two_way_audio method."""
    isapi = mock_isapi

    url = f"{isapi.host}/ISAPI/System/TwoWayAudio/channels/1/open"
    endpoint = respx.put(url).respond()

    await isapi.start_two_way_audio(channel_id=1)

    assert endpoint.called


@respx.mock
async def test_stop_two_way_audio_method(mock_isapi):
    """Test the ISAPIClient stop_two_way_audio method."""
    isapi = mock_isapi

    url = f"{isapi.host}/ISAPI/System/TwoWayAudio/channels/1/close"
    endpoint = respx.put(url).respond()

    await isapi.stop_two_way_audio(channel_id=1)

    assert endpoint.called


@respx.mock
async def test_start_two_way_audio_custom_channel(mock_isapi):
    """Test starting two-way audio on a custom channel."""
    isapi = mock_isapi

    url = f"{isapi.host}/ISAPI/System/TwoWayAudio/channels/2/open"
    endpoint = respx.put(url).respond()

    await isapi.start_two_way_audio(channel_id=2)

    assert endpoint.called


@respx.mock
async def test_stop_two_way_audio_custom_channel(mock_isapi):
    """Test stopping two-way audio on a custom channel."""
    isapi = mock_isapi

    url = f"{isapi.host}/ISAPI/System/TwoWayAudio/channels/2/close"
    endpoint = respx.put(url).respond()

    await isapi.stop_two_way_audio(channel_id=2)

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_nvr_two_way_audio_support(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test two-way audio support on NVR devices."""

    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # DS-7608NXI-I2 has voicetalkNums: "2" in the fixture
    assert device.capabilities.support_two_way_audio is True
    assert device.capabilities.two_way_audio_channels == 2
