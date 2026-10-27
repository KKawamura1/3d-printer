# 共通パーツ設計リファクタの検証

比較元: `c6be7c2368882331193bb3eec488a3fbc81c3e9a`。

## CADの比較

比較元のPythonソースから、通常2×4、丸角2×2、直線レール、2段トンネル、坂カーブF、XY補正2×2の6種類を生成してSTEPで保存。変更後のBRepと双方向の差分ソリッドを計算した。全6種類で削除/追加体積は0 mm³、判定閾値は合計 `1e-5 mm³`。数値は [shared-part-refactor-cad.json](shared-part-refactor-cad.json) を参照。

STEP経由の体積積分には微小な差があり、坂カーブでは約0.00265 mm³（約6.4×10⁻⁸相対）の差がある。体積の一致だけで形状を判定せず、双方向の差分で確認した。ここでいう一致はCADカーネルの数値精度内であり、印刷後の嵌合や保持力の保証ではない。

直線レールの従来の下面開口X=57.63、Y=25.48 mmも保存している。対称なトンネル用profileへ勝手に置き換えていない。

## 出力とブラウザ

以下の4種類だけを専用出力先へ生成した。各出力のCAD/STL/STEP検査はPASS。

- `python -m brickcad build --profile profiles/duplo-shared-nominal-v1.json --out build/shared-block`
- `python -m brickcad.tunnel --out build/shared-tunnel`
- `python -m brickcad.rail --kind rail --out build/shared-rail`
- `python -m brickcad.rail --kind brick --out build/shared-rounded`

それぞれ `npm run browser:check -- <output> <browser-output>` と `python scripts/review-sheet.py <browser-output>` を実行。Chromiumの実画面を開き、上面、下面、断面、組立、分解、90度交差、負例、モバイルを目視した。通常/丸角/レールは各10画面、トンネルは通常ブロックを上下に付ける画面を含め11画面。全41画面の自動チェックと目視を完了。入力・画像のハッシュ、使用ブラウザ、観察内容は [shared-part-refactor-browser.json](shared-part-refactor-browser.json) に保存した。

撮影はローカルの再生成物から実施し、過去の印刷ZIPやcurated exampleは更新していない。今回のPRで新しい嵌合条件を採用したり、過去の現物に別の刻印を付け直したりしていない。

## テスト

`python scripts/ci-tests.py --base <比較元> --plan` により、共通モデル/検証器/寸法profileに依存する13ファイルを選択。今回は共通CADを変更するため全13ファイルが対象になった。

各ファイルを `python -m unittest discover -s tests -p <ファイル名> -v` で別プロセスで実行し、**57件すべてOKの最終集計を確認**。新規の7件は、外形/下面/上面の独立性、版の不変性、不正寸法の拒否、JSON往復、名目形状の保存、再現情報を検査する。既存の干渉・不正メッシュ・過大球等の負例も維持した。ファイル別の件数は [shared-part-refactor-tests.json](shared-part-refactor-tests.json) を参照。

最初の単一プロセス実行は最終集計が得られなかったため、合格判定には使用していない。各ファイルの完了を確認できた個別実行のみを上の集計に含める。最後に坂カーブの既定チューブ径を版付きprofileから導出するよう整理し、その7件を再実行してOKを確認した。
