
"""Selenium automation for the local synthetic appointment mock only."""

import csv
import hashlib
import json
import logging
import os
import re
from datetime import date, datetime, time as dt_time
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "patients_appointments.xlsx"
STATUS = ROOT / "booking_results.csv"
LOG = ROOT / "appointment_errors.log"
URL = "http://127.0.0.1:5000/booking"
WAIT_SECONDS = 12

FIELDS = [
    "Excel_Row", "Row_Fingerprint", "Booking_Status",
    "Stage", "Details", "Updated_At"
]

REQUIRED_COLUMNS = [
    "ID type", "PatientName", "ScheduleDate",
    "StartTime", "EndTime", "IsVirtual",
    "CLINICCODE", "DoctorName"
]

KNOWN_ERRORS = {
    "Patient Not Found",
    "Patient File Closed",
    "Patient File Suspended",
    "Patient Name Mismatch",
    "Incomplete Mobile Number",
    "No Third Name",
    "Appointment Already Exists",
    "No available slot",
    "No Slot",
    "Overbooking Required",
    "Schedule Not Generated",
    "Invalid Visit Type",
    "Invalid Date or Time",
    "Invalid Time Range",
    "Required Fields Missing"
}

SKIP_STATUSES = {
    "Successfully Saved",
    "Save Status Uncertain",
    "Appointment Already Exists",
    "In Progress - Review Before Retry",
    "Review Required - Input Changed"
}

logging.basicConfig(
    filename=LOG,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8"
)


class BookingStageError(Exception):
    def __init__(self, stage, message):
        super().__init__(message)
        self.stage = stage


def as_text(value):
    return "" if pd.isna(value) else str(value).strip()


def synthetic_id(value):
    value = as_text(value)

    if value.endswith(".0"):
        value = value[:-2]

    if not re.fullmatch(r"900000000[1-7]", value):
        raise ValueError(
            "Test environment only: synthetic IDs "
            "9000000001–9000000007"
        )

    return value


def date_text(value):
    if isinstance(value, (datetime, pd.Timestamp, date)):
        return value.strftime("%Y-%m-%d")

    value = as_text(value)

    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S"
    ):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError("Invalid ScheduleDate")


def time_text(value):
    if isinstance(value, (datetime, pd.Timestamp, dt_time)):
        return value.strftime("%H:%M")

    value = as_text(value)

    for fmt in (
        "%H:%M",
        "%H:%M:%S",
        "%I:%M %p",
        "%I:%M:%S %p"
    ):
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            continue

    raise ValueError("Invalid Time")


def visit_type(value):
    value = as_text(value).lower()

    if value in ("0", "0.0"):
        return "Followup Visit"

    if value in ("1", "1.0"):
        return "TeleConsult"

    raise ValueError("Invalid IsVirtual: expected 0 or 1")


def load_rows():
    if not INPUT.exists():
        raise FileNotFoundError(
            "Put patients_appointments.xlsx in the mock-system folder"
        )

    df = pd.read_excel(
        INPUT,
        dtype=str,
        keep_default_na=False
    )

    missing = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing columns: " + ", ".join(missing)
        )

    return df


def row_fingerprint(row):
    values = [
        as_text(row[column])
        for column in REQUIRED_COLUMNS
    ]

    payload = json.dumps(
        values,
        ensure_ascii=False,
        separators=(",", ":")
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def previous_results():
    if not STATUS.exists():
        return {}

    with STATUS.open(
        newline="",
        encoding="utf-8-sig"
    ) as file:
        return {
            int(record["Excel_Row"]): record
            for record in csv.DictReader(file)
        }


def save_results(results):
    temporary = STATUS.with_suffix(".csv.tmp")

    with temporary.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDS,
            extrasaction="ignore"
        )

        writer.writeheader()

        for key in sorted(results):
            writer.writerow(results[key])

        file.flush()
        os.fsync(file.fileno())

    os.replace(temporary, STATUS)


