# 19 · 软件实现示例代码（安卓 APP · Kotlin）

> **状态：示例代码 / 参考实现。未编译、未在真机跑通。**
> 本章是 [16 章](./16-安卓APP架构与素材库.md) 的**代码化展开**，配套 [18 章](./18-软件实现示例代码-机载固件.md) 的机载固件。
> 目的是让实际使用者拿到一份"模块怎么切、协议怎么对、权限怎么申"的参考骨架，**不是可直接上线的成品**。
> 所有端点、key、阈值均为示例值，落地必须替换并实测。
>
> ⚠ **APP 全程不依赖公网**：地形图/影像在有网处预取落盘，飞行中纯本地（16.1 设计原则）。
> ⚠ **20 m 后 APP 只有只读权**：`ABORT` 按钮必须在 alt ≥ 20 m 时置灰，这是安全边界，不是 UI 偏好。

---

## 19.1 示例硬件与工程基线

| 项 | 示例值 | 说明 |
|:---|:---|:---|
| 终端 | Android 10+（API 29+）手机，支持 **Wi-Fi 直连 AP**、**USB OTG** | 示例假定有 OTG（死体回收读卡） |
| 语言 / UI | Kotlin + Jetpack Compose | 16.1 |
| 最低 SDK / 目标 | 29 / 34 | |
| 地图 | MapLibre Android（离线矢量）+ 自绘 DEM 晕渲 | 避免联网 SDK 依赖 |
| 网络 | OkHttp（仅任务前预取） | 飞行前用完即断 |
| 影像 | Coil + `BitmapRegionDecoder`（大图分块） | 16.1 |
| 持久化 | Room + 文件沙箱 | |

**依赖摘要（`build.gradle`）**

```kotlin
dependencies {
    implementation("androidx.compose.ui:ui:1.6.8")
    implementation("androidx.activity:activity-compose:1.9.0")
    implementation("org.maplibre.gl:android-sdk:11.x.x")   // 离线矢量
    implementation("com.squareup.okhttp3:okhttp:4.12.0")    // 仅预取
    implementation("io.coil-kt:coil-compose:2.6.0")
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.camera:camera-camera2:1.3.4")  // 标布校验
    implementation("androidx.documentfile:documentfile:1.0.1") // TF 卡 SAF
}
```

**权限摘要（`AndroidManifest.xml`）**

```xml
<!-- 配对与回收：Wi-Fi 直连飞机 AP，不需要互联网 -->
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
<uses-permission android:name="android.permission.CHANGE_WIFI_STATE" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" /> <!-- Android 10+ 扫 AP 必需 -->
<!-- 预取地形图（仅任务前，有网处） -->
<uses-permission android:name="android.permission.INTERNET" />
<!-- 回收：振铃 + 相机标布校验 + USB OTG 读卡 -->
<uses-permission android:name="android.permission.VIBRATE" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.hardware.usb.host" />
<uses-feature android:name="android.hardware.usb.host" android:required="false" />
```

> ⚠ **位置权限**：Android 10+ 扫描 Wi-Fi 需要 `ACCESS_FINE_LOCATION`（且需动态申请）。
> 这是系统限制，不是本 APP 要定位——需在 UI 上向操作员说明。

---

## 19.2 素材库 `sources.json` + 源探测 `SrcManager`

```json
/* assets/sources.json —— 16.2.2 源注册表（数据不是逻辑） */
[
  {"id":"COP_DEM30","type":"DEM","res":30,"coverage":"GLOBAL",
   "endpoint":"https://.../copernicus-dem","auth":"none","license":"OPEN"},
  {"id":"ALOS_AW3D","type":"DEM","res":30,"coverage":"GLOBAL",
   "endpoint":"https://.../aw3d","auth":"register","license":"OPEN"},
  {"id":"GS_CLOUD","type":"DEM_IMG","res":30,"coverage":"CN",
   "endpoint":"https://www.gscloud.cn/...","auth":"register","license":"OPEN"},
  {"id":"OPEN_TOPO","type":"DEM","res":1,"coverage":"GLOBAL",
   "endpoint":"https://.../opentopography","auth":"apikey","license":"OPEN"},
  {"id":"SENTINEL2","type":"IMG","res":10,"coverage":"GLOBAL",
   "endpoint":"https://.../sentinel2","auth":"none","license":"OPEN"},
  {"id":"GF_DISASTER","type":"IMG","res":1,"coverage":"CN",
   "endpoint":"https://.../gf-emergency","auth":"apply","license":"RESTRICTED"}
]
```

