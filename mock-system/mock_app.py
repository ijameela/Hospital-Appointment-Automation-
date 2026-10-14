"""Local-only synthetic appointment booking UI. No connection to hospital systems."""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request

BASE = Path(__file__).resolve().parent
DB = BASE / 'mock_appointments.db'
app = Flask(__name__)

PATIENTS = {
    '9000000001': {'name': 'TEST PATIENT ONE', 'mobile': '0500000001', 'state': 'active'},
    '9000000002': {'name': 'TEST PATIENT TWO', 'mobile': '0500000002', 'state': 'active'},
    '9000000003': {'name': 'TEST PATIENT THREE', 'mobile': '0500000003', 'state': 'closed'},
    '9000000004': {'name': 'TEST PATIENT FOUR', 'mobile': '0500000004', 'state': 'suspended'},
    '9000000005': {'name': 'TEST PATIENT FIVE', 'mobile': '0500000', 'state': 'active'},
    '9000000006': {'name': 'TEST PATIENT SIX', 'mobile': '0500000006', 'state': 'active'},
}
CLINICS = {'OPT1': 'OPTOMETRY CLINIC', 'NS04': 'NEUROLOGY CLINIC', 'SUBNS04': 'VIRTUAL NEUROLOGY CLINIC'}
VISIT_TYPES = ['Followup Visit','ER Visit','Investigation Visit','Dental Visit','Refill Visit','TeleConsult','Well Baby Visit']

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_key TEXT UNIQUE NOT NULL,
            national_id TEXT NOT NULL, patient_name TEXT NOT NULL,
            clinic_code TEXT NOT NULL, doctor_name TEXT NOT NULL,
            appointment_date TEXT NOT NULL, start_time TEXT NOT NULL,
            end_time TEXT NOT NULL, visit_type TEXT NOT NULL,
            created_at TEXT NOT NULL)''')

PAGE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Appointment Mock</title>
<style>body{font:15px Arial,sans-serif;max-width:1050px;margin:28px auto;color:#26364b;background:#f6f8fb}main{background:white;padding:24px;border-radius:12px;box-shadow:0 3px 18px #dde2eb}h1{color:#124e66}label{display:block;font-size:13px;font-weight:bold;margin-top:12px}input,select{padding:9px;width:100%;box-sizing:border-box;border:1px solid #bdc9d6;border-radius:5px}button{background:#0b7b86;color:white;border:0;border-radius:6px;padding:11px 18px;cursor:pointer;margin-top:14px}button:disabled{background:#aaa;cursor:not-allowed}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.note{background:#e9f5fa;padding:10px;border-radius:6px}.error{color:#ad2437}.ok{color:#126c3e}table{border-collapse:collapse;width:100%;margin-top:15px}td,th{border-bottom:1px solid #dfe4ec;padding:9px;text-align:left}#notice{display:none;background:#fff5d9;padding:10px;border:1px solid #e6d098;margin-top:12px}</style></head>
<body><main><h1>Appointment Booking — Test Environment</h1><p class="note">Synthetic patients only. No hospital connection. Choose clinic/date/time, patient, visit type, then save.</p>
<div class="grid"><div><label>Clinic Code</label><select id="clinic_code"><option value="">Select</option>{% for code,name in clinics.items() %}<option value="{{code}}">{{code}} — {{name}}</option>{% endfor %}</select></div><div><label>Doctor Name</label><input id="doctor_name" value="TEST DOCTOR"></div><div><label>Appointment Date</label><input id="appointment_date" type="date"></div><div><label>From Time</label><input id="start_time" type="time"></div><div><label>To Time</label><input id="end_time" type="time"></div><div><label>Search National ID or MRN</label><input id="national_id" placeholder="9000000001"></div><div><label>Patient Name (from Excel)</label><input id="patient_name" readonly></div><div><label>Patient Mobile</label><input id="mobile" readonly></div><div><label>Visit Type</label><select id="visit_type"><option value="">Select visit type</option>{% for v in visits %}<option>{{v}}</option>{% endfor %}</select></div></div>
<div id="notice"><span id="notice_text"></span> <button id="notice_ok" type="button">OK</button></div>
<p id="patient_message"></p><p id="slot_message"></p><button id="check_slot" type="button">Check Slot / Overbooking</button> <button id="overbook" type="button" style="display:none">+ OVER BOOKING</button> <button id="save" type="button">SAVE</button><p id="result" role="status"></p>
<h2>Booked Appointments</h2><button id="refresh" type="button">Refresh Schedule</button><table><thead><tr><th>Patient</th><th>Clinic</th><th>Date</th><th>From</th><th>Doctor</th><th>Visit</th><th>Status</th></tr></thead><tbody id="bookings"></tbody></table></main>
<script>
const el = id=>document.getElementById(id);let slotApproved=false;
function vals(){let o={};for(let id of ['clinic_code','doctor_name','appointment_date','start_time','end_time','national_id','patient_name','visit_type'])o[id]=el(id).value;return o;}
async function json(url,options){let r=await fetch(url,options);return await r.json()}
async function lookup(){let id=el('national_id').value.trim();el('patient_name').value='';el('mobile').value='';el('patient_message').textContent='';if(!id)return;let x=await json('/api/patient/'+encodeURIComponent(id));if(x.ok){el('patient_name').value=x.patient.name;el('mobile').value=x.patient.mobile;if(x.patient.state!=='active')el('patient_message').textContent='Patient File '+x.patient.state;}else el('patient_message').textContent=x.error;}
async function slots(){slotApproved=false;el('overbook').style.display='none';let o=vals();let u=new URLSearchParams({clinic_code:o.clinic_code,appointment_date:o.appointment_date,start_time:o.start_time,doctor_name:o.doctor_name});let x=await json('/api/slot?'+u);el('slot_message').textContent=x.message;if(x.count>=1 && x.count<3 && x.ok){el('overbook').style.display='inline-block'}else if(x.count===0 && x.ok)slotApproved=true;return x;}
async function bookings(){let x=await json('/api/bookings');el('bookings').innerHTML=x.bookings.map(b=>'<tr>'+[b.patient_name,b.clinic_code,b.appointment_date,b.start_time,b.doctor_name,b.visit_type,'Booked'].map(v=>'<td>'+String(v).replaceAll('&','&amp;').replaceAll('<','&lt;')+'</td>').join('')+'</tr>').join('');}
el('national_id').addEventListener('change',lookup);for(let id of ['clinic_code','appointment_date','start_time','doctor_name'])el(id).addEventListener('change',()=>{slotApproved=false;el('overbook').style.display='none';el('slot_message').textContent='';});
el('check_slot').onclick=slots;el('overbook').onclick=()=>{slotApproved=true;el('slot_message').textContent='Overbooking approved for this slot (maximum 3)';};
el('notice_ok').onclick=()=>{el('notice').style.display='none';};el('refresh').onclick=bookings;
el('save').onclick=async()=>{el('result').textContent='';let o=vals();o.overbooking=slotApproved;let x=await json('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o)});el('result').textContent=x.ok?'Successfully Saved — '+x.booking_id:x.error;el('result').className=x.ok?'ok':'error';if(x.ok){slotApproved=false;await bookings();}};
bookings();
</script></body></html>'''

