"""Test target-specific detection (Person/Vehicle) binary sensors."""

import pytest
from http import HTTPStatus
from homeassistant.core import HomeAssistant, Event
from custom_components.hikvision_next.notifications import EventNotificationsView
from custom_components.hikvision_next.const import HIKVISION_EVENT
from pytest_homeassistant_custom_component.common import MockConfigEntry
from unittest.mock import MagicMock
from tests.conftest import load_fixture, TEST_HOST_IP, TEST_CONFIG
from homeassistant.const import (
    STATE_ON,
    STATE_OFF
)
from custom_components.hikvision_next.hikvision_device import HikvisionDevice


def mock_event_notification(file) -> MagicMock:
    """Mock incoming event notification request."""

    mock_request = MagicMock()
    mock_request.headers = {
        'Content-Type': 'application/xml; charset="UTF-8"',
    }
    mock_request.remote = TEST_HOST_IP
    async def read():
        payload = load_fixture("ISAPI/EventNotificationAlert", file)
        return payload.encode()
    mock_request.read = read
    return mock_request


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_target_specific_entities_created(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that target-specific binary sensors are created for supported events."""

    device: HikvisionDevice = init_integration.runtime_data

    # Check that fielddetection creates generic + person + vehicle sensors
    fielddetection_events = [e for e in device.cameras[0].events_info if e.id == "fielddetection"]
    assert len(fielddetection_events) == 3  # generic, human, vehicle

    # Check unique_ids
    unique_ids = [e.unique_id for e in fielddetection_events]
    base_unique_id = "ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection"
    assert base_unique_id in unique_ids
    assert f"{base_unique_id}_human" in unique_ids
    assert f"{base_unique_id}_vehicle" in unique_ids

    # Check detection_target values
    targets = [e.detection_target for e in fielddetection_events]
    assert None in targets  # generic
    assert "human" in targets
    assert "vehicle" in targets


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_target_specific_linedetection_entities(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that target-specific binary sensors are created for linedetection events."""

    device: HikvisionDevice = init_integration.runtime_data

    # Check that linedetection creates generic + person + vehicle sensors
    linedetection_events = [e for e in device.cameras[0].events_info if e.id == "linedetection"]
    assert len(linedetection_events) == 3  # generic, human, vehicle

    # Check detection_target values
    targets = [e.detection_target for e in linedetection_events]
    assert None in targets  # generic
    assert "human" in targets
    assert "vehicle" in targets


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_human_detection_triggers_person_sensor(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that human detection triggers both generic and person-specific sensors."""

    # Entity IDs
    generic_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection"
    person_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_human"
    vehicle_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_vehicle"

    # Check initial states are OFF
    assert (sensor := hass.states.get(generic_entity_id))
    assert sensor.state == STATE_OFF
    assert (sensor := hass.states.get(person_entity_id))
    assert sensor.state == STATE_OFF
    assert (sensor := hass.states.get(vehicle_entity_id))
    assert sensor.state == STATE_OFF

    # Send human detection event
    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("fielddetection_human")
    response = await view.post(mock_request)

    assert response.status == HTTPStatus.OK

    # Generic sensor should be triggered
    assert (sensor := hass.states.get(generic_entity_id))
    assert sensor.state == STATE_ON

    # Person-specific sensor should be triggered
    assert (sensor := hass.states.get(person_entity_id))
    assert sensor.state == STATE_ON

    # Vehicle-specific sensor should NOT be triggered
    assert (sensor := hass.states.get(vehicle_entity_id))
    assert sensor.state == STATE_OFF


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_vehicle_detection_triggers_vehicle_sensor(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that vehicle detection triggers both generic and vehicle-specific sensors."""

    # Entity IDs
    generic_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection"
    person_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_human"
    vehicle_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_vehicle"

    # Check initial states are OFF
    assert (sensor := hass.states.get(generic_entity_id))
    assert sensor.state == STATE_OFF
    assert (sensor := hass.states.get(person_entity_id))
    assert sensor.state == STATE_OFF
    assert (sensor := hass.states.get(vehicle_entity_id))
    assert sensor.state == STATE_OFF

    # Send vehicle detection event
    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("fielddetection_vehicle")
    response = await view.post(mock_request)

    assert response.status == HTTPStatus.OK

    # Generic sensor should be triggered
    assert (sensor := hass.states.get(generic_entity_id))
    assert sensor.state == STATE_ON

    # Vehicle-specific sensor should be triggered
    assert (sensor := hass.states.get(vehicle_entity_id))
    assert sensor.state == STATE_ON

    # Person-specific sensor should NOT be triggered
    assert (sensor := hass.states.get(person_entity_id))
    assert sensor.state == STATE_OFF


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_hass_event_includes_detection_target(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that HASS events include detection_target for target-specific detections."""

    bus_events = []
    def bus_event_listener(event: Event) -> None:
        bus_events.append(event)
    hass.bus.async_listen(HIKVISION_EVENT, bus_event_listener)

    # Send human detection event
    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("fielddetection_human")
    await view.post(mock_request)

    await hass.async_block_till_done()
    assert len(bus_events) == 1
    data = bus_events[0].data
    assert data["event_id"] == "fielddetection"
    assert data["detection_target"] == "human"
    assert data["region_id"] == 3

    # Clear events and send vehicle detection
    bus_events.clear()
    mock_request = mock_event_notification("fielddetection_vehicle")
    await view.post(mock_request)

    await hass.async_block_till_done()
    assert len(bus_events) == 1
    data = bus_events[0].data
    assert data["event_id"] == "fielddetection"
    assert data["detection_target"] == "vehicle"
    assert data["region_id"] == 2


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_regionentrance_and_regionexiting_entities(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that regionentrance and regionexiting also have target-specific sensors."""

    device: HikvisionDevice = init_integration.runtime_data

    # Check that regionentrance creates generic + person + vehicle sensors
    regionentrance_events = [e for e in device.cameras[0].events_info if e.id == "regionentrance"]
    assert len(regionentrance_events) == 3  # generic, human, vehicle

    # Check that regionexiting creates generic + person + vehicle sensors
    regionexiting_events = [e for e in device.cameras[0].events_info if e.id == "regionexiting"]
    assert len(regionexiting_events) == 3  # generic, human, vehicle


@pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
async def test_motiondetection_no_target_specific_sensors(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that motiondetection does not create target-specific sensors."""

    device: HikvisionDevice = init_integration.runtime_data

    # Motion detection should only have generic sensor (no target detection support)
    motiondetection_events = [e for e in device.cameras[0].events_info if e.id == "motiondetection"]
    assert len(motiondetection_events) == 1
    assert motiondetection_events[0].detection_target is None


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_binary_sensor_entity_ids_format(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that binary sensor entity IDs follow the expected format."""

    # Check that person and vehicle sensors have proper entity IDs
    person_entity = hass.states.get("binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_human")
    assert person_entity is not None
    assert person_entity.state == STATE_OFF

    vehicle_entity = hass.states.get("binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_vehicle")
    assert vehicle_entity is not None
    assert vehicle_entity.state == STATE_OFF


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_nvr_target_specific_sensors(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test target-specific sensors on NVR cameras."""

    device: HikvisionDevice = init_integration.runtime_data

    # NVR cameras should also have target-specific sensors for fielddetection
    for camera in device.cameras:
        fielddetection_events = [e for e in camera.events_info if e.id == "fielddetection"]
        # If camera supports fielddetection, it should have 3 events (generic + human + vehicle)
        if fielddetection_events:
            assert len(fielddetection_events) == 3


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_event_without_detection_target_only_triggers_generic(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that events without detection_target only trigger generic sensor."""

    # Entity IDs
    generic_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection"
    person_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_human"
    vehicle_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_vehicle"

    # Check initial states are OFF
    assert (sensor := hass.states.get(generic_entity_id))
    assert sensor.state == STATE_OFF
    assert (sensor := hass.states.get(person_entity_id))
    assert sensor.state == STATE_OFF
    assert (sensor := hass.states.get(vehicle_entity_id))
    assert sensor.state == STATE_OFF

    # Send generic intrusion detection event (from IPC)
    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("ipc_1_fielddetection")
    response = await view.post(mock_request)

    assert response.status == HTTPStatus.OK

    # Generic sensor should be triggered
    assert (sensor := hass.states.get(generic_entity_id))
    assert sensor.state == STATE_ON

    # Person and vehicle sensors should NOT be triggered (no detection_target in event)
    assert (sensor := hass.states.get(person_entity_id))
    assert sensor.state == STATE_OFF
    assert (sensor := hass.states.get(vehicle_entity_id))
    assert sensor.state == STATE_OFF
