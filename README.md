# Hospital Appointment Automation

**Python · Selenium · Flask · SQLite · Pandas**

Two separate components are included for a technical demonstration:

| Component | Purpose | Verified status |
|---|---|---|
| `mock-system/` | Synthetic local booking UI and Selenium booking automation | Tested in the local mock; not a hospital system |
| `real-system/` | RABET integration candidate: manual login, Excel validation, stage-specific results, configurable selectors | **Not integrated or tested on RABET; not production ready** |

> **Important:** The real-system script is not a completed unattended booking bot. HTML selectors have not been verified, and schedule navigation and exact patient search result selection still require human involvement. It defaults to preview mode (no Save). Do not describe this as a production-ready solution.

## Repository structure

```text
mock-system/
  mock_app.py
  appointment_script.py
  create_sample_data.py
real-system/
  rabet_booking.py
  selectors.example.json
docs/
  TEST_RESULTS.md
  PRODUCTION_READINESS.md
requirements.txt
.gitignore
```

## Demonstrate the mock locally (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe mock-system\create_sample_data.py
```

Terminal 1:

```powershell
.\.venv\Scripts\python.exe mock-system\mock_app.py
```

Terminal 2:

```powershell
.\.venv\Scripts\python.exe mock-system\appointment_script.py
```

The mock is local only at `http://127.0.0.1:5000/booking`, and the mock Selenium script accepts only synthetic patient IDs. Do not modify it to target a hospital system.

## Real-system integration candidate

`real-system/rabet_booking.py` reads an **existing, local** Excel file with the following column names:

`ID type`, `PatientName`, `ScheduleDate`, `StartTime`, `EndTime`, `IsVirtual`, `CLINICCODE`, `DoctorName`.

It opens a configured **approved HTTPS** URL, waits for **manual login**, validates rows, and saves status/error information to a **separate local Excel file** without copying patient names or IDs. The original input workbook is not modified.

The provided `selectors.example.json` is deliberately incomplete: screenshots cannot reveal reliable HTML locators. On an authorized test environment, make a **local, private** copy named `selectors.json`, supply the approved host and verified locators, and run from the `real-system` directory:

```powershell
Copy-Item selectors.example.json selectors.json
..\.venv\Scripts\python.exe rabet_booking.py --excel "C:\private\appointments.xlsx" --config selectors.json --results "C:\private\booking_results.xlsx"
```

**Default is preview/no-save.** Do not enable submissions on a live clinical system. This candidate still requires implementation and formal testing of navigation, patient identity matching, error behavior, duplicate handling, post-save reconciliation, and overbooking approval before any clinical use.

## Testing and security

- See [`docs/TEST_RESULTS.md`](docs/TEST_RESULTS.md) for mock testing evidence and limitations.
- See [`docs/PRODUCTION_READINESS.md`](docs/PRODUCTION_READINESS.md) for remaining integration tasks.
- Never commit actual patient Excel files, output results, screenshots showing patients, passwords, cookies, internal system hostnames, or logs. `.gitignore` helps, but manually check the upload selection and repository history.
- This public repository contains no actual patient records or production portal configuration.

## Current status

**Proof of concept tested on a synthetic local mock. Real-system integration candidate remains unverified and must not be represented as deployed.**
