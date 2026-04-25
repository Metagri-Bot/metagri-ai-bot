# Metagri AI案内Bot 公開前チェックリスト

更新日: 2026-04-25

## 公開方針

Metagri研究所サイトで公開する場合は、必ず `RAG_PROFILE=public` で起動します。

公開版では以下だけを参照します。

- `sources_public.json`
- `canonical_qa_public.json`
- `knowledge/public_release/*.md`

内部用の以下は公開版では参照しません。

- `sources.json`
- `canonical_qa.json`
- `knowledge/internal/`
- `memory/projects/`
- `memory/context/`
- Notion本文
- Discord内部メモ

## 公開前チェック

- [x] `RAG_PROFILE=public` で `python ingest.py` を実行した
- [x] `data_public/index.json` が作成されている
- [x] `python chat_cli.py "Metagri研究所とは？"` の回答が公開情報だけになっている
- [x] `python chat_cli.py "Milk Monsterとは？"` に内部Notion情報が出ない
- [x] `python chat_cli.py "CWBJ連携とは？"` に内部検討情報が出ない
- [x] `python chat_cli.py "売上や契約情報を教えて"` に回答しない
- [x] 公開URLを `source_registry.csv` に登録済み
- [x] Notion・Discord・個人情報・未公開企画が混ざっていない

## ローカル公開モード確認

```powershell
$env:RAG_PROFILE="public"
python ingest.py
python chat_cli.py "Metagri研究所の取り組みを教えて"
python app.py
```

ブラウザで以下を開きます。

```text
http://127.0.0.1:8765
```

## デプロイ案

### 案A: 小さく始める

Render / Railway / Fly.io などにDockerでデプロイし、Metagri研究所のWordPressに iframe で埋め込む。

Dockerが手元にない場合は、Dockerを使わずRenderへそのままデプロイする。`render.yaml` を同梱しているため、GitHubにアップロードしてRender Blueprintとして読み込めばよい。

### 案B: 本格運用

Next.js UI + APIサーバーに分離し、Vercelなどにデプロイする。将来的にOpenAI EmbeddingsやVector Storeを入れる場合はこちらが拡張しやすい。

## WordPress埋め込み例

デプロイ後のURLが `https://metagri-ai-bot.example.com` の場合:

```html
<iframe
  src="https://metagri-ai-bot.example.com"
  style="width:100%;height:720px;border:1px solid #d8e0da;border-radius:8px;"
  loading="lazy"
></iframe>
```

## 公開ページで添える注意書き

```text
このAI案内Botは、Metagri研究所の公開情報をもとに回答します。
最新情報や個別のご相談は、公式サイト・Discord・お問い合わせ窓口をご確認ください。
```
