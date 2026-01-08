"""Tests for two-way audio support."""

import pytest
import respx
import httpx
from custom_components.hikvision_next.isapi import TwoWayAudioInfo
from custom_components.hikvision_next.hikvision_device import HikvisionDevice
from tests.conftest import mock_endpoint, load_fixture, TEST_HOST
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


@respx.mock
async def test_get_two_way_audio_channels_single(mock_isapi):
    """Test fetching single two-way audio channel."""
    isapi = mock_isapi

    mock_endpoint("System/TwoWayAudio/channels", "single_channel")
    channels = await isapi.get_two_way_audio_channels()

    assert len(channels) == 1
    assert channels[0] == TwoWayAudioInfo(
        id=1,
        enabled=True,
        audio_compression="G.711ulaw",
        audio_input_type="MicIn",
        speaker_volume=70,
        mic_volume=50,
    )


@respx.mock
async def test_get_two_way_audio_channels_multiple(mock_isapi):
    """Test fetching multiple two-way audio channels."""
    isapi = mock_isapi

    mock_endpoint("System/TwoWayAudio/channels", "multiple_channels")
    channels = await isapi.get_two_way_audio_channels()

    assert len(channels) == 2
    assert channels[0].id == 1
    assert channels[0].enabled is True
    assert channels[0].audio_compression == "G.711ulaw"
    assert channels[0].speaker_volume == 80
    assert channels[0].mic_volume == 60

    assert channels[1].id == 2
    assert channels[1].enabled is False
    assert channels[1].audio_compression == "G.711alaw"
    assert channels[1].audio_input_type == "LineIn"
    assert channels[1].speaker_volume == 50
    assert channels[1].mic_volume == 40


@respx.mock
async def test_get_two_way_audio_channels_not_supported(mock_isapi):
    """Test fetching two-way audio when not supported returns empty list."""
    isapi = mock_isapi

    mock_endpoint("System/TwoWayAudio/channels", status_code=403)
    channels = await isapi.get_two_way_audio_channels()

    assert len(channels) == 0


@respx.mock
async def test_get_two_way_audio_channel_by_id(mock_isapi):
    """Test getting two-way audio channel by id."""
    isapi = mock_isapi

    # Set up the two_way_audio list directly
    isapi.two_way_audio = [
        TwoWayAudioInfo(
            id=1,
            enabled=True,
            audio_compression="G.711ulaw",
            audio_input_type="MicIn",
            speaker_volume=70,
            mic_volume=50,
        ),
        TwoWayAudioInfo(
            id=2,
            enabled=False,
            audio_compression="G.711alaw",
            audio_input_type="LineIn",
            speaker_volume=50,
            mic_volume=40,
        ),
    ]

    channel = isapi.get_two_way_audio_channel_by_id(1)
    assert channel is not None
    assert channel.id == 1
    assert channel.enabled is True

    channel = isapi.get_two_way_audio_channel_by_id(2)
    assert channel is not None
    assert channel.id == 2
    assert channel.enabled is False

    channel = isapi.get_two_way_audio_channel_by_id(99)
    assert channel is None


@respx.mock
async def test_open_two_way_audio(mock_isapi):
    """Test opening two-way audio channel."""
    isapi = mock_isapi

    url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/open"
    endpoint = respx.put(url).respond(status_code=200)

    result = await isapi.open_two_way_audio(channel_id=1)

    assert result is True
    assert endpoint.called


@respx.mock
async def test_open_two_way_audio_failure(mock_isapi):
    """Test opening two-way audio channel when it fails."""
    isapi = mock_isapi

    url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/open"
    respx.put(url).respond(status_code=500)

    result = await isapi.open_two_way_audio(channel_id=1)

    assert result is False


@respx.mock
async def test_close_two_way_audio(mock_isapi):
    """Test closing two-way audio channel."""
    isapi = mock_isapi

    url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/close"
    endpoint = respx.put(url).respond(status_code=200)

    result = await isapi.close_two_way_audio(channel_id=1)

    assert result is True
    assert endpoint.called


@respx.mock
async def test_close_two_way_audio_failure(mock_isapi):
    """Test closing two-way audio channel when it fails."""
    isapi = mock_isapi

    url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/close"
    respx.put(url).respond(status_code=500)

    result = await isapi.close_two_way_audio(channel_id=1)

    assert result is False


@respx.mock
async def test_send_two_way_audio_data(mock_isapi):
    """Test sending audio data to two-way audio channel."""
    isapi = mock_isapi

    # Sample G.711 ulaw audio data (just binary bytes for testing)
    audio_data = b"\x00\x01\x02\x03\x04\x05" * 100

    url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/audioData"

    def validate_audio_request(request):
        # Verify the content-type and data
        assert request.headers.get("content-type") == "application/octet-stream"
        assert request.content == audio_data
        return httpx.Response(200)

    endpoint = respx.put(url).mock(side_effect=validate_audio_request)

    result = await isapi.send_two_way_audio_data(audio_data, channel_id=1)

    assert result is True
    assert endpoint.called


@respx.mock
async def test_send_two_way_audio_data_failure(mock_isapi):
    """Test sending audio data when transmission fails."""
    isapi = mock_isapi

    audio_data = b"\x00\x01\x02\x03"

    url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/audioData"
    respx.put(url).respond(status_code=500)

    result = await isapi.send_two_way_audio_data(audio_data, channel_id=1)

    assert result is False


@respx.mock
async def test_send_two_way_audio_data_different_channel(mock_isapi):
    """Test sending audio data to different channel."""
    isapi = mock_isapi

    audio_data = b"\x00\x01\x02\x03"

    url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/2/audioData"
    endpoint = respx.put(url).respond(status_code=200)

    result = await isapi.send_two_way_audio_data(audio_data, channel_id=2)

    assert result is True
    assert endpoint.called


