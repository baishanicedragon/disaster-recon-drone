# tools · 计算与建模脚本（可复现性）

> **为什么这个目录必须存在**：`docs/` 里的每一个数字、`assets/3d/` 里的每一个模型，
> 都是这些脚本算出来 / 生成出来的。没有它们，仓库就只是一堆**无法复算、无法重建**的结论。
>
> ⚠ 脚本为**随项目演进的工作脚本**，非产品级工具：缺少单元测试、参数硬编码较多、错误处理粗糙。
> 目的：让你能**复算文档里的数字、重建 3D 资产**，而不是开箱即用。

---

## 1. 目录

```
tools/
├── README.md          ← 本文件
├── calc/              ← 气动 / 重量 / 时间线的数值计算
│   ├── biplane_calc.py    双翼：等效展长、AR、升阻比、巡航与盘旋功率
│   ├── cg_calc.py         重心（CG）位置核算
│   ├── check_fold.py      收拢尺寸校核（能否进 ⌀380 / ⌀300 行军桶）
│   ├── check_timeline.py  任务时间线与能量预算校核
│   ├── v04_docs_calc.py   v0.4 文档里若干数字的复算入口
│   └── fetch_prop*.py     螺旋桨 / 电机数据抓取（外部数据源，需核对可用性）
└── model3d/           ← 3D 模型与任务动画的生成
    ├── build_static_obj.py   生成静态模型 OBJ
    ├── build_v04_obj.py      生成 v0.4 双翼静态模型 OBJ
    ├── build_v04_anim.py     生成 v0.4 任务剖面动画数据
    ├── prop_geom.js          螺旋桨几何（前端用）
    ├── app_core.js           静态模型查看器核心
    ├── app_anim.js           动画播放器核心
    ├── anim_data_v04.js      v0.4 动画关键帧数据
    └── templates/*.html      HTML 模板（查看器 / 动画页面骨架）
```

---

## 2. 依赖与运行

### calc/

```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install numpy scipy matplotlib                        # 国内镜像：-i https://pypi.tuna.tsinghua.edu.cn/simple

python calc/biplane_calc.py
python calc/cg_calc.py
python calc/check_fold.py
python calc/check_timeline.py
```

> `fetch_prop*.py` 会访问外部数据源（螺旋桨/电机数据库），
> **端点可能失效**，抓不到时请手动查厂商数据并替换脚本里的常量。

### model3d/

```bash
python model3d/build_v04_obj.py        # → v0.4 静态模型 .obj
python model3d/build_v04_anim.py       # → v0.4 动画数据
python model3d/build_static_obj.py     # → 通用静态模型 .obj
```

生成的 HTML 查看器依赖 `templates/` 下的模板与 `app_core.js` / `app_anim.js`；
产物为**单文件离线 HTML**（双击即可打开，无需服务器、不联网）——
这一点很重要：**灾区没有网络**。

---

## 3. 数字溯源（哪个脚本对应文档里的哪张表）

| 文档位置 | 数字 | 脚本 |
|:---|:---|:---|
| README「关键指标」 | 双翼 S=0.63 m²、等效展长 1.60 m、AR 4.04、L/D 9.12、巡航 750 W、盘旋 640 W | `calc/biplane_calc.py` |
| README「关键指标」 | 合 AC = STA 895 | `calc/cg_calc.py` |
| README 第 4 节 | 时间线（45 s + 25 s / 14.9 min / 5 min）与能量 516 Wh | `calc/check_timeline.py` |
| [docs/03](../docs/03-总体方案与气动布局.md) | 半翼 ≤ 750 mm、收拢 ⌀480 mm | `calc/check_fold.py` |
| [assets/3d/](../assets/3d/) | v0.4 静态模型与 72 s 任务动画 | `model3d/` |

> 改任何几何参数后，**重跑对应脚本**，让文档、模型、动画三者同步更新——
> 不要只改文档里的数字。

---

## 4. 已知问题

| 问题 | 说明 |
|:---|:---|
| 无单元测试 | 脚本输出靠人工对照文档；改脚本后请人工复核关键数字 |
| 参数硬编码 | 多处常量直接写在脚本里，未抽到统一配置 |
| 模板与产物混放 | `templates/` 是模板，生成的 HTML 直接放 `assets/3d/` |
| 外部抓取易失效 | `fetch_prop*.py` 依赖外部站点 |

---

## 相关

- [../docs/03-总体方案与气动布局.md](../docs/03-总体方案与气动布局.md)
- [../docs/05-动力系统与配电.md](../docs/05-动力系统与配电.md)
- [../assets/3d/README.md](../assets/3d/README.md)
- [../mission/scripts/](../mission/scripts/) · 航路规划脚本（另一套，GDAL 系）
