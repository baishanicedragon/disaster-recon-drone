# vision · 视觉推理固件说明

> **本目录是"机端推理"的说明**，**数据集/训练/量化流程在 [`../../models/`](../../models/)**。
> 本仓库**不存放任何模型权重**（YOLOv5/YOLOv8 为 **AGPL-3.0**，且体积大）。

---

## 1. 通道定位（[docs/07 7.4](../docs/07-电子系统与PCB设计.md)）

| 通道 | 器件 | 用途 |
|:---|:---|:---|
| **A 实时识别** | STM32N6（M55 @800 MHz + Neural-ART NPU）+ 全局快门 CMOS（OV9282 / AR0234 级） | 回收场十字标检测、疑似人体/车辆打点、地平线检测（姿态备份） |
| **B 高清成像** | IMX477 级 12 MP + 6 mm 定焦 + Linux 小板（Pi Zero 2W / CM4 级） | 事后 SfM 拼接 + 人工判读 |

> **只有 A 通道跑在本目录的固件上**；B 通道是独立成像链路（等距触发，见 [`../lua/camera_trigger.lua`](../lua/camera_trigger.lua)）。

---

## 2. 目录约定

```
vision/
├── README.md        ← 本文件
├── train/           ← 训练脚本（**权重不入库**；流程详见 ../../models/）
├── convert/         ← ONNX → INT8 → NPU 格式的转换脚本
└── infer/           ← 视觉 MCU 推理固件（本项目自定义部分）
```

---

## 3. 推理链路（端到端）

```
训练（../../models/）
   best.pt
     ↓  yolo export format=onnx imgsz=256
   best.onnx
     ↓  INT8 量化（**必须**——NPU 只跑整数）
     │   · X-CUBE-AI（STM32N6 首选）
     │   · TFLite Micro + 全整数量化（备选）
     │   · NNCASE（K210 备选路径）
   model_int8.bin
     ↓  烧进 OctoSPI Flash（8/16 MB）
   STM32N6 推理
     ↓  UART / MAVLink 隧道（921600）
   飞控（记入日志，双份）
```

---

## 4. 接口与性能指标

| 项 | 值 | 来源 |
|:---|---:|:---|
| 输入分辨率 | 256×256（算力允许可上 320） | [docs/09 9.3](../../docs/09-软件架构与识别算法.md) |
| 目标帧率 | **≥ 15 fps**（YOLOv8n INT8） | [docs/09 9.3.1](../../docs/09-软件架构与识别算法.md) |
| 量化 | **INT8 必须**；mAP 通常掉 2~4 点 | [../../models/README.md](../../models/README.md) |
| 输出 | `{cls, conf, x_c, y_c, w, h}` 每帧多目标 | [docs/09 9.3.4](../../docs/09-软件架构与识别算法.md) |
| 传输 | UART2 / MAVLink 隧道 921600 → 飞控 | [hardware/interface/pinmap.md](../../hardware/interface/pinmap.md) |
| 落盘 | 视觉 MCU 侧写 microSD；飞控侧日志**双份** | [docs/09 9.6](../../docs/09-软件架构与识别算法.md) |

**类别定义**（与 [`../../models/data.yaml`](../../models/data.yaml) 一致）：

| ID | 类别 |
|:--:|:---|
| 0 | `person` |
| 1 | `vehicle` |
| 2 | `structure` |
| 3 | `cross_red` |
| 4 | `debris` |

---

## 5. 诚实的期望值（**不要高估**）

```
250 m 高度、GSD 6.5 cm 下：
  1.7 m 人体 ≈ 1.7 / 0.065 ≈ 26 像素  → YOLOv8n 的**小目标困难区**
  → 召回率 50~70 % 就算不错
```

> **YOLO 是"打点提示"，不是"判定"。**
> 用它把几百张影像筛成几十张"疑似有人"，交给**人工判读**——这才是价值所在。

---

## 6. 部署检查清单

- [ ] 量化校准集**具代表性**（≥ 100 张，含泥灰色调、小目标）
- [ ] 逐层量化误差检查（通常检测头误差最大）
- [ ] 实机帧率 ≥ 15 fps（含 ISP + NMS 全链路，不只是推理核）
- [ ] MAVLink 隧道 921600 无丢帧（[pinmap 走线规则](../../hardware/interface/pinmap.md)）
- [ ] 与飞控日志**双份**记录一致
- [ ] 迫降后 LoRa 信标首帧含**目标计数摘要**（如 `P:12 V:5`），让赶路的人知道值不值得快一点

---

## 7. 许可

| 组件 | 许可 |
|:---|:---|
| Ultralytics YOLOv8 / YOLOv5 | **AGPL-3.0**（商用需授权） |
| NanoDet | Apache-2.0（更宽松的替代） |
| STM32N6 HAL / X-CUBE-AI / TFLite Micro | BSD / Apache-2.0 |
| 模型权重 | **不入库** |

---

## 相关

- [../../models/](../../models/) · 训练与量化流程
- [../docs/09-软件架构与识别算法.md](../docs/09-软件架构与识别算法.md)
- [../docs/18-软件实现示例代码-机载固件.md](../docs/18-软件实现示例代码-机载固件.md) · 18.9 `detect.c`
- [../../hardware/pcb/payload-board/README.md](../../hardware/pcb/payload-board/README.md)
