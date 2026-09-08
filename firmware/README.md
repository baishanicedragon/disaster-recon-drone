# firmware/ · 固件与任务逻辑

> 状态：**占位**。
> 本仓库**不重新实现飞控**。飞控直接用 **ArduPilot**（GPLv3）。
> 这里只放：飞控参数、任务层脚本、**自旋段控制器**、以及视觉推理代码。

---

## 设计原则

> **能不自己写就不自己写。**

ArduPilot 已经提供了：EKF3、tailsitter 过渡、地形跟随、RTL、自动降落、
失效保护、AutoTune、Lua 脚本接口。
**从零重写这些 = 项目失败率翻倍。**

本项目只在**两处**写自定义代码：

1. **自旋段控制器**（段 I，约 25 s）——ArduPilot 不支持滚动坐标系控制；
2. **任务层能量管理与状态机**——用 Lua 脚本或外部 companion computer 实现。

---

## 目录结构（规划）

```
firmware/
├── README.md                     ← 本文件
├── ardupilot/
│   ├── params/                   ← 参数文件（.param）
│   │   ├── 00-base.param         ← 机架、舵面、电调、失效保护
│   │   ├── 10-tailsitter.param   ← Q_TAILSIT_*、Q_ASSIST_*、过渡
│   │   ├── 20-terrain.param      ← TERRAIN_*、地形跟随
│   │   ├── 30-tune.param         ← PID、滤波（AutoTune 前初值）
│   │   └── README.md             ← 每个参数的作用与依据
│   └── lua/
│       ├── energy_manager.lua    ← 能量管理（强制返航判据）
│       ├── camera_trigger.lua    ← 等距触发
│       └── abort_logic.lua       ← 中止判据
├── spin_controller/              ← 自旋段控制器（自定义）
│   ├── src/spin_ctrl.c
│   ├── src/spin_ctrl.h
│   ├── tests/test_spin_ctrl.c    ← 单元测试（滚动坐标系分解）
│   └── README.md                 ← 算法说明与开环/闭环取舍
├── vision/
│   ├── README.md                 ← 模型训练与量化流程
│   ├── train/                    ← 训练脚本（不入库权重）
│   ├── convert/                  ← ONNX → TFLite/INT8 → NPU
│   └── infer/                    ← 视觉 MCU 推理固件
└── tools/
    ├── log_parser/               ← 飞控日志解析（验证用）
    └── sil/                      ← SITL 配置与场景
```

---

## 构建环境

| 组件 | 版本建议 | 说明 |
|:---|:---|:---|
| ArduPilot | 4.6+（以官方最新稳定版为准） | `./waf configure --board <your-board>` |
| Waf 构建 | 随 ArduPilot | |
| MAVProxy | 最新 | SITL 与日志分析 |
| ARM GCC | 随 ArduPilot 工具链 | 自旋控制器编译 |
| Python | 3.10+ | Lua 脚本测试、日志分析 |
| STM32CubeIDE / CubeMX | 随 N6 支持包 | 视觉 MCU 固件 |

---

## 关键参数说明（摘要，完整列表见 `ardupilot/params/`）

| 参数 | 值 | 理由 |
|:---|---:|:---|
| `Q_TAILSIT_ENABLE` | 1 | 启用尾坐构型 |
| `Q_ASSIST_SPEED` | 18 | 低于此空速自动补推力（过渡保护） |
| `TERRAIN_ENABLE` | 1 | 地形跟随（DEM 文件放 SD 卡） |
| `EK3_SRC1_POSZ` | BARO | 峡谷内 GPS 高度误差大 |
| `FS_GCS_ENABLE` | 0 | **禁止链路失效触发 RTL**（本设计无链路） |
| `BATT_FS_LOW_ACT` | 2 | 低电进入返航/迫降 |

> ⚠ **参数名会随固件版本变更**，以 ArduPilot 官方文档为准。

---

## 仿真优先

**在真实飞行前，必须过 SITL。**

```bash
# 示例（以官方文档为准）
cd ardupilot/ArduPlane
sim_vehicle.py -v ArduPlane -f tailsitter --console --map
```

SITL 中至少跑通：

- [ ] 垂直起飞 → 悬停 → 过渡 → 平飞
- [ ] 地形跟随（加载本地 DEM）
- [ ] 盘旋（LOITER_TURNS / LOITER_TIME）
- [ ] GNSS 关断 120 s 的航位推算
- [ ] 能量管理规则触发返航
- [ ] 每个状态机转移至少触发一次

---

## 测试

| 层 | 工具 | 范围 |
|:---|:---|:---|
| 单元 | 简易 C test / Unity | 自旋控制器的坐标分解、能量管理判据 |
| SITL | ArduPilot SITL | 状态机、任务逻辑 |
| HIL | 视情况 | 硬件在环 |
| 实飞 | — | 见 [docs/12](../docs/12-测试与验证流程.md) |

---

## 许可与第三方

- 本目录的**自有代码**：MIT
- **ArduPilot**：GPLv3（引用，不在此分发）
- **MAVLink**：MIT
- 模型权重：**不入库**（AGPL 风险）

---

## 相关文档

- [docs/07-电子系统与PCB设计.md](../docs/07-电子系统与PCB设计.md)
- [docs/08-自主导航与山区穿越.md](../docs/08-自主导航与山区穿越.md)
- [docs/09-软件架构与识别算法.md](../docs/09-软件架构与识别算法.md)
- [docs/13-开源资源与驱动索引.md](../docs/13-开源资源与驱动索引.md)
