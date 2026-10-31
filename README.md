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

## バージョン固定のCAD生成（GitHub Actions）

設計コードと小さな設定ファイルだけをpushする。重いSTL・STEP・プレビューは [CAD preview and print artifacts](https://github.com/KKawamura1/3d-printer/actions/workflows/cad-preview.yml) で生成し、14日間保持される `cad-verified-stl` Artifactから取得する。**生成対象のSTLには4方向の簡易画像（`*.preview.png`）が自動添付される。** `previews=true` を指定した手動実行では従来のChromiumによる詳細画像も追加できる。画像は形状の概観用であり、スライス・印刷・嵌合の検証ではない。

**パーツ**は `parts/<name>/cad-build.json` の `version` を形状変更時に必ず上げる。push時の自動生成は、そのpushでバージョンが新規追加・変更された `auto:true` のパーツだけ。パーツ単位の `test.py` とCAD/メッシュ検証を実行する。README、テスト、旧STLやワークフローを修正しただけならSTLは再生成しない。`auto` フラグだけの変更も形状変更とみなさず、バージョンを上げずに切り替えられる。バージョンを変えずにCADソース／設定を変更した場合はエラーとし、古いバージョンの形状を書き換えない。共通CADコードの変更でも影響を受ける各パーツのバージョン更新が必要。

**実験**も `experiments/<name>/cad-build.json` に独立した `version` を持たせ、既定で `auto:true` とする。実験自身の新規追加・バージョン更新時のみpushで自動生成し、参照先パーツのバージョン更新だけでは再生成しない。既存パーツを使う場合、`requires` にターゲットと**明示的なバージョン**を指定する。古いバージョンを指している場合、対応するGitコミットの設計コードを隔離checkoutして再現する。既存パーツを使わず、実験自身の `command` で寸法・形状を直接定義することもできる。

パーツの例：

```json
{
  "version": "T01-V2",
  "auto": true,
  "command": ["python", "-m", "parts.tunnel.design", "--out", "{out}"],
  "stl": ["brick.stl"],
  "timeout": 1200
}
```

パーツの特定版を使う実験／組立の例：

```json
{
  "version": "X07-V1",
  "auto": true,
  "requires": [{"target": "parts/tunnel", "version": "T01-V2"}],
  "command": ["python", "-m", "experiments.sample.design", "--out", "{out}", "--parts-root", "{deps}/parts"],
  "stl": ["brick.stl"]
}
```

`{out}` は対象バージョン専用の生成先、`{deps}` は指定版の依存パーツが配置されるディレクトリ。新しいパーツ／実験を追加するとき、YAMLの固定ターゲット一覧を増やす必要はない。1つの実行内で同じパーツの異なる2版を要求する構成は現在非対応で、明示的にエラーになる。

手動生成ではGitHub Actionsの **Run workflow** で対象ブランチを選び、`targets=parts/play_set` や `targets=experiments/pr20_comparison` を指定する。`targets=all` は `auto:true` のパーツと実験を列挙する。`auto:false` を明示した8個セットなどは指定したときだけ生成する。`previews=true` でChromium画像もArtifactに追加できるが、撮影成功を人間の目視確認済みとは扱わない。

生成済みのSTL・STEPと検証結果はバージョン別にGitHub Actionsキャッシュで可能な限り再利用する。キャッシュがない場合も、同一版の過去の設計コミットから再生成できる。キャッシュ・Artifactはいずれも永続保管を保証しないため、採用確定した印刷用STLは別途保管する。

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

CAD変更時は対象モデルを生成し、そのviewerで形状を確認する。[環境構築・ブラウザ確認](docs/new-session.md) と [検証の範囲](docs/design.md) を参照。push時のCADワークフローは、版が更新された `auto:true` のパーツと実験のみ生成する。参照先の変更では依存する実験を再生成せず、`auto:false` の大きな組立セットは手動で生成する。

CADの検証合格と、実物の嵌合・保持力の確認は区別する。過去の `examples/`・`prints/` はパーツ／実験へ統合した。旧ファイルと生成レポートはGit履歴に残る。[移行対応表](docs/repository-layout.md) を参照。