def record_result(results, excel_row, fingerprint,
                  status, stage, details):

    results[excel_row] = {
        "Excel_Row": excel_row,
        "Row_Fingerprint": fingerprint,
        "Booking_Status": status,
        "Stage": stage,
        "Details": details,
        "Updated_At": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    save_results(results)


def fill(driver, field, value):
    element = driver.find_element(By.ID, field)
    element.clear()
    element.send_keys(value)


def set_and_verify(driver, field, value):
    element = driver.find_element(By.ID, field)

    driver.execute_script(
        """
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(
            new Event('input', {bubbles: true})
        );
        arguments[0].dispatchEvent(
            new Event('change', {bubbles: true})
        );
        """,
        element,
        value
    )

    actual = driver.find_element(
        By.ID, field
    ).get_attribute("value")

    if actual != value:
        raise BookingStageError(
            "VERIFY_DATE_TIME",
            f"Appointment Date/Time Mismatch: {field}"
        )


def verify_date_time(driver, appointment_date, start, end):
    expected = {
        "appointment_date": appointment_date,
        "start_time": start,
        "end_time": end
    }

    for field, value in expected.items():
        actual = driver.find_element(
            By.ID, field
        ).get_attribute("value")

        if actual != value:
            raise BookingStageError(
                "VERIFY_DATE_TIME",
                f"Appointment Date/Time Mismatch: {field}"
            )


def wait_slot_result(driver):
    def ready(browser):
        message = browser.find_element(
            By.ID, "slot_message"
        ).text.strip()

        recognized = (
            "available slot",
            "occupied slot",
            "overbooking",
            "schedule not generated",
            "no slot",
            "invalid",
            "error"
        )

        if any(
            phrase in message.lower()
            for phrase in recognized
        ):
            return message

        return False

    return WebDriverWait(
        driver, WAIT_SECONDS
    ).until(ready)


def verify_booking(source_key):
    query = urlencode({"source_key": source_key})

    endpoint = (
        "http://127.0.0.1:5000/api/verify?" + query
    )

    with urlopen(endpoint, timeout=WAIT_SECONDS) as response:
        data = json.load(response)

    return data.get("found", False)


def prepare_row(row):
    national_id = synthetic_id(row["ID type"])
    patient = as_text(row["PatientName"])
    clinic = as_text(row["CLINICCODE"]).upper()
    doctor = as_text(row["DoctorName"])

    appointment_date = date_text(row["ScheduleDate"])
    start = time_text(row["StartTime"])
    end = time_text(row["EndTime"])
    visit = visit_type(row["IsVirtual"])

    if not patient or not clinic or not doctor:
        raise ValueError("Missing patient/clinic/doctor")

    if clinic not in ("OPT1", "NS04", "SUBNS04"):
        raise ValueError("Schedule Not Generated")

    if end <= start:
        raise ValueError("Invalid Appointment Time")

    source_key = "|".join([
        national_id,
        clinic,
        doctor,
        appointment_date,
        start,
        end
    ])

    return {
        "national_id": national_id,
        "patient": patient,
        "clinic": clinic,
        "doctor": doctor,
        "appointment_date": appointment_date,
        "start": start,
        "end": end,
        "visit": visit,
        "source_key": source_key
    }


def process(driver, row):
    stage = "VALIDATE_EXCEL"

    try:
        data = prepare_row(row)
    except Exception as exc:
        raise BookingStageError(
            stage, str(exc)
        ) from exc

    stage = "OPEN_BOOKING"

    try:
        driver.get(URL)

        WebDriverWait(
            driver, WAIT_SECONDS
        ).until(
            lambda browser: browser.find_element(
                By.ID, "clinic_code"
            )
        )

        Select(
            driver.find_element(By.ID, "clinic_code")
        ).select_by_value(data["clinic"])

        fill(driver, "doctor_name", data["doctor"])

    except Exception as exc:
        raise BookingStageError(
            stage, str(exc)
        ) from exc

    stage = "VERIFY_DATE_TIME"

    try:
        for field, value in (
            ("appointment_date", data["appointment_date"]),
            ("start_time", data["start"]),
            ("end_time", data["end"])
        ):
            set_and_verify(driver, field, value)

        verify_date_time(
            driver,
            data["appointment_date"],
            data["start"],
            data["end"]
        )

    except BookingStageError:
        raise
    except Exception as exc:
        raise BookingStageError(
            stage, str(exc)
        ) from exc

    stage = "PATIENT_SEARCH"

    try:
        fill(driver, "national_id", data["national_id"])

        driver.execute_script(
            """
            arguments[0].dispatchEvent(
                new Event('change', {bubbles: true})
            );
            """,
            driver.find_element(By.ID, "national_id")
        )

        WebDriverWait(
            driver, WAIT_SECONDS
        ).until(
            lambda browser:
                browser.find_element(
                    By.ID, "patient_name"
                ).get_attribute("value")
                or browser.find_element(
                    By.ID, "patient_message"
                ).text
        )

        actual = driver.find_element(
            By.ID, "patient_name"
        ).get_attribute("value").strip()

        message = driver.find_element(
            By.ID, "patient_message"
        ).text.strip()

        if not actual:
            raise BookingStageError(
                stage,
                message or "Patient Not Found"
            )

        if actual.casefold() != data["patient"].casefold():
            raise BookingStageError(
                stage, "Patient Name Mismatch"
            )

        if len(actual.split()) < 3:
            raise BookingStageError(
                stage, "No Third Name"
            )

        mobile = driver.find_element(
            By.ID, "mobile"
        ).get_attribute("value").strip()

        if not re.fullmatch(r"\d{10}", mobile):
            raise BookingStageError(
                stage, "Incomplete Mobile Number"
            )

        if message:
            raise BookingStageError(
                stage, message
            )

    except BookingStageError:
        raise
    except Exception as exc:
        raise BookingStageError(
            stage, str(exc)
        ) from exc

    stage = "VISIT_TYPE"

    try:
        Select(
            driver.find_element(By.ID, "visit_type")
        ).select_by_visible_text(data["visit"])

    except Exception as exc:
        raise BookingStageError(
            stage, "Invalid Visit Type"
        ) from exc

    stage = "SLOT_CHECK"

    try:
        driver.find_element(
            By.ID, "check_slot"
        ).click()

        message = wait_slot_result(driver)
        lower = message.lower()

        if "schedule not generated" in lower:
            raise BookingStageError(
                stage, "Schedule Not Generated"
            )

        if "no available slot" in lower or "no slot" in lower:
            raise BookingStageError(
                stage, "No available slot"
            )

        if "occupied slot" in lower:
            button = driver.find_element(
                By.ID, "overbook"
            )

            if not button.is_displayed():
                raise BookingStageError(
                    stage,
                    "Overbooking button not visible"
                )

            button.click()

            WebDriverWait(
                driver, WAIT_SECONDS
            ).until(
                lambda browser:
                    "approved" in browser.find_element(
                        By.ID, "slot_message"
                    ).text.lower()
            )

        elif "available slot" not in lower:
            raise BookingStageError(
                stage,
                "Unexpected slot result"
            )

    except BookingStageError:
        raise
    except Exception as exc:
        raise BookingStageError(
            stage, str(exc)
        ) from exc

    stage = "PRE_SAVE"

    try:
        verify_date_time(
            driver,
            data["appointment_date"],
            data["start"],
            data["end"]
        )

        save_button = driver.find_element(
            By.ID, "save"
        )

        if not save_button.is_enabled():
            raise BookingStageError(
                stage, "Save Button Disabled"
            )

    except BookingStageError:
        raise
    except Exception as exc:
        raise BookingStageError(
            stage, str(exc)
        ) from exc

    stage = "SAVE_CLICK"

    try:
        driver.execute_script(
            "document.getElementById('result').textContent = '';"
        )

        save_button.click()

        stage = "POST_SAVE"

        result = WebDriverWait(
            driver, WAIT_SECONDS
        ).until(
            lambda browser:
                browser.find_element(
                    By.ID, "result"
                ).text.strip() or False
        )

        if not result.startswith("Successfully Saved"):
            if result in KNOWN_ERRORS:
                raise BookingStageError(
                    stage, result
                )

            raise BookingStageError(
                stage,
                "Save Status Uncertain: " + result
            )

        stage = "VERIFY_BOOKING"

        if not verify_booking(data["source_key"]):
            raise BookingStageError(
                stage,
                "Save Status Uncertain: booking not verified"
            )

        return (
            "Successfully Saved",
            stage,
            "Verified using the mock booking API"
        )

    except BookingStageError:
        raise

    except Exception as exc:
        raise BookingStageError(
            stage,
            "Save Status Uncertain"
        ) from exc


def classify_error(exc):
    details = str(exc).strip() or type(exc).__name__
    stage = getattr(exc, "stage", "UNKNOWN")

    if "Appointment Date/Time Mismatch" in details:
        return (
            "Appointment Date Mismatch",
            stage,
            details
        )

    if stage in (
        "SAVE_CLICK",
        "POST_SAVE",
        "VERIFY_BOOKING"
    ):
        if details in KNOWN_ERRORS:
            return details, stage, details

        return (
            "Save Status Uncertain",
            stage,
            details
        )

    if details in KNOWN_ERRORS:
        return details, stage, details

    if isinstance(
        exc, (TimeoutException, WebDriverException)
    ):
        return (
            "Automation Error",
            stage,
            details
        )

    return (
        "Failed: " + details[:160],
        stage,
        details
    )


def main():
    parsed = urlparse(URL)

    if (
        parsed.scheme != "http"
        or parsed.hostname not in ("127.0.0.1", "localhost")
        or parsed.port != 5000
        or parsed.path != "/booking"
    ):
        raise RuntimeError(
            "Refusing non-local mock URL"
        )

    df = load_rows()
    results = previous_results()

    driver = webdriver.Chrome()

    try:
        driver.set_page_load_timeout(20)

        for index, row in df.iterrows():
            excel_row = index + 2
            fingerprint = row_fingerprint(row)
            old = results.get(excel_row, {})

            if old:
                old_fingerprint = old.get(
                    "Row_Fingerprint", ""
                )

                if not old_fingerprint:
                    print(
                        f"Row {excel_row}: legacy result "
                        "requires manual review"
                    )
                    continue

                if old_fingerprint != fingerprint:
                    record_result(
                        results,
                        excel_row,
                        fingerprint,
                        "Review Required - Input Changed",
                        "RESUME_CHECK",
                        "Excel row changed since previous run"
                    )
                    print(
                        f"Row {excel_row}: input changed, "
                        "manual review required"
                    )
                    continue

                if old.get("Booking_Status") in SKIP_STATUSES:
                    print(
                        f"Row {excel_row}: skipped "
                        f"({old['Booking_Status']})"
                    )
                    continue

            record_result(
                results,
                excel_row,
                fingerprint,
                "In Progress - Review Before Retry",
                "START",
                "Processing started"
            )

            try:
                status, stage, details = process(
                    driver, row
                )

            except Exception as exc:
                status, stage, details = classify_error(
                    exc
                )

                logging.exception(
                    "Row=%s stage=%s error=%s",
                    excel_row,
                    stage,
                    details
                )

            record_result(
                results,
                excel_row,
                fingerprint,
                status,
                stage,
                details
            )

            print(
                f"Row {excel_row}: {status}"
            )

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
