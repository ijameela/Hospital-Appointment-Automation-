
"""Local-only synthetic appointment simulator; never connects to hospital systems."""

import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request


BASE = Path(__file__).resolve().parent
DB = BASE / 'mock_appointments.db'

app = Flask(__name__)


PATIENTS = {
    '9000000001': {
        'name': 'TEST PATIENT ONE',
        'mobile': '0500000001',
        'state': 'active'
    },
    '9000000002': {
        'name': 'TEST PATIENT TWO',
        'mobile': '0500000002',
        'state': 'active'
    },
    '9000000003': {
        'name': 'TEST PATIENT THREE',
        'mobile': '0500000003',
        'state': 'closed'
    },
    '9000000004': {
        'name': 'TEST PATIENT FOUR',
        'mobile': '0500000004',
        'state': 'suspended'
    },
    '9000000005': {
        'name': 'TEST PATIENT FIVE',
        'mobile': '0500000',
        'state': 'active'
    },
    '9000000006': {
        'name': 'TEST PATIENT SIX',
        'mobile': '0500000006',
        'state': 'active'
    },
    '9000000007': {
        'name': 'TEST PATIENT',
        'mobile': '0500000007',
        'state': 'active'
    }
}


CLINICS = {
    'OPT1': 'OPTOMETRY CLINIC',
    'NS04': 'NEUROLOGY CLINIC',
    'SUBNS04': 'VIRTUAL NEUROLOGY CLINIC'
}


VISIT_TYPES = [
    'Followup Visit',
    'ER Visit',
    'Investigation Visit',
    'Dental Visit',
    'Refill Visit',
    'TeleConsult',
    'Well Baby Visit'
]


# Demo schedules vary by clinic.
# Python weekday numbering: Monday = 0.

WORK_DAYS = {
    'OPT1': {1, 3},
    'NS04': {0, 2, 3},
    'SUBNS04': {0, 3}
}

DEMO_DOCTOR = 'TEST DOCTOR'


def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA busy_timeout=5000')
    return con


def init_db():
    with connect() as con:
        con.execute(
            '''CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_key TEXT UNIQUE NOT NULL,
                national_id TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                clinic_code TEXT NOT NULL,
                doctor_name TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                visit_type TEXT NOT NULL,
                created_at TEXT NOT NULL
            )'''
        )


def schedule_state(clinic, doctor, day_text):
    if (
        clinic not in CLINICS
        or not str(doctor or '').strip()
        or str(doctor).strip().upper() == 'UNSCHEDULED DOCTOR'
    ):
        return 'Schedule Not Generated'

    try:
        day = datetime.strptime(
            day_text, '%Y-%m-%d'
        ).date()

    except (ValueError, TypeError):
        return 'Invalid Date or Time'

    if day.weekday() not in WORK_DAYS[clinic]:
        return 'No available slot'

    return None

PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hospital Appointment Automation | Demo</title>

<style>
:root {
    --teal: #159a9c;
    --dark: #123b42;
    --light: #edf7f7;
    --border: #d6e6e6;
    --gray: #e4e7e9;
    --red: #bb3434;
}

* { box-sizing: border-box; }

body {
    margin: 0;
    font-family: "Segoe UI", Arial, sans-serif;
    background: #f3f7f8;
    color: #263b42;
}

button, input, select {
    font: inherit;
}

button {
    cursor: pointer;
}

button:disabled {
    opacity: .55;
    cursor: not-allowed;
}

.hidden {
    display: none !important;
}

/* Login */

#login_page {
    min-height: 100vh;
    display: grid;
    grid-template-columns: 1fr 1fr;
}

.login_left {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 35px;
    background: #f7fafb;
}

.login_card {
    width: 100%;
    max-width: 400px;
    padding: 35px;
    background: white;
    border-radius: 16px;
    box-shadow: 0 10px 35px #173e4415;
}

.login_card h1 {
    color: var(--dark);
    font-size: 25px;
}

.login_right {
    background: linear-gradient(145deg, #087b80, #17464d);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 50px;
}

.login_right h2 {
    font-size: 34px;
}

.login_right p {
    line-height: 1.8;
}

label {
    display: block;
    margin: 13px 0 6px;
    font-weight: 600;
    font-size: 13px;
}

input, select {
    width: 100%;
    padding: 10px;
    border: 1px solid #bfd1d3;
    border-radius: 7px;
    background: white;
    color: #263b42;
}

.primary {
    background: var(--teal);
    color: white;
    border: 0;
    border-radius: 7px;
    padding: 11px 18px;
}

.secondary {
    background: white;
    border: 1px solid var(--border);
    border-radius: 7px;
    padding: 10px 15px;
    color: var(--dark);
}

.danger {
    color: var(--red);
}

.muted {
    color: #6a8187;
}

.demo_note {
    background: var(--light);
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 13px;
    margin: 15px 0;
    font-size: 13px;
}

/* Main layout */

#dashboard {
    min-height: 100vh;
    display: flex;
}

