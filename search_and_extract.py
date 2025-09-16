#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search_and_extract.py
ابحث عن يوزر داخل ملف نصي محلي أو GitHub raw واستخرج معلومات (الاسم، الهاتف، id، ايميل، key:value).
متطلبات: pip install requests
"""
import argparse, re, sys
from pathlib import Path
from typing import List, Dict

def try_read_local(path: Path) -> List[str]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return [l.rstrip('\n') for l in f]
    except Exception:
        with open(path, 'r', encoding='latin-1', errors='replace') as f:
            return [l.rstrip('\n') for l in f]

def fetch_github_raw(url: str) -> List[str]:
    try:
        import requests
    except ImportError:
        print('الرجاء تثبيت مكتبة requests: pip install requests')
        sys.exit(1)
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.text.splitlines()

# بسيط لاستخراج إيميل / أرقام / id / key:value
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
KV_RE = re.compile(r"(?P<key>[\w\u0600-\u06FF\s\-\:]{2,40})[:\-]\s*(?P<val>.+)")
NAME_KEYS = [r"اسم\s*كامل", r"الاسم", r"name", r"full\s*name"]
ID_KEYWORDS = [r"\bid\b", r"ايدي", r"رقم\s*المستخدم", r"userid", r"uid"]

def extract_fields_from_block(block: List[str]) -> Dict[str, List[str]]:
    found = {'name': [], 'phones': [], 'ids': [], 'emails': [], 'kv': []}
    text = '\n'.join(block)

    # ايميلات
    for m in EMAIL_RE.findall(text):
        if m not in found['emails']:
            found['emails'].append(m)

    # ارقام هاتف (قواعد عامة: مجموعات أرقام 7-15 رقماً)
    for m in re.findall(r"(\+?\d[\d\-\s]{6,}\d)", text):
        s = re.sub(r"[\s\-]", "", m)
        digits = re.sub(r"\D", "", s)
        if 6 <= len(digits) <= 15 and m.strip() not in found['phones']:
            found['phones'].append(m.strip())

    # key:value
    for line in block:
        kv = KV_RE.search(line)
        if kv:
            key = kv.group('key').strip()
            val = kv.group('val').strip()
            found['kv'].append((key, val))
            # اسم؟
            for nk in NAME_KEYS:
                if re.search(nk, key, re.IGNORECASE):
                    if val not in found['name']:
                        found['name'].append(val)
            # id؟
            for ik in ID_KEYWORDS:
                if re.search(ik, key, re.IGNORECASE):
                    if val not in found['ids']:
                        found['ids'].append(val)

    # اذا مفيش اسم واضح: محاولة heuristics لخط عربي بدون أرقام
    if not found['name']:
        for line in block:
            clean = line.strip()
            if 3 <= len(clean) <= 60 and not re.search(r"\d", clean) and re.search(r"[\u0600-\u06FF]", clean):
                found['name'].append(clean)
                break

    # محاولات لاستخراج id من سطور عامة (أرقام طويلة أو كلمات user...)
    for m in re.findall(r"\b([0-9A-Za-z\-]{6,20})\b", text):
        if re.search(r"\d", m) and len(m) >= 6 and m not in found['ids']:
            # قد يكون id أو رقم — نضيفه كاحتمال
            found['ids'].append(m)

    return found

def search_and_extract(lines: List[str], query: str, use_regex: bool, partial: bool, ignore_case: bool, context: int, max_results: int):
    flags = re.IGNORECASE if ignore_case else 0
    if use_regex:
        pat = re.compile(query, flags)
    else:
        esc = re.escape(query)
        pat = re.compile(esc if partial else r"\b" + esc + r"\b", flags)
    results = []
    total = len(lines)
    for i, line in enumerate(lines, start=1):
        if pat.search(line):
            start = max(1, i - context)
            end = min(total, i + context)
            block = lines[start-1:end]
            extracted = extract_fields_from_block(block)
            results.append({
                'match_line': i,
                'match_text': line.strip(),
                'context_start': start,
                'context_end': end,
                'context_block': block,
                'extracted': extracted
            })
            if max_results > 0 and len(results) >= max_results:
                break
    return results

def print_results(results):
    if not results:
        print('\nلم يتم العثور على نتائج.')
        return
    for idx, r in enumerate(results, start=1):
        print(f"\n=== النتيجة {idx} ===")
        print(f"سطر التطابق: {r['match_line']}")
        print(f"النص: {r['match_text']}")
        print(f"سياق الأسطر {r['context_start']}..{r['context_end']}")
        print('\nسطر(سطور) السياق:')
        for j, ln in enumerate(r['context_block'], start=r['context_start']):
            prefix = '>' if j == r['match_line'] else ' '
            print(f"{prefix}[{j}] {ln}")
        print('\n--- الاستخراج ---')
        ex = r['extracted']
        if ex['name']:
            print('الاسم/الأسماء: ' + ', '.join(ex['name']))
        if ex['phones']:
            print('أرقام الهاتف: ' + ', '.join(ex['phones']))
        if ex['ids']:
            print('الـ ID/الأرقام: ' + ', '.join(ex['ids']))
        if ex['emails']:
            print('البريد الإلكتروني: ' + ', '.join(ex['emails']))
        if ex['kv']:
            print('حقول أخرى (key: value):')
            for k, v in ex['kv']:
                print(f"  - {k}: {v}")

def main(argv=None):
    p = argparse.ArgumentParser(description='ابحث عن يوزر داخل ملف نصي محلي أو GitHub raw واستخرج معلومات عنه')
    p.add_argument('-f', '--file', help='مسار الملف النصي المحلي')
    p.add_argument('--github-url', help='رابط Raw لملف على GitHub (مثال: https://raw.githubusercontent.com/...)')
    p.add_argument('-u', '--user', required=True, help='اليوزر أو النص المراد البحث عنه')
    p.add_argument('--partial', action='store_true', help='تمكين البحث الجزئي')
    p.add_argument('--regex', action='store_true', help='اجعل البحث تعبيرًا منتظمًا')
    p.add_argument('--ignore-case', action='store_true', help='تجاهل حالة الحروف')
    p.add_argument('-c', '--context', type=int, default=3, help='عدد سطور السياق قبل وبعد السطر المطابق')
    p.add_argument('-o', '--output', help='حفظ النتائج إلى ملف (JSON)')
    p.add_argument('--max-results', type=int, default=0, help='حد لعدد النتائج')
    args = p.parse_args(argv)

    if not args.file and not args.github_url:
        print('خطأ: يجب تحديد ملف محلي (-f) أو رابط GitHub raw (--github-url)')
        sys.exit(2)

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f'الملف غير موجود: {path}')
            sys.exit(2)
        lines = try_read_local(path)
    else:
        lines = fetch_github_raw(args.github_url)

    results = search_and_extract(lines, args.user, use_regex=args.regex, partial=args.partial, ignore_case=args.ignore_case, context=args.context, max_results=args.max_results)
    print_results(results)

    if args.output:
        import json
        outpath = Path(args.output)
        try:
            with open(outpath, 'w', encoding='utf-8') as o:
                json.dump(results, o, ensure_ascii=False, indent=2)
            print(f"\nتم حفظ النتائج في: {outpath}")
        except Exception as e:
            print(f"خطأ أثناء حفظ الملف: {e}")

if __name__ == '__main__':
    main()
