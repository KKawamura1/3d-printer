# Issue #37 23分類CAD生成カタログ（PR #56）

23分類（開放10、トンネル13）は20個の固有CADでカバーする。水平のGC01-V5/C01-V6/C02-V8は逆走による左右共用候補であり、実機での逆向き転がりは未検証。急落下＋緩カーブの不採用No.22/23は対象外。

この機能は既存PRの**実績あるCAD生成元を固定SHAで再実行**するディスパッチ機構であり、未実装の任意曲線を正しく合成できると装うものではない。個別の刻印と左右反転は元のパーツ実装の手順をそのまま使い、別レシピとして形状を作り直さない。

- 検証のみ: `python scripts/course_catalog.py --mode validate`
- 生成対象確認: `python scripts/course_catalog.py --mode plan --targets all`
- 1形状: `python scripts/course_catalog.py --mode build --targets E01-V3`
- 複数形状: `python scripts/course_catalog.py --mode build --targets S01-V8,SD04-V10`
- 23分類すべて: `python scripts/course_catalog.py --mode build --targets all`
- 分類番号でも指定可能: `--targets 2,3,7`（2/3は1個のGC01-V5に統合）

Actions `Issue 37 course catalogue generator (23 categories)` の `workflow_dispatch` で `targets=all` を明示すると20個のSTLを生成する。通常push時はT01-V6の1個だけを実際に生成して経路を検証する。PR検査は台帳の高速テストだけで済ませる。

原典は #36/#38/#40/#41/#43/#44/#46/#48/#50/#64 と現行PR56のT01-V6/D01-V3。外部PR HEADが固定SHAから動いた場合は警告ではなく停止し、再照合・再ピン留めを促す。すべて元CADの`cad-build.json`版を照合し、BRep/CADレポートのPASS・メッシュ検査合格・STLハッシュを記録する。

唯一の例外`RAIL-LEGACY`は既存の水平直線レール試作コードから新しく生成できるが、最新E31-05・刻印/床面設計への適合を保証しない。manifestに`legacy_unverified_e31`を明示する。CAD合格はスライス/実印刷/嵌合/転がり成功とは異なる。
