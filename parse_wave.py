import sys
import json
from html.parser import HTMLParser
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

class WaveTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_td = False
        self.current_row = []
        self.records = []

    def handle_starttag(self, tag, attrs):
        if tag == 'td':
            self.in_td = True

    def handle_endtag(self, tag):
        if tag == 'td':
            self.in_td = False
        elif tag == 'tr':
            if self.current_row:
                self.records.append(self.current_row)
                self.current_row = []

    def handle_data(self, data):
        if self.in_td:
            self.current_row.append(data.strip())

def parse_html(filename, date_label, midnight_utc_ms):
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
        print(f"DEBUG: {filename} size={len(html)}", file=sys.stderr)
    except Exception as e:
        print(f"DEBUG: Failed to open {filename}: {e}", file=sys.stderr)
        return []

    parser = WaveTableParser()
    parser.feed(html)
    print(f"DEBUG: {filename} rows={len(parser.records)}", file=sys.stderr)

    records = []
    for row in parser.records:
        if len(row) < 6:
            continue
        hour_str = row[0].strip()
        if not hour_str.isdigit():
            continue
        hour = int(hour_str)
        if hour < 0 or hour > 23:
            continue
        try:
            wave_height = float(row[1])
            wave_period = float(row[2])
        except:
            continue
        try:
            current_speed = float(row[4])
        except:
            current_speed = 0.0
        current_dir = row[5].strip() if row[5].strip() != '-' else None

        utc_ms = midnight_utc_ms + hour * 3600000
        records.append({
            'label': f"{date_label} {str(hour).zfill(2)}:00",
            'utcMs': utc_ms,
            'waveHeight': wave_height,
            'wavePeriod': wave_period,
            'currentSpeed': current_speed,
            'currentDir': current_dir,
        })

    print(f"DEBUG: {filename} parsed={len(records)}", file=sys.stderr)
    return records

def main():
    now_jst = datetime.now(JST)
    yesterday_jst = now_jst - timedelta(days=1)

    def jst_midnight_utc_ms(dt):
        midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(midnight.timestamp() * 1000)

    today_label = f"{now_jst.month}/{now_jst.day}"
    yest_label = f"{yesterday_jst.month}/{yesterday_jst.day}"

    today_midnight = jst_midnight_utc_ms(now_jst)
    yest_midnight = jst_midnight_utc_ms(yesterday_jst)

    today_file = sys.argv[1] if len(sys.argv) > 1 else 'today.html'
    yest_file = sys.argv[2] if len(sys.argv) > 2 else 'yesterday.html'

    all_records = (
        parse_html(yest_file, yest_label, yest_midnight) +
        parse_html(today_file, today_label, today_midnight)
    )

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    cutoff_ms = now_ms - 25 * 3600000
    upper_ms = now_ms + 2 * 3600000

    filtered = [r for r in all_records if cutoff_ms <= r['utcMs'] <= upper_ms]
    filtered.sort(key=lambda r: r['utcMs'])

    print(f"DEBUG: total={len(all_records)} filtered={len(filtered)}", file=sys.stderr)
    print(json.dumps(filtered, ensure_ascii=False))

if __name__ == '__main__':
    main()
