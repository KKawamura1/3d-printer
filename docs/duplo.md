# デュプロ互換モデル

今回作りたい対象は通常サイズのレゴではなくDUPLO。2×4と、短い試し刷り用の2×2を用意した。通常サイズのモデル・profileも残す。

## 初回の接続校正

まず印刷するものは[補正違い2×2を5個配置したプレート](../examples/sim2real-duplo/plate.stl)です。[評価・補正の手順](sim2real-duplo.md)に沿って、純正DUPLOへの接続を上下別々に確認できます。`python -m brickcad.calibration`で再生成します。

## 印刷用ファイル

[名前付きSTL 2種類をまとめたZIP](../prints/duplo_bricks.zip)からも取得できる。中のファイル名は`duplo_2x4.stl`と`duplo_2x2.stl`。

- `examples/duplo-2x4/brick.stl`: 2×4、本体63.8 × 31.8 × 19.2 mm、スタッド込み高さ23.7 mm。
- `examples/duplo-2x2/brick.stl`: 2×2、本体31.8 × 31.8 × 19.2 mm、スタッド込み高さ23.7 mm。
- 同じフォルダのSTEPは他CADへ渡す用途。viewer.htmlはダウンロードして開く自己完結型ビューアー。

**スライサーにはmm単位・100%で読み込む。これらのSTLは既にデュプロ寸法なので、さらに200%へ拡大しない。** 旧`examples/first-print/`は通常レゴ寸法のまま。

## 単純な2倍拡大との違い

| 項目 | このDUPLO名目モデル | 根拠・位置づけ |
|---|---:|---|
| スタッド間隔 | 16.0 mm | 既存DUPLO互換設計、通常レゴの2倍のピッチ |
| 本体高さ | 19.2 mm | DobloFactory等で使われる標準高さ |
| 外形の合計隙間 | 0.2 mm | cfinke/LEGO.scadと同じ外形計算。旧レゴモデルの外形をそのまま2倍にはしない |
| スタッド外径 | 9.4 mm | cfinke/LEGO.scadのDUPLO設定 |
| スタッド高さ | 4.5 mm | cfinke/LEGO.scad、DobloFactory |
| スタッド穴径 | 6.5 mm | cfinke/LEGO.scadのDUPLO設定 |
| 裏面チューブ外径 / 内径 | 13.1 / 9.4 mm | cfinke/LEGO.scadのDUPLO設定を参照 |
| 側壁厚 | 3.2 mm | 本実装のリブなし簡略形状。16 mmピッチ、0.1 mm外形逃げ、4.7 mm半径から内壁との接点位置を計算 |
| 天井厚 | 1.6 mm | 本実装の暫定印刷設計値。純正実測値ではない |

スタッドは穴のある円筒に変更し、穴の下には天井を残した。純正の薄壁・リブ・補強・丸み・細かな内面形状の完全再現ではない。DUPLOのスタッドに穴があること、および通常レゴと組み合わせる仕組みはLEGO公式でも説明されている。ただし、本プロトタイプの通常レゴとの混在接続は検証対象に含めていない。

出典（2026-10-24確認）:
- LEGO公式: https://www.lego.com/en-us/history/articles/e-lego-duplo
- LEGO公式の組み合わせ説明: https://www.lego.com/en-us/service/help-topics/article/building-with-lego-and-duplo-bricks?age-gate=grown_up
- 既存互換生成器の寸法定義: https://github.com/cfinke/LEGO.scad/blob/master/LEGO.scad
- DobloFactory作者の解説: https://edutechwiki.unige.ch/en/Doblo_factory

公式情報はDUPLOの構造・互換性の説明で、製造公差付き図面ではない。細部の数値は第三者の互換設計を参考にした値と、このプロジェクトの簡略化・印刷設計値を区別して扱う。外部コードやメッシュは取り込まず、寸法と考え方を参照した。

## 作成・確認

```sh
# 既定の対象はDUPLO 2×4。形状生成・検証・公差5候補生成。
python -m brickcad all

# 小さい2×2
python -m brickcad build --profile profiles/duplo-2x2.json --out build/duplo-2x2

# 通常レゴの既存モデルを明示的に作る場合
python -m brickcad all --profile profiles/first-print.json --out build/first-print
```

常駐ブラウザ:

```sh
npm run browser:interactive -- build/duplo-2x4
```

Chromiumの導入は[新規セッションの手順](new-session.md)に従う。Linux代替ブラウザを使うときは同じ`BRICK_CHROMIUM_PACKAGE`を付ける。

## 公差・検証状態

`duplo-first-print.json`は`clearance=0`で、まず名目寸法を保持した未校正の試作品。通常レゴで使った+0.05 mmの補正を、そのままデュプロへ持ち込んでいない。

`build/duplo-2x4/calibration/`には半径補正-0.04、0、+0.04、+0.08、+0.12 mmの候補を生成できる。補正の意味は従来と同じで、正ならスタッドを細く、内壁とチューブ外周を逃がす。スタッド穴径は固定。全ての候補が適切な保持力になるという意味ではない。

合成のDUPLO名目モデルとの上下両方向、同じ印刷形状同士、16 mmずらし・90度交差、スタッド高さ4.5 mmに対応した挿入経路を幾何検証する。通常レゴの8 mm基準と混同しないよう、レポートに相手のパラメータも記録する。中空スタッドの穴・壁・穴の底も検査する。

CAD・STL・STEPと描画の確認は、純正DUPLOとの実物接続や保持力の保証ではない。機種・材料ごとの試し刷りで校正する。機種未指定のためG-codeは生成しない。

