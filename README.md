# Metagri AI案内Bot

Metagri研究所の公開情報にもとづいて回答する、公開用の小さなRAGチャットボットです。

このリポジトリには公開確認済みの情報だけを含めています。Notion、Discord、内部メモ、未公開企画、個人情報は含めません。

## ローカル起動

```powershell
python ingest.py
python app.py
```

ブラウザで以下を開きます。

```text
http://127.0.0.1:8765
```

## Renderで公開

`render.yaml` を同梱しています。RenderでこのGitHubリポジトリをBlueprintとして読み込むと、公開モードで起動できます。

## WordPress埋め込み例

Renderなどで発行されたURLを使って、Metagri研究所サイトに埋め込みます。

```html
<iframe
  src="https://your-metagri-ai-bot.example.com"
  style="width:100%;height:720px;border:1px solid #d8e0da;border-radius:8px;"
  loading="lazy"
></iframe>
```

## 公開版の回答方針

- 公開情報だけを根拠に回答する
- 根拠が薄い場合は無理に答えない
- 売上、契約、予算、アカウント、未公開企画などには回答しない
- 公開前チェックは `PUBLIC_RELEASE_CHECKLIST.md` を参照する
