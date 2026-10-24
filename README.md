# 3d-printer — ブロック設計・検証ハーネス

変則ブロックを作るための、パラメトリックCADと幾何検証の作業環境です。まずは2×4のレゴ互換を目指す試作品から始めます。**実物での嵌合は未検証**です。

![実際のCADから生成した外観・裏面・断面・組立図](examples/first-print/preview.png)

## 新規セッションで再開する

[新規セッションからの起動手順](docs/new-session.md)に、依存の確認・Chromium導入・常駐起動・撮影・CAD再生成までまとめています。前セッションのブラウザや一時ファイルは不要です。

## できること

- Pythonから寸法を変更して、裏面チューブ付きのブロックを生成。
- STL（印刷用）とSTEP（CAD編集用）を書き出し、ファイル自体も検査。
- CADの単一実体・寸法・体積・開口・スタッド・チューブを検査。
- 重ねる・1ピッチずらす・90度交差する姿勢で、BRepの共通体積を計算。
- 挿入方向の5姿勢と、公差の違う5候補を確認。
- 実際の形状の断面PNGと、オフラインで回転できるHTMLを生成。
- Chromiumでビューアーを操作し、上面・裏面・CAD断面・組立・干渉例・モバイル画面を実際に撮影。
- GitHub ActionsでCADとブラウザを再検証し、スクリーンショット・trace・レポートをartifactに保存。

## 最初の試作品を見る

`examples/first-print/`に生成済みの一式を置いています。

- [`brick.stl`](examples/first-print/brick.stl) — 半径方向+0.05 mmの未校正候補。
- [`brick.step`](examples/first-print/brick.step) — 他CADへ渡す形状。
- [`viewer.html`](examples/first-print/viewer.html) — ダウンロードしてブラウザで開く。GitHub上の表示はソースコードです。
- [`report.json`](examples/first-print/report.json) — 寸法、検証結果、干渉量、使用バージョン、出力ハッシュ。
- [`calibration/`](examples/first-print/calibration/) — 5種類の試し刷りSTLと実測用テンプレート。

`preview.png`の組立図は見やすいように2.5 mm浮かせています。HTMLでは追加高さ0 mmに戻して組立状態を確認できます。相手は合成の名目モデルです。純正をスキャン・実測したものではありません。

## 再生成

Python 3.11を使用します。MacではまずPython 3.11を用意し、以下をrepoのルートで実行してください。

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m brickcad all
open build/first-print/viewer.html
```

Mac以外では最後のHTMLをブラウザで開いてください。主要なCAD・数値計算・描画依存はバージョン固定していますが、全推移依存のlockfileではありません。検証時の実バージョンはレポートに残します。

```sh
# 合成の名目寸法モデル
python -m brickcad build --profile profiles/nominal.json --out build/nominal

