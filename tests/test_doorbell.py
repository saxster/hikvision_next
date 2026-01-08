"""Test doorbell/video intercom event support."""

import pytest
from http import HTTPStatus
from homeassistant.core import HomeAssistant, Event
from homeassistant.const import STATE_ON, STATE_OFF
from pytest_homeassistant_custom_component.common import MockConfigEntry
from unittest.mock import MagicMock

from custom_components.hikvision_next.notifications import EventNotificationsView
from custom_components.hikvision_next.const import HIKVISION_EVENT
from tests.conftest import load_fixture, TEST_HOST_IP, TEST_CONFIG


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


@pytest.mark.parametrize("init_integration", ["DS-KV8113-WME1"], indirect=True)
async def test_doorbell_device_initialization(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that doorbell device initializes correctly with videointercom event."""
    device = init_integration.runtime_data

    # Verify device is identified as supporting video intercom
    assert device.capabilities.support_video_intercom is True

    # Verify the videointercomevent is in the supported events
    event_ids = [event.id for event in device.supported_events]
    assert "videointercomevent" in event_ids

    # Verify the doorbell binary sensor entity exists
    entity_id = "binary_sensor.ds_kv8113_wme100000000aawrdb0000000_videointercomevent"
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF


@pytest.mark.parametrize("init_integration", ["DS-KV8113-WME1"], indirect=True)
async def test_doorbell_event_notification(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test doorbell event notification triggers the binary sensor."""
    entity_id = "binary_sensor.ds_kv8113_wme100000000aawrdb0000000_videointercomevent"
    bus_events = []

    def bus_event_listener(event: Event) -> None:
        bus_events.append(event)

    hass.bus.async_listen(HIKVISION_EVENT, bus_event_listener)

    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF

    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("doorbell_videointercomevent")
    response = await view.post(mock_request)

    assert response.status == HTTPStatus.OK
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_ON

    await hass.async_block_till_done()
    assert len(bus_events) == 1
    data = bus_events[0].data
    assert data["channel_id"] == 1
    assert data["event_id"] == "videointercomevent"


@pytest.mark.parametrize("init_integration", ["DS-KV8113-WME1"], indirect=True)
async def test_doorbell_alternate_event_notification(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test alternate doorbell event name (doorbellpress) triggers the binary sensor."""
    entity_id = "binary_sensor.ds_kv8113_wme100000000aawrdb0000000_videointercomevent"
    bus_events = []

    def bus_event_listener(event: Event) -> None:
        bus_events.append(event)

    hass.bus.async_listen(HIKVISION_EVENT, bus_event_listener)

    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF

    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("doorbell_doorbellpress")
    response = await view.post(mock_request)

    assert response.status == HTTPStatus.OK
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_ON

    await hass.async_block_till_done()
    assert len(bus_events) == 1
    data = bus_events[0].data
    # The event ID should be translated to videointercomevent
    assert data["event_id"] == "videointercomevent"


@pytest.mark.parametrize("init_integration", ["DS-2CD2386G2-IU"], indirect=True)
async def test_non_doorbell_device_no_videointercom_event(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that non-doorbell devices don't have the videointercom event."""
    device = init_integration.runtime_data

    # Verify device does not support video intercom
    assert device.capabilities.support_video_intercom is False

    # Verify the videointercomevent is NOT in the supported events
    event_ids = [event.id for event in device.supported_events]
    assert "videointercomevent" not in event_ids

    # Verify the doorbell binary sensor entity does not exist
    entity_id = "binary_sensor.ds_2cd2386g2_iu00000000aawrj00000000_videointercomevent"
    assert hass.states.get(entity_id) is None


@pytest.mark.parametrize("init_integration", ["DS-KV8113-WME1"], indirect=True)
async def test_doorbell_event_url(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that the doorbell event URL is correctly generated."""
    device = init_integration.runtime_data

    # Find the videointercomevent
    doorbell_events = [e for e in device.supported_events if e.id == "videointercomevent"]
    assert len(doorbell_events) == 1
    doorbell_event = doorbell_events[0]

    # Verify the URL points to VideoIntercom/callStatus
    assert doorbell_event.url == "VideoIntercom/callStatus"


@pytest.mark.parametrize("init_integration", ["DS-KV8113-WME1"], indirect=True)
async def test_doorbell_motion_and_intercom_events(
    hass: HomeAssistant, init_integration: MockConfigEntry,
) -> None:
    """Test that doorbell has both motion detection and video intercom events."""
    device = init_integration.runtime_data

    event_ids = [event.id for event in device.supported_events]

    # Doorbell should have both motion detection and videointercom events
    assert "motiondetection" in event_ids
    assert "videointercomevent" in event_ids