@app.get('/booking')
def booking():
    return render_template_string(PAGE, clinics=CLINICS, visits=VISIT_TYPES)

@app.get('/api/patient/<national_id>')
def patient(national_id):
    p = PATIENTS.get(national_id)
    return jsonify({'ok': bool(p), 'patient': p, 'error': None if p else 'Patient Not Found'})

@app.get('/api/slot')
def slot():
    q=request.args
    with connect() as con:
        count=con.execute('SELECT COUNT(*) FROM appointments WHERE clinic_code=? AND appointment_date=? AND start_time=? AND doctor_name=?',
            (q.get('clinic_code'),q.get('appointment_date'),q.get('start_time'),q.get('doctor_name'))).fetchone()[0]
    ok=q.get('clinic_code') in CLINICS and bool(q.get('appointment_date') and q.get('start_time') and q.get('doctor_name'))
    msg='Schedule Not Generated' if not ok else ('No available slot (maximum 3 appointments)' if count>=3 else ('Occupied slot — use OVER BOOKING' if count else 'Available slot'))
    return jsonify(ok=ok and count<3,count=count,message=msg)

@app.get('/api/bookings')
def list_bookings():
    with connect() as con:
        data=[dict(r) for r in con.execute('SELECT * FROM appointments ORDER BY id DESC LIMIT 200')]
    return jsonify(bookings=data)