.sidebar {
    width: 235px;
    background: var(--teal);
    color: white;
    padding: 24px 12px;
    flex-shrink: 0;
}

.sidebar h2 {
    font-size: 17px;
    padding: 0 12px 20px;
    border-bottom: 1px solid #ffffff40;
}

.nav_item {
    display: block;
    width: 100%;
    padding: 12px;
    margin: 5px 0;
    background: transparent;
    border: 0;
    border-radius: 8px;
    color: white;
    text-align: left;
}

.nav_item.active,
.nav_item:hover {
    background: #ffffff30;
}

.nav_sub {
    padding-left: 25px;
}

.content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
}

.topbar {
    background: white;
    padding: 17px 25px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.page {
    padding: 25px;
    flex: 1;
}

.panel {
    background: white;
    padding: 22px;
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 20px;
}

.filters {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
}

.page_title {
    font-size: 24px;
    margin: 0 0 18px;
}

/* Calendar */

.calendar_header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 15px;
}

.calendar_wrap {
    overflow-x: auto;
}

.calendar {
    display: grid;
    grid-template-columns: 80px repeat(7, minmax(115px, 1fr));
    min-width: 885px;
    gap: 3px;
}

.day_head {
    background: #e1f2f2;
    color: var(--dark);
    padding: 12px 5px;
    text-align: center;
    font-size: 12px;
    font-weight: 700;
}

.time_head {
    padding: 12px 4px;
    text-align: center;
    background: #f0f5f5;
    font-size: 12px;
}

.slot {
    min-height: 48px;
    border: 1px solid #d3e8e8;
    background: #d5f0ef;
    border-radius: 5px;
    color: #125c61;
    font-size: 12px;
}

.slot:hover:not(:disabled) {
    background: #aee1df;
}

.slot.unavailable {
    background: var(--gray);
    color: #889398;
    border-color: #d6dadd;
}

.slot.occupied {
    background: #b9e0e0;
}

.slot.missing {
    background: #e8e8e8;
    color: #909090;
}

/* Dialog */

.modal_backdrop {
    position: fixed;
    inset: 0;
    background: #102f3688;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
    z-index: 100;
}

.modal {
    width: 100%;
    max-width: 720px;
    max-height: 90vh;
    overflow-y: auto;
    background: white;
    border-radius: 12px;
    box-shadow: 0 20px 60px #0003;
}

.modal_title {
    padding: 15px 20px;
    background: var(--teal);
    color: white;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal_title button {
    background: transparent;
    color: white;
    border: 0;
    font-size: 23px;
}

.modal_body {
    padding: 22px;
}

.form_grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
}

.actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;
}

.message {
    padding: 12px;
    border-radius: 7px;
    margin-top: 12px;
    background: #eef7f7;
}

.message.error {
    background: #fceaea;
    color: var(--red);
}

.message.success {
    background: #e8f8ee;
    color: #177b48;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
}

th {
    background: #edf5f5;
}

footer {
    padding: 20px;
    text-align: center;
    font-size: 12px;
    color: #6a8187;
    border-top: 1px solid var(--border);
    background: white;
}

@media(max-width: 900px) {
    #login_page {
        grid-template-columns: 1fr;
    }

    .login_right {
        display: none;
    }

    .sidebar {
        width: 175px;
    }

    .filters {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media(max-width: 600px) {
    .sidebar {
        width: 120px;
    }

    .page {
        padding: 12px;
    }

    .filters, .form_grid {
        grid-template-columns: 1fr;
    }
}

.opd_toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: 600;
}

#opd_arrow {
    font-size: 17px;
    transition: transform 0.2s ease;
}

#opd_menu.hidden {
    display: none !important;
}
.bookings_header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 15px;
    flex-wrap: wrap;
    margin-bottom: 15px;
}

#reset_demo {
    color: #b42318;
    border: 1px solid #e6a6a0;
    background: #fff;
    font-weight: 600;
}

#reset_demo:hover {
    background: #fff0ee;
}

#reset_demo:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

</style>
</head>

<body>