```kotlin
// src/SrcManager.kt —— 16.2「源注册表 + 自动探测」（不是无脑爬虫）
data class SrcDef(
    val id: String, val type: String, val res: Int,
    val coverage: String, val endpoint: String, val auth: String
)

class SrcManager(ctx: Context) {
    private val defs: List<SrcDef> = loadFromAssets(ctx, "sources.json")

    /** 按任务区 bbox + 类型需求，自动探测「哪些源覆盖 & 当前可用」 */
    suspend fun probe(bbox: BBox, need: Set<String>): List<SrcDef> = withContext(Dispatchers.IO) {
        defs.filter { it.type in need && covers(it, bbox) }
            .filter { def ->                       // 轻量 HEAD 探测，不做页面爬取
                runCatching {
                    val req = Request.Builder().url(def.endpoint).head().build()
                    client.newCall(req).execute().use { it.isSuccessful }
                }.getOrDefault(false)
            }
            .sortedWith(compareBy({ authRank(it.auth) }, { it.res }))  // 免认证 + 高分辨率优先
    }

    /** 16.3 降级：高分源不可达 → 降到 COP_DEM30，并在任务卡标注净空提到 150 m */
    fun degrade(dem: List<SrcDef>): SrcDef =
        dem.firstOrNull { it.res <= 30 } ?: defs.first { it.id == "COP_DEM30" }
}
```

> **为什么不用爬虫**：任意站点 HTML 结构多变，爬虫易碎且多违反 ToS（16.2.1）。
> 「自动搜索」在代码层落实为**注册表 + HEAD 探测 + 排序择优**。

---

## 19.3 `MapFetch`：抓取并落盘

```kotlin
// map/MapFetch.kt —— 16.3 落 mission_staging/
class MapFetch(private val ctx: Context) {
    suspend fun fetch(bbox: BBox, srcs: List<SrcDef>): Staging = withContext(Dispatchers.IO) {
        val dir = File(ctx.filesDir, "mission_staging").apply { mkdirs() }
        val dem   = srcs.first { it.type.contains("DEM") }
        val img   = srcs.first { it.type == "IMG" || it.type == "DEM_IMG" }

        download(dem.endpoint, File(dir, "dem.tif"))     // GeoTIFF, WGS84/UTM
        download(img.endpoint, File(dir, "sat.jpg"))     // 带地理参考

        // 16.3 校验：bbox 完整、无空洞；空洞区在 08 章净空里加倍处理
        val holes = GeoTiff.checkHoles(File(dir, "dem.tif"), bbox)
        Staging(dir, holes)
    }
}
```

---

## 19.4 `TrajCompile`：生成 `mission.bin`（与 17.7 严格对称）

