from datetime import date, datetime
from pathlib import Path
import sys, openpyxl
SHEET='Budget Produksi'
ACTIVE={'MAGE':6,'BMKE':4,'BKCE':4,'BBGE':3,'BHPE':4,'SPGE':3}
def parse_date(v):
    if isinstance(v,datetime): return v.date()
    if isinstance(v,date): return v
    if isinstance(v,str):
        v=v.strip().split(':',1)[-1].strip()
        try: return date.fromisoformat(v[:10])
        except ValueError: return None
    return None
def main(path):
    p=Path(path)
    if not p.is_file(): raise SystemExit(f'File tidak ditemukan: {p}')
    wb=openpyxl.load_workbook(p,read_only=False,data_only=False)
    if SHEET not in wb.sheetnames: raise SystemExit(f'Sheet {SHEET!r} tidak ditemukan')
    ws=wb[SHEET]; report=parse_date(ws['B3'].value)
    expected={f'{e}{n}' for e,c in ACTIVE.items() for n in range(1,c+1)}
    found={}
    for r in range(1,ws.max_row+1):
        v=ws.cell(r,2).value
        if isinstance(v,str) and v.strip().upper() in expected: found.setdefault(v.strip().upper(),[]).append(r)
    print(f'File: {p.name}\nSheet: {SHEET}\nDimensi: {ws.max_row} x {ws.max_column}\nB3: {ws["B3"].value!r}\nTanggal laporan: {report}')
    print('Header hari E6:AI6:',[ws.cell(6,c).value for c in range(5,36)])
    for e,c in ACTIVE.items():
        for n in range(1,c+1):
            code=f'{e}{n}'; rows=found.get(code,[])
            print(f'{code}: baris {rows or "TIDAK DITEMUKAN"}')
            if len(rows)==1:
                max_day=report.day if report else 31
                vals=[ws.cell(rows[0],col).value for col in range(5,5+max_day)]
                invalid=[(i+1,v) for i,v in enumerate(vals) if isinstance(v,bool) or not isinstance(v,(int,float))]
                total=sum(v for v in vals if isinstance(v,(int,float)) and not isinstance(v,bool))
                print(f'  budget harian numerik={len(vals)-len(invalid)}/{len(vals)} hari sampai tanggal snapshot; jumlah={total:.4f}; invalid={invalid[:3]}')
    print('Kode hilang:',sorted(expected-set(found)))
    print('Kode ganda:',{k:v for k,v in found.items() if len(v)!=1})
    wb.close()
if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Pemakaian: python scripts/inspect_budget.py PATH_FILE.xlsx')
    main(sys.argv[1])
