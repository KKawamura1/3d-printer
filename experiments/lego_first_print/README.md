# 通常レゴの初期候補

8mmピッチの旧実験。デュプロとは別物。

印刷用: [model.stl](model.stl)。mm・100%で読み込み、スライスは手元で行う。

## 生成

```sh
python -m brickcad build --profile experiments/lego_first_print/profile.json --out build/lego-first-print
```

生成時のSTEP・viewer・画像・検証JSON等は `build/lego-first-print/` 内の中間生成物。採用するSTLだけを更新する。

```sh
cp build/lego-first-print/brick.stl experiments/lego_first_print/model.stl
```

この実験の刻印・条件・保存済みSTLは固定し、次の比較には新しい実験フォルダを作る。正確な過去の再現には [移行前のコミット](https://github.com/KKawamura1/3d-printer/tree/c0ff73d59efe906385426e859ac26ff70e7f650e) を使う。共通処理の更新後も当時の生成結果を保証するものではない。