```kotlin
// traj/TrajCompile.kt —— 小端；坐标 int32 定标 1e7
object MissionCodec {
    private const val MAGIC = "HDRS"

    fun encode(m: Mission): ByteArray {
        val b = ByteBuffer.allocate(1 shl 20).order(ByteOrder.LITTLE_ENDIAN)
        b.put(MAGIC.toByteArray())      // magic
        b.putShort(1)                   // ver
        val payloadStart = b.position() + 8   // 预留 crc32(4) + size(4)
        b.putInt(0); b.putInt(0)

        // [TRAJ]
        b.putShort(m.wp.size.toShort())
        m.wp.forEach { w ->
            b.putInt((w.lat * 1e7).toInt()); b.putInt((w.lon * 1e7).toInt())
            b.putShort(w.altAgl.toShort()); b.put(w.spd.toByte())
        }
        b.put(m.fence.size.toByte())
        m.fence.forEach { p -> b.putInt((p.lat*1e7).toInt()); b.putInt((p.lon*1e7).toInt()) }
        b.putShort(m.clearH.toShort())                       // 默认 150
        b.putInt((m.recover.lat*1e7).toInt()); b.putInt((m.recover.lon*1e7).toInt())
        b.putFloat(m.markerX); b.putFloat(m.markerY); b.putFloat(m.markerHeading)

        // [ROI] —— 16.5 圈注结果（polygon 是地理坐标，不是像素）
        b.put(m.roi.size.toByte())
        m.roi.forEach { r ->
            b.put(r.cls.toByte()); b.put(r.poly.size.toByte())
            r.poly.forEach { p -> b.putInt((p.lat*1e7).toInt()); b.putInt((p.lon*1e7).toInt()) }
            b.put(r.label.toByteArray().copyOf(24))
            b.put(r.priority.toByte()); b.put(r.expectCnt.toByte())
        }

        // [PARAMS]
        b.putFloat(20.9f)      // vs_thresh
        b.putShort(90)         // h_deploy_min
        b.putFloat(20.0f)      // comm_cut_alt —— 机载端会强制忽略此值（18.7）
        b.putShort(300)        // loiter_sec
        b.putFloat(1.15f)      // return_margin

        val payload = b.array().copyOfRange(payloadStart, b.position())
        val out = b.array().copyOf(b.position() + 32)
        // 回填 crc32 + size
        val crcBuf = ByteBuffer.wrap(out).order(ByteOrder.LITTLE_ENDIAN)
        crcBuf.putInt(payloadStart - 8, CRC32().apply { update(payload) }.value.toInt())
        crcBuf.putInt(payloadStart - 4, payload.size)
        // [TAIL] sha256
        System.arraycopy(MessageDigest.getInstance("SHA-256").digest(payload), 0,
                         out, b.position(), 32)
        return out
    }
}
```

> ⚠ **安全边界提示给实现者**：APP 侧虽然写了 `comm_cut_alt`，
> 但机载 `mission_rx_parse()` 会**强制用本地常量覆盖它**（18.7）。
> APP 不得提供任何"临时调高切断高度"的入口。

---

## 19.5 `Pairing`：Wi-Fi 直连 + 帧协议（16.6 / 17.3）

```kotlin
// link/Pairing.kt —— 连飞机 AP HDRS1_<sn4>，不走互联网
class Pairing(private val ctx: Context) {

    @RequiresApi(29)
    fun connectAp(ssidPrefix: String = "HDRS1_", pass: String? = null) {
        val spec = WifiNetworkSpecifier.Builder()
            .setSsidPattern(PatternMatcher(ssidPrefix + "*", PatternMatcher.PATTERN_PREFIX))
            .apply { pass?.let { setWpa2Passphrase(it) } }
            .build()
        val req = NetworkRequest.Builder()
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .setNetworkSpecifier(spec).build()

        val cm = ctx.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val cb = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(n: Network) { cm.bindProcessToNetwork(n) } // 关键：绑定到该网络
        }
        cm.requestNetwork(req, cb)
    }

    /* 帧格式与 18.6 一致：[0xAA][0x55][type][len u16][payload][crc16] */
    fun send(sock: Socket, type: Int, payload: ByteArray = ByteArray(0)) {
        val buf = ByteBuffer.allocate(7 + payload.size).order(ByteOrder.LITTLE_ENDIAN)
        buf.put(0xAA.toByte()); buf.put(0x55.toByte()); buf.put(type.toByte())
        buf.putShort(payload.size.toShort()); buf.put(payload)
        val crc = crc16(buf.array(), 5 + payload.size)
        buf.putShort(crc.toShort())
        sock.getOutputStream().write(buf.array())
    }

    /** 握手 → 下发任务 → 等 ACK（16.6） */
    suspend fun handshakeAndPush(sock: Socket, mission: ByteArray): Boolean {
        send(sock, F_HELLO, appVerBytes())               // HELLO{app_ver}
        val ready = readFrame(sock)                       // READY{hw_ver,status}
        if (ready.type != F_READY) return false
        send(sock, F_MISSION, mission)                    // MISSION{bin,sha256}
        val rsp = readFrame(sock)
        return rsp.type == F_ACK                          // ACK{sha256,PREP} / NAK{reason}
    }
}

const val F_HELLO=0x01; const val F_READY=0x02; const val F_MISSION=0x03
const val F_ACK=0x04;   const val F_NAK=0x05;   const val F_CHK=0x06
const val F_ARM=0x07;   const val F_ABORT=0x08; const val F_BEACON=0x09
const val F_DATA=0x0A
```

