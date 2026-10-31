# 3d-printer

デュプロ互換パーツをコードで設計し、STLを印刷して改良するリポジトリ。

```text
parts/          継続して使うパーツ。設計・テスト・現在の印刷用STL
experiments/    一度きりの調整・比較・組立実験。条件・STL・結果を保存
brickcad/       共通寸法、接続形状、CAD生成・検証・描画
profiles/       共通の合成基準・名前付き寸法設定
measurements/   複数実験にまたがる実測・分析の元データ
scripts/        開発補助
tests/         共通処理のテスト
docs/          共通の設計ルール・開発手順
build/         中間生成物（Git管理外）
```

## 今回印刷する

[週末用コースセット](parts/play_set/)：版付き刻印のある8個セット。坂カーブ2構造、直線トンネル4形状、90度トンネル2個を比較できる。通常ブロック／通常レールは含めない。新形状の実物検証は印刷後に行う。

## STLを変更部分だけGitHub Actionsで作る

新しいパーツやバリエーションは、`cad/jobs/<id>.json` に設定・生成コマンド・
依存関係を登録する。Pythonコードやその設定をpushすると、**変更に対応する
モデルだけがGitHub Actions上で生成**される。STL、形状検証レポート、
4方向の軽量プレビュー、SHA-256を `cad-<id>` Artifactとしてダウンロードできる。
大容量STLをChatGPT WorkからGitHubへ直接pushしない。

詳しくは [リモートCAD生成と反復レビュー](docs/remote-cad.md) を参照。
従来の8個セット専用手動Actionも残すが、今後は `Targeted CAD artifacts` が基本。

## パーツを変更する

各フォルダの `design.py` と `test.py` を入口にする。共通のピッチ・高さ・突起・下面・通路の規格は [brickcad/standards.py](brickcad/standards.py)、使用方法は [共通設計](docs/shared-part-design.md) を参照。

- [通常ブロック](parts/basic_brick/)
- [直線レール](parts/straight_rail/)
- [直線トンネル](parts/tunnel/)
- [90度トンネル](parts/elbow/)
- [坂カーブ](parts/sloped_curve/)

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m parts.tunnel.design --out build/tunnel
python -m unittest parts.tunnel.test -v
# 形状・スライスの確認後、採用するSTLを更新
cp build/tunnel/brick.stl parts/tunnel/model.stl
```

STLはmm・100%で読み込む。スライスは手元で行う。STEP・3MF・ZIP・画像・viewer・自動検証レポートは中間生成物として `build/` に出し、コミットしない。設計入力のJSON、実測値、判断の根拠となる記録はソース／実験記録として残す。

## 実験する

[experiments/](experiments/) に実験ごとのフォルダを作り、目的・条件・生成コード／入力・印刷用STL・結果を揃える。新規試料の刻印は実験番号＋候補番号（例 E07-03）。既存の刻印は変更しない。

実験結果を採用するときは共通規格に新しい版を追加し、対象パーツから明示的に選ぶ。`parts/` と `brickcad/` は `experiments/` をimportしない。終了した実験は固定し、次の比較は別フォルダへ。共有コードが変わった後の厳密な再現には当時のGitコミットを使う。

## 確認する

変更対象のテストだけを実行する。PRの影響範囲は次で確認できる。

```sh
python scripts/ci-tests.py --base <base-sha> --plan
python scripts/ci-tests.py --base <base-sha>
```

CAD変更時は対象モデルを生成し、そのviewerで形状を確認する。[環境構築・ブラウザ確認](docs/new-session.md) と [検証の範囲](docs/design.md) を参照。PRの自動CIは影響するテストを一度だけ実行し、モデル生成・撮影は必要時の手動CIで行う。

CADの検証合格と、実物の嵌合・保持力の確認は区別する。過去の `examples/`・`prints/` はパーツ／実験へ統合した。旧ファイルと生成レポートはGit履歴に残る。[移行対応表](docs/repository-layout.md) を参照。
