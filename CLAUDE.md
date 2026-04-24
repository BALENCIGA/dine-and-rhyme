# AutoInstagram (Dine & Rhyme) - Instagram自動投稿ツール

## 概要
食べ物の写真を分析し、ラップ調のキャプションを自動生成してInstagramに投稿するツール。
GitHub Pages上に「Dine & Rhyme」というWebツールも公開中。

## 技術スタック
- Python 3.13
- Gemini 3.1 Pro（キャプション生成）
- Instagram API
- GitHub Pages（Webツール: dine-and-rhyme.html）

## ファイル構成
- `src/` - メインソースコード
  - `analyzer.py` - 写真分析
  - `instagram.py` - Instagram API連携
  - `watcher.py` - フォルダ監視
  - `confirm.py` - 投稿確認
  - `config.py` - 設定
- `tests/` - テスト
- `photos/inbox/` - 投稿待ち写真
- `photos/posted/` - 投稿済み写真
- `dine-and-rhyme.html` - GitHub Pages用Webツール

## 現在の状態
- キャプション生成・Instagram投稿機能は完成
- ハッシュタグは英語5個のみに設定済み
- GitHubリポジトリ名は `dine-and-rhyme`

## 注意事項
- `.env` にAPIキー等を格納（GitHubには上げない）
- photos/inbox/, photos/posted/ の中身はgitignoreで除外
