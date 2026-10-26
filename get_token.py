"""ダッシュボードのトークン生成ボタンを使わずに、OAuthで長期トークン（60日）を取る。

事前準備: ユースケース「Threads APIにアクセス」→「設定」の
「コールバックURLをリダイレクト」に https://localhost/ を登録しておく。

使い方: python get_token.py
  1. 表示されたURLを、Threadsにログイン済みのブラウザで開いて「許可」
  2. https://localhost/?code=... に飛ばされる（ページはエラーでOK）ので、そのURLを丸ごと貼る
  3. 長期トークンが表示される
"""

import getpass
import json
import urllib.error
import urllib.parse
import urllib.request

REDIRECT_URI = "https://localhost/"
SCOPES = "threads_basic,threads_content_publish"


def request(url, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=60) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"エラー: {e.read().decode()}") from None


app_id = input("アプリID（Threads App ID）: ").strip()
app_secret = getpass.getpass("アプリシークレット（Threads App Secret、入力は表示されない）: ").strip()

auth_url = "https://threads.net/oauth/authorize?" + urllib.parse.urlencode({
    "client_id": app_id,
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPES,
    "response_type": "code",
})
print(f"\n1. このURLをブラウザで開いて許可する:\n{auth_url}\n")
redirected = input("2. 飛ばされた先のURL（https://localhost/?code=...）を貼る: ").strip()
code = urllib.parse.parse_qs(urllib.parse.urlparse(redirected).query).get("code", [redirected])[0]
code = code.removesuffix("#_")

short = request("https://graph.threads.net/oauth/access_token", {
    "client_id": app_id,
    "client_secret": app_secret,
    "grant_type": "authorization_code",
    "redirect_uri": REDIRECT_URI,
    "code": code,
})
long = request("https://graph.threads.net/access_token?" + urllib.parse.urlencode({
    "grant_type": "th_exchange_token",
    "client_secret": app_secret,
    "access_token": short["access_token"],
}))
me = request("https://graph.threads.net/v1.0/me?" + urllib.parse.urlencode({
    "fields": "username",
    "access_token": long["access_token"],
}))

print(f"\n@{me['username']} の長期トークン（{long.get('expires_in', 0) // 86400}日有効）:")
print(long["access_token"])
