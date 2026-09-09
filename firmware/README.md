# firmware/ · 固件与任务逻辑

> 状态：**占位**。
> 本仓库**不重新实现飞控**。飞控直接用 **ArduPilot**（GPLv3）。
> 这里只放：飞控参数、任务层脚本、**倒拖段 + 无动力改平段控制器**、以及视觉推理代码。

---

## 设计原则

> **能不自己写就不自己写。**

ArduPilot 已经提供了：EKF3、固定翼巡航、地形跟随、RTL、自动降落、
失效保护、AutoTune、Lua 脚本接口。
**从零重写这些 = 项目失败率翻倍。**

本项目只在**两处**写自定义代码（[docs/09](../docs/09-软件架构与识别算法.md) 9.5）：

1. **倒拖段控制器（段 I）**——ArduPilot 无"机头朝下倒拖爬升"原生模式；
   但倒拖段靠**被动摆式稳定**（无空速不需要自旋），控制器只做**差动推力阻尼**，实现量小；
2. **无动力改平段控制器（段 II：CUTOFF → DEPLY → FLARE）**——关机后俯冲增速、
   门控双翼撑开、2.0 g 拉平的时序状态机（见 [docs/08](../docs/08-自主导航与山区穿越.md) 8.6）。

> v0.3 已**删除自旋段控制器**（spin_controller 不再需要）——自旋体系整体废弃。

---

## 目录结构（规划）

```
firmware/
├── README.md                     ← 本文件
├── ardupilot/
│   ├── params/                   ← 参数文件（.param）
│   │   ├── 00-base.param         ← 机架、舵面、电调、失效保护
│   │   ├── 10-vtol-extra.param   ← 倒拖段自定义参数（非 Q_TAILSIT）
│   │   ├── 20-terrain.param      ← TERRAIN_*、地形跟随
│   │   ├── 30-tune.param         ← PID、滤波（AutoTune 前初值）
│   │   └── README.md             ← 每个参数的作用与依据
│   └── lua/
│       ├── energy_manager.lua    ← 能量管理（强制返航判据）
│       ├── camera_trigger.lua    ← 等距触发
│       └── abort_logic.lua       ← 中止判据
├── transition_controller/        ← 段 I + 段 II 控制器（自定义，最小实现）
│   ├── src/dragclimb_ctrl.c      ← 段 I：倒拖爬升差动推力阻尼
│   ├── src/deploy_ctrl.c         ← 段 II：关机-俯冲-双翼撑开门控-2.0g 拉平时序
│   ├── tests/                    ← 单元测试（门控逻辑、时序状态机）
│   └── README.md                 ← 算法说明
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
| ARM GCC | 随 ArduPilot 工具链 | 自定义控制器编译 |
| Python | 3.10+ | Lua 脚本测试、日志分析 |
| STM32CubeIDE / CubeMX | 随 N6 支持包 | 视觉 MCU 固件 |

---

## 关键参数说明（摘要，完整列表见 `ardupilot/params/`）

| 参数 | 值 | 理由 |
|:---|---:|:---|
| `TERRAIN_ENABLE` | 1 | 地形跟随（DEM 文件放 SD 卡） |
| `EK3_SRC1_POSZ` | BARO | 峡谷内 GPS 高度误差大 |
| `FS_GCS_ENABLE` | 0 | **禁止链路失效触发 RTL**（本设计无链路） |
| `BATT_FS_LOW_ACT` | 2 | 低电进入返航/迫降 |
| 倒拖段自定义 | 见 `transition_controller` | **不用 Q_TAILSIT**（非尾坐，是机头朝下倒拖） |

> ⚠ **参数名会随固件版本变更**，以 ArduPilot 官方文档为准。
> 倒拖段与改平段由**自定义状态机**接管（挂在 AUTO 外），ArduPilot 只负责巡航后的常规段。

---

## 仿真优先

**在真实飞行前，必须过 SITL。**

```bash
# 示例（以官方文档为准）
cd ardupilot/ArduPlane
sim_vehicle.py -v ArduPlane --console --map
```

SITL 中至少跑通：

- [ ] 倒拖爬升段（模拟推力线 + 差动阻尼；无空速姿态扰动注入）
- [ ] 关机 → 俯冲 → **双翼撑开门控**（空速 20.9 m/s + 高度 90 m 硬与门）→ 2.0 g 拉平 → 平飞
- [ ] 地形跟随（加载本地 DEM）
- [ ] 盘旋（LOITER_TURNS / LOITER_TIME）
- [ ] GNSS 关断 120 s 的航位推算
- [ ] 能量管理规则触发返航
- [ ] 每个状态机转移至少触发一次（含 V_NOSE 备用剖面）

---

## 测试

| 层 | 工具 | 范围 |
|:---|:---|:---|
| 单元 | 简易 C test / Unity | 倒拖阻尼增益、撑开门控（4 锁确认）、改平时序、能量管理判据 |
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
