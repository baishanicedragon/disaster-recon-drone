# ardupilot/params · 飞控参数

> **这 4 个 `.param` 文件是"意图清单"，不是可直接套用的成品配置。**
> ⚠ **参数名与枚举值随 ArduPilot 版本变更**（项目会重命名/增删）。
> **导入前必须**用 Mission Planner 或 QGC 的「完整参数树」逐项核对，确认参数存在且枚举含义一致后再写入。
> 加载方式：Mission Planner → *CONFIG/配置* → *Full Parameter Tree* → *Load from file*。

---

## 加载顺序

```
00-base.param      → 先加载（基础：EKF、失效保护、电池）
10-vtol-extra.param → 倒拖段与空速（**不用 Q_TAILSIT**）
20-terrain.param   → 地形跟随与高度源（峡谷关键）
30-tune.param      → 滤波与日志（PID 由 AutoTune 出，不在此预置）
```

> 每次加载后**写参数 → 重启 → 复查**，不要一次全导入后直接上电。

---

## 00-base.param（基础）

| 参数 | 值 | 依据 | 风险 |
|:---|---:|:---|:---|
| `AHRS_EKF_TYPE` | 3 | EKF3（[docs/07 7.2.1](../docs/07-电子系统与PCB设计.md)） | 老版本可能无 EKF3 |
| `EK3_ENABLE` | 1 | 启用 EKF3 | — |
| `EK2_ENABLE` | 0 | 关 EKF2，避免双 EKF 混用 | — |
| `FS_GCS_ENABLE` | **0** | **禁止链路失效触发 RTL**——本设计无 GCS 链路（[docs/09](../docs/09-软件架构与识别算法.md)） | **关键**：置非 0 会在无链路时误触发 RTL |
| `FS_LONG_ACTN` | 2 | 长时失效 → 迫降 | 按实际失效保护策略定 |
| `FS_SHORT_ACTN` | 0 | 短时失效不动作 | — |
| `BATT_FS_LOW_ACT` | 2 | 低电进入返航/迫降（[docs/07](../docs/07-电子系统与PCB设计.md)） | — |
| `BATT_FS_CRT_ACT` | 2 | 临界电量迫降 | 需与电池监测校准一致 |
| `BATT_MONITOR` | 4 | 模拟电压+电流 | 取决于配电板接口（INA226 走 I²C 时需改） |
| `ARMING_CHECK` | 1 | 保留全部解锁检查 | 自定义互锁到位后可放宽，但**禁止全关** |

---

## 10-vtol-extra.param（倒拖段 · **非 Q_TAILSIT**）

> **本项目不是尾坐（tailsitter）**：是机头朝下、尾桨朝上的**倒拖爬升**，ArduPilot 无原生模式。
> 倒拖段与改平段由**挂在 AUTO 之外的自定义状态机**接管（[docs/18 18.3](../docs/18-软件实现示例代码-机载固件.md)）。

| 参数 | 值 | 依据 |
|:---|---:|:---|
| `Q_ENABLE` | **0** | **不启用 Q 框架**（不用 Q_TAILSIT，[firmware README](../../README.md)） |
| `AIRSPEED_MIN` | **20.9** | 失速保护：低于 1.1 Vs（19.0）禁止撑开/拉平 |
| `AIRSPEED_CRUISE` | 28 | 巡航 28 m/s（README 关键指标） |
| `RESTART_CRUISE_ASP` | 22 | 拉平后重启推进的空速门槛（> 1.15 Vs） |
| `ARSPD_ENABLE` | 1 | 启用空速计（MS4525DO） |
| `ARSPD_USE` | 1 | 空速参与控制 |

### 自定义门控参数走 `SCR_USER*`

ArduPilot **没有** `vs_thresh` / `h_deploy_min` 这类原生参数。自定义门控值建议存进
**`SCR_USER1`~`SCR_USER4`**（脚本用户参数），由 `lua/` 脚本与自定义固件读取：

