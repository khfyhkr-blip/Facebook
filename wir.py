#!/usr/bin/env python3
"""
extract_user_info.py

سكريبت بايثون يبحث داخل مجموعة ملفات .txt (مثلاً Wiretun_1.txt ... Wiretun_35.txt)
عن يوزر أو آي دي المستخدم ثم يستخرج كل المعلومات المتعلقة به ويجمّعها في ملف JSON أو CSV.

كيفية الاستخدام:
    python extract_user_info.py --folder /path/to/repo --target john_doe --output result.json

المزايا:
- يبحث عن تطابق نصي دقيق وكمان بحث بـ regex (حساس/غير حساس للحروف)
- يحاول تحليل JSON داخل الملفات إن وجد
- يلتقط إيميلات، أرقام تليفون، UUIDs، وكلمات مفتاحية (key: value)
- يعطي سياق كل ظهور (3 سطور فوق/تحت)
- يجمع النتائج في ملف JSON منظم

ملاحظة أمان: تأكد إن عندك الحق القانوني في معالجة هذه البيانات — عدم استخدام السكربت لجمع بيانات أشخاص دون إذن.
"""

import argparse
import os
import re
import json
from pathlib import Path
from collections import defaultdict

# إعداد تعابير البحث
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"\+?\d[\d\s\-()]{6,}\d")
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
AT_USERNAME_RE = re.compile(r"@([A-Za-z0-9_\.\-]{3,})")
KEYVAL_RE = re.compile(r"([\w\- ]{2,40})\s*[:=]\s*([^,;\n]+)")

# عند البحث عن "يوزر" نقبل تطابق جزئي أو كامل

def read_lines_safe(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.readlines()
    except Exception as e:
        print(f"فشل قراءة الملف {path}: {e}")
        return []


def try_parse_json(blob):
    """يحاول تحويل نص كامل أو نصوص سطرية إلى JSON ويعيد قائمة من الكائنات المستخرجة."""
    objs = []
    # محاولة كإنه JSON كامل
    try:
        data = json.loads(blob)
        objs.append(data)
    except Exception:
        # محاولة لكل سطر
        for line in blob.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                objs.append(json.loads(line))
            except Exception:
                continue
    return objs


def extract_from_text(text, target, case_sensitive=False):
    results = {
        'emails': EMAIL_RE.findall(text),
        'phones': PHONE_RE.findall(text),
        'uuids': UUID_RE.findall(text),
        'ats': AT_USERNAME_RE.findall(text),
        'keyvals': KEYVAL_RE.findall(text)
    }
    # هل النص يحتوى على هدف البحث؟
    if case_sensitive:
        contains = target in text
    else:
        contains = target.lower() in text.lower()
    return contains, results


def scan_folder(folder, target, file_pattern='Wiretun_*.txt', context_lines=3, case_sensitive=False):
    folder = Path(folder)
    files = sorted(folder.glob(file_pattern))
    if not files:
        # fallback: كل الملفات txt
        files = sorted(folder.glob('*.txt'))

    aggregated = defaultdict(lambda: {'occurrences': []})

    for p in files:
        lines = read_lines_safe(p)
        full_text = ''.join(lines)

        # محاولة تحليل JSON داخل الملف
        json_objs = try_parse_json(full_text)
        # فحص JSON objects إذا احتوت على المفتاح أو القيمة
        for obj in json_objs:
            try:
                s = json.dumps(obj)
                if (target in s) if case_sensitive else (target.lower() in s.lower()):
                    aggregated[str(p)]['occurrences'].append({
                        'type': 'json_object',
                        'excerpt': s[:1000],
                        'full_object': obj
                    })
            except Exception:
                pass

        # بحث بالسطر وسحب سياق
        for i, line in enumerate(lines):
            hay = line
            if case_sensitive:
                found = target in hay
            else:
                found = target.lower() in hay.lower()
            if found:
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                excerpt = ''.join(lines[start:end])
                contains, extr = extract_from_text(excerpt, target, case_sensitive=case_sensitive)
                aggregated[str(p)]['occurrences'].append({
                    'type': 'text_context',
                    'line_index': i,
                    'excerpt': excerpt,
                    'extracted': extr
                })

        # حتى لو لم يظهر النص مباشرة، نبحث عن اليوزر كحقل في key: value داخل الملف
        # مثال: "user: john_doe"
        if not aggregated[str(p)]['occurrences']:
            # نبحث عن keyvals في كامل الملف
            kvs = KEYVAL_RE.findall(full_text)
            for k, v in kvs:
                if case_sensitive:
                    match = target == v.strip()
                else:
                    match = target.lower() == v.strip().lower()
                if match:
                    aggregated[str(p)]['occurrences'].append({
                        'type': 'keyval_match',
                        'key': k.strip(),
                        'value': v.strip()
                    })

    return aggregated


def save_output(data, output_path):
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"تم حفظ النتيجة في: {output_path}")
    except Exception as e:
        print(f"فشل حفظ النتيجة: {e}")


def main():
    parser = argparse.ArgumentParser(description='ابحث عن يوزر/آي دي داخل ملفات txt واجمع كل المعلومات المتعلقة به')
    parser.add_argument('--folder', '-f', required=True, help='مجلد يحتوي على ملفات Wiretun_*.txt')
    parser.add_argument('--target', '-t', required=True, help='اليوزر نيم أو الآي دي الذي تريد البحث عنه')
    parser.add_argument('--pattern', '-p', default='Wiretun_*.txt', help='نمط أسماء الملفات (افتراضي Wiretun_*.txt)')
    parser.add_argument('--context', '-c', type=int, default=3, help='عدد الأسطر المحيطة لإظهار السياق')
    parser.add_argument('--case', action='store_true', help='اجعل البحث حساس لحالة الحروف')
    parser.add_argument('--output', '-o', default='extracted_result.json', help='مسار ملف الخرج JSON')

    args = parser.parse_args()

    print(f"تفتيش المجلد: {args.folder} على الهدف: {args.target}")
    results = scan_folder(args.folder, args.target, file_pattern=args.pattern, context_lines=args.context, case_sensitive=args.case)

    # تحويل defaultdict الى dict
    results = {k: v for k, v in results.items()}
    save_output(results, args.output)


if __name__ == '__main__':
    main()
