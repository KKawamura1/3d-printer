# 丸角ブロック試作02

当時の丸角ブロック試作品。現行生成器の再出力と、保存した試作品のバイト一致は保証しない。

印刷用: [model.stl](model.stl)。mm・100%で読み込み、スライスは手元で行う。

## 生成

```sh
python -m parts.straight_rail.design --kind brick --out build/fit-trial-02
```

生成時のSTEP・viewer・画像・検証JSON等は `build/fit-trial-02/` 内の中間生成物。採用するSTLだけを更新する。

```sh
cp build/fit-trial-02/brick.stl experiments/fit_trial_02/model.stl
```

`records/` は当時の条件・記入票・確認記録。新規の実測結果も設計入力や自動検証の出力と区別して保存する。

この実験の刻印・条件・保存済みSTLは固定し、次の比較には新しい実験フォルダを作る。正確な過去の再現には [移行前のコミット](https://github.com/KKawamura1/3d-printer/tree/c0ff73d59efe906385426e859ac26ff70e7f650e) を使う。共通処理の更新後も当時の生成結果を保証するものではない。
