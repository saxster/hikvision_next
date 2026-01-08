"""Tests for target-specific binary sensors (Person and Vehicle detection)."""

import pytest
from http import HTTPStatus
from homeassistant.core import HomeAssistant, Event
from homeassistant.const import STATE_ON, STATE_OFF
from custom_components.hikvision_next.notifications import EventNotificationsView
from custom_components.hikvision_next.const import HIKVISION_EVENT
from custom_components.hikvision_next.hikvision_device import HikvisionDevice
from custom_components.hikvision_next.isapi.const import DETECTION_TARGETS, EVENTS_WITH_TARGET_DETECTION
from pytest_homeassistant_custom_component.common import MockConfigEntry
from unittest.mock import MagicMock
from tests.conftest import load_fixture, TEST_HOST_IP


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


def setup_bus_event_listener(hass: HomeAssistant) -> list[Event]:
    """Set up bus event listener and return events list."""
    bus_events = []

    def bus_event_listener(event: Event) -> None:
        bus_events.append(event)
    hass.bus.async_listen(HIKVISION_EVENT, bus_event_listener)
    return bus_events


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_target_specific_sensors_created(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that target-specific (person/vehicle) binary sensors are created for smart events."""

    device: HikvisionDevice = init_integration.runtime_data

    # Check that target-specific events are created for camera events
    camera = device.cameras[0]

    # Count events by type
    generic_events = [e for e in camera.events_info if e.detection_target is None]
    human_events = [e for e in camera.events_info if e.detection_target == "human"]
    vehicle_events = [e for e in camera.events_info if e.detection_target == "vehicle"]

    # For events in EVENTS_WITH_TARGET_DETECTION, there should be 3 entities: generic, human, vehicle
    smart_events_with_targets = [e for e in generic_events if e.id in EVENTS_WITH_TARGET_DETECTION]

    # Each smart event with target detection should have corresponding human and vehicle events
    for smart_event in smart_events_with_targets:
        human_matches = [e for e in human_events if e.id == smart_event.id and e.channel_id == smart_event.channel_id]
        vehicle_matches = [e for e in vehicle_events if e.id == smart_event.id and e.channel_id == smart_event.channel_id]
        assert len(human_matches) == 1, f"Expected 1 human event for {smart_event.id}, got {len(human_matches)}"
        assert len(vehicle_matches) == 1, f"Expected 1 vehicle event for {smart_event.id}, got {len(vehicle_matches)}"


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_person_sensor_entity_exists(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that person detection binary sensor entity is created."""

    # DS-2CD2146G2-ISU has fielddetection on channel 1
    entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_human"

    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_vehicle_sensor_entity_exists(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that vehicle detection binary sensor entity is created."""

    # DS-2CD2146G2-ISU has fielddetection on channel 1
    entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_vehicle"

    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_generic_sensor_still_exists(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that the generic (non-target-specific) binary sensor still exists."""

    # DS-2CD2146G2-ISU has fielddetection on channel 1
    entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection"

    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_person_detection_triggers_person_sensor(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that a person detection event triggers both generic and person-specific sensors."""

    generic_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection"
    person_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_human"
    vehicle_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_vehicle"

    bus_events = setup_bus_event_listener(hass)

    # Verify initial states
    assert (generic_sensor := hass.states.get(generic_entity_id))
    assert generic_sensor.state == STATE_OFF
    assert (person_sensor := hass.states.get(person_entity_id))
    assert person_sensor.state == STATE_OFF
    assert (vehicle_sensor := hass.states.get(vehicle_entity_id))
    assert vehicle_sensor.state == STATE_OFF

    # Send person detection event (fielddetection with detectionTarget="human")
    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("fielddetection_human")
    response = await view.post(mock_request)

    assert response.status == HTTPStatus.OK

    # Both generic and person sensors should be ON
    assert (generic_sensor := hass.states.get(generic_entity_id))
    assert generic_sensor.state == STATE_ON
    assert (person_sensor := hass.states.get(person_entity_id))
    assert person_sensor.state == STATE_ON
    # Vehicle sensor should still be OFF
    assert (vehicle_sensor := hass.states.get(vehicle_entity_id))
    assert vehicle_sensor.state == STATE_OFF

    await hass.async_block_till_done()

    # Verify bus event data
    assert len(bus_events) == 1
    data = bus_events[0].data
    assert data["event_id"] == "fielddetection"
    assert data["detection_target"] == "human"


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_vehicle_detection_triggers_vehicle_sensor(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that a vehicle detection event triggers both generic and vehicle-specific sensors."""

    generic_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection"
    person_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_human"
    vehicle_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection_vehicle"

    bus_events = setup_bus_event_listener(hass)

    # Verify initial states
    assert (generic_sensor := hass.states.get(generic_entity_id))
    assert generic_sensor.state == STATE_OFF
    assert (person_sensor := hass.states.get(person_entity_id))
    assert person_sensor.state == STATE_OFF
    assert (vehicle_sensor := hass.states.get(vehicle_entity_id))
    assert vehicle_sensor.state == STATE_OFF

    # Send vehicle detection event
    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("fielddetection_vehicle")
    response = await view.post(mock_request)

    assert response.status == HTTPStatus.OK

    # Both generic and vehicle sensors should be ON
    assert (generic_sensor := hass.states.get(generic_entity_id))
    assert generic_sensor.state == STATE_ON
    assert (vehicle_sensor := hass.states.get(vehicle_entity_id))
    assert vehicle_sensor.state == STATE_ON
    # Person sensor should still be OFF
    assert (person_sensor := hass.states.get(person_entity_id))
    assert person_sensor.state == STATE_OFF

    await hass.async_block_till_done()

    # Verify bus event data
    assert len(bus_events) == 1
    data = bus_events[0].data
    assert data["event_id"] == "fielddetection"
    assert data["detection_target"] == "vehicle"


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_linedetection_person_and_vehicle_sensors_exist(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that person and vehicle sensors are created for line detection."""

    # DS-2CD2146G2-ISU has linedetection on channel 1
    generic_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_linedetection"
    person_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_linedetection_human"
    vehicle_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_linedetection_vehicle"

    # All three entities should exist
    assert (sensor := hass.states.get(generic_entity_id))
    assert sensor.state == STATE_OFF

    assert (sensor := hass.states.get(person_entity_id))
    assert sensor.state == STATE_OFF

    assert (sensor := hass.states.get(vehicle_entity_id))
    assert sensor.state == STATE_OFF


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_regionentrance_person_and_vehicle_sensors_exist(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that person and vehicle sensors are created for region entrance detection."""

    # DS-2CD2146G2-ISU has regionentrance on channel 1
    generic_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_regionentrance"
    person_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_regionentrance_human"
    vehicle_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_regionentrance_vehicle"

    # All three entities should exist
    assert (sensor := hass.states.get(generic_entity_id))
    assert sensor.state == STATE_OFF

    assert (sensor := hass.states.get(person_entity_id))
    assert sensor.state == STATE_OFF

    assert (sensor := hass.states.get(vehicle_entity_id))
    assert sensor.state == STATE_OFF


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_regionexiting_person_and_vehicle_sensors_exist(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that person and vehicle sensors are created for region exiting detection."""

    # DS-2CD2146G2-ISU has regionexiting on channel 1
    generic_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_regionexiting"
    person_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_regionexiting_human"
    vehicle_entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_regionexiting_vehicle"

    # All three entities should exist
    assert (sensor := hass.states.get(generic_entity_id))
    assert sensor.state == STATE_OFF

    assert (sensor := hass.states.get(person_entity_id))
    assert sensor.state == STATE_OFF

    assert (sensor := hass.states.get(vehicle_entity_id))
    assert sensor.state == STATE_OFF


@pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
async def test_motion_detection_no_target_specific_sensors(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that motion detection (basic event) doesn't create target-specific sensors."""

    device: HikvisionDevice = init_integration.runtime_data

    # Motion detection is a basic event, not a smart event
    # It should not have target-specific variants
    camera = device.cameras[0]

    motion_events = [e for e in camera.events_info if e.id == "motiondetection"]

    # Motion detection should only have the generic event (no human/vehicle variants)
    assert len(motion_events) == 1
    assert motion_events[0].detection_target is None

    # The entity should exist
    entity_id = "binary_sensor.ds_2cd2386g2_iu00000000aawrj00000000_1_motiondetection"
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF

    # Human/vehicle variants should NOT exist
    human_entity_id = "binary_sensor.ds_2cd2386g2_iu00000000aawrj00000000_1_motiondetection_human"
    vehicle_entity_id = "binary_sensor.ds_2cd2386g2_iu00000000aawrj00000000_1_motiondetection_vehicle"
    assert hass.states.get(human_entity_id) is None
    assert hass.states.get(vehicle_entity_id) is None


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_event_info_unique_ids(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that target-specific events have correct unique IDs."""

    device: HikvisionDevice = init_integration.runtime_data
    camera = device.cameras[0]

    # Find fielddetection events
    fielddetection_events = [e for e in camera.events_info if e.id == "fielddetection"]

    # Should have 3 events: generic, human, vehicle
    assert len(fielddetection_events) == 3

    # Check unique IDs
    unique_ids = {e.unique_id for e in fielddetection_events}
    expected_prefix = "ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection"

    assert f"{expected_prefix}" in unique_ids
    assert f"{expected_prefix}_human" in unique_ids
    assert f"{expected_prefix}_vehicle" in unique_ids
