# 新規セッションからの起動

前セッションの実行プロセス・仮想環境・Chromium・`build/`が残っている前提にはしない。repoの追跡ファイルから起動し直せる。ブラウザは起動後に常駐させ、変更ごとのActionsやデプロイを待たずに操作する。

## 1. repoと依存を用意

このprivate repoをGitHub接続経由、または認証済みgitで取得し、repoのルートに移動する。ChatGPT WorkではGitHubコネクターが使えても、シェルの`git clone`が認証できるとは限らない。その場合は接続済みGitHubの機能で取得する。パスはセッションごとに変わるため、以前の`/workspace/scratch/...`を再利用しない。

必要なものはPython 3.11（3.12でも動作確認済み）、Node.js 22、npm。Linux代替ブラウザはx86_64 Linuxで動作確認済み。tarコマンドも使用する。

```sh
python --version
node --version
npm --version
```

CAD用パッケージがなければインストールする。既に利用できるWorkランタイムでも、まずimportとバージョンを確認する。

```sh
python -c 'import cadquery, matplotlib, numpy; print(cadquery.__version__, matplotlib.__version__, numpy.__version__)'
```

import失敗やバージョン不一致時は、Python環境を準備する。

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Python 3.11がなく3.12がある場合は、上の`python3.11`を`python3.12`へ置き換える。以後は同じPython環境を使う。別のシェル/ツール呼び出しでは`source .venv/bin/activate`を再実行するか、`.venv/bin/python`を直接使う。

```sh
npm ci
```

## 2. Chromiumを用意

### ChatGPT WorkのLinux環境で実証した経路

このrepoのWork環境では、Playwright自体は存在していてもブラウザの実行ファイルは当初なかった。通常のダウンロードは不完全なZIPになり、npm配布のChromiumで起動できた。新規Workセッションでは、この経路から始めてよい。

```sh
npm install --prefix ./build/browser-package --ignore-scripts --no-audit --no-fund @sparticuz/chromium@153.0.0
```

起動コマンドごとに、次の環境変数を渡す。前セッションのパッケージや、一時的な`export`が次のシェルに引き継がれる前提にしない。

```sh
BRICK_CHROMIUM_PACKAGE="$PWD/build/browser-package/node_modules/@sparticuz/chromium/build/index.js" npm run browser:interactive -- examples/duplo-2x4
```

`{"ready":true,...}`が出れば起動している。起動処理が圧縮バイナリ・フォント・SwiftShaderを`build/browser-runtime/`へ展開する。tarの元所有者は復元しない。`build/`は再生成可能な作業用ファイルで、gitへ追加しない。

このLinuxバイナリをMac/Windowsへ流用しない。OSの共有ライブラリなどが異なる環境での動作を保証するものではない。

### 通常のMac/Windows/Linux環境

```sh
npx playwright install --with-deps chromium
npm run browser:interactive -- examples/duplo-2x4
```

LinuxでのOSパッケージ導入には、その環境に応じた権限が必要な場合がある。ブラウザの導入が失敗したときは成功扱いにしない。

## 3. 撮影・画像確認まで行う

上の`examples/duplo-2x4`はrepoに含まれる生成済みモデルなので、CADの再生成前でもブラウザ単独の起動確認ができる。常駐プロセスの標準入力へ、以下を1行ずつ送る。

```json
{"action":"capture"}
{"action":"view","value":"underside"}
{"action":"mode","value":"section"}
{"action":"view","value":"section"}
```

各応答の`ok:true`、`errors:[]`、`screenshot`の絶対パスを確認し、返されたPNGを画像表示ツールで実際に開く。`ready:true`や画像ファイルの存在だけでは目視確認完了ではない。

ChatGPT Workでエージェントが起動するときは、対話可能な端末セッション（例: `exec_command`の`tty:true`）で実行する。返された実行セッションIDを保持し、同じプロセスへ`write_stdin`でJSON行を送る。セッションIDは新規セッションへ引き継がない。プロセスが終了していれば起動し直す。

