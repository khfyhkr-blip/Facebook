#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_remote_script.py
يحمل ملف بايثون من GitHub (raw) ويشغّله باستخدام نفس مفسّر بايثون.
استخدام:
    python3 run_remote_script.py --url <RAW_URL> --args "-f Wiretun_1.txt -u ahmed --partial"
أو مثال:
    python3 run_remote_script.py --url "https://raw.githubusercontent.com/khfyhkr-blip/Facebook/main/search_and_extract.py" --args "-u ahmed --github-url https://raw.githubusercontent.com/khfyhkr-blip/Facebook/main/Wiretun_1.txt --partial"
"""
import argparse
import os
import subprocess
import sys
import tempfile

def download(url: str) -> str:
    try:
        import requests
    except ImportError:
        print("المطلوب مكتبة requests. ثبّتها عبر: pip install requests")
        sys.exit(1)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text

def main():
    p = argparse.ArgumentParser(description="Download and run a remote Python script")
    p.add_argument('--url', required=True, help='Raw URL to the python file (raw.githubusercontent.com/...)')
    p.add_argument('--args', default='', help='Arguments to pass to the downloaded script (as single string)')
    p.add_argument('--keep', action='store_true', help='Keep the downloaded file instead of deleting it')
    args = p.parse_args()

    url = args.url
    script_args = args.args.strip()

    print(f"Downloading: {url}")
    try:
        code = download(url)
    except Exception as e:
        print(f"فشل التحميل: {e}")
        sys.exit(2)

    # اكتب الملف المؤقت
    fd, path = tempfile.mkstemp(suffix='.py', prefix='remote_')
    os.close(fd)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(code)

    print(f"Saved to temporary file: {path}")
    # نركّب الأمر لتشغيله بنفس مفسّر بايثون
    cmd = [sys.executable, path]
    if script_args:
        # ابقِ كل الـ args كسلسلة نقسمها بطريقة بسيطة
        import shlex
        cmd += shlex.split(script_args)

    print("Running the script...")
    try:
        # ننفذ ونرّبط المخرجات مباشرة إلى التيرمنال
        result = subprocess.run(cmd, check=False)
        ret = result.returncode
    except KeyboardInterrupt:
        print("\nتم إيقاف التنفيذ من المستخدم")
        ret = 130
    except Exception as e:
        print(f"حدث خطأ أثناء التشغيل: {e}")
        ret = 3

    print(f"Script exited with code: {ret}")

    if not args.keep:
        try:
            os.remove(path)
            print("Temporary file removed.")
        except Exception:
            pass

    sys.exit(ret)

if __name__ == '__main__':
    main()
