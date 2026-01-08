"""Tests for event definitions coverage."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from custom_components.hikvision_next.isapi.const import EVENTS as ISAPI_EVENTS, EVENT_BASIC, EVENT_SMART
from custom_components.hikvision_next.const import EVENTS


class TestNewEventDefinitions:
    """Test that new events are properly defined in both const files."""

    def test_visitorcall_in_isapi_events(self):
        """Test that visitor call event is defined in ISAPI events."""
        assert "visitorcall" in ISAPI_EVENTS
        event = ISAPI_EVENTS["visitorcall"]
        assert event["type"] == EVENT_BASIC
        assert event["label"] == "Visitor Call"
        assert event["slug"] == "visitorCall"

    def test_facedetection_in_isapi_events(self):
        """Test that face detection event is defined in ISAPI events."""
        assert "facedetection" in ISAPI_EVENTS
        event = ISAPI_EVENTS["facedetection"]
        assert event["type"] == EVENT_SMART
        assert event["label"] == "Face Detection"
        assert event["slug"] == "FaceDetection"

    def test_audioexception_in_isapi_events(self):
        """Test that audio exception event is defined in ISAPI events."""
        assert "audioexception" in ISAPI_EVENTS
        event = ISAPI_EVENTS["audioexception"]
        assert event["type"] == EVENT_SMART
        assert event["label"] == "Audio Exception"
        assert event["slug"] == "AudioException"

    def test_defocus_in_isapi_events(self):
        """Test that defocus detection event is defined in ISAPI events."""
        assert "defocus" in ISAPI_EVENTS
        event = ISAPI_EVENTS["defocus"]
        assert event["type"] == EVENT_BASIC
        assert event["label"] == "Defocus Detection"
        assert event["slug"] == "defocus"

    def test_unattendedbaggage_in_isapi_events(self):
        """Test that unattended baggage event is defined in ISAPI events."""
        assert "unattendedbaggage" in ISAPI_EVENTS
        event = ISAPI_EVENTS["unattendedbaggage"]
        assert event["type"] == EVENT_SMART
        assert event["label"] == "Unattended Baggage"
        assert event["slug"] == "UnattendedBaggage"

    def test_visitorcall_has_device_class(self):
        """Test that visitor call has correct device class mapping."""
        assert "visitorcall" in EVENTS
        assert EVENTS["visitorcall"]["device_class"] == BinarySensorDeviceClass.OCCUPANCY

    def test_facedetection_has_device_class(self):
        """Test that face detection has correct device class mapping."""
        assert "facedetection" in EVENTS
        assert EVENTS["facedetection"]["device_class"] == BinarySensorDeviceClass.MOTION

    def test_audioexception_has_device_class(self):
        """Test that audio exception has correct device class mapping."""
        assert "audioexception" in EVENTS
        assert EVENTS["audioexception"]["device_class"] == BinarySensorDeviceClass.SOUND

    def test_defocus_has_device_class(self):
        """Test that defocus has correct device class mapping."""
        assert "defocus" in EVENTS
        assert EVENTS["defocus"]["device_class"] == BinarySensorDeviceClass.PROBLEM

    def test_unattendedbaggage_has_device_class(self):
        """Test that unattended baggage has correct device class mapping."""
        assert "unattendedbaggage" in EVENTS
        assert EVENTS["unattendedbaggage"]["device_class"] == BinarySensorDeviceClass.PROBLEM

    def test_all_isapi_events_in_ha_events(self):
        """Test that all ISAPI events have corresponding Home Assistant event mappings."""
        for event_key in ISAPI_EVENTS.keys():
            assert event_key in EVENTS, f"ISAPI event '{event_key}' missing from HA EVENTS"
            assert "device_class" in EVENTS[event_key], f"Event '{event_key}' missing device_class"

    def test_new_events_have_required_fields(self):
        """Test that all new events have the required fields."""
        new_events = ["visitorcall", "facedetection", "audioexception", "defocus", "unattendedbaggage"]
        required_fields = ["type", "label", "slug"]
        
        for event_key in new_events:
            event = ISAPI_EVENTS[event_key]
            for field in required_fields:
                assert field in event, f"Event '{event_key}' missing required field '{field}'"
