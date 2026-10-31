# 水平90度トンネル

4×4、本体高さ38.40mm、スタッド込み42.90mm。R48の水平曲がり通路。

[現在の印刷用STL](model.stl)。今回の嵌合条件・角処理・印刷手順・残る確認は [週末用コースセット](../play_set/README.md) に集約。旧試作品はGit履歴とdesign-notes.mdを参照。

```sh
python -m parts.elbow.design --out build/elbow
python -m unittest parts.elbow.test -v
```

共通嵌合profileは duplo-e27-play-v1。保持力・実印刷・触感の新形状への転用は未検証。
