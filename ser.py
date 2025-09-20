#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ser_any_txt.py
يقرأ جميع ملفات .txt في المجلد الحالي، يعرض أول سطر مطابق فقط.
يحاول تحويل timestamp من epoch (ثواني أو ميليثانية) إلى تاريخ منسق في توقيت Africa/Cairo.
"""

import os
import sys
from datetime import datetime, timezone

# محاولة استيراد zoneinfo لـ Python 3.9+
try:
    from zoneinfo import ZoneInfo
    CAIRO_TZ = ZoneInfo("Africa/Cairo")
except ImportError:
    CAIRO_TZ = None

BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))

def parse_line_to_fields(line):
    parts = [p.strip() for p in line.rstrip("\n").split("|")]
    # تأكد إن القائمة على الأقل بطول 7 عشان ما يصير IndexError
    while len(parts) < 7:
        parts.append("")
    return {
        "index": parts[0],
        "first_name": parts[1],
        "last_name": parts[2],
        "phone": parts[3],
        "number": parts[4],
        "username": parts[5],
        "timestamp": parts[6],
    }

def format_timestamp(ts_str):
    ts_raw = (ts_str or "").strip()
    if not ts_raw:
        return ""
    # لو فيه أحرف غير رقمية، ما نحاولش نحول
    if not ts_raw.isdigit():
        return ts_raw
    try:
        ts_int = int(ts_raw)
        # إذا الرقم كبير جدًا، نفترض إنه ميليثانية
        if ts_int >= 10**12:
            ts_sec = ts_int / 1000.0
        else:
            ts_sec = ts_int
        dt_utc = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
        if CAIRO_TZ:
            dt_local = dt_utc.astimezone(CAIRO_TZ)
            tz_name = "Africa/Cairo"
        else:
            dt_local = dt_utc
            tz_name = "UTC"
        return dt_local.strftime("%Y-%m-%d %H:%M:%S") + f" ({tz_name})"
    except Exception:
        return ts_raw

def search_and_stop(query):
    q = query.strip().lower()

    # نختار جميع الملفات التي تنتهي بـ .txt في المجلد الحالي
    files = [os.path.join(BASE_FOLDER, fname) for fname in os.listdir(BASE_FOLDER) 
             if fname.lower().endswith(".txt")]

    # ترتيب الملفات حسب الاسم حتى يكون البحث منظم
    files.sort()

    if not files:
        print("لم أجد أي ملفات txt في المجلد الحالي.")
        return None

    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                for lineno, ln in enumerate(fh, start=1):
                    ln_stripped = ln.strip()
                    if not ln_stripped:
                        continue
                    if q in ln_stripped.lower():
                        fields = parse_line_to_fields(ln_stripped)
                        return {
                            "source_file": os.path.basename(fpath),
                            "line_number": lineno,
                            "fields": fields
                        }
        except Exception as e:
            print(f"خطأ بقراءة الملف {fpath}: {e}")
    return None

def print_record_with_date(rec):
    if not rec:
        print("لم يتم العثور على أي نتيجة.")
        return
    f = rec["fields"]
    print("تم العثور على نتيجة (أول مطابقة):")
    print(f"المصدر   : {rec.get('source_file')} (سطر {rec.get('line_number')})\n")
    def safe_print(label, value):
        value = (value or "").strip()
        if value:
            print(f"{label:11}: {value}")
    safe_print("index", f.get("index"))
    safe_print("first_name", f.get("first_name"))
    safe_print("last_name", f.get("last_name"))
    safe_print("phone", f.get("phone"))
    safe_print("number", f.get("number"))
    safe_print("username", f.get("username"))
    raw_ts = f.get("timestamp", "")
    formatted = format_timestamp(raw_ts)
    if formatted:
        print(f"{'birth_date':11}: {formatted}")

def usage_and_exit():
    print("الاستخدام:")
    print("  python3 ser_any_txt.py <query>")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        query = " ".join(sys.argv[1:]).strip()
    else:
        query = input("ادخل يوزر أو ايدي للبحث (سيقف عند أول تطابق): ").strip()

    if not query:
        usage_and_exit()

    print("جارِ البحث — سيتوقف عند أول نتيجة مطابقة...")
    result = search_and_stop(query)
    print_record_with_date(result)
