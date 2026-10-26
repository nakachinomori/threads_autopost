"""Threads 予約投稿スクリプト。

queue.json のうち、予定時刻を過ぎていて未投稿のものを古い順に投稿し、
結果を queue.json に書き戻す。依存ライブラリなし（Python 3.9+）。

環境変数:
  THREADS_ACCESS_TOKEN  Threads API の長期アクセストークン（必須）
  IMAGE_BASE_URL        画像投稿時に images/ を公開しているURLのベース（画像を使う場合のみ）
  DRY_RUN=1             APIを呼ばずに投稿予定だけ表示する
  MAX_POSTS_PER_RUN     1回の実行で投稿する最大件数（既定 1。溜まった分の連投を防ぐ）
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://graph.threads.net/v1.0"
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent
QUEUE = ROOT / "queue.json"
MAX_TEXT = 500


def call(method, path, params):
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()}") from None


def wait_until_ready(container_id, token, timeout=300):
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = call("GET", container_id, {"fields": "status,error_message", "access_token": token})
        status = res.get("status")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {container_id} {status}: {res.get('error_message')}")
        time.sleep(10)
    raise RuntimeError(f"container {container_id} not ready after {timeout}s")


def publish(entry, token):
    params = {"text": entry["text"], "access_token": token}
    if entry.get("image"):
        base = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")
        if not base:
            raise RuntimeError("画像投稿には IMAGE_BASE_URL が必要")
        params.update(media_type="IMAGE", image_url=f"{base}/{urllib.parse.quote(entry['image'])}")
    else:
        params["media_type"] = "TEXT"

    container = call("POST", "me/threads", params)["id"]
    wait_until_ready(container, token)
    return call("POST", "me/threads_publish", {"creation_id": container, "access_token": token})["id"]


def parse_time(s):
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=JST)


def main():
    dry_run = os.environ.get("DRY_RUN") == "1"
    token = os.environ.get("THREADS_ACCESS_TOKEN")
    if not token and not dry_run:
        sys.exit("THREADS_ACCESS_TOKEN が未設定")
    limit = int(os.environ.get("MAX_POSTS_PER_RUN", "1"))

    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    now = datetime.now(JST)
    due = sorted(
        (e for e in queue if not e.get("posted_at") and parse_time(e["at"]) <= now),
        key=lambda e: parse_time(e["at"]),
    )

    failed = False
    for entry in due[:limit]:
        if len(entry["text"]) > MAX_TEXT:
            print(f"[skip] {entry['at']} 本文が{MAX_TEXT}字超え", file=sys.stderr)
            entry["error"] = "too long"
            failed = True
            continue
        if dry_run:
            print(f"[dry-run] {entry['at']}: {entry['text'][:40]}")
            continue
        try:
            post_id = publish(entry, token)
        except RuntimeError as e:
            print(f"[error] {entry['at']}: {e}", file=sys.stderr)
            entry["error"] = str(e)[:300]
            failed = True
            continue
        entry["posted_at"] = datetime.now(JST).isoformat(timespec="seconds")
        entry["post_id"] = post_id
        entry.pop("error", None)
        print(f"[posted] {entry['at']} -> {post_id}")

    if not due:
        print("投稿予定なし")
        if not dry_run:
            me = call("GET", "me", {"fields": "username", "access_token": token})
            print(f"トークンOK: @{me['username']}")
    if not dry_run:
        QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
