"""Local synthetic appointment mock only. Never use with real patient data or hospital systems."""
import csv
import logging
import os
import re
from datetime import date, datetime, time as dt_time
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / 'patients_appointments.xlsx'
STATUS = ROOT / 'booking_results.csv'
LOG = ROOT / 'appointment_errors.log'
URL = 'http://127.0.0.1:5000/booking'
WAIT_SECONDS = 12
FIELDS = ['Excel_Row', 'Booking_Status', 'Stage', 'Details', 'Updated_At']

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')

class BookingStageError(Exception):
    def __init__(self, stage, message):
        super().__init__(message)
        self.stage = stage

def as_text(value):
    return '' if pd.isna(value) else str(value).strip()

def synthetic_id(value):
    s = as_text(value)
    if s.endswith('.0'):
        s = s[:-2]
    if not re.fullmatch(r'900000000[1-6]', s):
        raise ValueError('Test environment only: synthetic IDs 9000000001–9000000006')
    return s

def date_text(value):
    if isinstance(value, (datetime, pd.Timestamp, date)):
        return value.strftime('%Y-%m-%d')
    s = as_text(value)
    if not s:
        raise ValueError('Missing ScheduleDate')
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
                '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    raise ValueError('Invalid ScheduleDate: ' + s)

def time_text(value):
    if isinstance(value, (datetime, pd.Timestamp, dt_time)):
        return value.strftime('%H:%M')
    s = as_text(value)
    for fmt in ('%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M:%S %p'):
        try:
            return datetime.strptime(s, fmt).strftime('%H:%M')
        except ValueError:
            pass
    raise ValueError('Invalid Time: ' + s)

def visit_type(value):
    s = as_text(value).lower()
    if s in ('0', '0.0'):
        return 'Followup Visit'
    if s in ('1', '1.0'):
        return 'TeleConsult'
    raise ValueError('Invalid IsVirtual: expected 0 or 1')

def load_rows():
    if not INPUT.exists():
        raise FileNotFoundError('Put patients_appointments.xlsx in the project folder')
    df = pd.read_excel(INPUT, dtype=str, keep_default_na=False)
    needed = ['ID type', 'PatientName', 'ScheduleDate', 'StartTime',
              'EndTime', 'IsVirtual', 'CLINICCODE', 'DoctorName']
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError('Missing columns: ' + ', '.join(missing))
    return df

def previous_results():
    if not STATUS.exists():
        return {}
    with STATUS.open(newline='', encoding='utf-8-sig') as f:
        return {int(r['Excel_Row']): r for r in csv.DictReader(f)}

def save_results(rows):
    temp = STATUS.with_suffix('.csv.tmp')
    with temp.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows[k] for k in sorted(rows))
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, STATUS)

def fill(driver, field, value):
    element = driver.find_element(By.ID, field)
    element.clear()
    element.send_keys(value)

def set_and_verify(driver, field, value):
    element = driver.find_element(By.ID, field)
    driver.execute_script('''
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
        arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
    ''', element, value)
    actual = driver.find_element(By.ID, field).get_attribute('value')
    if actual != value:
        raise BookingStageError('VERIFY_DATE_TIME',
            f'Appointment Date/Time Mismatch: {field}, Expected={value}, Actual={actual}')

def verify_date_time(driver, appointment_date, start, end):
    for field, expected in [('appointment_date', appointment_date),
                            ('start_time', start), ('end_time', end)]:
        actual = driver.find_element(By.ID, field).get_attribute('value')
        if actual != expected:
            raise BookingStageError('VERIFY_DATE_TIME',
                f'Appointment Date/Time Mismatch: {field}, Expected={expected}, Actual={actual}')

def table_snapshot(driver):
    # Atomic DOM read avoids stale Selenium row/cell references during table refresh.
    return driver.execute_script('''
        return Array.from(document.querySelectorAll('#bookings tr'))
          .map(tr => Array.from(tr.querySelectorAll('td'))
          .map(td => td.textContent.trim()));
    ''')

def verify_booking_in_table(driver, patient, clinic, appointment_date, start, doctor, visit):
    expected = [patient, clinic, appointment_date, start, doctor, visit, 'Booked']
    driver.find_element(By.ID, 'refresh').click()
    return WebDriverWait(driver, WAIT_SECONDS).until(
        lambda d: any(len(cells) >= 7 and cells[:7] == expected
                      for cells in table_snapshot(d)))

