"""Tests for playback/recording search functionality."""

import pytest
import respx
from custom_components.hikvision_next.isapi import (
    RecordingSearchResult,
    PlaybackSession,
)
from tests.conftest import TEST_HOST


def mock_search_endpoint(file=None, status_code=200):
    """Mock ISAPI ContentMgmt/search endpoint."""
    url = f"{TEST_HOST}/ISAPI/ContentMgmt/search"
    if not file:
        return respx.post(url).respond(status_code=status_code)
    with open(f"tests/fixtures/ISAPI/ContentMgmt.search/{file}.xml", "r") as f:
        return respx.post(url).respond(text=f.read())


def mock_calendar_endpoint(file=None, status_code=200):
    """Mock ISAPI ContentMgmt/record/tracks/daily endpoint."""
    url = f"{TEST_HOST}/ISAPI/ContentMgmt/record/tracks/daily"
    if not file:
        return respx.post(url).respond(status_code=status_code)
    with open(f"tests/fixtures/ISAPI/ContentMgmt.record.tracks.daily/{file}.xml", "r") as f:
        return respx.post(url).respond(text=f.read())


@respx.mock
async def test_search_recordings_empty(mock_isapi):
    """Test searching for recordings when no results are found."""
    isapi = mock_isapi

    mock_search_endpoint("empty_result")
    results = await isapi.search_recordings(
        channel_id=1,
        start_time="2024-01-15T00:00:00Z",
        end_time="2024-01-15T23:59:59Z",
    )
    assert len(results) == 0


@respx.mock
async def test_search_recordings_single_result(mock_isapi):
    """Test searching for recordings with a single result."""
    isapi = mock_isapi

    mock_search_endpoint("single_result")
    results = await isapi.search_recordings(
        channel_id=1,
        start_time="2024-01-15T10:00:00Z",
        end_time="2024-01-15T11:00:00Z",
    )

    assert len(results) == 1
    assert results[0].channel_id == 1
    assert results[0].start_time == "2024-01-15T10:00:00Z"
    assert results[0].end_time == "2024-01-15T10:30:00Z"
    assert results[0].track_id == "101"
    assert "rtsp://" in results[0].playback_uri


@respx.mock
async def test_search_recordings_multiple_results(mock_isapi):
    """Test searching for recordings with multiple results."""
    isapi = mock_isapi

    mock_search_endpoint("multiple_results")
    results = await isapi.search_recordings(
        channel_id=1,
        start_time="2024-01-15T00:00:00Z",
        end_time="2024-01-15T23:59:59Z",
        max_results=100,
    )

    assert len(results) == 3
    assert all(r.channel_id == 1 for r in results)
    assert results[0].start_time == "2024-01-15T08:00:00Z"
    assert results[1].start_time == "2024-01-15T12:00:00Z"
    assert results[2].start_time == "2024-01-15T18:00:00Z"


@respx.mock
async def test_search_event_recordings(mock_isapi):
    """Test searching for event-triggered recordings."""
    isapi = mock_isapi

    mock_search_endpoint("event_results")
    results = await isapi.search_event_recordings(
        channel_id=1,
        start_time="2024-01-15T00:00:00Z",
        end_time="2024-01-15T23:59:59Z",
        event_type="VMD",
    )

    assert len(results) == 2
    assert all(r.event_type == "VMD" for r in results)
    assert results[0].start_time == "2024-01-15T09:15:00Z"
    assert results[1].start_time == "2024-01-15T14:30:00Z"


@respx.mock
async def test_search_event_recordings_line_detection(mock_isapi):
    """Test searching for line detection event recordings."""
    isapi = mock_isapi

    mock_search_endpoint("linedetection_results")
    results = await isapi.search_event_recordings(
        channel_id=2,
        start_time="2024-01-15T00:00:00Z",
        end_time="2024-01-15T23:59:59Z",
        event_type="linedetection",
    )

    assert len(results) == 1
    assert results[0].event_type == "linedetection"
    assert results[0].channel_id == 2


def test_get_playback_url(mock_isapi):
    """Test generating playback URL."""
    isapi = mock_isapi
    isapi.device_info.ip_address = "192.168.1.100"
    isapi.protocols.rtsp_port = 554

    url = isapi.get_playback_url(
        channel_id=1,
        start_time="2024-01-15T10:00:00Z",
        end_time="2024-01-15T11:00:00Z",
        stream_type=1,
    )

    assert url.startswith("rtsp://")
    assert "192.168.1.100:554" in url
    assert "Streaming/tracks/101" in url
    assert "starttime=20240115T100000z" in url
    assert "endtime=20240115T110000z" in url


