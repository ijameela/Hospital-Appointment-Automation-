# Hospital Appointment Automation

### A Python and Selenium-Based Framework for Automated Appointment Scheduling

A healthcare appointment automation project designed to streamline appointment entry from Excel, reduce repetitive manual work, improve error tracking, and support reliable processing of appointment records.

The project includes a **tested local simulation environment (Mock System)** and a separate **automation script designed for the real hospital appointment scheduling system**.
---
## Problem Statement

Manual appointment scheduling in healthcare systems is time-consuming, repetitive, and prone to human errors, particularly when handling large volumes of patient appointments.

Key challenges include:

- **Manual Data Entry:** Repetitive tasks increase workload and processing time.
- **Human Errors:** Incorrect patient information, dates, or appointment details.
- **Duplicate Bookings:** Repeated attempts may create duplicate appointments.
- **Error Tracking:** Difficulty identifying booking failures and their causes.
- **System Timeouts:** Unexpected interruptions may affect appointment processing.
- **Process Recovery:** Difficulty resuming operations safely after interruptions.

This project aims to address these challenges through **reliable appointment automation, error tracking, and safe process recovery**.

---
## Project Objectives

The primary objective of this project is to **automate hospital appointment scheduling using Python and Selenium**, improving efficiency, accuracy, and reliability.

Key objectives include:

- **Automated Scheduling:** Read appointment data from Excel and automate appointment entry.
- **Data Validation:** Verify patient and appointment information before booking.
- **Error Detection:** Identify booking errors, including duplicate appointments and unavailable slots.
- **Error Logging:** Record booking results, failure reasons, and processing stages in Excel.
- **Timeout Handling:** Detect system delays and unexpected interruptions.
- **Safe Recovery:** Resume processing without automatically repeating uncertain bookings.
- **Testing:** Validate automation workflows using a local Mock System before real-system deployment.

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
| **Logging** | Records errors, exceptions, and processing stages for troubleshooting. |
| **CSV / Excel** | Stores appointment input data, processing results, and error reports. |

---
## How It Works

The appointment automation workflow is designed to process appointment records from Excel using Python and Selenium.

| Step | Description |
|---|---|
| **1. Manual Login** | The user logs into the hospital system using authorized credentials. |
| **2. Excel Data Extraction** | The script reads patient and appointment details from an Excel file. |
| **3. Data Validation** | Validates patient information, appointment dates, times, clinics, and visit types. |
| **4. Appointment Processing** | Searches for patients, selects appointment details, and processes bookings. |
| **5. Error Detection** | Identifies issues such as duplicate appointments, unavailable slots, invalid patient records, and timeouts. |
| **6. Result Logging** | Records each appointment's status, error type, and processing stage in an output file. |
| **7. Safe Recovery** | Skips completed or uncertain bookings during subsequent runs to prevent unintended duplicates. |

### Implementation Status

| System | Description |
|---|---|
| **Mock System** | The booking workflow and key error-handling scenarios have been tested locally. |
| **Real System** | A separate automation script has been developed for the hospital appointment scheduling system. |

---
## Testing & Results

The appointment automation workflow was evaluated using a local Mock System with synthetic patient data to assess booking functionality, error handling, and process reliability.

| Test Scenario | Result |
|---|---|
| Appointment Booking | Successfully tested |
| Overbooking | Successfully tested |
| Duplicate Appointment Detection | Successfully tested |
| Error Logging | Successfully tested |
| Timeout Detection | Successfully tested |
| Booking Status Tracking | Successfully tested |
| Interrupted-Row Handling | Successfully tested |
| Mock System Response Recovery | Successfully tested |

**Testing Environment:** Local Flask-based Mock System using synthetic patient records.

**Note:** These results are based on local simulation tests and do not represent testing on the real hospital system.

---
## Future Work

Future development will focus on enhancing the automation framework and extending its capabilities to the real hospital appointment scheduling system.

- **Real-System Automation:** Complete and validate automated appointment processing on the hospital scheduling interface.
- **Enhanced Error Handling:** Improve error classification, timeout handling, and recovery from unexpected interruptions.
- **Booking Verification:** Strengthen post-save verification to prevent duplicate or uncertain bookings.
- **Performance Optimization:** Improve processing efficiency and reliability for large Excel datasets.
- **Testing and Validation:** Conduct further testing to evaluate accuracy, stability, and operational readiness.

---
