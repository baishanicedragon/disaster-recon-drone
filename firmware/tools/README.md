# tools · 日志解析与 SITL

> 两个用途：**把飞控日志变成可判读的证据**（log_parser），
> 以及**在真实飞行前把状态机跑一遍**（sil）。
> ⚠ 本目录为**说明 + 配置约定**，脚本需按你的实际环境补齐。

---

## 1. log_parser · 飞控日志解析（验证用）

### 依赖

```bash
pip install pymavlink numpy matplotlib
# 或直接用 MAVProxy 自带的 mavlogdump.py
```

### 常用命令

```bash
# 1) 导出为文本/CSV
mavlogdump.py --format csv --types ATT,GPS,CTUN,BAT flight.bin > flight.csv

# 2) 只抽关键类型（姿态 / 控制 / 电池 / 地形）
mavlogdump.py --types ATT,AHR2,CTUN,NKF4,BAT,TERR flight.bin

# 3) 用 pymavlink 自己解析（推荐，可写判据）
python - <<'PY'
from pymavlink import mavutil
m = mavutil.mavlink_connection('flight.bin')
while True:
    msg = m.recv_match(blocking=False)
    if msg is None: break
    if msg.get_type() in ('ATT', 'BAT', 'TERR'):
        print(msg.get_type(), msg.to_dict())
PY
```

### 本项目的关键判据（**解析后要回答的问题**）

| # | 问题 | 数据来源 |
|:--:|:---|:---|
| 1 | 段 I 爬升率是否稳定在 ~3.3 m/s、45 s 到 150 m？ | `CTUN` / `BARO` |
| 2 | 关机点高度是否为 150 m？上飘过冲多少？ | `BARO` / `TERR` |
| 3 | 撑开瞬间：**空速 ≥ 20.9 m/s 且高度 ≥ 90 m** 是否成立？ | `ARSP` / `BARO` |
| 4 | 拉平过载是否 ≤ 2.5 g、掉高是否 ≈ 90 m？ | `IMU` / `CTUN` |
| 5 | `>20 m` 通讯切断发生在哪个高度？（`COMM_CUT` 标记） | 自定义日志 / `STAT` |
| 6 | 盘旋时长是否 = `LOITER`（300 s）？ | `MODE` / 时间轴 |
| 7 | 能量：实际消耗 vs 预算 516 Wh 的偏差 | `BAT` |
| 8 | GNSS 关断 120 s 内的航位误差是否 < 60 m？ | `GPS` / `NKF4` |

> **撞击记录仪是另一套**（三轴加速度 ≥ 500 Hz，[docs/09 9.6](../../docs/09-软件架构与识别算法.md)），
> 用于验证 [docs/06](../../docs/06-末端迫降与泡沫机头吸能.md) 的 25 g 目标——
> **没有它就无法判断"是设计问题还是操作问题"**。

---

## 2. sil · SITL 配置与场景

> **在真实飞行前，必须过 SITL**（[firmware README](../../README.md) 仿真优先）。

### 启动

```bash
cd ardupilot/ArduPlane
sim_vehicle.py -v ArduPlane --console --map        # 以官方文档为准
```

### 至少要跑通的场景

- [ ] 倒拖爬升段（模拟推力线 + 差动阻尼；注入无空速姿态扰动）
- [ ] 关机 → 俯冲 → **双翼撑开门控**（20.9 m/s ∧ 90 m）→ 2.0 g 拉平 → 平飞
- [ ] 地形跟随（加载本地 DEM）
- [ ] 盘旋（`LOITER_TURNS` / `LOITER_TIME`）
- [ ] **GNSS 关断 120 s** 的航位推算
- [ ] 能量管理规则触发返航
- [ ] **每个状态机转移至少触发一次（含 `GATE_ABORT_PROFILE` 备用剖面）**

### 场景文件约定

```
sil/
├── README.md              ← 本文件
├── scenarios/
│   ├── 01_dragclimb.parm  ← 倒拖段：初始姿态、推力线、扰动
│   ├── 02_transition.parm ← 关机/俯冲/撑开/拉平
│   ├── 03_terrain.parm    ← 本地 DEM 与地形跟随
│   └── 04_gnss_outage.parm← GNSS 关断 120 s
└── notes.md               ← 每次 SITL 的结论与失败模式记录
```

> ⚠ 上述场景文件**尚未创建**，本目录先给出约定与判据。
> 落地时按 ArduPilot SITL 的实际参数机制补齐（`.parm` 覆盖 + Lua/自定义状态机注入）。

---

## 3. 与验证流程的关系

| 阶段 | 工具 | 出处 |
|:---|:---|:---|
| 单元 | `transition_controller/tests/` | [../transition_controller/tests/](../transition_controller/tests/) |
| SITL | 本目录 `sil/` | 本文件 |
| 地面 / 实飞 | — | [../../docs/12-测试与验证流程.md](../../docs/12-测试与验证流程.md) |

---

## 相关

- [../README.md](../../README.md) · 仿真优先与测试分层
- [../transition_controller/README.md](../transition_controller/README.md) · 分步验证
- [../../docs/12-测试与验证流程.md](../../docs/12-测试与验证流程.md)
