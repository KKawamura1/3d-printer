# SC05-V1 — 緩坂＋緩左カーブ開放レール

Issue #37 No.13 / Issue #60。**実装先はPR #46（右SC03-V5との左右統合）**。
`parts.sloped_curve_open_right.design`の無刻印走路と同じCADを反対方向へ鏡映し、**鏡映後に**SC05-V1を西側外壁へ標準3.0mm/0.4mmで凹刻印する。右の刻印を鏡映しない。
右4×4×2・落差19.2mm・E31-05 B条件短縮スリット・切断支持材・開放レール仕様を共有する。

生成: `python -m parts.sloped_curve_open_left.design --out build/sc05`。
現行版STL生成・Bambu Studioスライス・実物印刷/転がり/嵌合は個別確認。右の実機結果を左へ自動転用しない。
