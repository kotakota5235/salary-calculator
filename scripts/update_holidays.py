"""内閣府CSVから、通信不要で使える祝日データを生成する。"""
import csv
import io
import json
import sys
import urllib.request
from pathlib import Path

URL = 'https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv'
raw = Path(sys.argv[1]).read_bytes() if len(sys.argv) > 1 else urllib.request.urlopen(URL, timeout=30).read()
rows = list(csv.reader(io.StringIO(raw.decode('cp932'))))[1:]
holidays = {}
for day, name in rows:
    y, m, d = map(int, day.split('/'))
    holidays[f'{y:04}-{m:02}-{d:02}'] = name
years = sorted({int(day[:4]) for day in holidays})
assert len(holidays) > 1000 and years[0] == 1955
payload = {'minYear': years[0], 'maxYear': years[-1], 'dates': holidays}
Path(__file__).resolve().parents[1].joinpath('holidays.js').write_text(
    '// Source: ' + URL + '\nwindow.HOLIDAYS = ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
print(f'祝日データ: {years[0]}–{years[-1]}年、{len(holidays)}件')
