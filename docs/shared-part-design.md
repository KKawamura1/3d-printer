# 共通規格からパーツを作る

単位は mm、Z 上向き、下面の縁を z=0 とする。今後のパーツは、接続規格・嵌合寸法・通路規格を選び、固有の形状を追加して作る。

## 定義を置く場所

| 場所 | 責務 |
|---|---|
| `brickcad/standards.py` | 版付きの寸法定義。CADやプリンターに依存しない |
| `brickcad/model.py` | 寸法の解決、スタッド/チューブ配置、通常ブロック、旧APIの互換 |
| `brickcad/connections.py` | 突起と下面の共通CAD生成。寸法の既定値を持たない |
| `parts/*/design.py` | 固有の通路・天井・切断・曲線形状 |
| `brickcad/provenance.py` | 解決済み寸法、選んだ規格、ソースのハッシュ |
| `measurements/` | 印刷条件、実測、相手、嵌合結果。設計の既定値へ自動適用しない |

`FamilyStandard` はピッチ・1段の高さ・突起高さ・本体隙間・天井厚、`FitProfile` は突起外径/内径・チューブ外径/内径・下面内壁の位置を持つ。`ChannelStandard` は対象ボール径と通路断面の基準、`EdgeFinish` は外角・突起上端・下面入口の処理を持つ。

`duplo-nominal-v1` は合成基準、`duplo-rail-trial-v1` は従来の丸角ブロック/トンネル条件、`duplo-straight-rail-trial-v1` は直線レール条件、`duplo-curve-trial-v1` は従来の坂カーブ条件、`duplo-xy-trial-v1` は過去のXY補正候補の嵌合条件である。最後のものにも外形補正量は含めない。**いずれも全パーツ・全接続相手に対する採用済み最良条件という意味ではない。** 最新版を暗黙に参照する `latest` は設けない。

## 通常ブロックの例

```python
from brickcad.model import brick_from_fit, build

p = brick_from_fit('duplo-nominal-v1', nx=2, ny=2, height_units=2)
shape = build(p)
```

既存CLIでも名前付きprofileを読める。

```sh
python -m brickcad build --profile profiles/duplo-shared-nominal-v1.json --out build/shared-block
```

これは合成名目モデルの例であり、最新の印刷推奨候補ではない。CLIの既定profileも変更していない。

## 外形と下面を独立して調整する

```python
from dataclasses import replace

wider = replace(p, body_offset_xy=(0.20, 0.07))
receiver_trial = replace(p, receiver_inset_xy=(3.20, 3.40), tube_radius=6.70)
stud_trial = replace(p, stud_radius=4.66)
```

`body_offset_xy` は本体全幅/全奥行きへ加える量。スタッド位置・ピッチ・下面内壁は動かない。2×2 の名目外形31.8×31.8に適用すると32.0×31.87になる。

`receiver_inset_xy` は**仮想セル境界から内壁まで**の距離であり、側壁厚ではない。2×2、16 mmピッチ、inset 3.30なら開口幅は `2*16-2*3.30=25.40`。列数を増やすと16 mmずつ広がる。X/Yを独立に指定できる。外形補正を加えてもこの開口は一定。

新しい名前付きprofileでは下面を `receiver_inset_xy` で調整する。`wall` は旧profile/実験との互換のため残っている値で、新APIの下面を操作するものではない。寸法検査・解析体積・壁側隙間は実際の `cavity_xy` を参照する。

旧 `Brick` / `from_profile` / `receiver(..., footprint=...)` は継続利用できる。`receiver_inset_xy=None` の旧profileでは従来通り、外形と `wall` から開口を計算する。既存の `clearance` も古い校正スイープの再現用に残す。新しい調整では上面と下面の値を別々に変更する。

## 固有形状を追加する

トンネルは `brick_from_fit('duplo-rail-trial-v1', nx=2, ny=2, height_units=2)` で基礎寸法を解決し、共通の `receiver()` と `make_studs()` を使い、通路と天井を追加している。`make_studs()` には突起上端の丸みも指定できる。通常の丸角ブロックも同じ生成器を使う。

従来の直線レールは実測外幅に合わせて側壁厚を変更していたため、X開口57.63 mm、Y開口25.48 mmになっていた。このX/Y差も専用の版で保存し、今回勝手に等方化しない。

レールとトンネルは `BALL_TRACK` の床高さ・断面半径を共有する。各モデルで変更した値はレポートに残す。接続口の位置・方向・断面の一致は既存の `ports.py` で検査する。坂カーブの切断後の縁など、形状に依存する処理は各パーツ側に置く。

このリファクタで移行したのは、通常ブロック、丸角ブロック、レール、トンネル、および共通profileに依存する坂カーブの寸法選択。過去の校正片・XY試作品の生成手順や刻印は維持する。任意の幅/高さで通路や天井まで成立することを保証する汎用トンネルAPIではない。

## 版と印刷記録

既存の版の寸法を上書きせず、新しいIDを追加する。パーツ側で新IDを選ぶ変更は、形状を変える変更として検査・試し刷りする。`fit_profile_id` は基準条件のIDであり、override後の形状の認証IDではない。

通常ブロック・レール・丸角ブロック・トンネルの `report.json` には `design` を追加した。

- 基準profileの全寸法と根拠、解決済みの全パラメータ、実際の外形と下面開口。
- 通路/角処理の設定（該当するもの）、CAD・viewerソースのSHA-256。
- `print_setup=null` と `physical_fit_validated=false`。印刷条件は未指定であり推定しない。

再現時は同じコミットのソースと入力profileを使い、ソースハッシュと解決済み寸法を照合する。印刷条件・ベッド配置・スライサー設定は別の試験記録に保持する。純正凸→印刷凹、印刷凸→純正凹、印刷凸→印刷凹は別々の評価として記録し、サイズ/曲率/肉厚が違うパーツへの転用は未検証として扱う。

次回から新規実験は実験番号＋候補番号（例 `E07-03`）で刻印・ファイル名・試験記録を揃える。過去の同一番号の現物をこのPRで識別し直すことはできないため、既存の刻印と生成物は改変していない。

## 検証の範囲

共通CAD生成と寸法解決に変更があるため、PRではimport依存で影響を受けるテストを選ぶ。過去のSTL/印刷ZIPの一括再生成はしない。新しいprofile追加時には、外形・開口・ピッチ・上下面の独立性、名目基準との上下両方向、印刷品同士の干渉を確認する。無干渉やCADの一致から保持力を推定しない。

## E27後の実用候補

`duplo-e27-play-v1` は2026-10-30のE27実物報告に基づく移植候補。上面外径9.40／穴6.40、下面チューブ外径13.50／穴9.40、下面inset3.30。下面はE27-04、上面の再現目標はE27-02の現物。上面は同じCADでも02と04で接続感が異なり、原因未特定。実用候補の新形状への移植を物理検証済みとはしない。旧profileは変更しない。