---

## 19.6 `ChecklistUi`：三步顺序确认（16.7）

```kotlin
// ui/ChecklistUi.kt —— 飞机回报状态字驱动，不可跳步
data class ChkWord(
    val voltOk: Boolean, val wingLock: List<Boolean>,
    val prop: List<Boolean>, val wireOk: Boolean
) {
    val allGreen get() = voltOk && wireOk && wingLock.all { it } && prop.all { it }
}

@Composable
fun ChecklistScreen(chk: ChkWord, onArm: () -> Unit) {
    Column {
        Step(1, "电压指示灯", chk.voltOk, "电芯 < 3.5 V 或压差 > 0.2 V")
        Step(2, "机翼/螺旋桨限动器",
             chk.wingLock.all { it } && chk.prop.all { it },
             "任一片半翼未锁 / 桨未顺桨")
        Step(3, "导线连接", chk.wireOk, "主供电或 ESC 回路开路")

        Button(onClick = onArm, enabled = chk.allGreen) {
            Text(if (chk.allGreen) "起飞就绪 · 解锁" else "检查未通过")
        }
        // 16.7 软硬双保险：两端不一致以飞机为准，飞机不会 ARM
    }
}
```

---

## 19.7 `FlightMon`：ETA + 撤销 + T-10 min 振铃（16.8）

```kotlin
// ui/FlightMon.kt
@Composable
fun FlightScreen(seg: Seg, altM: Float, etaSec: Int, onAbort: () -> Unit) {
    val cutAlt = 20.0f
    val abortable = altM < cutAlt && seg == Seg.SEG_I      // 仅 <20 m 可撤销

    Column {
        Text("段 ${seg.ordinal + 1} · 高度 ${altM}m · 返程 ETA ${etaSec / 60}分")
        Button(onClick = onAbort, enabled = abortable) {
            Text(if (abortable) "撤销任务（就地回收）" else "已切断指令链 · 自主飞行中")
        }
    }
}

/** T-10 min 触发振铃 + 通知（16.9.1） */
fun scheduleReturnAlert(ctx: Context, etaSec: Int) {
    val lead = 10 * 60
    if (etaSec <= lead) {
        val v = ctx.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        if (Build.VERSION.SDK_INT >= 26)
            v.vibrate(VibrationEffect.createWaveform(longArrayOf(0, 800, 400, 800), -1))
        notify(ctx, "前往回收场 R0", "预计 ${etaSec / 60} 分钟后落地，请检查地面标布")
    }
}
```

> ⚠ **`abortable` 判据是安全边界**：`altM >= cutAlt` 时按钮必须置灰。
> 即便 APP 强行发出 `ABORT`，机载 `link_rx_accept()` 也会丢弃（18.4）。

---

## 19.8 `RecoverUi`：标布几何引导（不依赖 AI）

```kotlin
// ui/RecoverUi.kt —— 16.9.1 只用手机相机 + 几何引导
data class MarkerGuide(val dxM: Float, val rotDeg: Float, val inFrame: Boolean)

/** 由 mission.bin 预期位（x,y,heading）与手机当前位姿算偏移 */
fun computeGuide(expect: FloatArray, cur: Pose): MarkerGuide {
    val dx = expect[0] - cur.x; val dy = expect[1] - cur.y
    return MarkerGuide(
        dxM = kotlin.math.sqrt(dx*dx + dy*dy),
        rotDeg = Math.toDegrees(kotlin.math.atan2(dy, dx).toDouble()).toFloat() - expect[2],
        inFrame = true
    )
}

@Composable
fun MarkerOverlay(g: MarkerGuide) {
    // 叠加引导框 + 文字/箭头指示（16.9.1）
    Text(when {
        !g.inFrame       -> "标布不在画面内，请后退取景"
        g.dxM > 0.5f     -> "标布需向${if (g.dxM > 0) "左" else "右"}移 %.1f m".format(g.dxM)
        abs(g.rotDeg) > 5 -> "标布需旋转 %.0f°".format(g.rotDeg)
        else             -> "标布位置正确，等待落地"
    })
}
```