<section id="login_page">
    <div class="login_left">
        <div class="login_card">
            <h1>Hospital Appointment Automation</h1>
            <p class="muted">Local Training Environment</p>

            <div class="demo_note">
                    <strong>Developed by Jameelah Algethami</strong>
        </div>

            <label>Username</label>
            <input id="login_username" value="demo"
                   autocomplete="off">

            <label>Password</label>
            <input id="login_password" type="password"
                   placeholder="Demo password">

            <button class="primary"
                    id="login_button"
                    style="width:100%;margin-top:20px">
                SIGN IN
            </button>

            <p id="login_error" class="danger"></p>
        </div>
    </div>

    <div class="login_right">
        <div>
            <h2>Appointment Management</h2>
            <p>
                 A dedicated Mock System for testing
                appointment automation, scheduling,
                validation and error handling.
            </p>
        </div>
    </div>
</section>

<div id="dashboard" class="hidden">

    <aside class="sidebar">
       
<button class="nav_item opd_toggle"
        id="nav_opd"
        type="button"
        aria-expanded="false"
        aria-controls="opd_menu">
    <span>OPD</span>
    <span id="opd_arrow">▸</span>
</button>

<div id="opd_menu" class="hidden">
    <button class="nav_item nav_sub active"
            id="nav_appointments"
            type="button">
        Appointments
    </button>

    <button class="nav_item nav_sub"
            id="nav_schedule"
            type="button">
        Careprovider Schedule
    </button>
</div>

    </aside>

    <div class="content">

        <header class="topbar">
            <strong>Hospital Appointment Automation</strong>
            <button class="secondary" id="logout">
                Log out
            </button>
        </header>

        <main class="page">

            <section id="appointments_page">

                <h1 class="page_title">Appointments</h1>

                <div class="panel">
                    <div class="filters">

                        <div>
                            <label>Department / Clinic</label>
                            <select id="clinic_code">
                                <option value="">Select clinic</option>
                                {% for code, name in clinics.items() %}
                                <option value="{{ code }}">
                                    {{ code }} — {{ name }}
                                </option>
                                {% endfor %}
                            </select>
                        </div>

                        <div>
                            <label>Care Provider</label>
                            <input id="doctor_name"
                                   value="TEST DOCTOR">
                        </div>

                        <div>
                            <label>Appointment Date</label>
                            <input id="appointment_date"
                                   type="date">
                        </div>

                        <div>
                            <label>Visit Type</label>
                            <select id="visit_type">
                                <option value="">Select visit type</option>
                                {% for visit in visits %}
                                <option value="{{ visit }}">
                                    {{ visit }}
                                </option>
                                {% endfor %}
                            </select>
                        </div>

                    </div>
                </div>

                <div class="panel">

                    <div class="calendar_header">
                        <h2>Weekly Schedule</h2>
                        <button class="secondary"
                                id="refresh">
                            Refresh Schedule
                        </button>
                    </div>

                    <div class="calendar_wrap">
                        <div class="calendar"
                             id="weekly_calendar"></div>
                    </div>

                    <p id="slot_message"
                       role="status"></p>
                </div>

                <div class="panel">

                <div class="bookings_header">
                       <h2>Booked Appointments</h2>

                                 <button class="secondary"
                                      id="reset_demo"
                                             type="button">
                                          Reset Demo Data
                                             </button>
    </div>

                    <div style="overflow-x:auto">
                        <table>
                            <thead>
                                <tr>
                                    <th>Patient</th>
                                    <th>Clinic</th>
                                    <th>Date</th>
                                    <th>Time</th>
                                    <th>Doctor</th>
                                    <th>Visit Type</th>
                                    <th>Status</th>
                                </tr>
                            </thead>

                            <tbody id="bookings"></tbody>
                        </table>
                    </div>
                </div>

            </section>

            <section id="schedule_page" class="hidden">

                <h1 class="page_title">
                    Careprovider Schedule
                </h1>

                <div class="panel">
                    <p class="muted">
                        Synthetic clinic schedules used
                        for appointment automation testing.
                    </p>

                    <table>
                        <thead>
                            <tr>
                                <th>Clinic</th>
                                <th>Care Provider</th>
                                <th>Working Days</th>
                                <th>Action</th>
                            </tr>
                        </thead>

                        <tbody>
                            {% for code, name in clinics.items() %}
                            <tr>
                                <td>{{ code }} — {{ name }}</td>
                                <td>TEST DOCTOR</td>
                                <td>
                                    {{ work_days[code] | join(', ') }}
                                </td>
                                <td>
                                    <button class="secondary"
                                            data-clinic="{{ code }}"
                                            onclick="viewSchedule(this.dataset.clinic)">
                                        VIEW
                                    </button>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>

            </section>

        </main>

        <footer>
            The training environment uses demo data only. No real patient information appears.
        </footer>

    </div>
</div>

