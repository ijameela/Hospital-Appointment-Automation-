
# Hospital Appointment Automation

A healthcare appointment automation project designed to streamline appointment entry from Excel, reduce repetitive manual work, improve error tracking, and support reliable processing of appointment records.

---

## Problem Statement

Manual appointment scheduling in healthcare systems is time-consuming, repetitive, and prone to human errors, particularly when handling large volumes of patient appointments.

Key challenges include:

- **Manual Data Entry:** Repetitive tasks increase workload and processing time.
- **Human Errors:** Incorrect patient information, dates, or appointment details.
  
This project aims to address these challenges through **reliable appointment automation, error tracking, and safe process recovery**.

---

## Project Objectives

The primary objective of this project is to **automate hospital appointment scheduling using Python and Selenium**, improving efficiency, accuracy, and reliability.

Key objectives include:

- **Automated Scheduling:** Read appointment data from Excel and automate appointment entry.
- **Data Validation:** Verify patient and appointment information before booking.
- **Error Detection:** Identify booking errors, including duplicate appointments and unavailable slots.
- **Error Logging:** Record booking results, failure reasons, and processing stages in Excel, CSV, and log files.
- **Timeout Handling:** Detect system delays and unexpected interruptions.
- **Safe Recovery:** Resume processing without automatically repeating completed or uncertain bookings.
- **Testing:** Validate automation workflows using a local Mock System with synthetic patient records.

---

## Technologies Used

The project utilizes the following technologies to automate appointment scheduling, validate data, and manage errors.

| Technology | Purpose |
|---|---|
| **Python** | Develops and controls the appointment automation workflow. |
| **Selenium WebDriver** | Automates browser interactions, including patient searches, form entry, and appointment processing. |
| **Pandas** | Reads and validates appointment data from Excel files. |
| **OpenPyXL** | Supports Excel file processing and recording booking results. |
| **Flask** | Provides a local web application for simulating the appointment scheduling system. |
| **SQLite** | Stores simulated patient appointments and booking records. |
| **Logging** | Records errors, exceptions, timestamps, and processing stages for troubleshooting. |
| **Excel** | Stores appointment input data, processing results, and error reports. |

---

## Testing & Results

The appointment automation workflow was evaluated using a **local Flask-based Mock System with synthetic patient data**.

The tests focused on appointment processing, error detection, logging, and recovery behavior.

### Functional Testing

| Test Scenario | Expected Behavior | Result |
|---|---|---|
| **Successful Appointment Booking** | Save an appointment and verify its existence in the database. | Passed |
| **Overbooking** | Process an appointment using the supported overbooking workflow. | Passed |
| **Duplicate Appointment Detection** | Identify an existing appointment and avoid creating another booking. | Passed |
| **Incomplete Mobile Number** | Detect invalid patient contact information. | Passed |
| **Patient File Closed** | Identify a closed patient file and record the failure. | Passed |
| **Patient File Suspended** | Detect a suspended patient file and record the error. | Passed |
| **No Third Name** | Identify incomplete patient name information. | Passed |
| **No Available Slot** | Detect unavailable appointment slots. | Passed |
| **Schedule Not Generated** | Detect when the appointment schedule is unavailable. | Passed |
| **Booking Verification** | Confirm that a successful booking exists in the Mock System database. | Passed |

### Reliability & Recovery Testing

| Test Scenario | Expected Behavior | Result |
|---|---|---|
| **Resume Functionality** | Skip previously processed appointments during subsequent runs. | Passed |
| **Row-Level Tracking** | Record the Excel row number associated with each booking result. | Passed |
| **Timeout Handling** | Classify and record a simulated timeout with its processing stage. | Passed (Simulated) |
| **Continue After Timeout** | Continue processing the next appointment after a simulated timeout. | Passed |
| **Unknown Error Handling** | Classify and record a simulated unexpected error without terminating the entire process. | Passed (Simulated) |
| **Excel Status Tracking** | Write booking status, error reason, stage, and timestamp into Excel. | Passed |
| **Detailed Error Logging** | Record timestamps, Excel row numbers, error details, stages, and exception tracebacks. | Passed |

### Resume Testing

The Resume mechanism was tested by executing the automation script multiple times against the same Excel dataset.

Previously processed appointments were automatically skipped, while newly added rows were processed.

This mechanism supports:

- Avoiding unnecessary reprocessing of completed appointments.
- Preserving previous booking results.
- Tracking individual records using Excel row numbers and row fingerprints.
- Identifying records requiring manual review before retrying.
- Continuing appointment processing after previous runs.

### Timeout Handling Test

A controlled timeout error was simulated during the `CALENDAR_LOAD` stage.

The automation successfully:

1. Detected and classified the simulated timeout.
2. Recorded the affected Excel row number.
3. Identified the processing stage as `CALENDAR_LOAD`.
4. Saved the error details in Excel, CSV, and the error log.
5. Continued processing the next appointment.


### Unknown Error Handling Test

An unexpected error was intentionally simulated during the `PATIENT_LOOKUP` stage.

The error was classified and recorded with its timestamp, row number, processing stage, and exception details.

### Error Reporting

The automation maintains three reporting mechanisms:

| File | Purpose |
|---|---|
| **patients_appointments.xlsx** | Stores appointment input data and updates the processing status of each row. |
| **booking_results.csv** | Maintains a record of booking results, row fingerprints, stages, details, and timestamps. |
| **appointment_errors.log** | Stores detailed error messages, processing stages, and exception tracebacks. |

### Testing Summary

The completed local tests demonstrated:

- Successful automated appointment processing.
- Duplicate detection and booking verification.
- Identification of common patient and scheduling errors.
- Row-level error tracking and detailed logging.
- Resume functionality across repeated executions.
- Handling of simulated timeout and unexpected error scenarios.
- Continuation of processing after a simulated timeout.

---

**File Descriptions:**

| File | Description |
|---|---|
| `mock_app.py` | Local Flask appointment scheduling application. |
| `appointment_script.py` | Selenium automation script used for local testing. |
| `create_sample_data.py` | Generates synthetic appointment test data. |
| `production.py` | Production-oriented appointment automation script (in development). |
| `README.md` | Project documentation and testing results. |
| `requirements.txt` | Python package dependencies. |
| `.gitignore` | Excludes local environments, generated files, and sensitive data from version control. |

---

**Developed by Jameelah Algethami**
