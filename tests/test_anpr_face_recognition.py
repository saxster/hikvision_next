"""Tests for ANPR (License Plate) and Face Recognition sensors."""

import pytest
from homeassistant.core import HomeAssistant, Event
from custom_components.hikvision_next.notifications import EventNotificationsView
from custom_components.hikvision_next.const import HIKVISION_EVENT
from custom_components.hikvision_next.isapi import ISAPIClient, AlertInfo
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


class TestANPREventParsing:
    """Test ANPR event notification parsing."""

    def test_parse_anpr_event(self):
        """Test parsing of ANPR event notification XML."""
        xml = load_fixture("ISAPI/EventNotificationAlert", "anpr_license_plate")
        alert = ISAPIClient.parse_event_notification(xml)

        assert alert.event_id == "vehicledetection"
        assert alert.channel_id == 1
        assert alert.license_plate == "ABC-1234"
        assert alert.plate_confidence == 95
        assert alert.plate_color == "white"
        assert alert.plate_type == "normal"
        assert alert.vehicle_color == "blue"

    def test_parse_anpr_event_minimal(self):
        """Test parsing of ANPR event with minimal data."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <EventNotificationAlert version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
          <channelID>2</channelID>
          <eventType>ANPR</eventType>
          <ANPR>
            <licensePlate>XYZ-9999</licensePlate>
            <confidenceLevel>80</confidenceLevel>
          </ANPR>
        </EventNotificationAlert>
        """
        alert = ISAPIClient.parse_event_notification(xml)

        assert alert.event_id == "vehicledetection"
        assert alert.channel_id == 2
        assert alert.license_plate == "XYZ-9999"
        assert alert.plate_confidence == 80
        assert alert.plate_color is None
        assert alert.plate_type is None


class TestFaceRecognitionEventParsing:
    """Test Face Recognition event notification parsing."""

    def test_parse_facedetection_event(self):
        """Test parsing of face detection event notification XML."""
        xml = load_fixture("ISAPI/EventNotificationAlert", "facedetection_recognized")
        alert = ISAPIClient.parse_event_notification(xml)

        assert alert.event_id == "facedetection"
        assert alert.channel_id == 1
        assert alert.person_name == "John Doe"
        assert alert.face_score == 98
        assert alert.person_id == "1001"

    def test_parse_facerecognition_alternative_format(self):
        """Test parsing of face recognition event with alternative XML format."""
        xml = load_fixture("ISAPI/EventNotificationAlert", "facerecognition_alternative")
        alert = ISAPIClient.parse_event_notification(xml)

        assert alert.event_id == "facedetection"
        assert alert.channel_id == 1
        assert alert.person_name == "Sarah Smith"
        assert alert.face_score == 96
        assert alert.person_id == "2002"

    def test_parse_facedetection_event_minimal(self):
        """Test parsing of face detection event with minimal data."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <EventNotificationAlert version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
          <channelID>3</channelID>
          <eventType>facedetection</eventType>
          <personName>Unknown Person</personName>
          <faceScore>75</faceScore>
        </EventNotificationAlert>
        """
        alert = ISAPIClient.parse_event_notification(xml)

        assert alert.event_id == "facedetection"
        assert alert.channel_id == 3
        assert alert.person_name == "Unknown Person"
        assert alert.face_score == 75
        assert alert.person_id is None


class TestRegularEventParsing:
    """Test that regular events still parse correctly."""

    def test_parse_fielddetection_event(self):
        """Test parsing of field detection event still works."""
        xml = load_fixture("ISAPI/EventNotificationAlert", "fielddetection_human")
        alert = ISAPIClient.parse_event_notification(xml)

        assert alert.event_id == "fielddetection"
        assert alert.channel_id == 1
        assert alert.detection_target == "human"
        assert alert.region_id == 3
        # ANPR and Face fields should be None/0
        assert alert.license_plate is None
        assert alert.plate_confidence == 0
        assert alert.person_name is None
        assert alert.face_score == 0

    def test_parse_nvr_fielddetection_event(self):
        """Test parsing of NVR field detection event still works."""
        xml = load_fixture("ISAPI/EventNotificationAlert", "nvr_2_fielddetection")
        alert = ISAPIClient.parse_event_notification(xml)

        assert alert.event_id == "fielddetection"
        assert alert.channel_id == 34
        # ANPR and Face fields should be None/0
        assert alert.license_plate is None
        assert alert.person_name is None


