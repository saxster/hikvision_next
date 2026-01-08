"""Tests for actions."""

import pytest
import respx
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.hikvision_next.const import (
    ACTION_PTZ_GOTO_PRESET,
    ACTION_PTZ_SET_PATROL,
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
@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_ptz_goto_preset_action(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test sending PTZ go to preset request."""

    mock_config_entry = init_integration

    # Test going to preset 1 on channel 1
    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/presets/1/goto"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_PTZ_GOTO_PRESET,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "channel_id": 1,
            "preset_id": 1,
        },
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_ptz_goto_preset_action_different_preset(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test sending PTZ go to preset request with different preset number."""

    mock_config_entry = init_integration

    # Test going to preset 5 on channel 2
    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/2/presets/5/goto"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_PTZ_GOTO_PRESET,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "channel_id": 2,
            "preset_id": 5,
        },
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_ptz_set_patrol_start_action(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test sending PTZ start patrol request."""

    mock_config_entry = init_integration

    # Test starting patrol 1 on channel 1
    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/patrols/1/status"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_PTZ_SET_PATROL,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "channel_id": 1,
            "patrol_id": 1,
            "enabled": True,
        },
        blocking=True,
    )

    assert endpoint.called
    # Verify the request body contains start status
    request_content = endpoint.calls[0].request.content.decode("utf-8")
    assert "<enabled>true</enabled>" in request_content
    assert "<status>start</status>" in request_content


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_ptz_set_patrol_stop_action(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test sending PTZ stop patrol request."""

    mock_config_entry = init_integration

    # Test stopping patrol 1 on channel 1
    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/patrols/1/status"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_PTZ_SET_PATROL,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "channel_id": 1,
            "patrol_id": 1,
            "enabled": False,
        },
        blocking=True,
    )

    assert endpoint.called
    # Verify the request body contains stop status
    request_content = endpoint.calls[0].request.content.decode("utf-8")
    assert "<enabled>false</enabled>" in request_content
    assert "<status>stop</status>" in request_content


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_ptz_set_patrol_different_channel_patrol(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test sending PTZ patrol request with different channel and patrol numbers."""

    mock_config_entry = init_integration

    # Test starting patrol 3 on channel 2
    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/2/patrols/3/status"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_PTZ_SET_PATROL,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "channel_id": 2,
            "patrol_id": 3,
            "enabled": True,
        },
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2SE4C425MWG-E-26"], indirect=True)
async def test_ptz_goto_preset_on_ptz_camera(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test sending PTZ go to preset request on actual PTZ camera (DS-2SE4C425MWG-E-26)."""

    mock_config_entry = init_integration

    # Test going to preset 1 on channel 1 (PTZ channel)
    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/presets/1/goto"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_PTZ_GOTO_PRESET,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "channel_id": 1,
            "preset_id": 1,
        },
        blocking=True,
    )

    assert endpoint.called


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-2SE4C425MWG-E-26"], indirect=True)
async def test_ptz_set_patrol_on_ptz_camera(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test sending PTZ patrol request on actual PTZ camera (DS-2SE4C425MWG-E-26)."""

    mock_config_entry = init_integration

    # Test starting patrol 1 on channel 1 (PTZ channel)
    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/patrols/1/status"
    endpoint = respx.put(url).respond()

    await hass.services.async_call(
        DOMAIN,
        ACTION_PTZ_SET_PATROL,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            "channel_id": 1,
            "patrol_id": 1,
            "enabled": True,
        },
        blocking=True,
    )

    assert endpoint.called
    request_content = endpoint.calls[0].request.content.decode("utf-8")
    assert "<enabled>true</enabled>" in request_content
    assert "<status>start</status>" in request_content
