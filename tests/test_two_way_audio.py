"""Tests for two-way audio functionality."""

import pytest
import respx
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.hikvision_next.isapi import TwoWayAudioInfo
from custom_components.hikvision_next.hikvision_device import HikvisionDevice
from tests.conftest import TEST_HOST


# Test fixtures for two-way audio API responses
TWO_WAY_AUDIO_CHANNELS_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<TwoWayAudioChannelList version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
    <TwoWayAudioChannel>
        <id>1</id>
        <enabled>true</enabled>
        <audioCompressionType>G.711ulaw</audioCompressionType>
        <audioInputType>MicIn</audioInputType>
        <speakerVolume>75</speakerVolume>
        <noisereduce>true</noisereduce>
    </TwoWayAudioChannel>
</TwoWayAudioChannelList>
"""

TWO_WAY_AUDIO_CHANNELS_MULTI_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<TwoWayAudioChannelList version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
    <TwoWayAudioChannel>
        <id>1</id>
        <enabled>true</enabled>
        <audioCompressionType>G.711ulaw</audioCompressionType>
        <audioInputType>MicIn</audioInputType>
        <speakerVolume>50</speakerVolume>
        <noisereduce>false</noisereduce>
    </TwoWayAudioChannel>
    <TwoWayAudioChannel>
        <id>2</id>
        <enabled>false</enabled>
        <audioCompressionType>G.711alaw</audioCompressionType>
        <audioInputType>LineIn</audioInputType>
        <speakerVolume>80</speakerVolume>
        <noisereduce>true</noisereduce>
    </TwoWayAudioChannel>
</TwoWayAudioChannelList>
"""

TWO_WAY_AUDIO_OPEN_SUCCESS = """<?xml version="1.0" encoding="UTF-8"?>
<ResponseStatus version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
    <requestURL>/ISAPI/System/TwoWayAudio/channels/1/open</requestURL>
    <statusCode>1</statusCode>
    <statusString>OK</statusString>
    <subStatusCode>ok</subStatusCode>
</ResponseStatus>
"""

TWO_WAY_AUDIO_CLOSE_SUCCESS = """<?xml version="1.0" encoding="UTF-8"?>
<ResponseStatus version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
    <requestURL>/ISAPI/System/TwoWayAudio/channels/1/close</requestURL>
    <statusCode>1</statusCode>
    <statusString>OK</statusString>
    <subStatusCode>ok</subStatusCode>
</ResponseStatus>
"""

TWO_WAY_AUDIO_DATA_SUCCESS = """<?xml version="1.0" encoding="UTF-8"?>
<ResponseStatus version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
    <requestURL>/ISAPI/System/TwoWayAudio/channels/1/audioData</requestURL>
    <statusCode>1</statusCode>
    <statusString>OK</statusString>
    <subStatusCode>ok</subStatusCode>
</ResponseStatus>
"""


class TestTwoWayAudioModel:
    """Test TwoWayAudioInfo model."""

    def test_two_way_audio_info_creation(self):
        """Test creating a TwoWayAudioInfo instance."""
        audio_info = TwoWayAudioInfo(
            id=1,
            enabled=True,
            audio_compression_type="G.711ulaw",
            audio_input_type="MicIn",
            speaker_volume=75,
            noisereduce=True,
        )

        assert audio_info.id == 1
        assert audio_info.enabled is True
        assert audio_info.audio_compression_type == "G.711ulaw"
        assert audio_info.audio_input_type == "MicIn"
        assert audio_info.speaker_volume == 75
        assert audio_info.noisereduce is True

    def test_two_way_audio_info_defaults(self):
        """Test TwoWayAudioInfo default values."""
        audio_info = TwoWayAudioInfo(id=1, enabled=False)

        assert audio_info.id == 1
        assert audio_info.enabled is False
        assert audio_info.audio_compression_type == "G.711ulaw"
        assert audio_info.audio_input_type == "MicIn"
        assert audio_info.speaker_volume == 50
        assert audio_info.noisereduce is False