class TestFireHassEvent:
    """Test fire_hass_event includes ANPR and Face data correctly."""

    @pytest.fixture
    def mock_device(self):
        """Create a mock device for testing."""
        device = MagicMock()
        device.get_camera_by_id.return_value = MagicMock(name="Test Camera")
        return device

    @pytest.fixture
    def view(self, hass):
        """Create a notifications view for testing."""
        view = EventNotificationsView(hass)
        return view

    async def test_fire_event_with_anpr_data(self, hass: HomeAssistant, mock_device):
        """Test that fire_hass_event includes ANPR data in the event."""
        bus_events = []

        def bus_event_listener(event: Event) -> None:
            bus_events.append(event)

        hass.bus.async_listen(HIKVISION_EVENT, bus_event_listener)

        view = EventNotificationsView(hass)
        view.device = mock_device

        alert = AlertInfo(
            channel_id=1,
            io_port_id=0,
            event_id="vehicledetection",
            license_plate="ABC-1234",
            plate_confidence=95,
            plate_color="white",
            plate_type="normal",
            vehicle_color="blue",
        )

        view.fire_hass_event(alert)

        await hass.async_block_till_done()
        assert len(bus_events) == 1
        data = bus_events[0].data
        assert data["channel_id"] == 1
        assert data["event_id"] == "vehicledetection"
        assert data["license_plate"] == "ABC-1234"
        assert data["plate_confidence"] == 95
        assert data["plate_color"] == "white"
        assert data["plate_type"] == "normal"
        assert data["vehicle_color"] == "blue"

    async def test_fire_event_with_face_data(self, hass: HomeAssistant, mock_device):
        """Test that fire_hass_event includes face recognition data in the event."""
        bus_events = []

        def bus_event_listener(event: Event) -> None:
            bus_events.append(event)

        hass.bus.async_listen(HIKVISION_EVENT, bus_event_listener)

        view = EventNotificationsView(hass)
        view.device = mock_device

        alert = AlertInfo(
            channel_id=1,
            io_port_id=0,
            event_id="facedetection",
            person_name="John Doe",
            face_score=98,
            person_id="1001",
        )

        view.fire_hass_event(alert)

        await hass.async_block_till_done()
        assert len(bus_events) == 1
        data = bus_events[0].data
        assert data["channel_id"] == 1
        assert data["event_id"] == "facedetection"
        assert data["person_name"] == "John Doe"
        assert data["face_score"] == 98
        assert data["person_id"] == "1001"

    async def test_fire_event_without_anpr_face_data(self, hass: HomeAssistant, mock_device):
        """Test that fire_hass_event doesn't include ANPR/face data when not present."""
        bus_events = []

        def bus_event_listener(event: Event) -> None:
            bus_events.append(event)

        hass.bus.async_listen(HIKVISION_EVENT, bus_event_listener)

        view = EventNotificationsView(hass)
        view.device = mock_device

        alert = AlertInfo(
            channel_id=1,
            io_port_id=0,
            event_id="fielddetection",
            detection_target="human",
            region_id=3,
        )

        view.fire_hass_event(alert)

        await hass.async_block_till_done()
        assert len(bus_events) == 1
        data = bus_events[0].data
        assert data["channel_id"] == 1
        assert data["event_id"] == "fielddetection"
        assert data["detection_target"] == "human"
        assert data["region_id"] == 3
        # Should not have ANPR or Face data
        assert "license_plate" not in data
        assert "person_name" not in data


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_regular_events_still_work(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that regular events still work after adding ANPR and Face Recognition support."""

    bus_events = []

    def bus_event_listener(event: Event) -> None:
        bus_events.append(event)

    hass.bus.async_listen(HIKVISION_EVENT, bus_event_listener)

    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("fielddetection_human")
    await view.post(mock_request)

    await hass.async_block_till_done()
    assert len(bus_events) == 1
    data = bus_events[0].data
    assert data["channel_id"] == 1
    assert data["event_id"] == "fielddetection"
    assert data["detection_target"] == "human"
    assert data["region_id"] == 3
    # Should not have ANPR or Face data
    assert "license_plate" not in data
    assert "person_name" not in data
