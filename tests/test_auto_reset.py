"""Test auto-reset functionality for event binary sensors.

This module tests the auto-reset mechanism that automatically resets binary sensors
to OFF state after a timeout when no new events are received. This prevents sensors
from getting "stuck" in the ON state when the "inactive" event packet is dropped.
"""

from datetime import timedelta
from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.hikvision_next.const import EVENT_AUTO_RESET_TIMEOUT, RTSP_PORT_FORCED
from custom_components.hikvision_next.notifications import (
    EventNotificationsView,
    cancel_all_pending_resets,
    get_pending_resets_count,
    has_pending_reset,
)
from tests.conftest import TEST_CONFIG, TEST_CONFIG_OUTSIDE_NETWORK, TEST_HOST_IP, load_fixture


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


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_sensor_auto_resets_after_timeout(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer,
) -> None:
    """Test that sensor automatically resets to OFF after timeout.

    When an event notification is received, the sensor should turn ON and then
    automatically reset to OFF after EVENT_AUTO_RESET_TIMEOUT seconds if no
    new events are received.
    """
    entity_id = "binary_sensor.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_2_fielddetection"

    # Verify initial state is OFF
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF

    # Trigger the sensor with an event
    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("nvr_2_fielddetection")
    response = await view.post(mock_request)

    assert response.status == HTTPStatus.OK
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_ON

    # A pending reset should be scheduled
    assert has_pending_reset(entity_id)

    # Advance time past the auto-reset timeout
    freezer.tick(timedelta(seconds=EVENT_AUTO_RESET_TIMEOUT + 1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # Sensor should now be OFF
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF

    # Pending reset should be cleaned up
    assert not has_pending_reset(entity_id)


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_sensor_stays_on_immediately_after_trigger(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that sensor is ON immediately after being triggered.

    The sensor should be ON right after an event is received, and a pending
    reset should be scheduled.
    """
    entity_id = "binary_sensor.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_2_fielddetection"

    # Trigger the sensor
    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("nvr_2_fielddetection")
    await view.post(mock_request)

    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_ON

    # A pending reset should be scheduled
    assert has_pending_reset(entity_id)

    # Wait for the event loop to process
    await hass.async_block_till_done()

    # Sensor should still be ON (no time has advanced)
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_ON


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_new_event_resets_timeout(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer,
) -> None:
    """Test that receiving a new event resets the timeout timer.

    When a new event is received before the timeout expires, the timeout should
    be reset, extending the time before the sensor turns OFF.
    """
    entity_id = "binary_sensor.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_2_fielddetection"

    # Trigger the first event
    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("nvr_2_fielddetection")
    await view.post(mock_request)

    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_ON

    # Verify a pending reset is scheduled
    assert has_pending_reset(entity_id)

    # Trigger another event (this should reset the timeout)
    mock_request = mock_event_notification("nvr_2_fielddetection")
    await view.post(mock_request)

    # The entity should still have a pending reset (the old one was cancelled
    # and a new one was scheduled)
    assert has_pending_reset(entity_id)

    # Sensor should still be ON
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_ON

    # Now advance past the timeout
    freezer.tick(timedelta(seconds=EVENT_AUTO_RESET_TIMEOUT + 1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # Now sensor should be OFF
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF


@pytest.mark.parametrize(
    "init_multi_device_integration",
    [
        [
            {"model": "DS-7608NXI-I2", "config": TEST_CONFIG},
            {"model": "DS-2CD2T86G2-ISU", "config": {**TEST_CONFIG_OUTSIDE_NETWORK, RTSP_PORT_FORCED: 5153}},
        ]
    ],
    indirect=True,
)
async def test_multiple_sensors_have_independent_timeouts(
    hass: HomeAssistant,
    init_multi_device_integration: list[MockConfigEntry],
    freezer,
) -> None:
    """Test that multiple sensors have independent auto-reset timers.

    Each sensor should have its own timeout timer, so triggering one sensor
    should not affect the timeout of another sensor.
    """
    entity_nvr_id = "binary_sensor.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_2_fielddetection"
    entity_cam_id = "binary_sensor.ds_2cd2t86g2_isu_sl00000000aawrae0000000_1_io"

    # Verify initial states are OFF
    assert (sensor_nvr := hass.states.get(entity_nvr_id))
    assert (sensor_cam := hass.states.get(entity_cam_id))
    assert sensor_nvr.state == STATE_OFF
    assert sensor_cam.state == STATE_OFF

    # Trigger the NVR sensor first
    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("nvr_2_fielddetection")
    await view.post(mock_request)

    assert (sensor_nvr := hass.states.get(entity_nvr_id))
    assert sensor_nvr.state == STATE_ON
    assert (sensor_cam := hass.states.get(entity_cam_id))
    assert sensor_cam.state == STATE_OFF

    # Both sensors should have pending resets
    assert has_pending_reset(entity_nvr_id)

    # Trigger the camera sensor
    mock_request = mock_event_notification("cam3_DS-2CD2T86G2-ISU_io_notification")
    await view.post(mock_request)

    assert (sensor_nvr := hass.states.get(entity_nvr_id))
    assert sensor_nvr.state == STATE_ON
    assert (sensor_cam := hass.states.get(entity_cam_id))
    assert sensor_cam.state == STATE_ON

    # Both sensors should have pending resets
    assert has_pending_reset(entity_nvr_id)
    assert has_pending_reset(entity_cam_id)

    # Advance time past the timeout for both sensors
    freezer.tick(timedelta(seconds=EVENT_AUTO_RESET_TIMEOUT + 1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # Both sensors should be OFF now
    assert (sensor_nvr := hass.states.get(entity_nvr_id))
    assert sensor_nvr.state == STATE_OFF
    assert (sensor_cam := hass.states.get(entity_cam_id))
    assert sensor_cam.state == STATE_OFF

    # Both pending resets should be cleaned up
    assert not has_pending_reset(entity_nvr_id)
    assert not has_pending_reset(entity_cam_id)


@pytest.mark.parametrize("init_integration", ["DS-2CD2443G0-IW"], indirect=True)
async def test_pir_sensor_auto_reset(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer,
) -> None:
    """Test that PIR sensor also auto-resets after timeout."""
    entity_id = "binary_sensor.ds_2cd2443g0_iw00000000aawre00000000_1_pir"

    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF

    # Trigger PIR sensor
    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("pir")
    response = await view.post(mock_request)

    assert response.status == HTTPStatus.OK
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_ON

    # A pending reset should be scheduled
    assert has_pending_reset(entity_id)

    # Advance time past the auto-reset timeout
    freezer.tick(timedelta(seconds=EVENT_AUTO_RESET_TIMEOUT + 1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # Sensor should now be OFF
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_cancel_all_pending_resets(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that cancel_all_pending_resets clears all pending timers."""
    entity_id = "binary_sensor.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_2_fielddetection"

    # Trigger the sensor to create a pending reset
    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("nvr_2_fielddetection")
    await view.post(mock_request)

    # Verify a pending reset exists
    assert has_pending_reset(entity_id)
    assert get_pending_resets_count() >= 1

    # Cancel all pending resets
    cancel_all_pending_resets()

    # Should be empty
    assert get_pending_resets_count() == 0
    assert not has_pending_reset(entity_id)


@pytest.mark.parametrize("init_integration", ["DS-7608NXI-I2"], indirect=True)
async def test_sensor_not_reset_if_state_changed_externally(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer,
) -> None:
    """Test that auto-reset doesn't reset sensor if state was already changed.

    If the sensor state is changed to OFF by some other means before the timeout,
    the auto-reset should not try to reset it again.
    """
    entity_id = "binary_sensor.ds_7608nxi_i0_0p_s0000000000ccrrj00000000wcvu_2_fielddetection"

    # Trigger the sensor
    view = EventNotificationsView(hass)
    mock_request = mock_event_notification("nvr_2_fielddetection")
    await view.post(mock_request)

    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_ON

    # Externally set the sensor to OFF (simulating an "inactive" event being received)
    hass.states.async_set(entity_id, STATE_OFF, sensor.attributes)
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF

    # Advance time past the timeout
    freezer.tick(timedelta(seconds=EVENT_AUTO_RESET_TIMEOUT + 1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # Sensor should still be OFF (the auto-reset callback should have
    # detected the state was already OFF and not done anything)
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF


@pytest.mark.parametrize("init_integration", ["DS-2CD2146G2-ISU"], indirect=True)
async def test_rapid_fire_events_only_one_pending_reset(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer,
) -> None:
    """Test that rapid-fire events result in only one pending reset timer.

    When multiple events are received in quick succession, only the most
    recent timeout should be active.
    """
    entity_id = "binary_sensor.ds_2cd2146g2_isu00000000aawrg00000000_1_fielddetection"

    view = EventNotificationsView(hass)

    # Fire multiple events rapidly
    for _ in range(5):
        mock_request = mock_event_notification("fielddetection_human")
        await view.post(mock_request)
        await hass.async_block_till_done()

    # Sensor should be ON
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_ON

    # There should only be one pending reset (the most recent one)
    assert has_pending_reset(entity_id)

    # Advance time past the timeout
    freezer.tick(timedelta(seconds=EVENT_AUTO_RESET_TIMEOUT + 1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # Sensor should be OFF
    assert (sensor := hass.states.get(entity_id))
    assert sensor.state == STATE_OFF

    # Pending reset should be cleaned up
    assert not has_pending_reset(entity_id)
