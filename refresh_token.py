"""Threads の長期トークン（有効期限60日）を延長し、新しいトークンを標準出力に出す。

使い方: THREADS_ACCESS_TOKEN=... python refresh_token.py
"""

import json
import os
import sys
import urllib.parse
import urllib.request

token = os.environ.get("THREADS_ACCESS_TOKEN") or sys.exit("THREADS_ACCESS_TOKEN が未設定")
query = urllib.parse.urlencode({"grant_type": "th_refresh_token", "access_token": token})
with urllib.request.urlopen(f"https://graph.threads.net/refresh_access_token?{query}", timeout=60) as res:
    body = json.load(res)
print(body["access_token"])
print(f"有効期限: {body.get('expires_in', 0) // 86400}日", file=sys.stderr)
