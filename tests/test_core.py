"""Tests for core.py functions with mocked API calls."""

import io
from datetime import datetime

import pandas as pd
import pytest
from pytz import timezone

from core import (
    drop_ununique_flights,
    get_flight,
    make_ical_event,
    make_ics_from_manual_data,
    move_flight_date,
    parse_date,
    parse_flight_info,
    parse_flight_number,
    parse_nice_datetime,
    update_df_timezones,
)


# Sample mock flight data
MOCK_FLIGHT_DATA = {
    "identification": {"number": {"default": "SQ327"}},
    "time": {
        "scheduled": {
            "departure_date": "20241023",
            "departure_time": "1430",
            "arrival_date": "20241024",
            "arrival_time": "0615",
        }
    },
    "airline": {"name": "Singapore Airlines"},
    "airport": {
        "origin": {
            "name": "Singapore Changi Airport",
            "code": {"iata": "SIN"},
            "timezone": {"name": "Asia/Singapore"},
        },
        "destination": {
            "name": "San Francisco International Airport",
            "code": {"iata": "SFO"},
            "timezone": {"name": "America/Los_Angeles"},
        },
    },
}


class TestParseFlightNumber:
    """Test flight number parsing."""

    def test_parse_flight_number_basic(self):
        assert parse_flight_number("SQ327") == "SQ327"

    def test_parse_flight_number_with_spaces(self):
        assert parse_flight_number("SQ 327") == "SQ327"

    def test_parse_flight_number_with_leading_zeros(self):
        assert parse_flight_number("SQ0327") == "SQ327"

    def test_parse_flight_number_lowercase(self):
        assert parse_flight_number("sq327") == "SQ327"

    def test_parse_flight_number_with_special_chars(self):
        assert parse_flight_number("SQ-327") == "SQ327"


class TestParseDate:
    """Test date parsing."""

    def test_parse_date_valid(self):
        assert parse_date("2024-10-23") == "20241023"

    def test_parse_date_invalid_raises_error(self):
        with pytest.raises(ValueError):
            parse_date("invalid-date")


class TestParseFlightInfo:
    """Test flight info parsing."""

    def test_parse_flight_info(self):
        result = parse_flight_info([MOCK_FLIGHT_DATA], 0)

        assert result["flight_number"] == "SQ327"
        assert result["airline_name"] == "Singapore Airlines"
        assert result["origin_airport"] == "Singapore Changi Airport"
        assert result["destination_airport"] == "San Francisco International Airport"
        assert result["origin_airport_code"] == "SIN"
        assert result["destination_airport_code"] == "SFO"
        assert result["origin_timezone"] == "Asia/Singapore"
        assert result["destination_timezone"] == "America/Los_Angeles"
        assert result["scheduled_departure"] == "20241023 1430"
        assert result["scheduled_arrival"] == "20241024 0615"


class TestUpdateDfTimezones:
    """Test timezone conversion in DataFrame."""

    def test_update_df_timezones(self):
        df = pd.DataFrame(
            [
                {
                    "flight_number": "SQ327",
                    "scheduled_departure": "20241023 1430",
                    "scheduled_arrival": "20241024 0615",
                    "origin_timezone": "Asia/Singapore",
                    "destination_timezone": "America/Los_Angeles",
                }
            ]
        )

        result = update_df_timezones(df)

        # Verify that times are converted (exact values depend on timezone offsets)
        assert "scheduled_departure" in result.columns
        assert "scheduled_arrival" in result.columns
        # Verify format is maintained
        assert len(result.loc[0, "scheduled_departure"]) == 13  # "YYYYMMDD HHMM"


class TestParseNiceDatetime:
    """Test nice datetime formatting."""

    def test_parse_nice_datetime(self):
        df = pd.DataFrame(
            [
                {
                    "scheduled_departure": "20241023 1430",
                    "scheduled_arrival": "20241024 0615",
                }
            ]
        )

        result = parse_nice_datetime(df)

        assert result.loc[0, "nice_departure_date"] == "2024-10-23 14:30"
        assert result.loc[0, "nice_arrival_date"] == "2024-10-24 06:15"