def wait_slot_result(driver):
    # The mock updates slot_message asynchronously. Never interpret an empty message as available.
    def ready(d):
        msg = d.find_element(By.ID, 'slot_message').text.strip()
        if not msg:
            return False
        lower = msg.lower()
        recognized = ('available slot', 'occupied slot', 'overbooking',
                      'no available slot', 'no slot', 'schedule not generated',
                      'already exists', 'invalid', 'error')
        return msg if any(word in lower for word in recognized) else False
    return WebDriverWait(driver, WAIT_SECONDS).until(ready)

def process(driver, row):
    stage = 'VALIDATE_EXCEL'
    try:
        national_id = synthetic_id(row['ID type'])
        patient = as_text(row['PatientName'])
        clinic = as_text(row['CLINICCODE']).upper()
        doctor = as_text(row['DoctorName'])
        appointment_date = date_text(row['ScheduleDate'])
        start = time_text(row['StartTime'])
        end = time_text(row['EndTime'])
        visit = visit_type(row['IsVirtual'])
        if not patient or not clinic or not doctor:
            raise ValueError('Missing patient/clinic/doctor')
        if clinic not in ('OPT1', 'NS04', 'SUBNS04'):
            raise ValueError('Schedule Not Generated: clinic not configured in mock')
        if end <= start:
            raise ValueError('Invalid Appointment Time: EndTime must be after StartTime')
    except Exception as exc:
        raise BookingStageError(stage, str(exc)) from exc

    stage = 'OPEN_BOOKING'
    try:
        driver.get(URL)
        WebDriverWait(driver, WAIT_SECONDS).until(
            lambda d: d.find_element(By.ID, 'clinic_code'))
        Select(driver.find_element(By.ID, 'clinic_code')).select_by_value(clinic)
        fill(driver, 'doctor_name', doctor)
    except Exception as exc:
        raise BookingStageError(stage, str(exc)) from exc

    stage = 'VERIFY_DATE_TIME'
    for field, value in [('appointment_date', appointment_date),
                         ('start_time', start), ('end_time', end)]:
        set_and_verify(driver, field, value)
    verify_date_time(driver, appointment_date, start, end)

    stage = 'PATIENT_SEARCH'
    try:
        fill(driver, 'national_id', national_id)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                              driver.find_element(By.ID, 'national_id'))
        WebDriverWait(driver, WAIT_SECONDS).until(
            lambda d: d.find_element(By.ID, 'patient_name').get_attribute('value')
            or d.find_element(By.ID, 'patient_message').text)
        actual = driver.find_element(By.ID, 'patient_name').get_attribute('value').strip()
        message = driver.find_element(By.ID, 'patient_message').text.strip()
        if not actual:
            raise BookingStageError(stage, message or 'Patient Not Found')
        if actual.casefold() != patient.casefold():
            raise BookingStageError(stage, 'Patient Name Mismatch')
        mobile = driver.find_element(By.ID, 'mobile').get_attribute('value').strip()
        if not re.fullmatch(r'\d{10}', mobile):
            raise BookingStageError(stage, 'Incomplete Mobile Number')
        if message:
            raise BookingStageError(stage, message)
    except BookingStageError:
        raise
    except Exception as exc:
        raise BookingStageError(stage, str(exc)) from exc

    stage = 'VISIT_TYPE'
    try:
        Select(driver.find_element(By.ID, 'visit_type')).select_by_visible_text(visit)
    except Exception as exc:
        raise BookingStageError(stage, 'Invalid Visit Type') from exc

    stage = 'SLOT_CHECK'
    try:
        driver.find_element(By.ID, 'check_slot').click()
        msg = wait_slot_result(driver)
        lower = msg.lower()
        if 'schedule not generated' in lower:
            raise BookingStageError(stage, 'Schedule Not Generated')
        if 'no available slot' in lower or 'no slot' in lower:
            raise BookingStageError(stage, 'No Slot')
        if 'occupied slot' in lower or 'overbooking required' in lower:
            button = driver.find_element(By.ID, 'overbook')
            if not button.is_displayed() or not button.is_enabled():
                raise BookingStageError(stage, 'Overbooking button not visible')
            button.click()
            WebDriverWait(driver, WAIT_SECONDS).until(
                lambda d: 'approved' in d.find_element(By.ID, 'slot_message').text.lower())
        elif 'available slot' not in lower and 'approved' not in lower:
            raise BookingStageError(stage, 'Unexpected slot result: ' + msg)
    except BookingStageError:
        raise
    except Exception as exc:
        raise BookingStageError(stage, str(exc)) from exc

    stage = 'PRE_SAVE'
    verify_date_time(driver, appointment_date, start, end)
    save = driver.find_element(By.ID, 'save')
    if not save.is_enabled():
        raise BookingStageError(stage, 'Save Button Disabled')

    stage = 'SAVE_CLICK'
    try:
        # Clear old result to ensure the next result belongs to this SAVE.
        driver.execute_script("document.getElementById('result').textContent = ''; ")
        save.click()
        stage = 'POST_SAVE'
        result = WebDriverWait(driver, WAIT_SECONDS).until(
            lambda d: d.find_element(By.ID, 'result').text.strip() or False)
        if not result.startswith('Successfully Saved'):
            # Explicit server rejection is a known failure; ambiguous outcomes stay uncertain.
            if result in ('Overbooking Required', 'Appointment Already Exists',
                          'No Slot', 'Schedule Not Generated'):
                raise BookingStageError(stage, result)
            raise BookingStageError(stage, 'Save Status Uncertain: ' + result)
        stage = 'VERIFY_BOOKING'
        verify_booking_in_table(driver, patient, clinic, appointment_date, start, doctor, visit)
    except BookingStageError:
        raise
    except Exception as exc:
        raise BookingStageError(stage, 'Save Status Uncertain') from exc
    return 'Successfully Saved', 'VERIFY_BOOKING', 'Verified in schedule with matching appointment date'

