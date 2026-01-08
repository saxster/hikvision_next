"""Tests for PTZ presets and patrol mode."""

import pytest
import respx
import httpx
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN, SERVICE_SELECT_OPTION
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN, SERVICE_TURN_ON, SERVICE_TURN_OFF
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON, STATE_OFF
import homeassistant.helpers.entity_registry as er
from tests.conftest import TEST_HOST


@pytest.mark.parametrize("init_integration", ["DS-2SE4C425MWG-E-26"], indirect=True)
async def test_ptz_preset_select_entity_not_created_without_ptz(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test PTZ preset select entity is not created when no presets are available."""
    # The DS-2SE4C425MWG-E-26 fixture doesn't have PTZ preset endpoints mocked
    # so no PTZ presets will be found, and no select entity should be created
    entity_id = "select.ds_2se4c425mwg_e_0000000000aawrfc0000000_ptz_preset"
    assert hass.states.get(entity_id) is None


@pytest.mark.parametrize("init_integration", ["DS-2SE4C425MWG-E-26"], indirect=True)
async def test_ptz_patrol_switch_not_created_without_patrols(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test PTZ patrol switch is not created when no patrols are available."""
    # Check that no patrol switch exists for the camera
    entity_registry = er.async_get(hass)
    entities = [
        entity for entity in entity_registry.entities.values()
        if "ptz_patrol" in entity.entity_id
    ]
    assert len(entities) == 0


@respx.mock
@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_ptz_capabilities_detection(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that PTZ capabilities are correctly detected from device."""
    device = init_integration.runtime_data

    # The fixture doesn't include PTZ endpoints, so all cameras should have PTZ disabled
    for camera in device.cameras:
        assert camera.ptz_info.is_supported is False
        assert len(camera.ptz_info.presets) == 0
        assert len(camera.ptz_info.patrols) == 0


@respx.mock
async def test_ptz_info_parsing(hass: HomeAssistant, mock_isapi) -> None:
    """Test PTZ info parsing from ISAPI responses."""
    from custom_components.hikvision_next.isapi import ISAPIClient

    isapi: ISAPIClient = mock_isapi

    # Mock PTZ capabilities endpoint
    ptz_capabilities_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <PTZChannelCap version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
        <AbsolutePanTiltPositionSpace>
            <isSupport>true</isSupport>
        </AbsolutePanTiltPositionSpace>
        <RelativePanTiltPositionSpace>
            <isSupport>true</isSupport>
        </RelativePanTiltPositionSpace>
        <ContinuousPanTiltVelocitySpace>
            <isSupport>true</isSupport>
        </ContinuousPanTiltVelocitySpace>
    </PTZChannelCap>"""

    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/capabilities").respond(
        text=ptz_capabilities_xml
    )

    # Mock PTZ presets endpoint
    ptz_presets_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <PTZPresetList version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
        <PTZPreset>
            <id>1</id>
            <presetName>Front Gate</presetName>
            <enabled>true</enabled>
        </PTZPreset>
        <PTZPreset>
            <id>2</id>
            <presetName>Driveway</presetName>
            <enabled>true</enabled>
        </PTZPreset>
        <PTZPreset>
            <id>3</id>
            <presetName></presetName>
            <enabled>true</enabled>
        </PTZPreset>
    </PTZPresetList>"""

    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/presets").respond(
        text=ptz_presets_xml
    )

    # Mock PTZ patrols endpoint
    ptz_patrols_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <PTZPatrolList version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
        <PTZPatrol>
            <id>1</id>
            <patrolName>Perimeter Patrol</patrolName>
            <enabled>true</enabled>
        </PTZPatrol>
        <PTZPatrol>
            <id>2</id>
            <patrolName>Night Watch</patrolName>
            <enabled>true</enabled>
        </PTZPatrol>
    </PTZPatrolList>"""

    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/patrols").respond(
        text=ptz_patrols_xml
    )

    ptz_info = await isapi.get_ptz_info(1)

    # Verify PTZ capabilities
    assert ptz_info.is_supported is True
    assert ptz_info.absolute_move is True
    assert ptz_info.relative_move is True
    assert ptz_info.continuous_move is True

    # Verify presets (only named presets should be included)
    assert len(ptz_info.presets) == 2
    assert ptz_info.presets[0].id == 1
    assert ptz_info.presets[0].name == "Front Gate"
    assert ptz_info.presets[1].id == 2
    assert ptz_info.presets[1].name == "Driveway"

    # Verify patrols
    assert len(ptz_info.patrols) == 2
    assert ptz_info.patrols[0].id == 1
    assert ptz_info.patrols[0].name == "Perimeter Patrol"
    assert ptz_info.patrols[1].id == 2
    assert ptz_info.patrols[1].name == "Night Watch"


@respx.mock
async def test_goto_ptz_preset(hass: HomeAssistant, mock_isapi) -> None:
    """Test going to a PTZ preset."""
    from custom_components.hikvision_next.isapi import ISAPIClient

    isapi: ISAPIClient = mock_isapi

    # Mock the goto preset endpoint with a proper XML response
    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/presets/1/goto"
    endpoint = respx.put(url).respond(
        text='<?xml version="1.0" encoding="UTF-8"?><ResponseStatus><statusCode>1</statusCode><statusString>OK</statusString></ResponseStatus>'
    )

    await isapi.goto_ptz_preset(1, 1)

    assert endpoint.called


