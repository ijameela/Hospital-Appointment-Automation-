"""Create a synthetic Excel input file for the local mock. No real patients."""
from pathlib import Path
import pandas as pd

out = Path(__file__).resolve().parent / 'patients_appointments.xlsx'
if out.exists():
    raise SystemExit('File already exists; refusing to overwrite: ' + str(out))
rows = [
    ['9000000001','TEST PATIENT ONE','18/02/2027','10:30','10:45','0','OPT1','TEST DOCTOR'],
    ['9000000002','TEST PATIENT TWO','18/02/2027','10:30','10:45','0','OPT1','TEST DOCTOR'],
    ['9000000006','TEST PATIENT SIX','19/02/2027','11:00','11:15','1','SUBNS04','TEST DOCTOR'],
    ['9000000005','TEST PATIENT FIVE','20/02/2027','09:00','09:15','0','NS04','TEST DOCTOR'],
    ['9000000003','TEST PATIENT THREE','20/02/2027','09:30','09:45','0','NS04','TEST DOCTOR'],
    ['9000000004','TEST PATIENT FOUR','20/02/2027','10:00','10:15','0','NS04','TEST DOCTOR'],
]
columns = ['ID type','PatientName','ScheduleDate','StartTime','EndTime','IsVirtual','CLINICCODE','DoctorName']
pd.DataFrame(rows,columns=columns).to_excel(out,index=False)
print('Created synthetic sample:', out.name)