def test_get_playback_url_substream(mock_isapi):
    """Test generating playback URL for substream."""
    isapi = mock_isapi
    isapi.device_info.ip_address = "192.168.1.100"
    isapi.protocols.rtsp_port = 10554

    url = isapi.get_playback_url(
        channel_id=2,
        start_time="2024-01-20T14:00:00Z",
        end_time="2024-01-20T15:00:00Z",
        stream_type=2,
    )

    assert "192.168.1.100:10554" in url
    assert "Streaming/tracks/202" in url


def test_get_playback_url_credentials_encoded(mock_isapi):
    """Test that credentials are URL encoded in playback URL."""
    isapi = mock_isapi
    isapi.username = "admin"
    isapi.password = "pa$$w0rd!@#"
    isapi.device_info.ip_address = "192.168.1.100"
    isapi.protocols.rtsp_port = 554

    url = isapi.get_playback_url(
        channel_id=1,
        start_time="2024-01-15T10:00:00Z",
        end_time="2024-01-15T11:00:00Z",
    )

    # Password should be URL encoded
    assert "pa%24%24w0rd%21%40%23" in url


@respx.mock
async def test_get_recording_calendar(mock_isapi):
    """Test getting calendar of recording days."""
    isapi = mock_isapi

    mock_calendar_endpoint("january_2024")
    days = await isapi.get_recording_calendar(
        channel_id=1,
        year=2024,
        month=1,
    )

    assert len(days) > 0
    assert all(1 <= d <= 31 for d in days)


@respx.mock
async def test_get_recording_calendar_empty_month(mock_isapi):
    """Test getting calendar for month with no recordings."""
    isapi = mock_isapi

    mock_calendar_endpoint("empty_month")
    days = await isapi.get_recording_calendar(
        channel_id=1,
        year=2024,
        month=2,
    )

    assert len(days) == 0


@respx.mock
async def test_get_recording_calendar_december(mock_isapi):
    """Test getting calendar for December (edge case for year boundary)."""
    isapi = mock_isapi

    mock_calendar_endpoint("december_2024")
    days = await isapi.get_recording_calendar(
        channel_id=1,
        year=2024,
        month=12,
    )

    assert len(days) == 5


@respx.mock
async def test_search_recordings_different_channel(mock_isapi):
    """Test searching recordings for different channels."""
    isapi = mock_isapi

    mock_search_endpoint("channel2_results")
    results = await isapi.search_recordings(
        channel_id=2,
        start_time="2024-01-15T00:00:00Z",
        end_time="2024-01-15T23:59:59Z",
    )

    assert len(results) == 2
    assert all(r.channel_id == 2 for r in results)


def test_recording_search_result_model():
    """Test RecordingSearchResult dataclass."""
    result = RecordingSearchResult(
        channel_id=1,
        start_time="2024-01-15T10:00:00Z",
        end_time="2024-01-15T11:00:00Z",
        source_id="source123",
        track_id="101",
        playback_uri="rtsp://192.168.1.100/Streaming/tracks/101",
        event_type="VMD",
    )

    assert result.channel_id == 1
    assert result.start_time == "2024-01-15T10:00:00Z"
    assert result.end_time == "2024-01-15T11:00:00Z"
    assert result.source_id == "source123"
    assert result.track_id == "101"
    assert result.playback_uri == "rtsp://192.168.1.100/Streaming/tracks/101"
    assert result.event_type == "VMD"
    assert result.content_type == "video"


def test_playback_session_model():
    """Test PlaybackSession dataclass."""
    session = PlaybackSession(
        session_id="session123",
        playback_uri="rtsp://192.168.1.100/Streaming/tracks/101",
        channel_id=1,
        start_time="2024-01-15T10:00:00Z",
        end_time="2024-01-15T11:00:00Z",
    )

    assert session.session_id == "session123"
    assert session.playback_uri == "rtsp://192.168.1.100/Streaming/tracks/101"
    assert session.channel_id == 1
    assert session.start_time == "2024-01-15T10:00:00Z"
    assert session.end_time == "2024-01-15T11:00:00Z"


@respx.mock
async def test_search_recordings_server_error(mock_isapi):
    """Test handling server error when searching recordings."""
    isapi = mock_isapi

    mock_search_endpoint(status_code=500)

    # This should raise an exception on server error
    with pytest.raises(Exception):
        await isapi.search_recordings(
            channel_id=1,
            start_time="2024-01-15T00:00:00Z",
            end_time="2024-01-15T23:59:59Z",
        )


@respx.mock
async def test_search_recordings_with_custom_search_type(mock_isapi):
    """Test searching recordings with different search types."""
    isapi = mock_isapi

    mock_search_endpoint("motion_results")
    results = await isapi.search_recordings(
        channel_id=1,
        start_time="2024-01-15T00:00:00Z",
        end_time="2024-01-15T23:59:59Z",
        search_type="MOTION",
    )

    assert len(results) >= 0  # Should not error regardless of results
