# train · 训练流程

> **权重不入库。** 本目录只放流程与脚本，**不存放任何模型权重或训练影像**
> （YOLOv5/YOLOv8 为 **AGPL-3.0**；影像涉及伦理红线，见 [../data.yaml](../data.yaml)）。
> 总纲见 [../README.md](../README.md)。

---

## 1. 环境

```bash
# 建议独立虚拟环境
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install ultralytics            # 若走清华镜像：pip install -i https://pypi.tuna.tsinghua.edu.cn/simple ultralytics
```

| 组件 | 说明 |
|:---|:---|
| Ultralytics | 训练 / 验证 / 导出（**AGPL-3.0**，商用需授权） |
| 备选模型 | NanoDet（Apache-2.0）、PP-PicoDet（Apache-2.0）——许可更宽松 |
| 标注工具 | Label Studio / CVAT / Roboflow（本地部署优先，数据不出本机） |

---

## 2. 数据准备

```
dataset/
├── images/{train,val}/*.jpg
├── labels/{train,val}/*.txt      # YOLO 格式：cls x_c y_c w h（归一化）
└── data.yaml                     # ← 见 ../data.yaml
```

### 数据来源（**按此优先级**）

| 优先级 | 来源 | 说明 |
|:--:|:---|:---|
| 1 | **自建数据** | 本地河滩、工地、山地道路自行采集 + 人工标注。**必需** |
| 2 | **VisDrone** | 航拍小目标（人/车），**最贴近本场景的公开数据** |
| 3 | COCO | `person` / `car` / `truck`，通用但**域差大** |
| 4 | DOTA | 航拍旋转框，大目标为主 |

> ⚠ **域适应是最大的问题**：公开数据集里没有"淤泥覆盖的残骸""部分掩埋的人体""灰褐色单调地表"。
> **直接拿 COCO 训出来的模型，在灾区影像上大概率很差。**

### 合成增强（按有效性排序）

1. **颜色变换**到泥灰色系（HSV 扰动 + 色偏）；
2. **随机遮挡**（模拟掩埋：从下方裁剪）；
3. 低对比度、雾霾、阴影；
4. **随机旋转**（盘旋时目标方向任意）。

### 小目标专项

- 训练时用 **mosaic / tile** 增强；
- 输入分辨率**不要低于 640**（算力允许时）；
- 后处理阶段可考虑 **SAHI**（切片推理）提升小目标召回。

---

## 3. 训练

```bash
yolo detect train \
  model=yolov8n.pt \
  data=dataset/data.yaml \
  imgsz=640 \
  epochs=200 \
  batch=16 \
  mosaic=1.0 \
  device=0
```

| 超参 | 建议 | 理由 |
|:---|:---|:---|
| `model` | `yolov8n`（3.2 M） | 端侧首选；备选 `yolov5n` / NanoDet |
| `imgsz` | 640（训练） | 训练别用 256，**部署才降到 256** |
| `mosaic` | 1.0 | 小目标增益明显 |
| `epochs` | 200 | 早停按 val 指标 |

---

## 4. 验证（**重点看小目标召回**）

```bash
yolo detect val model=runs/detect/train/weights/best.pt data=dataset/data.yaml
```

**关键指标（按优先级）：**

1. `person` 类的 **recall @ conf=0.25**（宁可误报，不要漏）
2. `person` 类的 **PR 曲线下面积**
3. **误报数/帧**（太高会让人工判读失去意义）

---

## 5. 诚实的期望值

```
250 m 高度、GSD 6.5 cm 下：
  1.7 m 人体 ≈ 1.7 / 0.065 ≈ 26 像素  → YOLOv8n 的**小目标困难区**
  → 召回率 50~70 % 就算不错
```

> **YOLO 在这里是"打点提示"，不是"判定"。**
> 用它把几百张影像筛成几十张"疑似有人"，交给**人工判读**。

---

## 6. 验收协议（**必须做，否则不知道模型能不能用**）

| 步骤 | 做法 |
|:--:|:---|
| 1 | 在本地相似环境布设 **1.7 m 人体靶 ×5、车辆靶 ×3**（不同姿态、部分遮挡） |
| 2 | 按任务剖面（250 m AGL、盘旋）实飞采集 |
| 3 | 跑模型，统计：真检 / 漏检 / 误报 |
| 4 | 与**人工判读**结果比对（人工判读作为"真值上限"） |
| 5 | 记录：召回率、精确率、平均置信度 |

**验收判据**：`person` 召回 **≥ 50 %**（目标 70 %），误报 **≤ 5 / 帧**。

---

## 7. 下一步

导出与量化见 [../convert/README.md](../convert/README.md)；机端推理见
[../../firmware/vision/README.md](../../firmware/vision/README.md)。

---

## 许可

| 组件 | 许可 |
|:---|:---|
| Ultralytics YOLOv8 / YOLOv5 | **AGPL-3.0**（商用需取得商用授权） |
| NanoDet / PP-PicoDet | Apache-2.0 |
| 训练数据 | 各自许可（COCO=CC BY 4.0；VisDrone 需查最新条款） |