def classify_error(exc):
    details = str(exc).strip() or type(exc).__name__
    stage = getattr(exc, 'stage', 'UNKNOWN')
    if 'Appointment Date/Time Mismatch' in details:
        return 'Appointment Date Mismatch', stage, details
    if stage in ('SAVE_CLICK', 'POST_SAVE', 'VERIFY_BOOKING'):
        if details in ('Overbooking Required', 'Appointment Already Exists',
                       'No Slot', 'Schedule Not Generated'):
            return details, stage, details
        return 'Save Status Uncertain', stage, details
    known = {'Patient Not Found', 'Patient File Closed', 'Patient File Suspended',
             'Patient File closed', 'Patient File suspended', 'Incomplete Mobile Number',
             'Patient Name Mismatch', 'No Slot', 'Schedule Not Generated',
             'Overbooking button not visible', 'Save Button Disabled', 'Invalid Visit Type'}
    if details in known:
        return details, stage, details
    if isinstance(exc, (TimeoutException, WebDriverException)):
        return 'Automation Error', stage, details
    return 'Failed: ' + details[:160], stage, details

def main():
    url = urlparse(URL)
    if (url.scheme != 'http' or url.hostname not in ('127.0.0.1', 'localhost')
            or url.port != 5000 or url.path != '/booking'):
        raise RuntimeError('Refusing non-local mock URL')
    df = load_rows()
    results = previous_results()
    driver = webdriver.Chrome()
    try:
        driver.set_page_load_timeout(20)
        for index, row in df.iterrows():
            excel_row = index + 2
            old = results.get(excel_row, {})
            # All ambiguous and interrupted attempts require manual review.
            if old.get('Booking_Status') in (
                'Successfully Saved', 'Save Status Uncertain',
                'Appointment Already Exists', 'In Progress - Review Before Retry'):
                print(f'Row {excel_row}: skipped ({old["Booking_Status"]})')
                continue
            results[excel_row] = {
                'Excel_Row': excel_row,
                'Booking_Status': 'In Progress - Review Before Retry',
                'Stage': 'START', 'Details': 'Processing started',
                'Updated_At': datetime.now().isoformat(timespec='seconds')}
            save_results(results)
            try:
                result, stage, details = process(driver, row)
            except Exception as exc:
                result, stage, details = classify_error(exc)
                logging.exception('Row=%s stage=%s error=%s', excel_row, stage, details)
            results[excel_row] = {
                'Excel_Row': excel_row, 'Booking_Status': result,
                'Stage': stage, 'Details': details,
                'Updated_At': datetime.now().isoformat(timespec='seconds')}
            save_results(results)
            print(f'Row {excel_row}: {result}')
    finally:
        driver.quit()

if __name__ == '__main__':
    main()