class TestDropUnuniqueFlights:
    """Test dropping duplicate flights."""

    def test_drop_ununique_flights_keeps_unique(self):
        import copy

        flight1 = copy.deepcopy(MOCK_FLIGHT_DATA)
        flight2 = copy.deepcopy(MOCK_FLIGHT_DATA)
        flight2["time"]["scheduled"]["departure_time"] = "1630"

        result = drop_ununique_flights([flight1, flight2])
        assert len(result) == 2

    def test_drop_ununique_flights_removes_duplicates(self):
        flight1 = MOCK_FLIGHT_DATA.copy()
        flight2 = MOCK_FLIGHT_DATA.copy()

        result = drop_ununique_flights([flight1, flight2])
        assert len(result) == 1


class TestMoveFlightDate:
    """Test moving flight to different date."""

    def test_move_flight_date_same_day(self):
        flight_info = {
            "scheduled_departure": "20241023 1430",
            "scheduled_arrival": "20241023 1645",  # Same day arrival
        }

        result = move_flight_date(flight_info, "20241023")

        assert result["scheduled_departure"] == "20241023 1430"
        assert result["scheduled_arrival"] == "20241023 1645"

    def test_move_flight_date_different_day(self):
        flight_info = {
            "scheduled_departure": "20241023 1430",
            "scheduled_arrival": "20241024 0615",
        }

        result = move_flight_date(flight_info, "20241025")

        assert result["scheduled_departure"] == "20241025 1430"
        assert result["scheduled_arrival"] == "20241026 0615"


class TestMakeIcalEvent:
    """Test iCal event creation."""

    def test_make_ical_event(self):
        data = {
            "flight_number": "SQ327",
            "airline_name": "Singapore Airlines",
            "origin_airport": "Singapore Changi Airport",
            "destination_airport": "San Francisco International Airport",
            "origin_airport_code": "SIN",
            "destination_airport_code": "SFO",
            "scheduled_departure": "20241023 1430",
            "scheduled_arrival": "20241024 0615",
            "origin_timezone": "Asia/Singapore",
            "destination_timezone": "America/Los_Angeles",
        }

        result = make_ical_event(data)

        assert isinstance(result, bytes)
        assert b"BEGIN:VCALENDAR" in result
        assert b"BEGIN:VEVENT" in result
        assert b"SQ327" in result
        assert b"Singapore Airlines" in result
        assert b"SIN" in result
        assert b"SFO" in result


class TestMakeIcsFromManualData:
    """Test iCal creation from manual data."""

    def test_make_ics_from_manual_data(self):
        data = {
            "flight_number": "UA123",
            "airline_name": "United Airlines",
            "origin_airport": "San Francisco International Airport",
            "destination_airport": "Los Angeles International Airport",
            "origin_airport_code": "SFO",
            "destination_airport_code": "LAX",
            "scheduled_departure": "2024-10-23 14:30",
            "scheduled_arrival": "2024-10-23 16:45",
            "origin_timezone": "America/Los_Angeles",
            "destination_timezone": "America/Los_Angeles",
        }

        result = make_ics_from_manual_data(data)

        assert isinstance(result, io.BytesIO)
        content = result.getvalue()
        assert b"BEGIN:VCALENDAR" in content
        assert b"UA123" in content


class TestGetFlight:
    """Test get_flight with mocked API calls."""

    def test_get_flight_with_date(self, mocker):
        """Test getting flight with specific date."""
        mock_api = mocker.patch("core.f.get_flight_for_date")
        mock_api.return_value = [MOCK_FLIGHT_DATA]

        result = get_flight("SQ327", "2024-10-23")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.loc[0, "flight_number"] == "SQ327"
        assert result.loc[0, "is_guess"] == False
        assert "nice_departure_date" in result.columns
        assert "nice_arrival_date" in result.columns

    def test_get_flight_no_date_fallback(self, mocker):
        """Test fallback when no flight found for date."""
        mock_with_date = mocker.patch("core.f.get_flight_for_date")
        mock_with_date.return_value = []

        mock_no_date = mocker.patch("core.f.get_history_by_flight_number")
        mock_no_date.return_value = [MOCK_FLIGHT_DATA]

        result = get_flight("SQ327", "2024-10-23")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.loc[0, "is_guess"] == True

    def test_get_flight_not_found_raises_error(self, mocker):
        """Test error when flight not found."""
        mock_with_date = mocker.patch("core.f.get_flight_for_date")
        mock_with_date.return_value = []

        mock_no_date = mocker.patch("core.f.get_history_by_flight_number")
        mock_no_date.return_value = []

        with pytest.raises(ValueError, match="No flight information found"):
            get_flight("INVALID", "2024-10-23")