## 4. CADを生成して、同じブラウザへ反映

**新規セッションの起動は全モデルのテスト・再生成を要求しない。** 別の端末/コマンドから、変更したモデルのテストと生成だけを実行する。例：下面保持力の3条件試作品を変更した場合。

```sh
python -m unittest discover -s tests -p 'test_receiver_trial.py' -v
python -m brickcad.receiver_trial --out build/duplo-receiver-trial-01
```

別のモデルでは、該当する `tests/test_*.py` と専用生成コマンドに置き換える。複数モジュールや共通実装を変更したPRでは、次のように依存先を選ぶ（`<base-sha>` はPRの比較元のコミットSHA）。

```sh
python scripts/ci-tests.py --base <base-sha> --plan
python scripts/ci-tests.py --base <base-sha>
```

`python -m unittest discover -s tests -v` や `python -m brickcad all` を毎回実行しない。後者はデフォルトDUPLO 2x4の生成に加えて5条件の校正スイープを行う。共有基盤に広い影響があるとき、または明示的な全件検証依頼があるときに限り範囲を広げる。

常駐ブラウザを**今回生成したモデル**のviewerへ向ける。下面試作品01の場合：

```sh
BRICK_CHROMIUM_PACKAGE="$PWD/build/browser-package/node_modules/@sparticuz/chromium/build/index.js" npm run browser:interactive -- build/duplo-receiver-trial-01/01
```

以後は対象モデルだけを再生成し、同じブラウザへ `{"action":"reload"}` を送る。視点・回転・分解・拡大縮小だけならCADの再生成は不要。終了時は `{"action":"close"}` を送る。

まとめて画面を検証する場合も、対象モデルのパスを指定する。

```sh
BRICK_CHROMIUM_PACKAGE="$PWD/build/browser-package/node_modules/@sparticuz/chromium/build/index.js" npm run browser:check -- build/duplo-receiver-trial-01/01 build/browser-qa
python scripts/review-sheet.py build/browser-qa
```

## 再起動時の切り分け

| 症状 | 確認・対応 |
|---|---|
| `Cannot find module 'playwright'` | repoルートで`npm ci`を実行する。Workランタイムに偶然あるNodeモジュールへ依存しない |
| `Executable doesn't exist` | Playwrightのライブラリ導入とブラウザ実体の導入は別。手順2を行う |
| ZIPの展開失敗 | ダウンロード失敗。Linux用npm配布経路を使う |
| `chown`の`EINVAL` | npmパッケージの`executablePath()`を直接呼ばず、repoの起動スクリプトを使う |
| 日本語が四角になる | 最新の生成済みHTMLか確認。日本語UIフォントはrepoの`brickcad/assets/`から埋め込まれる |
| runtimeの展開途中で中断・バージョン変更 | ブラウザを終了し、作業用`build/browser-runtime/`を退避してから起動し直す |
| `file`/HTMLが見つからない | 作業ディレクトリと`examples/duplo-2x4`または`build/duplo-2x4`の指定を確認 |
| 別のツールからlocalhostへ接続できない | 実行環境が別のネットワーク空間の場合がある。本手順は`file://`でHTMLを開き、HTTPサーバーを必要としない |

通常の開発はこの常駐ブラウザで反復する。ローカルの導入・起動が解決できない場合に限り、CIの撮影結果取得やデプロイ先をクラウドブラウザで操作する方法を検討する。

## 再現確認記録

2026-10-24、通常レゴを対象にしていた時点でrepoの追跡ファイルだけを新しいディレクトリへ展開し、既存の`build/`・`node_modules/`・前のChromium常駐プロセスを利用せずに確認した。`npm ci`、Linux用Chromiumの新規配置、生成済みサンプルでの起動、通常撮影・裏面撮影、終了コマンドまで実行できた。両撮影の応答は`ok:true`・`errors:[]`で、裏面PNGも実際に開いて確認した。この検証は同じWork環境内の別ディレクトリでの再現であり、全く異なるOS・共有ライブラリ構成や将来の全Work環境での保証ではない。
