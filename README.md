# Threads 自動投稿

`queue.json` に書いた投稿を、GitHub Actions が毎日 JST 7:30 / 12:00 / 21:00 に1件ずつ投稿する仕組み。

## ファイル

| ファイル | 役割 |
|---|---|
| `queue.json` | 投稿キュー。`at`（予定時刻）と `text`（本文、500字まで）、画像付きなら `image` |
| `post.py` | 予定時刻を過ぎた未投稿を1件投稿し、`posted_at` を書き戻す |
| `refresh_token.py` | 60日で切れるトークンを延長する |
| `images/` | 画像投稿用の写真置き場 |
| `.github/workflows/post.yml` | 1日3回 `post.py` を実行 |
| `.github/workflows/refresh-token.yml` | 毎月1日にトークンを延長 |

## セットアップ

### 1. Threads のアクセストークンを取る
1. https://developers.facebook.com/ でアプリを作成し、ユースケースに「Threads APIにアクセス」を選ぶ
2. 権限に `threads_basic` と `threads_content_publish` を追加
3. 「アプリの役割」→「役割」→「メンバーを追加」で「Threadsテスター」として自分のThreadsユーザー名を追加し、Threadsアプリの「設定」→「アカウント」→「ウェブサイトのアクセス許可」→「招待」で承認
4. ダッシュボードの「ユースケース」→「Threads APIにアクセス」→「カスタマイズ」→「設定」タブの一番下（アクセストークン生成）でトークンを発行。見つからない場合は Graph API Explorer で「Generate Threads Access Token」を押しても取れる。`TH` で始まる文字列がトークン
5. 短期トークンを長期トークン（60日）に交換する
   `https://graph.threads.net/access_token?grant_type=th_exchange_token&client_secret=<アプリシークレット>&access_token=<短期トークン>`

### 2. GitHub リポジトリに置く
1. このフォルダの中身をそのままリポジトリに push
2. Settings → Secrets and variables → Actions で以下を登録
   - Secret `THREADS_ACCESS_TOKEN`：長期トークン
   - Secret `GH_PAT`：トークン自動延長用。Fine-grained PAT で対象リポジトリの「Secrets: Read and write」権限
   - Variable `IMAGE_BASE_URL`（画像を使うなら）：例 `https://raw.githubusercontent.com/nakachinomori/threads_autopost/main/images`
3. Actions タブで `threads-post` を手動実行（Run workflow）して動作確認

画像は Threads 側が URL から取りに来るので、公開URLが必要。上の raw URL はリポジトリが public のときだけ使える。

## 投稿の追加

`queue.json` に追記するだけ。

```json
{ "at": "2026-10-23T12:00:00+09:00", "text": "本文" },
{ "at": "2026-10-23T21:00:00+09:00", "text": "本文", "image": "cafe1.jpg" }
```

- 投稿済みのものには `posted_at` と `post_id` が付く
- 失敗したものには `error` が付き、次回の実行で再挑戦する
- 1回の実行で投稿するのは1件だけ（止まっていた間の分を連投しない）

## ローカルで確認

```bash
DRY_RUN=1 python post.py   # 投稿せずに、今投稿される予定のものを表示
```

## 写真投稿（Googleドライブ連携）

1. スマホのドライブアプリで `threads-post` フォルダに写真を入れる
2. 毎晩 Claude の定期タスクがフォルダを確認し、新しい写真ごとに一言を書いて `queue.json` に追加する
   - 写真は `prepare_photo.py` で JPEG・長辺1440px に変換し、撮影場所などの EXIF を消してから `images/` に置く
   - 投稿は翌日以降の 18:00 枠に1日1枚ずつ入る
   - 処理済みの写真は `queue.json` の `drive_id` で判別するので、ドライブ側は消さなくていい
3. 文を直したいときは `queue.json` の該当エントリを編集する
