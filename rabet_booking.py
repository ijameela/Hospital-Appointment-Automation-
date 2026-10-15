"""RABET Selenium integration candidate. Requires approved selectors and authorized testing.

Default mode is preview only. Never commit patient workbooks or logs to GitHub.
"""
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select

REQUIRED = ['ID type', 'PatientName', 'ScheduleDate', 'StartTime', 'EndTime', 'IsVirtual', 'CLINICCODE', 'DoctorName']
COLUMNS = ['Excel_Row', 'Booking_Status', 'Stage', 'Error_Type', 'Details', 'Updated_At']
SKIP = {'Successfully Saved', 'Save Status Uncertain', 'In Progress - Review Before Retry', 'Appointment Already Exists'}
ERROR_PATTERNS = {
    'Appointment Already Exists': ['appointment already exists', 'duplicate appointment'],
    'Patient Not Found': ['patient not found', 'no record found'],
    'Patient File Closed': ['patient file closed', 'file closed'],
    'Patient File Suspended': ['patient file suspended', 'file suspended'],
    'Incomplete Mobile Number': ['incomplete mobile', 'invalid mobile'],
    'No Third Name': ['no third name', 'third name required'],
    'Schedule Not Generated': ['schedule not generated'],
    'No Slot': ['no slot', 'no available slot'],
    'Overbooking Required': ['overbooking required', 'over booking required'],
}

class StageError(Exception):
    def __init__(self, stage, message):
        super().__init__(message)
        self.stage = stage

def normalize_date(v):
    s = str(v).strip()
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(s, fmt).strftime('%d-%m-%Y')
        except ValueError:
            pass
    raise ValueError('Invalid ScheduleDate')

def normalize_time(v):
    s = str(v).strip()
    for fmt in ('%H:%M', '%H:%M:%S', '%I:%M %p'):
        try:
            return datetime.strptime(s, fmt).strftime('%H:%M')
        except ValueError:
            pass
    raise ValueError('Invalid appointment time')

def validate(row):
    p = {key: str(row[key]).strip() for key in REQUIRED}
    if not re.fullmatch(r'\d{10}', p['ID type']):
        raise ValueError('Invalid ID format; expected 10 digits')
    for key in ('PatientName', 'CLINICCODE', 'DoctorName'):
        if not p[key]:
            raise ValueError(f'Missing {key}')
    p['ScheduleDate'] = normalize_date(p['ScheduleDate'])
    p['StartTime'] = normalize_time(p['StartTime'])
    p['EndTime'] = normalize_time(p['EndTime'])
    if p['EndTime'] <= p['StartTime']:
        raise ValueError('EndTime must be later than StartTime')
    flag = p['IsVirtual'].removesuffix('.0')
    if flag not in ('0', '1'):
        raise ValueError('IsVirtual must be 0 or 1')
    p['VisitType'] = 'TeleConsult' if flag == '1' else 'Followup Visit'
    return p

def error_type(message):
    low = message.lower()
    for label, terms in ERROR_PATTERNS.items():
        if any(t in low for t in terms):
            return label
    return 'Unexpected Error'

def record(results, path, row_num, status, stage, error='', details=''):
    # Only row number and generic error details; never write identifiers or patient names.
    results[row_num] = dict(Excel_Row=row_num, Booking_Status=status, Stage=stage,
                            Error_Type=error, Details=details[:180],
                            Updated_At=datetime.now().isoformat(timespec='seconds'))
    frame = pd.DataFrame([results[k] for k in sorted(results)], columns=COLUMNS)
    temp = path.with_name(path.stem + '.tmp.xlsx')
    frame.to_excel(temp, index=False, engine='xlsxwriter')
    os.replace(temp, path)

def read_results(path):
    if not path.exists():
        return {}
    frame = pd.read_excel(path, dtype=str, keep_default_na=False)
    return {int(r['Excel_Row']): r.to_dict() for _, r in frame.iterrows()}

def loc(config, key):
    value = config.get('selectors', {}).get(key)
    if not value or len(value) != 2 or value[0] not in ('css', 'xpath', 'id', 'name'):
        raise StageError('CONFIG', f'Missing or unverified selector: {key}')
    return {'css': By.CSS_SELECTOR, 'xpath': By.XPATH, 'id': By.ID, 'name': By.NAME}[value[0]], value[1]

def element(driver, config, key, timeout=15):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located(loc(config, key)))

def set_field(driver, config, key, value):
    el = element(driver, config, key)
    if el.tag_name.lower() == 'select':
        Select(el).select_by_visible_text(value)
    else:
        el.clear()
        el.send_keys(value)
    # Read back only for simple text controls; custom calendar/time widgets need tested adapters.
    if el.tag_name.lower() in ('input', 'textarea') and (el.get_attribute('value') or '').strip() != value:
        raise StageError('VERIFY_FIELDS', f'Field did not retain expected value: {key}')

def visible_message(driver, config, key):
    return element(driver, config, key).text.strip()