class TestTwoWayAudioCapabilityDetection:
    """Test two-way audio capability detection."""

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_two_way_audio_supported(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test detection of two-way audio support when channels are available."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # Mock the two-way audio channels endpoint
        url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels"
        respx.get(url).respond(text=TWO_WAY_AUDIO_CHANNELS_RESPONSE)

        # Fetch two-way audio channels
        channels = await device.get_two_way_audio_channels()

        assert device.capabilities.support_two_way_audio is True
        assert len(channels) == 1
        assert channels[0].id == 1
        assert channels[0].enabled is True
        assert channels[0].audio_compression_type == "G.711ulaw"
        assert channels[0].speaker_volume == 75
        assert channels[0].noisereduce is True

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_two_way_audio_multiple_channels(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test detection of multiple two-way audio channels."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # Mock the two-way audio channels endpoint with multiple channels
        url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels"
        respx.get(url).respond(text=TWO_WAY_AUDIO_CHANNELS_MULTI_RESPONSE)

        channels = await device.get_two_way_audio_channels()

        assert device.capabilities.support_two_way_audio is True
        assert len(channels) == 2

        # Verify first channel
        assert channels[0].id == 1
        assert channels[0].enabled is True
        assert channels[0].audio_compression_type == "G.711ulaw"

        # Verify second channel
        assert channels[1].id == 2
        assert channels[1].enabled is False
        assert channels[1].audio_compression_type == "G.711alaw"
        assert channels[1].speaker_volume == 80

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_two_way_audio_not_supported(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test detection when two-way audio is not supported."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # Reset capabilities
        device.capabilities.support_two_way_audio = False
        device.capabilities.two_way_audio_channels = []

        # Mock 403 Forbidden response for unsupported devices
        url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels"
        respx.get(url).respond(status_code=403)

        # Should not raise an exception, just return empty list
        channels = await device.get_two_way_audio_channels()

        assert channels == []
        assert device.capabilities.support_two_way_audio is False

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_get_two_way_audio_channel_by_id(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test getting a specific two-way audio channel by ID."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # Mock the two-way audio channels endpoint with multiple channels
        url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels"
        respx.get(url).respond(text=TWO_WAY_AUDIO_CHANNELS_MULTI_RESPONSE)

        await device.get_two_way_audio_channels()

        # Get channel by ID
        channel_1 = device.get_two_way_audio_channel(1)
        assert channel_1 is not None
        assert channel_1.id == 1

        channel_2 = device.get_two_way_audio_channel(2)
        assert channel_2 is not None
        assert channel_2.id == 2

        # Non-existent channel
        channel_99 = device.get_two_way_audio_channel(99)
        assert channel_99 is None


class TestTwoWayAudioSessionManagement:
    """Test two-way audio session management."""

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_open_two_way_audio_session(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test opening a two-way audio session."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # First enable two-way audio support
        url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels"
        respx.get(url).respond(text=TWO_WAY_AUDIO_CHANNELS_RESPONSE)
        await device.get_two_way_audio_channels()

        # Mock the open endpoint
        open_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/open"
        open_route = respx.put(open_url).respond(text=TWO_WAY_AUDIO_OPEN_SUCCESS)

        result = await device.open_two_way_audio(channel_id=1)

        assert result is True
        assert open_route.called

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_close_two_way_audio_session(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test closing a two-way audio session."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # First enable two-way audio support
        url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels"
        respx.get(url).respond(text=TWO_WAY_AUDIO_CHANNELS_RESPONSE)
        await device.get_two_way_audio_channels()

        # Mock the close endpoint
        close_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/close"
        close_route = respx.put(close_url).respond(text=TWO_WAY_AUDIO_CLOSE_SUCCESS)

        result = await device.close_two_way_audio(channel_id=1)

        assert result is True
        assert close_route.called

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_open_two_way_audio_not_supported(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test opening two-way audio when not supported."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # Ensure two-way audio is not supported
        device.capabilities.support_two_way_audio = False

        result = await device.open_two_way_audio(channel_id=1)

        assert result is False

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_close_two_way_audio_not_supported(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test closing two-way audio when not supported."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # Ensure two-way audio is not supported
        device.capabilities.support_two_way_audio = False

        result = await device.close_two_way_audio(channel_id=1)

        assert result is False

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_open_two_way_audio_failure(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test handling failure when opening two-way audio session."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # First enable two-way audio support
        url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels"
        respx.get(url).respond(text=TWO_WAY_AUDIO_CHANNELS_RESPONSE)
        await device.get_two_way_audio_channels()

        # Mock a failure response
        open_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/open"
        respx.put(open_url).respond(status_code=500)

        result = await device.open_two_way_audio(channel_id=1)

        assert result is False


class TestTwoWayAudioDataTransmission:
    """Test two-way audio data transmission."""

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_send_audio_data(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test sending audio data to the camera."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # First enable two-way audio support
        url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels"
        respx.get(url).respond(text=TWO_WAY_AUDIO_CHANNELS_RESPONSE)
        await device.get_two_way_audio_channels()

        # Mock the audioData endpoint
        audio_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/audioData"
        audio_route = respx.put(audio_url).respond(text=TWO_WAY_AUDIO_DATA_SUCCESS)

        # Send some test audio data (simulated G.711 ulaw data)
        test_audio_data = b"\xff\x00\x01\x02\x03\x04" * 100

        result = await device.send_audio_data(test_audio_data, channel_id=1)

        assert result is True
        assert audio_route.called

        # Verify the content type header was set correctly
        request = audio_route.calls[0].request
        assert request.headers.get("content-type") == "application/octet-stream"

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_send_audio_data_not_supported(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test sending audio data when two-way audio not supported."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # Ensure two-way audio is not supported
        device.capabilities.support_two_way_audio = False

        result = await device.send_audio_data(b"test audio data", channel_id=1)

        assert result is False

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_send_audio_data_empty(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test sending empty audio data."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # First enable two-way audio support
        url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels"
        respx.get(url).respond(text=TWO_WAY_AUDIO_CHANNELS_RESPONSE)
        await device.get_two_way_audio_channels()

        result = await device.send_audio_data(b"", channel_id=1)

        assert result is False

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_send_audio_data_failure(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test handling failure when sending audio data."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # First enable two-way audio support
        url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels"
        respx.get(url).respond(text=TWO_WAY_AUDIO_CHANNELS_RESPONSE)
        await device.get_two_way_audio_channels()

        # Mock a failure response
        audio_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/audioData"
        respx.put(audio_url).respond(status_code=500)

        result = await device.send_audio_data(b"test audio data", channel_id=1)

        assert result is False


class TestTwoWayAudioURL:
    """Test two-way audio URL generation."""

    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_get_two_way_audio_url(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test generation of two-way audio RTSP URL."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        url = device.get_two_way_audio_url(channel_id=1)

        # Verify the URL contains the expected components
        assert "rtsp://" in url
        assert "u1:" in url  # username from test config
        assert "/Streaming/channels/101" in url
        assert "backchannel=0" in url

    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_get_two_way_audio_url_different_channel(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test generation of two-way audio RTSP URL for different channel."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        url = device.get_two_way_audio_url(channel_id=2)

        # Channel 2 should produce stream ID 201
        assert "/Streaming/channels/201" in url


class TestTwoWayAudioIntegration:
    """Integration tests for two-way audio workflow."""

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_full_two_way_audio_workflow(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test complete two-way audio workflow: discover -> open -> send -> close."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # Step 1: Discover two-way audio channels
        channels_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels"
        respx.get(channels_url).respond(text=TWO_WAY_AUDIO_CHANNELS_RESPONSE)

        channels = await device.get_two_way_audio_channels()
        assert len(channels) == 1
        assert device.capabilities.support_two_way_audio is True

        # Step 2: Open audio session
        open_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/open"
        respx.put(open_url).respond(text=TWO_WAY_AUDIO_OPEN_SUCCESS)

        open_result = await device.open_two_way_audio(channel_id=1)
        assert open_result is True

        # Step 3: Send audio data
        audio_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/audioData"
        respx.put(audio_url).respond(text=TWO_WAY_AUDIO_DATA_SUCCESS)

        test_audio = b"\x00\x01\x02\x03" * 50
        send_result = await device.send_audio_data(test_audio, channel_id=1)
        assert send_result is True

        # Step 4: Close audio session
        close_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/close"
        respx.put(close_url).respond(text=TWO_WAY_AUDIO_CLOSE_SUCCESS)

        close_result = await device.close_two_way_audio(channel_id=1)
        assert close_result is True

    @respx.mock
    @pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
    async def test_two_way_audio_session_reopen(
        self, hass: HomeAssistant, init_integration: MockConfigEntry
    ) -> None:
        """Test reopening a two-way audio session (close before open pattern)."""
        entry = init_integration
        device: HikvisionDevice = entry.runtime_data

        # Enable two-way audio support
        channels_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels"
        respx.get(channels_url).respond(text=TWO_WAY_AUDIO_CHANNELS_RESPONSE)
        await device.get_two_way_audio_channels()

        # Setup mock endpoints
        open_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/open"
        close_url = f"{TEST_HOST}/ISAPI/System/TwoWayAudio/channels/1/close"

        open_route = respx.put(open_url).respond(text=TWO_WAY_AUDIO_OPEN_SUCCESS)
        close_route = respx.put(close_url).respond(text=TWO_WAY_AUDIO_CLOSE_SUCCESS)

        # Close first (recommended pattern to ensure clean state)
        await device.close_two_way_audio(channel_id=1)

        # Then open
        await device.open_two_way_audio(channel_id=1)

        assert close_route.called
        assert open_route.called
