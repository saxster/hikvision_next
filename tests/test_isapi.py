"""Tests for specific ISAPI responses."""

import respx
import httpx
from contextlib import suppress
from custom_components.hikvision_next.isapi import StorageInfo, PTZPresetInfo
from tests.conftest import mock_endpoint, load_fixture, TEST_HOST


@respx.mock
async def test_storage(mock_isapi):
    isapi = mock_isapi

    mock_endpoint("ContentMgmt/Storage", "hdd1")
    storage_list = await isapi.get_storage_devices()
    assert len(storage_list) == 1
    assert storage_list[0] == StorageInfo(
        id=1,
        name="hdd1",
        type="SATA",
        status="ok",
        capacity=1907729,
        freespace=0,
        property="RW",
        ip="",
    )

    mock_endpoint("ContentMgmt/Storage", "hdd1_nas1")
    storage_list = await isapi.get_storage_devices()
    assert len(storage_list) == 2
    assert storage_list[0].type == "SATA"
    assert storage_list[1].type == "NFS"
    assert storage_list[1].ip != ""

    mock_endpoint("ContentMgmt/Storage", status_code=500)
    with suppress(Exception):
        storage_list = await isapi.get_storage_devices()
        assert len(storage_list) == 0


@respx.mock
async def test_notification_hosts(mock_isapi):
    isapi = mock_isapi

    mock_endpoint("Event/notification/httpHosts", "nvr_single_item")
    host_nvr = await isapi.get_alarm_server()

    mock_endpoint("Event/notification/httpHosts", "ipc_list")
    host_ipc = await isapi.get_alarm_server()

    assert host_nvr == host_ipc


@respx.mock
async def test_update_notification_hosts(mock_isapi):
    isapi = mock_isapi

    def update_side_effect(request, route):
        payload = load_fixture("ISAPI/Event.notification.httpHosts", "set_alarm_server_payload")
        if request.content.decode("utf-8") != payload:
            raise AssertionError("Request content does not match expected payload")
        return httpx.Response(200)

    mock_endpoint("Event/notification/httpHosts", "nvr_single_item")
    url = f"{isapi.host}/ISAPI/Event/notification/httpHosts"
    endpoint = respx.put(url).mock(side_effect=update_side_effect)
    await isapi.set_alarm_server("http://1.0.0.11:8123", "/api/hikvision")

    assert endpoint.called


@respx.mock
async def test_update_notification_hosts_from_ipaddress_to_hostname(mock_isapi):
    isapi = mock_isapi

    def update_side_effect(request, route):
        payload = load_fixture("ISAPI/Event.notification.httpHosts", "set_alarm_server_outside_network_payload")
        if request.content.decode("utf-8") != payload:
            raise AssertionError("Request content does not match expected payload")
        return httpx.Response(200)

    mock_endpoint("Event/notification/httpHosts", "nvr_single_item")
    url = f"{isapi.host}/ISAPI/Event/notification/httpHosts"
    endpoint = respx.put(url).mock(side_effect=update_side_effect)
    await isapi.set_alarm_server("https://ha.hostname.domain", "/api/hikvision")

    assert endpoint.called


@respx.mock
async def test_ptz_support_check(mock_isapi):
    """Test checking PTZ support for a channel."""
    isapi = mock_isapi

    # Enable device-level PTZ support
    isapi.capabilities.support_ptz = True

    # Test when PTZ is supported (endpoint returns valid response)
    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/capabilities").respond(
        text="""<?xml version="1.0" encoding="UTF-8"?>
        <PTZChannel>
            <id>1</id>
            <enabled>true</enabled>
        </PTZChannel>"""
    )
    result = await isapi.get_ptz_support(1)
    assert result is True

    # Test when PTZ is not supported (endpoint returns error)
    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/2/capabilities").respond(status_code=404)
    result = await isapi.get_ptz_support(2)
    assert result is False


@respx.mock
async def test_ptz_support_check_device_not_supported(mock_isapi):
    """Test PTZ support check when device doesn't support PTZ at all."""
    isapi = mock_isapi

    # Device-level PTZ support disabled
    isapi.capabilities.support_ptz = False

    result = await isapi.get_ptz_support(1)
    assert result is False


