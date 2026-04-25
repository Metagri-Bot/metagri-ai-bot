# Metagri AI案内Bot

Metagri研究所の公開情報にもとづいて回答する、公開用の小さなRAGチャットボットです。

- リポジトリ: https://github.com/Metagri-Bot/metagri-ai-bot
- 運営: 株式会社農情人 / Metagri研究所
- 公式サイト: https://metagri-labo.com/

このリポジトリには公開確認済みの情報だけを含めています。Notion、Discord、内部メモ、未公開企画、個人情報は含めません。

## できること

- Metagri研究所の活動、参加方法、運営会社、注目している技術領域などの基本案内
- 公開ページがあるプロジェクト（農業AI通信、白井市PR動画コンテスト、未来の農業シミュレーター、農業AIハッカソン、4年間DAOレポート など）の概要説明
- MLTT / MLTG / NFT / FarmFiなど公開済みの仕組みの概要説明
- 軌跡、強み、課題感、これまでの学び、今後の方向性、農情人、参加者層、費用などの汎用質問

## できないこと

- 売上・契約・予算・ライセンス・アカウント情報
- Discord内部の議事録・個別メッセージ・個人面談メモ
- 未公開企画の詳細
- 個別メンバーの実名や役割の特定
- 一般知識・他社サービスの詳細解説

## ローカル起動

```powershell
python ingest.py
python app.py
```

ブラウザで以下を開きます。

```text
http://127.0.0.1:8765
```

CLIで一発確認:

```powershell
python chat_cli.py "Metagri研究所とは？"
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
- 古参メンバーや個別役割は個人特定せず一般化して答える
- 未来予測は「推測です」と明示する
- 公開前チェックは `PUBLIC_RELEASE_CHECKLIST.md` を参照する

## ファイル構成

```
metagri-ai-bot/
├── app.py                        # WebサーバーUI
├── chat_cli.py                   # CLI質問
├── ingest.py                     # インデックス構築
├── rag_core.py                   # RAGコア (TF-IDF + canonical_qa)
├── canonical_qa_public.json      # 公開用定型回答 (40+項目)
├── sources_public.json           # 取り込みマニフェスト
├── knowledge/public_release/*.md # 公開用知識ベース
├── data_public/index.json        # 構築済みインデックス
├── Dockerfile / render.yaml      # デプロイ設定
└── PUBLIC_RELEASE_CHECKLIST.md   # 公開前チェック
```