# 公差5候補のSTL・比較結果・計測テンプレートだけ生成
python -m brickcad sweep --profile profiles/first-print.json --out build/trial
```

寸法変更はJSON profileを追加して`--profile`で指定します。省略した項目は`brickcad/model.py`の既定値です。現在の対応範囲は両軸2〜12スタッドの長方形です。例えば2×3は`{"nx":3,"ny":2,"clearance":0.05}`。

```text
brickcad/model.py       CAD生成・寸法定義
brickcad/verify.py      BRep・STL・組立の検証
brickcad/render.py      CAD断面画像・HTML生成
brickcad/viewer.html    外部ライブラリ不要の3D表示
brickcad/__main__.py    build / sweep / all
profiles/              名目設定と初回印刷候補
examples/first-print/  生成済み試作品・検証結果
measurements/          実測記録（取得後に追加）
tests/                 正常例・欠陥を検出する負例
```

## 「検証済み」の意味

`report.json`の`passed=true`は、CAD/STL/STEPの検査、検査した組立姿勢の無干渉、負例の検出を通ったという意味です。締まり具合・保持力・印刷精度の保証ではありません。負の公差で意図的に食い込ませた候補は、sweep内では正常に生成されても干渉ありと報告します。

次の段階ではプリンター機種・ノズル・材料・スライサーを特定し、試し刷りの実測値からprofileを調整します。[設計の根拠・検証範囲・実測手順](docs/design.md)を参照してください。

## インタラクティブに確認する（通常の開発ループ）

CAD生成後、ブラウザを常駐させます。操作ごとの再起動・push・デプロイ・Actions待ちは不要です。

```sh
npm ci
npx playwright install --with-deps chromium
npm run browser:interactive -- build/first-print
```

起動後の入力はJSONを1行ずつ渡します。各操作の後に、スクリーンショットの絶対パス・所要時間・画面の検証表示を返します。撮影画像をエージェントが開き、必要な次の操作を判断できます。

```json
{"action":"view","value":"underside"}
{"action":"mode","value":"section"}
{"action":"view","value":"section"}
{"action":"mode","value":"stack"}
{"action":"view","value":"perspective"}
{"action":"lift","value":8}
{"action":"orbit","dx":100,"dy":40}
{"action":"zoom","value":-120}
{"action":"reload"}
{"action":"close"}
```

別のターミナルで`python -m brickcad build`を再実行し、`reload`すると新しいCADが表示されます。`build`は数秒のCAD生成を含みますが、視点・組立の操作ではCADを再生成しません。今回の環境では操作と撮影が約0.17〜0.32秒、再読み込みと撮影が約0.33秒でした。速度は環境で変わります。

標準のブラウザ導入ができないLinux環境では、npm配布のバイナリを使う経路も用意しています。

```sh
npm install --prefix /tmp/brick-browser-runtime --ignore-scripts @sparticuz/chromium@153.0.0
BRICK_CHROMIUM_PACKAGE=/tmp/brick-browser-runtime/node_modules/@sparticuz/chromium/build/index.js npm run browser:interactive -- build/first-print
```

この経路は圧縮バイナリと描画ライブラリを`build/browser-runtime/`に展開します。tarの所有者変更を行わないため、所有者変更に制約のある環境でも使えます。Linux用の代替経路で、通常のMac/Windowsは標準Playwrightを使います。描画はWebGLの深度バッファを使い、裏側の面が手前へ出る描画順の問題を避けています。日本語UIの必要文字はOFLフォントのサブセットをHTMLへ埋め込んでいます。

[実ブラウザの撮影一覧](examples/browser/review-sheet.jpg)・[目視確認記録](examples/browser/visual-review.md)も参照してください。

## ブラウザでの一括撮影と目視確認（回帰確認）

Node.js 22を用意し、CAD生成後に以下を実行します。

```sh
npm ci
npx playwright install --with-deps chromium
npm run browser:check -- build/first-print build/browser-qa
python scripts/review-sheet.py build/browser-qa
```

`build/browser-qa/`に10視点の実ブラウザPNG、一覧用`review-sheet.jpg`、操作を再生できる`trace.zip`、ブラウザバージョン・入力ハッシュ・画像ハッシュ付き`browser-report.json`が残ります。外部CDNから描画ライブラリを読み込まず、生成済みHTMLをChromiumで開きます。

自動検査はJavaScriptエラー、空のキャンバス、組立部品の描画漏れ、視点変更、ドラッグ・拡大縮小、表示上の干渉判定、モバイルの横はみ出しを確認します。形状の意味を理解した目視判定は行いません。`automated_passed`と`visual_review_performed`は別です。画像をエージェントが実際に開いて確認し、欠陥があれば修正・再撮影することが作業完了条件です。

上のLinux用代替経路も使えない場合は、GitHub Actionsの`brick-cad-and-verification` artifactから同じ画像を取り出して確認します。未取得・未確認なら目視確認済みと扱いません。


## 小さな初回接続試験

[sim2real印刷プレート](examples/sim2real/plate.stl)は、2×2を5個、補正を変えて同時印刷するデータです。配置55.8×35.8 mm、最大高さ11.4 mm、CAD体積換算でPLA約7.74 g。側面の溝1〜5本で識別します。上下を純正と別々に比較し、突起・受けを独立選択できます。[印刷・評価・再生成の手順](docs/sim2real.md)を参照してください。