<div id="booking_modal"
     class="modal_backdrop hidden">

    <div class="modal">

        <div class="modal_title">
            <strong>Book Appointment</strong>
            <button id="close_modal"
                    type="button">×</button>
        </div>

        <div class="modal_body">

            <div class="form_grid">

                <div>
                    <label>National ID / MRN</label>
                    <input id="national_id"
                           placeholder="9000000001">
                </div>

                <div>
                    <label>Patient Name</label>
                    <input id="patient_name"
                           readonly>
                </div>

                <div>
                    <label>Patient Mobile</label>
                    <input id="mobile"
                           readonly>
                </div>

                <div>
                    <label>Appointment Date</label>
                    <input id="modal_date"
                           readonly>
                </div>

                <div>
                    <label>From Time</label>
                    <input id="start_time"
                           readonly>
                </div>

                <div>
                    <label>To Time</label>
                    <input id="end_time"
                           readonly>
                </div>

            </div>

            <p id="patient_message"
               role="status"></p>

            <div id="notice"
                 class="message hidden">
                <span id="notice_text"></span>
                <button id="notice_ok"
                        class="secondary"
                        type="button">
                    OK
                </button>
            </div>

            <div id="appointment_detail"
                 class="hidden">

                <div class="demo_note">
                    Appointment Detail
                    <p id="detail_text"></p>
                </div>

                <button id="overbook"
                        class="secondary"
                        type="button">
                    OVER BOOKING
                </button>

            </div>

            <div class="actions">
                <button class="secondary"
                        id="cancel_booking"
                        type="button">
                    CANCEL
                </button>

                <button class="primary"
                        id="save"
                        type="button">
                    SAVE
                </button>
            </div>

            <p id="result"
               role="status"></p>

        </div>
    </div>
</div>

<script>
const el = id => document.getElementById(id);

let slotApproved = false;
let selectedSlot = null;
let calendarRequest = 0;

const TIMES = [
    "08:00", "08:15", "08:30", "08:45",
    "09:00", "09:15", "09:30", "09:45",
    "10:00", "10:15", "10:30", "10:45",
    "11:00", "11:15", "11:30", "11:45",
    "12:00", "12:15", "12:30", "12:45",
    "13:00", "13:15", "13:30", "13:45",
    "14:00", "14:15", "14:30", "14:45",
    "15:00", "15:15", "15:30", "15:45"
];