def ensure_approved_host(url, config):
    parsed = urlparse(url)
    host = config.get('approved_host', '').strip().lower()
    if not host or parsed.scheme != 'https' or parsed.hostname != host:
        raise ValueError('HTTPS URL must match approved_host in config')

def booking_flow(driver, config, p, submit):
    # The schedule's clinic, doctor, date and slot must be opened manually until verified locators exist.
    input('Open the correct clinic, doctor, date and EMPTY Book Appointment dialog; then press Enter... ')
    if not element(driver, config, 'patient_search').is_displayed():
        raise StageError('OPEN_BOOKING', 'Booking dialog not visible')
    stage = 'VERIFY_CONTEXT'
    # Explicitly require human verification for schedule context; screenshots cannot establish DOM locators.
    print(f"Verify clinic={p['CLINICCODE']}, doctor={p['DoctorName']}, date={p['ScheduleDate']}, time={p['StartTime']}-{p['EndTime']}")
    if input('Does the booking dialog match this schedule? Type YES: ').strip() != 'YES':
        raise StageError(stage, 'Schedule context not confirmed')
    stage = 'PATIENT_SEARCH'
    set_field(driver, config, 'patient_search', p['ID type'])
    element(driver, config, 'patient_search_button').click()
    # Search result selection is purposely manual until row selectors and exact-ID comparison are verified.
    input('Inspect search results, select the EXACT matching patient record, then press Enter... ')
    stage = 'VERIFY_PATIENT'
    selected_id = element(driver, config, 'selected_patient_id').get_attribute('value') or element(driver, config, 'selected_patient_id').text
    if selected_id.strip() != p['ID type']:
        raise StageError(stage, 'Patient ID Mismatch')
    stage = 'FILL_APPOINTMENT'
    for key, value in (('appointment_date', p['ScheduleDate']), ('start_time', p['StartTime']),
                       ('end_time', p['EndTime']), ('visit_type', p['VisitType'])):
        set_field(driver, config, key, value)
    print('Booking form populated. Check patient, clinic, doctor, date, time, and visit type.')
    if not submit:
        return 'Preview Only - Not Booked', 'PRE_SAVE', '', 'Save not clicked (default preview mode)'
    if input('Authorized test only: type APPROVE SAVE to submit this ONE appointment: ').strip() != 'APPROVE SAVE':
        return 'Not Submitted', 'PRE_SAVE', '', 'User declined submission'
    stage = 'SAVE_CLICK'
    element(driver, config, 'save_button').click()
    stage = 'POST_SAVE'
    try:
        msg = WebDriverWait(driver, 15).until(lambda d: visible_message(d, config, 'save_message') or False)
    except Exception as exc:
        raise StageError(stage, 'Save Status Uncertain: no confirmation returned') from exc
    err = error_type(msg)
    if err != 'Unexpected Error':
        raise StageError(stage, err)
    # A success banner alone is not sufficient to mark booking as confirmed.
    return 'Save Status Uncertain', 'VERIFY_BOOKING', '', 'Manual schedule verification required after Save'

def main():
    parser = argparse.ArgumentParser(description='RABET booking integration candidate')
    parser.add_argument('--excel', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=Path('selectors.json'))
    parser.add_argument('--results', type=Path, default=Path('booking_results.xlsx'))
    parser.add_argument('--enable-save', action='store_true', help='Requires per-appointment confirmation; approved test only')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    url = config.get('login_url', '')
    ensure_approved_host(url, config)
    df = pd.read_excel(args.excel, dtype=str, keep_default_na=False)
    missing = [k for k in REQUIRED if k not in df.columns]
    if missing:
        raise ValueError('Missing columns: ' + ', '.join(missing))
    results = read_results(args.results)
    driver = webdriver.Chrome()
    try:
        driver.set_page_load_timeout(30)
        driver.get(url)
        input('Log in MANUALLY in Chrome (including MFA), then press Enter... ')
        ensure_approved_host(driver.current_url, config)
        for idx, row in df.iterrows():
            n = idx + 2
            if results.get(n, {}).get('Booking_Status') in SKIP:
                print(f'Row {n}: skipped; requires review or already processed')
                continue
            record(results, args.results, n, 'In Progress - Review Before Retry', 'START')
            try:
                p = validate(row)
                status, stage, err, details = booking_flow(driver, config, p, args.enable_save)
            except StageError as exc:
                stage, details = exc.stage, str(exc)
                err = error_type(details)
                status = 'Save Status Uncertain' if stage in ('SAVE_CLICK', 'POST_SAVE', 'VERIFY_BOOKING') else 'Failed'
            except (TimeoutException, WebDriverException) as exc:
                stage, details, err = 'SELENIUM', type(exc).__name__, 'Automation Error'
                status = 'Save Status Uncertain' if args.enable_save else 'Failed'
            except Exception as exc:
                stage, details, err = 'VALIDATE_OR_UI', type(exc).__name__, 'Unexpected Error'
                status = 'Failed'
            record(results, args.results, n, status, stage, err, details)
            print(f'Excel row {n}: {status} / {stage} / {err}')
    finally:
        driver.quit()

if __name__ == '__main__':
    main()