| 参数 | 值 | 含义 | 对应 |
|:---|---:|:---|:---|
| `SCR_USER1` | 20.9 | `vs_thresh`（撑开门控空速） | [docs/09 9.5](../docs/09-软件架构与识别算法.md) |
| `SCR_USER2` | 90 | `h_deploy_min`（撑开门控最低高度） | [docs/09 9.5](../docs/09-软件架构与识别算法.md) |
| `SCR_USER3` | 20.0 | `COMM_CUT_ALT`（**仅作显示/日志，机载端强制用本地常量，不接受此值**） | [docs/17 17.8](../docs/17-机载嵌入式软件框架.md) |
| `SCR_USER4` | 150 | 段 I 关机高度 `CLIMB_CUTOFF_H` | [docs/07 7.2.2](../docs/07-电子系统与PCB设计.md) |

> ⚠ **`SCR_USER3` 不可作为安全边界**：`>20 m` 通讯切断是**不可屏蔽**逻辑，
> 机载 `mission_rx_parse()` 会**强制用本地 `COMM_CUT_ALT` 覆盖**任何下发值（[docs/18 18.7](../docs/18-软件实现示例代码-机载固件.md)）。

---

## 20-terrain.param（地形跟随 · 峡谷关键）

| 参数 | 值 | 依据 | 风险 |
|:---|---:|:---|:---|
| `TERRAIN_ENABLE` | **1** | 地形跟随（DEM 文件放 SD 卡），[docs/07](../docs/07-电子系统与PCB设计.md) | DEM 文件缺失会导致跟随失效 |
| `TERRAIN_FOLLOW` | 1 | 启用跟随 | — |
| `TERRAIN_MARGIN` | 150 | 按走廊净空 150 m 设（[docs/08](../docs/08-自主导航与山区穿越.md)） | 过大 → 飞太高；过小 → 撞坡 |
| `EK3_SRC1_POSXY` | 3 | 主定位 GPS | 枚举值需核对版本 |
| `EK3_SRC1_VELXY` | 3 | GPS | 同上 |
| `EK3_SRC1_POSZ` | **1** | **高度以气压为主**（峡谷内 GPS 高误差大） | **关键** |
| `EK3_SRC1_YAW` | 2 | 用 GPS 航向（COG）为主航向源 | ⚠ 峡谷**磁异常严重**（[docs/07 7.3](../docs/07-电子系统与PCB设计.md)） |

> **磁罗盘**：吉隆沟为深切构造带，岩体磁性不均 → 磁罗盘误差可达数十度。
> 对策：起飞前在**已知航向**完成校准；飞行中**禁用或以 GPS 航向为主**（`EK3_SRC1_YAW`），磁罗盘仅作静态初始化。
> 若实测确认不可用，进一步把 `COMPASS_USE` 置 0——**必须实测后决定**，不要默认全关。

---

## 30-tune.param（滤波与日志）

| 参数 | 值 | 依据 |
|:---|---:|:---|
| `INS_GYRO_FILTER` | 40 | 陀螺低通初值（按振动实测调） |
| `INS_ACCEL_FILTER` | 20 | 加速度低通初值 |
| `LOG_BITMASK` | 默认 + 姿态/控制 | 取证用，[docs/09 9.6](../docs/09-软件架构与识别算法.md) |
| `LOG_DISARMED` | 1 | 未解锁也记日志（地面排查） |

> **PID 不在此预置**：舵面 PID 由 **AutoTune** 出，或按 [docs/12](../docs/12-测试与验证流程.md) 手动整定。
> 预置他人 PID 在 12.93 kg / 双翼构型上**有害无益**。

---

## 导入后必做

- [ ] 每个参数在**当前固件版本**中存在且枚举含义一致
- [ ] `FS_GCS_ENABLE = 0` 已确认（否则无链路即 RTL）
- [ ] `EK3_SRC1_POSZ` 为气压（峡谷高度源）
- [ ] 空速计校准完成（`ARSPD_*` 与地面值对得上）
- [ ] DEM/.terrain 文件已放进飞控 SD 卡，`TERRAIN_ENABLE=1` 生效
- [ ] 全参数**导出备份**一份（`.param`），再进入 SITL

---

## 相关

- [docs/07-电子系统与PCB设计.md](../docs/07-电子系统与PCB设计.md) · 7.2.1 必需参数
- [docs/08-自主导航与山区穿越.md](../docs/08-自主导航与山区穿越.md)
- [docs/09-软件架构与识别算法.md](../docs/09-软件架构与识别算法.md)
- [../lua/](../lua/) · 读取 `SCR_USER*` 的脚本
- [docs/18-软件实现示例代码-机载固件.md](../docs/18-软件实现示例代码-机载固件.md)