function localDateString(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function addDays(date, days) {
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    return result;
}

function addMinutes(time, minutes) {
    const [hours, mins] = time.split(":").map(Number);
    const total = hours * 60 + mins + minutes;

    return [
        String(Math.floor(total / 60)).padStart(2, "0"),
        String(total % 60).padStart(2, "0")
    ].join(":");
}

async function api(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();

    return data;
}

function showMessage(id, message, type = "") {
    const node = el(id);
    node.textContent = message || "";
    node.className = type ? `message ${type}` : "";
}

function showPage(page) {
    el("appointments_page").classList.toggle(
        "hidden", page !== "appointments"
    );

    el("schedule_page").classList.toggle(
        "hidden", page !== "schedule"
    );

    el("nav_appointments").classList.toggle(
        "active", page === "appointments"
    );

    el("nav_schedule").classList.toggle(
        "active", page === "schedule"
    );
}

function signIn() {
    const username = el("login_username").value.trim();
    const password = el("login_password").value;

    if (username !== "demo" || password !== "demo") {
        showMessage(
            "login_error",
            "Invalid demo credentials.",
            "error"
        );
        return;
    }

    el("login_page").classList.add("hidden");
    el("dashboard").classList.remove("hidden");

    showPage("appointments");
    renderCalendar();
    refreshBookings();
}

function logout() {
    el("dashboard").classList.add("hidden");
    el("login_page").classList.remove("hidden");

    el("login_password").value = "";
    closeBooking();
}

function viewSchedule(clinic) {
    el("clinic_code").value = clinic;
    showPage("appointments");
    renderCalendar();
}

function selectedFilters() {
    return {
        clinic_code: el("clinic_code").value,
        doctor_name: el("doctor_name").value.trim(),
        appointment_date: el("appointment_date").value,
        visit_type: el("visit_type").value
    };
}

async function renderCalendar() {
    const requestId = ++calendarRequest;
    const calendar = el("weekly_calendar");
    const filters = selectedFilters();

    calendar.replaceChildren();
    calendar.dataset.ready = "false";
    showMessage("slot_message", "");

    if (
        !filters.clinic_code ||
        !filters.doctor_name ||
        !filters.appointment_date
    ) {
        calendar.textContent =
            "Select clinic, care provider and date to load the schedule.";
        return;
    }

    const selectedDate = new Date(
        filters.appointment_date + "T12:00:00"
    );

    if (Number.isNaN(selectedDate.getTime())) {
        showMessage(
            "slot_message",
            "Invalid Date or Time",
            "error"
        );
        return;
    }

    const sundayOffset = selectedDate.getDay();
    const weekStart = addDays(selectedDate, -sundayOffset);

    const days = Array.from(
        { length: 7 },
        (_, index) => addDays(weekStart, index)
    );

    calendar.textContent = "Loading schedule...";

    try {
        const response = await api("/api/bookings");
        const bookings = response.bookings || [];

        const checks = await Promise.all(
            days.flatMap(day =>
                TIMES.map(async time => {
                    const params = new URLSearchParams({
                        clinic_code: filters.clinic_code,
                        doctor_name: filters.doctor_name,
                        appointment_date: localDateString(day),
                        start_time: time
                    });

                    return api("/api/slot?" + params);
                })
            )
        );

        if (requestId !== calendarRequest) {
            return;
        }

        calendar.replaceChildren();

        const corner = document.createElement("div");
        corner.className = "day_head";
        corner.textContent = "Time";
        calendar.appendChild(corner);

        days.forEach(day => {
            const head = document.createElement("div");
            head.className = "day_head";

            head.textContent = day.toLocaleDateString("en-GB", {
                weekday: "short",
                day: "2-digit",
                month: "2-digit"
            });

            calendar.appendChild(head);
        });

        TIMES.forEach((time, timeIndex) => {
            const timeHead = document.createElement("div");
            timeHead.className = "time_head";
            timeHead.textContent = time;
            calendar.appendChild(timeHead);

            days.forEach((day, dayIndex) => {
                const dateText = localDateString(day);
                const slotData = checks[
                    dayIndex * TIMES.length + timeIndex
                ];

                const matchingBookings = bookings.filter(b =>
                    b.clinic_code === filters.clinic_code &&
                    b.doctor_name === filters.doctor_name &&
                    b.appointment_date === dateText &&
                    b.start_time === time
                );

                const button = document.createElement("button");
                button.type = "button";
                button.className = "slot";

                button.dataset.date = dateText;
                button.dataset.time = time;

                if (!slotData.ok) {
                    button.disabled = true;

                    if (
                        slotData.message === "Schedule Not Generated"
                    ) {
                        button.classList.add("missing");
                    } else {
                        button.classList.add("unavailable");
                    }

                    button.title = slotData.message;
                    button.textContent = "Unavailable";

                } else if (slotData.count > 0) {
                    button.classList.add("occupied");

                    button.textContent =
                        `${slotData.count} Booked`;

                    button.addEventListener("click", () => {
                        openBooking(
                            dateText,
                            time,
                            slotData,
                            true
                        );
                    });

                } else {
                    button.textContent = "Available";

                    button.addEventListener("click", () => {
                        openBooking(
                            dateText,
                            time,
                            slotData,
                            false
                        );
                    });
                }

                calendar.appendChild(button);
            });
        });

        calendar.dataset.ready = "true";

    } catch (error) {
        if (requestId !== calendarRequest) {
            return;
        }

        calendar.textContent = "";

        showMessage(
            "slot_message",
            "Unable to load schedule.",
            "error"
        );
    }
}

function resetBookingForm() {
    for (const id of [
        "national_id",
        "patient_name",
        "mobile"
    ]) {
        el(id).value = "";
    }

    slotApproved = false;

    el("appointment_detail").classList.add("hidden");
    el("notice").classList.add("hidden");

    showMessage("patient_message", "");
    showMessage("result", "");

    el("save").disabled = false;
}

function openBooking(date, time, slotData, occupied) {
    resetBookingForm();

    selectedSlot = {
        clinic_code: el("clinic_code").value,
        doctor_name: el("doctor_name").value.trim(),
        appointment_date: date,
        start_time: time,
        end_time: addMinutes(time, 15),
        occupied: occupied
    };

    el("modal_date").value = date;
    el("start_time").value = time;
    el("end_time").value = selectedSlot.end_time;

    if (occupied) {
        el("appointment_detail").classList.remove("hidden");

        el("detail_text").textContent =
            `${date} ${time} — Existing appointment. ` +
            "Use OVER BOOKING to add another booking.";

        el("save").disabled = true;

    } else {
        slotApproved = true;
    }

    el("booking_modal").classList.remove("hidden");
}

function closeBooking() {
    el("booking_modal").classList.add("hidden");
    selectedSlot = null;
    slotApproved = false;
}

async function lookupPatient() {
    const nationalId = el("national_id").value.trim();

    el("patient_name").value = "";
    el("mobile").value = "";

    showMessage("patient_message", "");

    if (!nationalId) {
        return;
    }

    try {
        const result = await api(
            "/api/patient/" + encodeURIComponent(nationalId)
        );

        if (!result.ok) {
            showMessage(
                "patient_message",
                result.error || "No records found",
                "error"
            );
            return;
        }

        const patient = result.patient;

        if (patient.state === "closed") {
            showMessage(
                "patient_message",
                "Patient File Closed",
                "error"
            );
            return;
        }

        el("patient_name").value = patient.name;
        el("mobile").value = patient.mobile;

        if (patient.mobile.length !== 10) {
            showMessage(
                "patient_message",
                "Incomplete Mobile Number",
                "error"
            );

        } else if (patient.name.trim().split(/\s+/).length < 3) {
            showMessage(
                "patient_message",
                "No Third Name",
                "error"
            );

        } else {
            showMessage(
                "patient_message",
                "Patient found.",
                "success"
            );
        }

    } catch (error) {
        showMessage(
            "patient_message",
            "Patient lookup failed.",
            "error"
        );
    }
}

function approveOverbooking() {
    if (!selectedSlot || !selectedSlot.occupied) {
        return;
    }

    slotApproved = true;

    el("save").disabled = false;

    showMessage(
        "result",
        "Overbooking approved for this slot.",
        "success"
    );
}

async function saveBooking() {
    if (!selectedSlot) {
        return;
    }

    const saveButton = el("save");

    if (saveButton.disabled) {
        return;
    }

    const nationalId = el("national_id").value.trim();
    const patientName = el("patient_name").value.trim();
    const mobile = el("mobile").value.trim();

    if (!nationalId || !patientName) {
        showMessage(
            "result",
            "Required Fields Missing",
            "error"
        );
        return;
    }

    if (mobile.length !== 10) {
        showMessage(
            "result",
            "Incomplete Mobile Number",
            "error"
        );
        return;
    }

    if (patientName.split(/\s+/).length < 3) {
        showMessage(
            "result",
            "No Third Name",
            "error"
        );
        return;
    }

    const visitType = el("visit_type").value;

    if (!visitType) {
        showMessage(
            "result",
            "Select a visit type.",
            "error"
        );
        return;
    }

    const payload = {
        national_id: nationalId,
        patient_name: patientName,
        clinic_code: selectedSlot.clinic_code,
        doctor_name: selectedSlot.doctor_name,
        appointment_date: selectedSlot.appointment_date,
        start_time: selectedSlot.start_time,
        end_time: selectedSlot.end_time,
        visit_type: visitType,
        overbooking: slotApproved
    };

    saveButton.disabled = true;
    showMessage("result", "Saving appointment...");

    try {
        const response = await api("/api/save", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            showMessage(
                "result",
                response.error || "Booking failed.",
                "error"
            );
            return;
        }

        showMessage(
            "result",
            "Successfully Saved — " + response.booking_id,
            "success"
        );

        try {
            await refreshBookings();
            await renderCalendar();
        } catch (refreshError) {
            console.warn("Booking saved, but schedule refresh failed.", refreshError);
        }

    } catch (error) {
        showMessage(
            "result",
            "Request failed — verify booking status before retrying.",
            "error"
        );

    } finally {
        saveButton.disabled = false;
    }
}

async function refreshBookings() {
    const body = el("bookings");

    try {
        const result = await api("/api/bookings");
        const bookings = result.bookings || [];

        body.replaceChildren();

        if (!bookings.length) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");

            cell.colSpan = 7;
            cell.textContent = "No appointments booked yet.";

            row.appendChild(cell);
            body.appendChild(row);
            return;
        }

        bookings.forEach(booking => {
            const row = document.createElement("tr");

            const values = [
                booking.patient_name,
                booking.clinic_code,
                booking.appointment_date,
                booking.start_time,
                booking.doctor_name,
                booking.visit_type,
                "Booked"
            ];

            values.forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value ?? "";
                row.appendChild(cell);
            });

            body.appendChild(row);
        });

    } catch (error) {
        body.replaceChildren();

        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 7;
        cell.textContent = "Unable to load appointments.";

        row.appendChild(cell);
        body.appendChild(row);
    }
}

