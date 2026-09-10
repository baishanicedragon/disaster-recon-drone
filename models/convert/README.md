# convert · 量化与部署

> **权重与派生二进制不入库。** 本目录只放流程与脚本。
> 链路总纲见 [../README.md](../README.md)，机端推理见
> [../../firmware/vision/README.md](../../firmware/vision/README.md)。

---

## 1. 链路

```
best.pt                       ← 训练产出（不入库）
   ↓  yolo export format=onnx imgsz=256
best.onnx
   ↓  INT8 量化（**必须**——NPU 只跑整数）
   │   · X-CUBE-AI（STM32N6 首选）
   │   · TFLite Micro + 全整数量化（备选）
   │   · NNCASE（K210 备选路径）
model_int8.bin
   ↓  烧进 OctoSPI Flash（8/16 MB）
STM32N6 推理（目标 ≥ 15 fps）
   ↓  UART / MAVLink 隧道 921600
飞控（记入日志，双份）
```

---

## 2. 导出 ONNX

```bash
yolo export model=best.pt format=onnx imgsz=256 opset=12 simplify
```

| 项 | 值 | 说明 |
|:---|---:|:---|
| `imgsz` | **256** | 与机端输入一致（算力允许可上 320） |
| `opset` | 12 | 与下游量化工具兼容；按工具链要求调 |
| `simplify` | 开 | 去掉冗余算子，量化更顺 |

> ⚠ 训练用 640、**部署用 256**，分辨率不一致会带来召回下降——
> 这是有意的算力取舍，但**必须实测下降幅度**再决定是否可接受。

---

## 3. INT8 量化

### 3.1 路线 A：X-CUBE-AI（STM32N6 首选）

```bash
# STM32CubeIDE / X-CUBE-AI CLI（命令以 ST 官方文档为准）
ai validate --model best.onnx --target stm32n6
ai generate --model best.onnx --target stm32n6 --quantization int8 \
            --calibration calib_set/      # 代表集
```

### 3.2 路线 B：TFLite Micro（全整数量化）

```python
import tensorflow as tf

converter = tf.lite.TFLiteConverter.from_saved_model("saved_model/")
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_dataset_gen   # 代表集
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type  = tf.int8
converter.inference_output_type = tf.int8
tflite_int8 = converter.convert()
open("model_int8.tflite", "wb").write(tflite_int8)
```

### 3.3 路线 C：NNCASE（K210 备选）

```bash
ncc compile best.onnx model_int8.kmodel -i onnx \
    --dataset calib_set --inference-type uint8
```

---

## 4. 量化要点

| 项 | 说明 |
|:---|:---|
| **校准集** | **必须用代表性数据**：≥ 100 张，含泥灰色调、小目标、部分遮挡 |
| 精度损失 | INT8 通常 **mAP 掉 2~4 个点**，可接受 |
| 输入尺寸 | 256×256（STM32N6 目标 ≥ 15 fps）；算力允许可上 320 |
| 逐层检查 | 用工具看哪些层量化误差大（**通常是检测头**）→ 考虑头部分浮点或混合精度 |
| 前后对比 | 量化前后在**同一验证集**上对拍，记录召回下降幅度 |

> ⚠ **校准集随便凑 = 量化后大概率崩**。宁可少跑一次训练，也要把校准集做对。

---

## 5. 烧录与验证

| 步骤 | 做法 |
|:--:|:---|
| 1 | `model_int8.bin` 烧进 OctoSPI Flash（8/16 MB），保留固件分区 |
| 2 | 上电自检：模型加载成功、版本与类别 ID 与 [../data.yaml](../data.yaml) 一致 |
| 3 | **实测帧率 ≥ 15 fps**（含 ISP + NMS 全链路，不只是推理核） |
| 4 | MAVLink 隧道 921600 抓包无丢帧 |
| 5 | 与飞控日志**双份**记录一致 |

---

## 6. 类别 ID 一致性（**最容易出错**）

| 位置 | 要求 |
|:---|:---|
| [../data.yaml](../data.yaml) | `names` 顺序 = ID |
| 机端推理固件 | 输出 ID 必须与 `data.yaml` 一致 |
| [../../docs/18 18.9](../../docs/18-软件实现示例代码-机载固件.md) `CLS_NAME[]` | 顺序一致 |

> 类别顺序错一位，`person` 就会被当成 `vehicle`——**打点全错**。
> 每次改数据集都要复核这三处。

---

## 许可

| 组件 | 许可 |
|:---|:---|
| 模型权重 | **不入库**（AGPL 风险） |
| X-CUBE-AI | ST 自有许可（按官方条款） |
| TFLite Micro | Apache-2.0 |
| NNCASE | Apache-2.0 |
