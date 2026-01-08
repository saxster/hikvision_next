"""Tests for actions."""

import pytest
import respx
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.hikvision_next.const import (
    ACTION_PTZ_MOVE,
    ACTION_PTZ_PRESET,
    ACTION_REBOOT,
    ATTR_CONFIG_ENTRY_ID,
    DOMAIN,
)
from tests.conftest import TEST_HOST


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_reboot_action(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test sending reboot request on reboot action."""

    mock_config_entry = init_integration

    url = f"{TEST_HOST}/ISAPI/System/reboot"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_REBOOT,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2SE4C425MWG-E-26"], indirect=True)
async def test_ptz_move_action(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test sending PTZ move request."""

    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Mock the PTZ capabilities endpoint to enable PTZ support
    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/capabilities").respond(
        text="""<?xml version="1.0" encoding="UTF-8"?>
        <PTZChannel>
            <id>1</id>
            <enabled>true</enabled>
        </PTZChannel>"""
    )

    # Mark the camera as supporting PTZ
    device.cameras[0].support_ptz = True

    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/continuous"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_PTZ_MOVE,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "channel_id": 1,
            "pan": 50,
            "tilt": 25,
            "zoom": 0,
        },
        blocking=True,
    )

    assert endpoint.called
    # Verify the XML payload contains the correct values
    request_body = endpoint.calls.last.request.content.decode()
    assert "<pan>50</pan>" in request_body
    assert "<tilt>25</tilt>" in request_body
    assert "<zoom>0</zoom>" in request_body


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2SE4C425MWG-E-26"], indirect=True)
async def test_ptz_move_stop_action(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test sending PTZ stop request (all values set to 0)."""

    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Mark the camera as supporting PTZ
    device.cameras[0].support_ptz = True

    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/continuous"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_PTZ_MOVE,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "channel_id": 1,
            "pan": 0,
            "tilt": 0,
            "zoom": 0,
        },
        blocking=True,
    )

    assert endpoint.called
    # Verify the XML payload contains zeros (stop command)
    request_body = endpoint.calls.last.request.content.decode()
    assert "<pan>0</pan>" in request_body
    assert "<tilt>0</tilt>" in request_body
    assert "<zoom>0</zoom>" in request_body


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2SE4C425MWG-E-26"], indirect=True)
async def test_ptz_move_defaults(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test PTZ move with default values (should default to 0)."""

    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Mark the camera as supporting PTZ
    device.cameras[0].support_ptz = True

    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/continuous"
    endpoint = respx.put(url).respond()

    # Call without pan, tilt, zoom - should default to 0
    await hass.services.async_call(
        DOMAIN,
        ACTION_PTZ_MOVE,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "channel_id": 1,
        },
        blocking=True,
    )

    assert endpoint.called
    request_body = endpoint.calls.last.request.content.decode()
    assert "<pan>0</pan>" in request_body
    assert "<tilt>0</tilt>" in request_body
    assert "<zoom>0</zoom>" in request_body


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2SE4C425MWG-E-26"], indirect=True)
async def test_ptz_preset_action(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test sending PTZ preset request."""

    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Mark the camera as supporting PTZ
    device.cameras[0].support_ptz = True

    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/presets/5/goto"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_PTZ_PRESET,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "channel_id": 1,
            "preset_id": 5,
        },
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2SE4C425MWG-E-26"], indirect=True)
async def test_ptz_move_camera_not_found(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test PTZ move with non-existent camera."""

    mock_config_entry = init_integration

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            ACTION_PTZ_MOVE,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                "channel_id": 999,  # Non-existent channel
                "pan": 50,
            },
            blocking=True,
        )

    assert "not found" in str(exc_info.value)


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2SE4C425MWG-E-26"], indirect=True)
async def test_ptz_move_camera_no_ptz_support(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test PTZ move on camera without PTZ support."""

    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Ensure the camera does NOT support PTZ
    device.cameras[0].support_ptz = False

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            ACTION_PTZ_MOVE,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                "channel_id": 1,
                "pan": 50,
            },
            blocking=True,
        )

    assert "does not support PTZ" in str(exc_info.value)


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2SE4C425MWG-E-26"], indirect=True)
async def test_ptz_preset_camera_not_found(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test PTZ preset with non-existent camera."""

    mock_config_entry = init_integration

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            ACTION_PTZ_PRESET,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                "channel_id": 999,  # Non-existent channel
                "preset_id": 1,
            },
            blocking=True,
        )

    assert "not found" in str(exc_info.value)


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2SE4C425MWG-E-26"], indirect=True)
async def test_ptz_preset_camera_no_ptz_support(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test PTZ preset on camera without PTZ support."""

    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Ensure the camera does NOT support PTZ
    device.cameras[0].support_ptz = False

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            ACTION_PTZ_PRESET,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                "channel_id": 1,
                "preset_id": 1,
            },
            blocking=True,
        )

    assert "does not support PTZ" in str(exc_info.value)


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2SE4C425MWG-E-26"], indirect=True)
async def test_ptz_move_negative_values(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test PTZ move with negative values (left/down/wide)."""

    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # Mark the camera as supporting PTZ
    device.cameras[0].support_ptz = True

    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/continuous"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_PTZ_MOVE,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "channel_id": 1,
            "pan": -100,
            "tilt": -50,
            "zoom": -25,
        },
        blocking=True,
    )

    assert endpoint.called
    request_body = endpoint.calls.last.request.content.decode()
    assert "<pan>-100</pan>" in request_body
    assert "<tilt>-50</tilt>" in request_body
    assert "<zoom>-25</zoom>" in request_body


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_ptz_move_nvr_camera(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test PTZ move on an NVR connected camera."""

    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # NVR has multiple cameras - mark the first one as supporting PTZ
    if len(device.cameras) > 0:
        device.cameras[0].support_ptz = True
        camera_id = device.cameras[0].id

        url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/{camera_id}/continuous"
        endpoint = respx.put(url).respond()

        await hass.services.async_call(
            DOMAIN,
            ACTION_PTZ_MOVE,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                "channel_id": camera_id,
                "pan": 30,
                "tilt": 20,
            },
            blocking=True,
        )

        assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_ptz_preset_nvr_camera(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test PTZ preset on an NVR connected camera."""

    mock_config_entry = init_integration
    device = mock_config_entry.runtime_data

    # NVR has multiple cameras - mark the first one as supporting PTZ
    if len(device.cameras) > 0:
        device.cameras[0].support_ptz = True
        camera_id = device.cameras[0].id

        url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/{camera_id}/presets/10/goto"
        endpoint = respx.put(url).respond()

        await hass.services.async_call(
            DOMAIN,
            ACTION_PTZ_PRESET,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                "channel_id": camera_id,
                "preset_id": 10,
            },
            blocking=True,
        )

        assert endpoint.called