el("login_button").addEventListener("click", signIn);

el("login_password").addEventListener("keydown", event => {
    if (event.key === "Enter") {
        signIn();
    }
});

el("logout").addEventListener("click", logout);

el("nav_opd").addEventListener("click", () => {
    const menu = el("opd_menu");
    const isClosed = menu.classList.toggle("hidden");

    el("nav_opd").setAttribute(
        "aria-expanded",
        String(!isClosed)
    );

    el("opd_arrow").textContent = isClosed ? "▸" : "▾";
});
el("nav_appointments").addEventListener("click", () => {
    showPage("appointments");
});

el("nav_schedule").addEventListener("click", () => {
    showPage("schedule");
});

for (const id of [
    "clinic_code",
    "doctor_name",
    "appointment_date"
]) {
    el(id).addEventListener("change", renderCalendar);
}

el("refresh").addEventListener("click", async () => {
    await refreshBookings();
    await renderCalendar();
});
el("reset_demo").addEventListener("click", async () => {
    const confirmed = window.confirm(
        "Are you sure you want to delete all demo bookings?\n\n" +
        "Excel files and error logs will not be deleted."
    );

    if (!confirmed) {
        return;
    }

    const button = el("reset_demo");
    button.disabled = true;
    button.textContent = "Resetting...";

    try {
        const response = await api("/api/reset-demo", {
            method: "POST"
        });

        if (!response.ok) {
            throw new Error(
                response.message || "Reset failed."
            );
        }

        await refreshBookings();
        await renderCalendar();

        window.alert("Demo bookings cleared successfully.");

    } catch (error) {
        window.alert(
            "Unable to reset demo bookings: " + error.message
        );

    } finally {
        button.disabled = false;
        button.textContent = "Reset Demo Data";
    }
});
el("national_id").addEventListener("change", lookupPatient);