@app.get('/api/verify')
def verify():
    q=request.args
    with connect() as con:
        row=con.execute('SELECT * FROM appointments WHERE source_key=?', (q.get('source_key',''),)).fetchone()
    return jsonify(found=bool(row), booking=dict(row) if row else None)

@app.post('/api/save')
def save():
    d=request.get_json(silent=True) or {}
    def fail(msg, status=400): return jsonify(ok=False,error=msg),status
    required=['national_id','patient_name','clinic_code','doctor_name','appointment_date','start_time','end_time','visit_type']
    if any(not str(d.get(k,'')).strip() for k in required): return fail('Required Fields Missing')
    patient=PATIENTS.get(str(d['national_id']).strip())
    if not patient: return fail('Patient Not Found')
    if patient['state']=='closed': return fail('Patient File Closed')
    if patient['state']=='suspended': return fail('Patient File Suspended')
    if patient['name'].casefold()!=str(d['patient_name']).strip().casefold(): return fail('Patient Name Mismatch')
    if len(patient['mobile'])!=10: return fail('Incomplete Mobile Number')
    if d['clinic_code'] not in CLINICS: return fail('Schedule Not Generated')
    if d['visit_type'] not in VISIT_TYPES: return fail('Invalid Visit Type')
    try:
        day=datetime.strptime(d['appointment_date'],'%Y-%m-%d')
        start=datetime.strptime(d['start_time'],'%H:%M')
        end=datetime.strptime(d['end_time'],'%H:%M')
        if end<=start: return fail('Invalid Time Range')
    except ValueError: return fail('Invalid Date or Time')
    source_key='|'.join(str(d[k]).strip() for k in ['national_id','clinic_code','doctor_name','appointment_date','start_time','end_time'])
    with connect() as con:
        existing=con.execute('SELECT id FROM appointments WHERE source_key=?', (source_key,)).fetchone()
        if existing: return fail('Appointment Already Exists',409)
        same_patient=con.execute('SELECT id FROM appointments WHERE national_id=? AND appointment_date=? AND start_time=?',
            (d['national_id'],d['appointment_date'],d['start_time'])).fetchone()
        if same_patient: return fail('Appointment Already Exists',409)
        count=con.execute('SELECT COUNT(*) FROM appointments WHERE clinic_code=? AND appointment_date=? AND start_time=? AND doctor_name=?',
            (d['clinic_code'],d['appointment_date'],d['start_time'],d['doctor_name'])).fetchone()[0]
        if count>=3: return fail('No available slot',409)
        if count>=1 and not d.get('overbooking'): return fail('Overbooking Required',409)
        cur=con.execute('''INSERT INTO appointments(source_key,national_id,patient_name,clinic_code,doctor_name,appointment_date,start_time,end_time,visit_type,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?)''', (source_key,d['national_id'],patient['name'],d['clinic_code'],d['doctor_name'],d['appointment_date'],d['start_time'],d['end_time'],d['visit_type'],datetime.now().isoformat()))
        return jsonify(ok=True,booking_id=cur.lastrowid)

if __name__=='__main__':
    init_db()
    app.run(host='127.0.0.1',port=5000,debug=False)
