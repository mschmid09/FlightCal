import os
import re

import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, send_file, session

from core import (
    get_flight,
    make_ics_from_selected_df_index,
    make_ics_from_manual_data,
    get_timezones_with_offsets,
)

app = Flask(__name__)


secret_key = os.urandom(24)
app.secret_key = secret_key


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/create_event", methods=["POST"])
def create_ical():
    try:
        flight = request.form.get("flight_number")
        date = request.form.get("flight_date")
        df = get_flight(flight, date)
        # Store the DataFrame as JSON in the session
        session["df"] = df.to_json(orient="split")
        return render_template(
            "select_flight.html", flights=df.to_dict(orient="records")
        )
    except Exception as e:
        error_message = str(e)
        return render_template("index.html", error=error_message)


@app.route("/create_event/<int:index>", methods=["POST"])
def create_ical_from_selected(index):
    # Retrieve the DataFrame from the session and reconstruct it
    df_json = session.get("df")
    if df_json is None:
        return "No flight data found", 400

    df = pd.read_json(df_json, orient="split")

    # Check if any custom fields were provided (user edited the flight)
    custom_fields = {
        "flight_number": request.form.get("flight_number"),
        "airline_name": request.form.get("airline_name"),
        "origin_airport": request.form.get("origin_airport"),
        "origin_airport_code": request.form.get("origin_airport_code"),
        "destination_airport": request.form.get("destination_airport"),
        "destination_airport_code": request.form.get("destination_airport_code"),
        "scheduled_departure": request.form.get("scheduled_departure"),
        "scheduled_arrival": request.form.get("scheduled_arrival"),
        "origin_timezone": request.form.get("origin_timezone"),
        "destination_timezone": request.form.get("destination_timezone"),
    }

    # Update the DataFrame with custom fields if they were provided
    for field, value in custom_fields.items():
        if value:
            df.at[index, field] = value

    ics_data = make_ics_from_selected_df_index(df, index)
    flight = df.iloc[index]["flight_number"]

    return send_file(ics_data, as_attachment=True, download_name=f"{flight}.ics")


@app.route("/manual_entry")
def manual_entry():
    timezones = get_timezones_with_offsets()
    return render_template("manual_entry.html", timezones=timezones)


@app.route("/create_manual_event", methods=["POST"])
def create_manual_event():
    try:
        # Get all form data
        flight_data = {
            "flight_number": request.form.get("flight_number"),
            "airline_name": request.form.get("airline_name"),
            "origin_airport": request.form.get("origin_airport"),
            "origin_airport_code": request.form.get("origin_airport_code"),
            "destination_airport": request.form.get("destination_airport"),
            "destination_airport_code": request.form.get("destination_airport_code"),
            "scheduled_departure": request.form.get("scheduled_departure"),
            "scheduled_arrival": request.form.get("scheduled_arrival"),
            "origin_timezone": request.form.get("origin_timezone"),
            "destination_timezone": request.form.get("destination_timezone"),
        }

        # Validate required fields
        required_fields = [
            "flight_number",
            "airline_name",
            "origin_airport",
            "origin_airport_code",
            "destination_airport",
            "destination_airport_code",
            "scheduled_departure",
            "scheduled_arrival",
            "origin_timezone",
            "destination_timezone",
        ]
        for field in required_fields:
            if not flight_data.get(field):
                raise ValueError(f"Missing required field: {field}")

        # Validate airport codes (should be 3 uppercase letters)
        if not re.match(r"^[A-Z]{3}$", flight_data["origin_airport_code"]):
            raise ValueError("Origin airport code must be 3 uppercase letters")
        if not re.match(r"^[A-Z]{3}$", flight_data["destination_airport_code"]):
            raise ValueError("Destination airport code must be 3 uppercase letters")

        # Validate datetime format (datetime-local format: YYYY-MM-DDTHH:MM or YYYY-MM-DD HH:MM)
        # Convert datetime-local format to the expected format
        try:
            # Try datetime-local format first (YYYY-MM-DDTHH:MM)
            if "T" in flight_data["scheduled_departure"]:
                flight_data["scheduled_departure"] = flight_data[
                    "scheduled_departure"
                ].replace("T", " ")
            if "T" in flight_data["scheduled_arrival"]:
                flight_data["scheduled_arrival"] = flight_data[
                    "scheduled_arrival"
                ].replace("T", " ")

            datetime.strptime(flight_data["scheduled_departure"], "%Y-%m-%d %H:%M")
            datetime.strptime(flight_data["scheduled_arrival"], "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValueError("Invalid datetime format. Use: yyyy-mm-dd hh:mm")

        # Create iCal file from manual data
        ics_data = make_ics_from_manual_data(flight_data)
        flight = flight_data["flight_number"]

        return send_file(ics_data, as_attachment=True, download_name=f"{flight}.ics")
    except Exception as e:
        error_message = str(e)
        timezones = get_timezones_with_offsets()
        return render_template(
            "manual_entry.html", error=error_message, timezones=timezones
        )


if __name__ == "__main__":
    app.run()
