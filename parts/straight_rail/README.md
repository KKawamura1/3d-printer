# 直線レール

継続利用するレール。丸角通常ブロックも --kind brick で生成できる。寸法・嵌合条件は従来どおり。

印刷用: [model.stl](model.stl)。mm・100%で読み込み、スライスは手元で行う。

## 生成

```sh
python -m parts.straight_rail.design --out build/straight-rail
```

生成時のSTEP・viewer・画像・検証JSON等は `build/straight-rail/` 内の中間生成物。採用するSTLだけを更新する。

```sh
cp build/straight-rail/brick.stl parts/straight_rail/model.stl
```

## 検証

```sh
python -m unittest parts.straight_rail.test -v
```

[設計・実験の詳細記録](design-notes.md)

`records/` は当時の条件・記入票・確認記録。新規の実測結果も設計入力や自動検証の出力と区別して保存する。

既存STLをそのまま移動したもの。今回の構成整理では形状・寸法・印刷条件は変更していない。