el("overbook").addEventListener("click", approveOverbooking);

el("save").addEventListener("click", saveBooking);

el("close_modal").addEventListener("click", closeBooking);

el("cancel_booking").addEventListener("click", closeBooking);

el("notice_ok").addEventListener("click", () => {
    el("notice").classList.add("hidden");
});

el("appointment_date").value = localDateString(new Date());
</script>
</body>
</html>
"""

@app.get('/')
def home():
    return booking()


@app.get('/booking')
def booking():
    readable_days = {
        code: [
            ['Monday', 'Tuesday', 'Wednesday',
             'Thursday', 'Friday', 'Saturday', 'Sunday'][day]
            for day in sorted(days)
        ]
        for code, days in WORK_DAYS.items()
    }

    return render_template_string(
        PAGE,
        clinics=CLINICS,
        visits=VISIT_TYPES,
        work_days=readable_days
    )


@app.get('/api/patient/<national_id>')
def patient(national_id):
    patient_data = PATIENTS.get(national_id.strip())

    if patient_data is None:
        return jsonify(
            ok=False,
            patient=None,
            error='No records found'
        )

    if patient_data['state'] == 'closed':
        return jsonify(
            ok=False,
            patient=None,
            error='Patient File Closed'
        )

    return jsonify(
        ok=True,
        patient=patient_data,
        error=None
    )


@app.get('/api/slot')
def slot():
    query = request.args

    clinic = str(query.get('clinic_code', '')).strip()
    doctor = str(query.get('doctor_name', '')).strip()
    appointment_date = str(
        query.get('appointment_date', '')
    ).strip()
    start_time = str(query.get('start_time', '')).strip()

    state = schedule_state(
        clinic,
        doctor,
        appointment_date
    )

    if state:
        return jsonify(
            ok=False,
            count=0,
            message=state
        )

    try:
        datetime.strptime(start_time, '%H:%M')
    except (ValueError, TypeError):
        return jsonify(
            ok=False,
            count=0,
            message='Invalid Date or Time'
        )

    with connect() as con:
        count = con.execute(
            '''
            SELECT COUNT(*)
            FROM appointments
            WHERE clinic_code = ?
              AND doctor_name = ?
              AND appointment_date = ?
              AND start_time = ?
            ''',
            (
                clinic,
                doctor,
                appointment_date,
                start_time
            )
        ).fetchone()[0]

    if count >= 3:
        return jsonify(
            ok=False,
            count=count,
            message='No available slot'
        )

    if count >= 1:
        return jsonify(
            ok=True,
            count=count,
            message='Occupied slot — use OVER BOOKING'
        )

    return jsonify(
        ok=True,
        count=0,
        message='Available slot'
    )

@app.post('/api/reset-demo')
def reset_demo_data():
    try:
        with connect() as con:
            con.execute('DELETE FROM appointments')
            con.commit()

        return jsonify(
            ok=True,
            message='Demo bookings cleared successfully.'
        )

    except Exception:
        app.logger.exception('Failed to reset demo bookings')

        return jsonify(
            ok=False,
            message='Unable to reset demo bookings.'
        ), 500

@app.get('/api/bookings')
def list_bookings():
    with connect() as con:
        rows = con.execute(
            '''
            SELECT *
            FROM appointments
            ORDER BY id DESC
            LIMIT 200
            '''
        ).fetchall()

    return jsonify(
        bookings=[dict(row) for row in rows]
    )


@app.get('/api/verify')
def verify():
    source_key = request.args.get(
        'source_key', ''
    ).strip()

    if not source_key:
        return jsonify(
            found=False,
            booking=None
        )

    with connect() as con:
        row = con.execute(
            '''
            SELECT *
            FROM appointments
            WHERE source_key = ?
            ''',
            (source_key,)
        ).fetchone()

    return jsonify(
        found=bool(row),
        booking=dict(row) if row else None
    )


@app.post('/api/save')
def save():
    data = request.get_json(silent=True) or {}

    def fail(message, status=400):
        return jsonify(
            ok=False,
            error=message
        ), status

    required = [
        'national_id',
        'patient_name',
        'clinic_code',
        'doctor_name',
        'appointment_date',
        'start_time',
        'end_time',
        'visit_type'
    ]

    if any(
        not str(data.get(field, '')).strip()
        for field in required
    ):
        return fail('Required Fields Missing')

    data = {
        key: value.strip()
        if isinstance(value, str)
        else value
        for key, value in data.items()
    }

    national_id = str(data['national_id'])
    patient_data = PATIENTS.get(national_id)

    if patient_data is None:
        return fail('No records found')

    if patient_data['state'] == 'closed':
        return fail('Patient File Closed')

    if patient_data['state'] == 'suspended':
        return fail(
            'This patient file is suspended'
        )

    if (
        patient_data['name'].casefold()
        != str(data['patient_name']).casefold()
    ):
        return fail('Patient Name Mismatch')

    if len(patient_data['name'].split()) < 3:
        return fail('No Third Name')

    if len(patient_data['mobile']) != 10:
        return fail('Incomplete Mobile Number')

    if data['visit_type'] not in VISIT_TYPES:
        return fail('Invalid Visit Type')

    state = schedule_state(
        data['clinic_code'],
        data['doctor_name'],
        data['appointment_date']
    )

    if state:
        return fail(state)

    try:
        start = datetime.strptime(
            data['start_time'],
            '%H:%M'
        )

        end = datetime.strptime(
            data['end_time'],
            '%H:%M'
        )

        if end <= start:
            return fail('Invalid Time Range')

    except (ValueError, TypeError):
        return fail('Invalid Date or Time')

    source_key = '|'.join(
        str(data[field])
        for field in [
            'national_id',
            'clinic_code',
            'doctor_name',
            'appointment_date',
            'start_time',
            'end_time'
        ]
    )

    with connect() as con:
        con.execute('BEGIN IMMEDIATE')

        existing = con.execute(
            '''
            SELECT id
            FROM appointments
            WHERE source_key = ?
            ''',
            (source_key,)
        ).fetchone()

        if existing:
            return fail(
                'Appointment Already Exists',
                409
            )

        same_patient = con.execute(
            '''
            SELECT id
            FROM appointments
            WHERE national_id = ?
              AND appointment_date = ?
              AND start_time = ?
            ''',
            (
                national_id,
                data['appointment_date'],
                data['start_time']
            )
        ).fetchone()

        if same_patient:
            return fail(
                'Appointment Already Exists',
                409
            )

        count = con.execute(
            '''
            SELECT COUNT(*)
            FROM appointments
            WHERE clinic_code = ?
              AND doctor_name = ?
              AND appointment_date = ?
              AND start_time = ?
            ''',
            (
                data['clinic_code'],
                data['doctor_name'],
                data['appointment_date'],
                data['start_time']
            )
        ).fetchone()[0]

        if count >= 3:
            return fail(
                'No available slot',
                409
            )

        if (
            count >= 1
            and data.get('overbooking') is not True
        ):
            return fail(
                'Overbooking Required',
                409
            )

        cursor = con.execute(
            '''
            INSERT INTO appointments (
                source_key,
                national_id,
                patient_name,
                clinic_code,
                doctor_name,
                appointment_date,
                start_time,
                end_time,
                visit_type,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                source_key,
                national_id,
                patient_data['name'],
                data['clinic_code'],
                data['doctor_name'],
                data['appointment_date'],
                data['start_time'],
                data['end_time'],
                data['visit_type'],
                datetime.now().isoformat()
            )
        )

        return jsonify(
            ok=True,
            booking_id=cursor.lastrowid
        )


if __name__ == '__main__':
    init_db()

    app.run(
        host='127.0.0.1',
        port=5000,
        debug=False
    )