@respx.mock
async def test_two_way_audio_workflow(mock_isapi):
    """Test complete two-way audio workflow: open, send, close."""
    isapi = mock_isapi

    # Mock all endpoints
    open_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/open"
    audio_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/audioData"
    close_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/close"

    open_endpoint = respx.put(open_url).respond(status_code=200)
    audio_endpoint = respx.put(audio_url).respond(status_code=200)
    close_endpoint = respx.put(close_url).respond(status_code=200)

    # Simulate workflow
    audio_data = b"\x00\x01\x02\x03" * 50

    # Step 1: Open channel
    open_result = await isapi.open_two_way_audio(channel_id=1)
    assert open_result is True
    assert open_endpoint.called

    # Step 2: Send audio data
    send_result = await isapi.send_two_way_audio_data(audio_data, channel_id=1)
    assert send_result is True
    assert audio_endpoint.called

    # Step 3: Close channel
    close_result = await isapi.close_two_way_audio(channel_id=1)
    assert close_result is True
    assert close_endpoint.called


def test_two_way_audio_info_model():
    """Test TwoWayAudioInfo dataclass."""
    audio_info = TwoWayAudioInfo(
        id=1,
        enabled=True,
        audio_compression="G.711ulaw",
        audio_input_type="MicIn",
        speaker_volume=75,
        mic_volume=60,
    )

    assert audio_info.id == 1
    assert audio_info.enabled is True
    assert audio_info.audio_compression == "G.711ulaw"
    assert audio_info.audio_input_type == "MicIn"
    assert audio_info.speaker_volume == 75
    assert audio_info.mic_volume == 60


def test_two_way_audio_info_default_values():
    """Test TwoWayAudioInfo dataclass default values."""
    audio_info = TwoWayAudioInfo(
        id=1,
        enabled=False,
        audio_compression="G.711alaw",
        audio_input_type="LineIn",
    )

    assert audio_info.id == 1
    assert audio_info.enabled is False
    assert audio_info.speaker_volume == 50  # default value
    assert audio_info.mic_volume == 50  # default value


# Integration tests with device initialization
@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_two_way_audio_capabilities_detection(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test that two-way audio capabilities are detected during device initialization."""
    entry = init_integration

    device: HikvisionDevice = entry.runtime_data
    # DS-7608NXI-I2 has voicetalkNums: 2 in its capabilities
    assert device.capabilities.support_two_way_audio is True


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_two_way_audio_channels_loaded(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test that two-way audio channels are loaded during device initialization."""
    entry = init_integration

    device: HikvisionDevice = entry.runtime_data
    # DS-7608NXI-I2 fixture has 2 two-way audio channels configured
    assert len(device.two_way_audio) == 2

    # Check first channel
    channel1 = device.get_two_way_audio_channel_by_id(1)
    assert channel1 is not None
    assert channel1.enabled is True
    assert channel1.audio_compression == "G.711ulaw"
    assert channel1.speaker_volume == 75

    # Check second channel
    channel2 = device.get_two_way_audio_channel_by_id(2)
    assert channel2 is not None
    assert channel2.enabled is False


@pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
async def test_two_way_audio_not_supported(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test device without two-way audio support has no audio channels."""
    entry = init_integration

    device: HikvisionDevice = entry.runtime_data
    # DS-2CD2386G2-IU has voicetalkNums: 0 or missing
    assert device.capabilities.support_two_way_audio is False
    assert len(device.two_way_audio) == 0


@pytest.mark.parametrize("init_integration", ["DS-2CD2443G0-IW"], indirect=True)
async def test_two_way_audio_single_channel_camera(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test IP camera with single two-way audio channel."""
    entry = init_integration

    device: HikvisionDevice = entry.runtime_data
    # DS-2CD2443G0-IW has voicetalkNums: 1
    assert device.capabilities.support_two_way_audio is True
    assert len(device.two_way_audio) == 1

    channel = device.get_two_way_audio_channel_by_id(1)
    assert channel is not None
    assert channel.enabled is True
    assert channel.audio_compression == "G.711ulaw"
    assert channel.speaker_volume == 60
    assert channel.mic_volume == 45


@respx.mock
async def test_open_close_workflow_error_handling(mock_isapi):
    """Test error handling in open/close workflow."""
    isapi = mock_isapi

    # Test that closing without opening returns success (API doesn't error)
    close_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/close"
    respx.put(close_url).respond(status_code=200)
    result = await isapi.close_two_way_audio(channel_id=1)
    assert result is True

    # Test opening a non-existent channel
    open_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/99/open"
    respx.put(open_url).respond(status_code=404)
    result = await isapi.open_two_way_audio(channel_id=99)
    assert result is False


@respx.mock
async def test_send_audio_empty_data(mock_isapi):
    """Test sending empty audio data."""
    isapi = mock_isapi

    audio_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/audioData"
    endpoint = respx.put(audio_url).respond(status_code=200)

    # Empty data should still work (though not useful)
    result = await isapi.send_two_way_audio_data(b"", channel_id=1)
    assert result is True
    assert endpoint.called


@respx.mock
async def test_send_audio_large_data(mock_isapi):
    """Test sending large audio data."""
    isapi = mock_isapi

    # Simulate 5 seconds of G.711 ulaw audio at 8kHz mono (8000 bytes/sec)
    large_audio_data = b"\x7f\x00" * 20000  # 40KB

    audio_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/audioData"

    def validate_large_audio(request):
        assert len(request.content) == len(large_audio_data)
        return httpx.Response(200)

    endpoint = respx.put(audio_url).mock(side_effect=validate_large_audio)

    result = await isapi.send_two_way_audio_data(large_audio_data, channel_id=1)
    assert result is True
    assert endpoint.called