@respx.mock
async def test_get_ptz_presets(mock_isapi):
    """Test getting PTZ presets."""
    isapi = mock_isapi

    # Mock the presets endpoint
    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/presets").respond(
        text="""<?xml version="1.0" encoding="UTF-8"?>
        <PTZPresetList>
            <PTZPreset>
                <id>1</id>
                <presetName>Home</presetName>
                <enabled>true</enabled>
            </PTZPreset>
            <PTZPreset>
                <id>2</id>
                <presetName>Driveway</presetName>
                <enabled>true</enabled>
            </PTZPreset>
            <PTZPreset>
                <id>3</id>
                <presetName>Backyard</presetName>
                <enabled>false</enabled>
            </PTZPreset>
        </PTZPresetList>"""
    )

    presets = await isapi.get_ptz_presets(1)

    assert len(presets) == 3
    assert presets[0] == PTZPresetInfo(id=1, name="Home", enabled=True)
    assert presets[1] == PTZPresetInfo(id=2, name="Driveway", enabled=True)
    assert presets[2] == PTZPresetInfo(id=3, name="Backyard", enabled=False)


@respx.mock
async def test_get_ptz_presets_empty(mock_isapi):
    """Test getting PTZ presets when none exist."""
    isapi = mock_isapi

    # Mock the presets endpoint with empty list
    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/presets").respond(
        text="""<?xml version="1.0" encoding="UTF-8"?>
        <PTZPresetList>
        </PTZPresetList>"""
    )

    presets = await isapi.get_ptz_presets(1)
    assert len(presets) == 0


@respx.mock
async def test_get_ptz_presets_error(mock_isapi):
    """Test getting PTZ presets when endpoint returns an error."""
    isapi = mock_isapi

    # Mock the presets endpoint with error
    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/presets").respond(status_code=404)

    presets = await isapi.get_ptz_presets(1)
    assert len(presets) == 0


@respx.mock
async def test_ptz_move(mock_isapi):
    """Test PTZ continuous movement."""
    isapi = mock_isapi

    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/continuous"
    endpoint = respx.put(url).respond()

    await isapi.ptz_move(1, pan=50, tilt=30, zoom=10)

    assert endpoint.called
    request_body = endpoint.calls.last.request.content.decode()
    assert "<pan>50</pan>" in request_body
    assert "<tilt>30</tilt>" in request_body
    assert "<zoom>10</zoom>" in request_body


@respx.mock
async def test_ptz_move_negative_values(mock_isapi):
    """Test PTZ movement with negative values."""
    isapi = mock_isapi

    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/continuous"
    endpoint = respx.put(url).respond()

    await isapi.ptz_move(1, pan=-100, tilt=-50, zoom=-25)

    assert endpoint.called
    request_body = endpoint.calls.last.request.content.decode()
    assert "<pan>-100</pan>" in request_body
    assert "<tilt>-50</tilt>" in request_body
    assert "<zoom>-25</zoom>" in request_body


@respx.mock
async def test_ptz_stop(mock_isapi):
    """Test PTZ stop (all values set to 0)."""
    isapi = mock_isapi

    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/continuous"
    endpoint = respx.put(url).respond()

    await isapi.ptz_stop(1)

    assert endpoint.called
    request_body = endpoint.calls.last.request.content.decode()
    assert "<pan>0</pan>" in request_body
    assert "<tilt>0</tilt>" in request_body
    assert "<zoom>0</zoom>" in request_body


@respx.mock
async def test_ptz_goto_preset(mock_isapi):
    """Test PTZ go to preset."""
    isapi = mock_isapi

    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/presets/5/goto"
    endpoint = respx.put(url).respond()

    await isapi.ptz_goto_preset(1, 5)

    assert endpoint.called


@respx.mock
async def test_ptz_goto_preset_different_channel(mock_isapi):
    """Test PTZ go to preset on different channel."""
    isapi = mock_isapi

    url = f"{TEST_HOST}/ISAPI/PTZCtrl/channels/3/presets/10/goto"
    endpoint = respx.put(url).respond()

    await isapi.ptz_goto_preset(3, 10)

    assert endpoint.called


@respx.mock
async def test_get_ptz_presets_single_preset(mock_isapi):
    """Test getting PTZ presets when only one preset exists."""
    isapi = mock_isapi

    # Mock the presets endpoint with single preset (not in a list)
    respx.get(f"{TEST_HOST}/ISAPI/PTZCtrl/channels/1/presets").respond(
        text="""<?xml version="1.0" encoding="UTF-8"?>
        <PTZPresetList>
            <PTZPreset>
                <id>1</id>
                <presetName>Home</presetName>
                <enabled>true</enabled>
            </PTZPreset>
        </PTZPresetList>"""
    )

    presets = await isapi.get_ptz_presets(1)

    assert len(presets) == 1
    assert presets[0] == PTZPresetInfo(id=1, name="Home", enabled=True)
