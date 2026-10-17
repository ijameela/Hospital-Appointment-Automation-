
"""Create synthetic Excel appointments for the local mock only."""

from pathlib import Path
import pandas as pd


BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "patients_appointments.xlsx"

if OUTPUT.exists():
    raise SystemExit(
        "File already exists; refusing to overwrite: "
        + str(OUTPUT)
    )


COLUMNS = [
    "ID type",
    "PatientName",
    "ScheduleDate",
    "StartTime",
    "EndTime",
    "IsVirtual",
    "CLINICCODE",
    "DoctorName"
]


ROWS = [
    # 1. Successful booking
    [
        "9000000001",
        "TEST PATIENT ONE",
        "18/02/2027",
        "10:30",
        "10:45",
        "0",
        "OPT1",
        "TEST DOCTOR"
    ],

    # 2. Same slot, different patient: OVER BOOKING
    [
        "9000000002",
        "TEST PATIENT TWO",
        "18/02/2027",
        "10:30",
        "10:45",
        "0",
        "OPT1",
        "TEST DOCTOR"
    ],

    # 3. Duplicate of the first appointment
    [
        "9000000001",
        "TEST PATIENT ONE",
        "18/02/2027",
        "10:30",
        "10:45",
        "0",
        "OPT1",
        "TEST DOCTOR"
    ],

    # 4. Successful virtual appointment
    [
        "9000000006",
        "TEST PATIENT SIX",
        "22/02/2027",
        "11:00",
        "11:15",
        "1",
        "SUBNS04",
        "TEST DOCTOR"
    ],

    # 5. Incomplete Mobile Number
    [
        "9000000005",
        "TEST PATIENT FIVE",
        "22/02/2027",
        "09:00",
        "09:15",
        "0",
        "NS04",
        "TEST DOCTOR"
    ],

    # 6. Patient File Closed
    [
        "9000000003",
        "TEST PATIENT THREE",
        "22/02/2027",
        "09:30",
        "09:45",
        "0",
        "NS04",
        "TEST DOCTOR"
    ],

    # 7. Suspended patient: error after SAVE
    [
        "9000000004",
        "TEST PATIENT FOUR",
        "22/02/2027",
        "10:00",
        "10:15",
        "0",
        "NS04",
        "TEST DOCTOR"
    ],

    # 8. No Third Name
    [
        "9000000007",
        "TEST PATIENT",
        "22/02/2027",
        "10:30",
        "10:45",
        "0",
        "NS04",
        "TEST DOCTOR"
    ],

    # 9. No available slot: Friday
    [
        "9000000006",
        "TEST PATIENT SIX",
        "19/02/2027",
        "11:00",
        "11:15",
        "1",
        "SUBNS04",
        "TEST DOCTOR"
    ],

    # 10. Schedule Not Generated
    [
        "9000000006",
        "TEST PATIENT SIX",
        "22/02/2027",
        "12:00",
        "12:15",
        "1",
        "SUBNS04",
        "UNSCHEDULED DOCTOR"
    ]
]


def main():
    dataframe = pd.DataFrame(
        ROWS,
        columns=COLUMNS
    )

    dataframe.to_excel(
        OUTPUT,
        index=False
    )

    print(
        f"Created {len(dataframe)} synthetic appointments:"
    )
    print(OUTPUT.name)


if __name__ == "__main__":
    main()
