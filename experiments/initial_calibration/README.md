# 初回デュプロ嵌合校正

初回の5条件比較。通常レゴ用とは区別する。

印刷用: [plate.stl](plate.stl)。mm・100%で読み込み、スライスは手元で行う。

## 生成

```sh
python -m experiments.initial_calibration.design build/initial-calibration
```

生成時のSTEP・viewer・画像・検証JSON等は `build/initial-calibration/` 内の中間生成物。採用するSTLだけを更新する。

```sh
cp build/initial-calibration/plate.stl experiments/initial_calibration/plate.stl
```

## 検証

```sh
python -m unittest experiments.initial_calibration.test -v
```

[設計・実験の詳細記録](design-notes.md)

`records/` は当時の条件・記入票・確認記録。新規の実測結果も設計入力や自動検証の出力と区別して保存する。

この実験の刻印・条件・保存済みSTLは固定し、次の比較には新しい実験フォルダを作る。正確な過去の再現には [移行前のコミット](https://github.com/KKawamura1/3d-printer/tree/c0ff73d59efe906385426e859ac26ff70e7f650e) を使う。共通処理の更新後も当時の生成結果を保証するものではない。
