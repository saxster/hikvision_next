"""Tests for camera platform."""

import pytest
import respx
import httpx
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import STATE_IDLE
from homeassistant.components.camera.helper import get_camera_from_entity_id
from homeassistant.components.camera import (
    DOMAIN as CAMERA_DOMAIN,
    CameraEntityFeature,
    StreamType,
    async_register_webrtc_provider,
    CameraWebRTCProvider,
    WebRTCSendMessage,
)
from webrtc_models import RTCIceCandidateInit
from custom_components.hikvision_next.hikvision_device import HikvisionDevice
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.conftest import load_fixture
from tests.conftest import TEST_HOST
import homeassistant.helpers.entity_registry as er


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_camera(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test camera initialization."""

    assert len(hass.states.async_entity_ids(CAMERA_DOMAIN)) == 3

    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_101"
    assert hass.states.get(entity_id)

    camera_entity = get_camera_from_entity_id(hass, entity_id)
    assert camera_entity.state == STATE_IDLE
    assert camera_entity.name == "garden"

    stream_url = await camera_entity.stream_source()
    assert stream_url == "rtsp://u1:%2A%2A%2A@1.0.0.255:10554/Streaming/channels/101"

    entity_registry = er.async_get(hass)
    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_102"
    camera_entity = entity_registry.async_get(entity_id)
    assert camera_entity.disabled
    assert camera_entity.original_name == "Sub-Stream"

    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_104"
    camera_entity = entity_registry.async_get(entity_id)
    assert camera_entity.disabled
    assert camera_entity.original_name == "Transcoded Stream"


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_camera_snapshot(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test camera snapshot."""

    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_101"
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    image_url = f"{TEST_HOST}/ISAPI/Streaming/channels/101/picture"
    respx.get(image_url).respond(content=b"binary image data")
    image = await camera_entity.async_camera_image()
    assert image == b"binary image data"


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_camera_snapshot_device_error(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test camera snapshot with 2 attempts."""

    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_101"
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    image_url = f"{TEST_HOST}/ISAPI/Streaming/channels/101/picture"
    route = respx.get(image_url)
    error_response = load_fixture("ISAPI/Streaming.channels.x0y.picture", "deviceError")
    route.side_effect = [
        httpx.Response(200, content=error_response),
        httpx.Response(200, content=error_response),
        httpx.Response(200, content=b"binary image data"),
    ]
    image = await camera_entity.async_camera_image()
    assert image == b"binary image data"


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-7616NI-Q2"], indirect=True)
async def test_camera_snapshot_alternate_url(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test camera snapshot with alternate url."""

    entity_id = "camera.ds_7616ni_q2_00p0000000000ccrre00000000wcvu_101"
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    error_response = load_fixture("ISAPI/Streaming.channels.x0y.picture", "badXmlContent")
    image_url = f"{TEST_HOST}/ISAPI/Streaming/channels/101/picture"
    respx.get(image_url).respond(content=error_response)
    image_url = f"{TEST_HOST}/ISAPI/ContentMgmt/StreamingProxy/channels/101/picture"
    respx.get(image_url).respond(content=b"binary image data")
    image = await camera_entity.async_camera_image()
    assert image == b"binary image data"


device_data = {
    "DS-7608NXI-I2": {
        "entity_id": "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_101",
        "codec": "H.264",
        "width": "3840",
        "height": "2160",
        "rtsp_port": 10554,
    },
    "DS-7616NI-Q2": {
        "entity_id": "camera.ds_7616ni_q2_00p0000000000ccrre00000000wcvu_101",
        "codec": "H.265",
        "width": "2560",
        "height": "1440",
        "rtsp_port": 554,
    },
}

@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2", "DS-7616NI-Q2"], indirect=True)
async def test_camera_stream_info(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test camera snapshot with alternate url."""

    data = device_data[init_integration.title]
    entity_id = data["entity_id"]
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    assert camera_entity.stream_info.codec == data["codec"]
    assert camera_entity.stream_info.width == data["width"]
    assert camera_entity.stream_info.height == data["height"]

    stream_url = await camera_entity.stream_source()
    assert stream_url == f"rtsp://u1:%2A%2A%2A@1.0.0.255:{data['rtsp_port']}/Streaming/channels/101"

@pytest.mark.parametrize("init_integration", ["DS-2TD1228-2-QA"], indirect=True)
async def test_camera_multichannel(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    entry = init_integration

    device: HikvisionDevice = entry.runtime_data
    assert len(device.cameras) == 2 # video channel + thermal channel
    assert device.cameras[0].input_port == 1
    assert device.cameras[1].input_port == 2


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2", "DS-7732NI-M4"], indirect=True)
async def test_nvr_with_onvif_cameras(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test proxy cameras with repeated serial no."""

    entry = init_integration
    device: HikvisionDevice = entry.runtime_data

    unique_serial_no = set()
    for camera in device.cameras:
        unique_serial_no.add(camera.serial_no)

    assert len(device.cameras) == len(unique_serial_no)


# WebRTC Tests


class MockWebRTCProvider(CameraWebRTCProvider):
    """Mock WebRTC provider for testing."""

    def __init__(self) -> None:
        """Initialize the mock provider."""
        self._supported_streams = frozenset(("rtsp", "rtsps"))

    @property
    def domain(self) -> str:
        """Return the integration domain of the provider."""
        return "mock_webrtc"

    @callback
    def async_is_supported(self, stream_source: str) -> bool:
        """Return if this provider supports the stream source."""
        return stream_source.partition(":")[0] in self._supported_streams

    async def async_handle_async_webrtc_offer(
        self,
        camera,
        offer_sdp: str,
        session_id: str,
        send_message: WebRTCSendMessage,
    ) -> None:
        """Handle the WebRTC offer and return the answer via the provided callback."""
        pass

    async def async_on_webrtc_candidate(
        self,
        session_id: str,
        candidate: RTCIceCandidateInit,
    ) -> None:
        """Handle the WebRTC candidate."""
        pass


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_camera_supports_stream_feature(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that camera supports streaming feature."""

    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_101"
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    # Verify stream feature is supported
    assert CameraEntityFeature.STREAM in camera_entity.supported_features


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_camera_stream_source_rtsp_format(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that camera stream source is in RTSP format compatible with WebRTC providers."""

    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_101"
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    stream_url = await camera_entity.stream_source()

    # Verify the stream source is RTSP format
    assert stream_url is not None
    assert stream_url.startswith("rtsp://")
    # Verify it contains the proper Hikvision streaming path
    assert "/Streaming/channels/" in stream_url


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_camera_webrtc_provider_compatible(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that camera stream source is compatible with WebRTC providers like go2rtc."""

    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_101"
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    stream_url = await camera_entity.stream_source()

    # Create a mock WebRTC provider that supports RTSP
    mock_provider = MockWebRTCProvider()

    # Verify the stream URL is supported by RTSP-capable WebRTC providers
    assert mock_provider.async_is_supported(stream_url)


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_camera_frontend_stream_type_hls_default(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that camera frontend_stream_type is HLS by default (no WebRTC provider)."""

    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_101"
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    # Without a WebRTC provider, should fall back to HLS
    assert camera_entity.frontend_stream_type == StreamType.HLS


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_camera_frontend_stream_type_webrtc_with_provider(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that camera frontend_stream_type becomes WebRTC when a provider is registered."""

    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_101"
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    # Register a mock WebRTC provider
    mock_provider = MockWebRTCProvider()
    unregister = async_register_webrtc_provider(hass, mock_provider)

    # Refresh providers to pick up the new provider
    await camera_entity.async_refresh_providers()

    # With a WebRTC provider, should be WebRTC
    assert camera_entity.frontend_stream_type == StreamType.WEB_RTC

    # Cleanup
    unregister()


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2", "DS-7616NI-Q2"], indirect=True)
async def test_camera_webrtc_stream_urls_all_devices(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test all device stream URLs are WebRTC-compatible (RTSP format)."""

    data = device_data[init_integration.title]
    entity_id = data["entity_id"]
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    stream_url = await camera_entity.stream_source()

    # All streams should be RTSP format for WebRTC compatibility
    assert stream_url.startswith("rtsp://")

    # Verify stream is compatible with RTSP-based WebRTC providers
    mock_provider = MockWebRTCProvider()
    assert mock_provider.async_is_supported(stream_url)


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_camera_capabilities_include_stream_types(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test camera capabilities include appropriate stream types."""

    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_101"
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    # Get camera capabilities
    capabilities = camera_entity.camera_capabilities

    # Should have frontend_stream_types in capabilities
    assert capabilities.frontend_stream_types is not None
    # HLS should always be available as baseline
    assert StreamType.HLS in capabilities.frontend_stream_types


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_camera_webrtc_capabilities_with_provider(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test camera capabilities include WebRTC when provider is registered."""

    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_101"
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    # Register a mock WebRTC provider
    mock_provider = MockWebRTCProvider()
    unregister = async_register_webrtc_provider(hass, mock_provider)

    # Refresh providers
    await camera_entity.async_refresh_providers()

    # Get camera capabilities
    capabilities = camera_entity.camera_capabilities

    # Should now include WebRTC as available stream type
    assert StreamType.WEB_RTC in capabilities.frontend_stream_types

    # Cleanup
    unregister()


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_camera_stream_url_contains_authentication(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that stream URL contains proper authentication for WebRTC providers."""

    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_101"
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    stream_url = await camera_entity.stream_source()

    # Verify authentication is embedded in URL (required for go2rtc and similar)
    # URL format: rtsp://username:password@host:port/path
    assert "@" in stream_url
    assert "u1:" in stream_url  # username from test config


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_camera_stream_url_port_configuration(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that stream URL uses correct RTSP port from device configuration."""

    entity_id = "camera.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_101"
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    stream_url = await camera_entity.stream_source()

    # Verify correct RTSP port is used (10554 for this device)
    assert ":10554/" in stream_url


@pytest.mark.parametrize("init_integration", ["DS-7616NI-Q2"], indirect=True)
async def test_camera_stream_url_default_port(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that stream URL uses default RTSP port (554) when appropriate."""

    entity_id = "camera.ds_7616ni_q2_00p0000000000ccrre00000000wcvu_101"
    camera_entity = get_camera_from_entity_id(hass, entity_id)

    stream_url = await camera_entity.stream_source()

    # Verify default RTSP port 554 is used
    assert ":554/" in stream_url
