# 坂カーブ 試作02：底面の切断端を丸める

試作01への実物フィードバック「坂カーブは良好だが、途中で切れた底面チューブがギザギザして痛い」を反映した改訂。旧版は[試作01](duplo-sloped-curve-trial-01.md)に保存する。

- [印刷用STL](../examples/duplo-sloped-curve-trial-02/brick.stl)
- [STL・STEP・プレビュー・検証結果のZIP](../prints/duplo_sloped_curve_trial_02.zip)
- [実ブラウザの確認画像](../examples/duplo-sloped-curve-trial-02/review-sheet.jpg)
- [検証結果](../examples/duplo-sloped-curve-trial-02/report.json)

## 変更した形

カーブの輪郭で床とチューブを切った**後**、切断で生じた縦の角20か所（チューブ端と側壁端）をR0.70 mmで丸める。底面の縁全周は、切断前の0.30 mm面取りから、切断後のR0.50 mm丸みに置き換える。切断で新しく現れる縁にも丸みがつく。

チューブの外径13.30 mm、内径9.40 mm、受け壁3.20 mm、16 mm格子、4×4占有範囲、19.20 mm落差は従来と同じ。レールの走行面・入口・出口も変えない。

底から0.50 mmまでは差し込み口の形が変わる。その上の嵌合部分は旧CADとの差分と合成9.40 mm突起の接触領域を突き合わせ、接触領域で失われた材料・追加された材料とも0 mm³であることを確認する。これは保持力の計算ではない。底面の輪郭は凹凸を残し、尖った端を丸くする設計。

## 印刷と実物確認

STLをmm単位・100%で読み込み、水平な受け面をプレート側に置く。大きさは約63.8×63.8×38.33 mm。比較しやすいよう、従来のA1 mini・0.4 mmノズル・PLA Basic・0.20 mm積層などの条件を維持する。スライスプレビューで底面の丸み付近、チューブの壁、ブリッジを確認する。

印刷後は大人が切断端・底の縁を指でなぞり、痛みやバリが残らないか確認する。その後、旧版と同じ相手ブロックで着座・着脱・傾けたときの保持を比較し、球の通過も確認する。3MFと配置方向を残す。

この改訂の `physical_fit_validated`、`physical_rolling_validated`、`physical_touch_validated` は未検証。旧版の良好な実物評価を新版の評価へ引き継がない。印刷品の触感と保持力は試し刷りで確認する。

## 再生成

```sh
python -m brickcad.sloped_curve --out build/duplo-sloped-curve-trial-02
python -m unittest discover -s tests -v
BRICK_CHROMIUM_PACKAGE="$PWD/build/browser-package/node_modules/@sparticuz/chromium/build/index.js" node scripts/sloped-curve-browser-check.cjs build/duplo-sloped-curve-trial-02 build/sloped-curve-browser
python scripts/review-sheet.py build/sloped-curve-browser
```

旧形状は `build_curve(softened=False)` で再現できる。検証は旧版との差分、16突起・5挿入高さ、走路と球の静的49位置、メッシュ、STEP再読込を含む。
