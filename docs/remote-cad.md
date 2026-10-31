# 変更分だけをGitHub ActionsでSTL生成する

設計コード・パラメータJSONだけをGitへpushする。STLはActions runner内で作り、
形状チェック・4方向画像・SHA-256付きでArtifactに保存する。数MBのSTLを
ChatGPT Work/GitHubコネクターから直接アップロードしない。

## 新規パーツ・設定の登録

`cad/jobs/<id>.json` に1モデル（1つの設定・バリエーション）の定義を追加する。
すべてのジョブ定義を `scripts/cad_remote.py` が発見するため、ワークフロー
YAMLや中央の巨大switch/caseを毎回編集する必要はない。

例（仮のプロファイルを使う自作ブロック）：

```json
{
  "id": "my-brick",
  "watch": ["cad/jobs/my-brick.json", "profiles/my-brick.json", "brickcad/model.py"],
  "depends_on": [],
  "command": [
    "python", "-m", "brickcad", "build",
    "--profile", "profiles/my-brick.json",
    "--out", "build/remote/my-brick"
  ],
  "outputs": [{
    "path": "build/remote/my-brick/brick.stl",
    "name": "my-brick.stl",
    "report": "build/remote/my-brick/report.json"
  }]
}
```

- `watch`: globで変更検出する入力ファイル。**READMEやSTLを含むフォルダ全体を指定しない**。設計ソースと実際のパラメータだけを記載する。ワークフローはPython/JSON等の変更に限定されており、ドキュメントだけのpushでは走らない。
- `command`: 実行するPython生成コマンド。コマンドライン配列（shellを経由しない）。既存の設計モジュールでも、新しいモジュールでもよい。
- `outputs`: 印刷する個別STLの入力パス、配布名、および幾何検証結果の `report.json`。一つのジョブに複数ファイルを指定できる。
- `depends_on`: 組立などで生成前に必要な別ジョブ。選択された場合だけ、その依存ジョブを先に実行する。
- `rebuild_on_dependency_change`: 省略時は `false`。例えばトンネルだけ変更しても8個セットの巨大な再生成を自動では行わない。依存変更でも必ず組立を更新したい場合だけ `true` にする。

同じPython生成器でパラメータが異なるモデルは、設定ごとに別ジョブIDを付ける。
共通ソースの変更は、そのソースを`watch`しているジョブがすべて対象になる。

## 自動トリガーと生成範囲

- `push`：変更された設計・設定にマッチするジョブ**だけ**選択して並列生成（同時最大2）。
- `workflow_dispatch`：`targets`に `tunnel`、`play-set-8`、またはカンマ区切りで明示する。いきなり全件生成しない。
- `docs/`、README、既存STLの変更だけなら生成しない。
- `play-set-8`だけを選ぶと必要な個別モデルを内部で生成して8個セットに組み立てるが、配布Artifactは8個セットのみ。個別ファイルが必要なら個別IDを選ぶ。
- 同じブランチへ新しいpushが来たら、古い未完了ジョブはcancelし、最新コミットだけを処理する。

ワークフロー：[Targeted CAD artifacts](../.github/workflows/cad-targeted.yml)。

## 完了物とレビュー

各実行のArtifactsに `cad-<job-id>` が現れる。

```text
cad-tunnel/
  T01-V2.stl
  T01-V2.report.json
  T01-V2.preview.png      # STL全三角形を4視点から陰影付きで描画
  manifest.json           # 元コミット、依存、サイズ、三角形数、hash
  SHA256SUMS.txt
```

画像はSTL表面の確認用で、スライサーの表示・ブリッジの印刷性・BRep断面の正式な目視検査を代替しない。
CADレポートに `passed=true` かつ `mesh.passed=true` が必要。
STLの構造（50バイト単位のfacet、ファイルサイズ）、ハッシュを検査してから配布する。

推奨する反復：

1. 設計コードまたは設定JSONを1対象だけ変更し、pushする。
2. Actionsの `plan` で期待したジョブのみ選ばれたことを確認する。
3. `cad-<job-id>` をダウンロードし、レポートと画像を実際に開いて確認する。
4. 問題があれば形状やパラメータを直して再pushする。**画像を開かずに目視合格と記載しない。**
5. Bambu Studioのスライスや印刷の結果は別途ユーザーが確認する。

ChatGPTは接続済みGitHubからworkflow runとArtifactを読み、保存先ファイルを開くことでこのループを行える。
ただし**ユーザーの依頼なしに常時監視・自動修正しているわけではない**。
生成が失敗した場合は `cad-failure-<job-id>` を取得し、該当モデルのログから原因を特定する。

## 開発時にすぐ試す

```sh
python -m unittest scripts.test_cad_remote -v
python scripts/cad_remote.py list
python scripts/cad_remote.py plan --targets tunnel
python scripts/cad_remote.py plan --before <old-commit> --after <new-commit>
# ローカルで該当モデルだけ試す場合
python scripts/cad_remote.py build --job tunnel
```

ジョブ定義の追加はCAD幾何自体の検証に替わらない。刻印ID、寸法、安全な形状、
物理保持力、スライスの確認については既存のプロジェクトルールを守る。