@respx.mock
async def test_start_stop_ptz_patrol(hass: HomeAssistant, mock_isapi) -> None:
    """Test starting and stopping PTZ patrol."""
    from custom_components.hikvision_next.isapi import ISAPIClient

    isapi: ISAPIClient = mock_isapi

    # Mock the start patrol endpoint
    start_url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/patrols/1/start"
    start_endpoint = respx.put(start_url).respond(
        text='<?xml version="1.0" encoding="UTF-8"?><ResponseStatus><statusCode>1</statusCode><statusString>OK</statusString></ResponseStatus>'
    )

    await isapi.start_ptz_patrol(1, 1)
    assert start_endpoint.called

    # Mock the stop patrol endpoint
    stop_url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/patrols/1/stop"
    stop_endpoint = respx.put(stop_url).respond(
        text='<?xml version="1.0" encoding="UTF-8"?><ResponseStatus><statusCode>1</statusCode><statusString>OK</statusString></ResponseStatus>'
    )

    await isapi.stop_ptz_patrol(1, 1)
    assert stop_endpoint.called


@respx.mock
async def test_get_ptz_patrol_status(hass: HomeAssistant, mock_isapi) -> None:
    """Test getting PTZ patrol status."""
    from custom_components.hikvision_next.isapi import ISAPIClient

    isapi: ISAPIClient = mock_isapi

    # Mock running status
    status_xml_running = """<?xml version="1.0" encoding="UTF-8"?>
    <PTZStatus version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
        <patrolStatus>running</patrolStatus>
    </PTZStatus>"""

    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/patrols/1/status").respond(
        text=status_xml_running
    )

    status = await isapi.get_ptz_patrol_status(1, 1)
    assert status is True

    # Mock idle status
    status_xml_idle = """<?xml version="1.0" encoding="UTF-8"?>
    <PTZStatus version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
        <patrolStatus>idle</patrolStatus>
    </PTZStatus>"""

    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/patrols/1/status").respond(
        text=status_xml_idle
    )

    status = await isapi.get_ptz_patrol_status(1, 1)
    assert status is False


@respx.mock
async def test_ptz_presets_single_preset(hass: HomeAssistant, mock_isapi) -> None:
    """Test PTZ presets parsing with a single preset."""
    from custom_components.hikvision_next.isapi import ISAPIClient

    isapi: ISAPIClient = mock_isapi

    # Single preset returns as a dict, not a list
    ptz_presets_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <PTZPresetList version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
        <PTZPreset>
            <id>1</id>
            <presetName>Front Gate</presetName>
            <enabled>true</enabled>
        </PTZPreset>
    </PTZPresetList>"""

    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/presets").respond(
        text=ptz_presets_xml
    )

    presets = await isapi.get_ptz_presets(1)

    assert len(presets) == 1
    assert presets[0].id == 1
    assert presets[0].name == "Front Gate"


@respx.mock
async def test_ptz_patrols_single_patrol(hass: HomeAssistant, mock_isapi) -> None:
    """Test PTZ patrols parsing with a single patrol."""
    from custom_components.hikvision_next.isapi import ISAPIClient

    isapi: ISAPIClient = mock_isapi

    # Single patrol returns as a dict, not a list
    ptz_patrols_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <PTZPatrolList version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
        <PTZPatrol>
            <id>1</id>
            <patrolName>Perimeter Patrol</patrolName>
            <enabled>true</enabled>
        </PTZPatrol>
    </PTZPatrolList>"""

    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/patrols").respond(
        text=ptz_patrols_xml
    )

    patrols = await isapi.get_ptz_patrols(1)

    assert len(patrols) == 1
    assert patrols[0].id == 1
    assert patrols[0].name == "Perimeter Patrol"


@respx.mock
async def test_ptz_empty_responses(hass: HomeAssistant, mock_isapi) -> None:
    """Test handling empty PTZ responses."""
    from custom_components.hikvision_next.isapi import ISAPIClient

    isapi: ISAPIClient = mock_isapi

    # Empty presets response (404)
    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/presets").respond(status_code=404)

    presets = await isapi.get_ptz_presets(1)
    assert len(presets) == 0

    # Empty patrols response (404)
    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/patrols").respond(status_code=404)

    patrols = await isapi.get_ptz_patrols(1)
    assert len(patrols) == 0


@respx.mock
async def test_ptz_info_no_capabilities(hass: HomeAssistant, mock_isapi) -> None:
    """Test PTZ info when PTZ is not supported."""
    from custom_components.hikvision_next.isapi import ISAPIClient

    isapi: ISAPIClient = mock_isapi

    # PTZ capabilities endpoint returns 404 (not supported)
    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/capabilities").respond(status_code=404)

    ptz_info = await isapi.get_ptz_info(1)

    assert ptz_info.is_supported is False
    assert ptz_info.absolute_move is False
    assert ptz_info.relative_move is False
    assert ptz_info.continuous_move is False
    assert len(ptz_info.presets) == 0
    assert len(ptz_info.patrols) == 0
