# 新規セッションからの起動

前セッションのプロセス・依存・Chromium・build/の存在を前提にしない。現在の構成は [repository-layout.md](repository-layout.md) を参照。

## CADの準備

認証済みgitまたは接続済みGitHub経由でリポジトリを取得する。コネクターが使えてもシェルのgit認証が使えるとは限らない。Python 3.11を用意し、依存がまだなければ次を実行する。

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

起動確認のために全テストや旧モデルを生成する必要はない。変更するフォルダのREADMEを読み、そのテストと生成コマンドだけを実行する。

```sh
python -m unittest experiments.receiver_fit.test -v
python -m experiments.receiver_fit.design --out build/receiver-fit
```

複数モジュールに影響する変更はimport依存から選ぶ。

```sh
python scripts/ci-tests.py --base <base-sha> --plan
python scripts/ci-tests.py --base <base-sha>
```

## 変更した形状を確認する

CAD形状やviewerを変更した場合は、そのモデルを生成して実ブラウザで確認する。配置・import・文書だけの変更では撮影は不要。viewerはGitに保存しないため、STLだけから起動するのではなく対象の生成先を指定する。

Node.js 22を用意し、必要時のみ導入する。

```sh
npm ci
npx playwright install --with-deps chromium
# 例: 上で生成した下面比較の01を表示
npm run browser:interactive -- build/receiver-fit/01
```

常駐プロセスの標準入力へJSONを1行ずつ送る。ChatGPT Workでは対話可能な端末セッションを使い、同じセッションの標準入力へ書き込む。セッションIDを次回へ引き継がない。

```json
{"action":"view","value":"underside"}
{"action":"mode","value":"section"}
{"action":"view","value":"section"}
{"action":"reload"}
{"action":"close"}
```

別の端末で同じモデルを再生成してreloadする。視点変更・回転・拡大だけならCADは再生成しない。各応答のスクリーンショットを実際に開き、形状を目視確認する。コマンド成功や画像の存在だけで目視確認済みと扱わない。

## Linuxで標準Chromiumを取得できない場合

x86_64 Linuxではnpm配布の代替バイナリを利用できる。Mac/Windowsでは標準Playwrightを使う。

```sh
npm install --prefix ./build/browser-package --ignore-scripts --no-audit --no-fund @sparticuz/chromium@153.0.0
BRICK_CHROMIUM_PACKAGE="$PWD/build/browser-package/node_modules/@sparticuz/chromium/build/index.js" npm run browser:interactive -- build/receiver-fit/01
```

この経路は圧縮バイナリ等をbuild/browser-runtime/へ展開する。所有者情報は復元しない。環境変数は起動ごとに指定する。

## 一括撮影

```sh
npm run browser:check -- build/receiver-fit/01 build/browser-qa
python scripts/review-sheet.py build/browser-qa
```

返された画像を実際に開き、上面・下面・断面・組立・分解・交差姿勢を確認する。特有の表示を持つ坂カーブ・90度トンネル・組立実験にはscripts/の専用撮影コマンドを使う。ローカルの標準経路も代替経路も使えないときは、手動のCAD previewで対象を一つ選んで撮影する。取得していない画像を確認済みと扱わない。

## 印刷用STLの更新

採用するSTLだけをパーツ／実験のフォルダへコピーする。途中のSTEP・HTML・PNG・自動検証JSON・ZIPはbuild/に残す。印刷条件と実測値、判断の記録はソースと別に保存する。