---

## 19.9 `TfReader`：死体回收（USB OTG / SAF）

```kotlin
// usb/TfReader.kt —— 16.9.2 拔 microSD → 手机读卡器
class TfReader(private val act: ComponentActivity) {

    /** 用 SAF 让用户选中 OTG 读卡器中的 datalog 目录（避免自研 mass-storage 驱动） */
    fun openCard(result: (Uri?) -> Unit) {
        val i = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).apply {
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        act.registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { r ->
            result(r.data?.data)
        }.launch(i)
    }

    /** 解析 17.6 目录：video.mp4 / annotations.json / frames/ / telemetry.log */
    fun readDatalog(ctx: Context, root: Uri): Datalog? {
        val df = DocumentFile.fromTreeUri(ctx, root) ?: return null
        val taskDir = df.listFiles().firstOrNull { it.name?.startsWith("HDRS") == true }
            ?: return null
        val ann = taskDir.listFiles().firstOrNull { it.name == "annotations.json" }
            ?.let { ctx.contentResolver.openInputStream(it.uri)?.readBytes() }
        val json = ann?.let { JSONObject(String(it)) }
        return Datalog(
            video = taskDir.listFiles().firstOrNull { it.name == "video.mp4" }?.uri,
            annotations = json,
            telemetry = taskDir.listFiles().firstOrNull { it.name == "telemetry.log" }?.uri
        )
    }
}
```

---

## 19.10 `Share`：系统分享（微信 / 钉钉 / 邮件）

```kotlin
// share/Share.kt —— 16.10 不集成私有 SDK，走系统 ACTION_SEND
fun shareToCommand(ctx: Context, images: List<Uri>, ann: JSONObject?, cmdEmail: String) {
    val summary = ann?.optJSONArray("missing")?.let { "未发现目标 ${it.length()} 项" } ?: "齐全"

    val i = Intent(Intent.ACTION_SEND_MULTIPLE).apply {
        type = "image/*"
        putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(images))
        putExtra(Intent.EXTRA_EMAIL, arrayOf(cmdEmail))       // 指挥部地址预填
        putExtra(Intent.EXTRA_SUBJECT, "HDRS-1 侦察结果 · ${System.currentTimeMillis()}")
        putExtra(Intent.EXTRA_TEXT, "任务摘要：$summary")
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    ctx.startActivity(Intent.createChooser(i, "发送到救灾群 / 钉钉 / 邮件"))
}
```

> **为什么不集成微信 SDK**：系统分享表已覆盖微信/钉钉/邮件，避开私有 SDK 的审核与密钥（16.10）。

---

## 19.11 状态机与验证提示（对应 15.5.2）

```
CONNECTING → CHECKLIST → READY → FLYING → MONITORING → RETURN_ALERT → RECOVER → SHARE
```

| 项 | 说明 |
|:---|:---|
| **离线优先** | 地形图/影像在有网处预取落盘；飞行中禁用网络请求（16.1）。 |
| **撤销边界** | `ABORT` 仅在 `alt < 20 m` 且段 I 时可用；置灰由 UI 与机载双重把关。 |
| **标布校验** | 只用相机 + 几何引导，**不做 AI 识别**（16.9.1）——简单可靠。 |
| **两通道导入统一** | WiFi 活体与 TF 死体回收后都进本地库，按 ROI `priority` 排序展示。 |
| **真机验证清单** | ① Android 10+ 扫 AP 的位置权限；② OTG 读卡器兼容性（exFAT/FAT32）；③ 大卫星图分块解码内存；④ 振铃在静音/勿扰下的行为。 |
| **未覆盖** | 本章不含 Gradle 完整配置、Room schema、Compose 导航与 Hilt 注入。 |

---

**上一章**：[18-软件实现示例代码-机载固件.md](./18-软件实现示例代码-机载固件.md)
