/* HDRS-1「迅鸢」— 场景 / 任务剖面动画 / 交互面板 */

const ALT_VIS = 0.05;          // 真实高度 -> 视觉高度（80 m -> 4 m）
const T_END = 70;

/* ---------------- 场景 ---------------- */
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0f14);
scene.fog = new THREE.Fog(0x0b0f14, 18, 90);

const camera = new THREE.PerspectiveCamera(45, innerWidth / innerHeight, 0.05, 2000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.getElementById('stage').appendChild(renderer.domElement);

scene.add(new THREE.HemisphereLight(0xbcd4ff, 0x2a2b26, 0.75));
const sun = new THREE.DirectionalLight(0xfff3e0, 1.5);
sun.position.set(6, 12, 8); sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
sun.shadow.camera.left = -8; sun.shadow.camera.right = 8;
sun.shadow.camera.top = 8; sun.shadow.camera.bottom = -8;
scene.add(sun);
const rim = new THREE.DirectionalLight(0x7fb0ff, 0.5); rim.position.set(-8, 4, -6); scene.add(rim);

/* 地面：软质河滩 / 草甸（迫降场） */
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(400, 400),
  new THREE.MeshStandardMaterial({ color: 0x2c3128, roughness: 1.0, metalness: 0 }));
ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);
const grid = new THREE.GridHelper(400, 80, 0x3d4a38, 0x242a22);
grid.position.y = 0.002; scene.add(grid);
/* 迫降场标记：红布十字（文档：地面铺设红布十字标） */
const LZ_X = 30;
const crossMat = new THREE.MeshBasicMaterial({ color: 0xd6453f, transparent: true, opacity: 0.55 });
[[6.0, 0.5], [0.5, 6.0]].forEach(([w, d]) => {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), crossMat);
  m.rotation.x = -Math.PI / 2; m.position.set(LZ_X, 0.01, 0); scene.add(m);
});
/* 远山剪影（吉隆沟谷意象） */
for (let i = 0; i < 22; i++) {
  const h = 6 + Math.random() * 16;
  const c = new THREE.Mesh(
    new THREE.ConeGeometry(4 + Math.random() * 8, h, 5),
    new THREE.MeshStandardMaterial({ color: 0x1a2430, roughness: 1, flatShading: true }));
  const a = Math.random() * Math.PI * 2, r = 55 + Math.random() * 45;
  c.position.set(Math.cos(a) * r, h / 2 - 1, Math.sin(a) * r);
  scene.add(c);
}

/* ---------------- 机体 ---------------- */
const world = new THREE.Group(); scene.add(world);
const posG = new THREE.Group(); world.add(posG);        // 位置 + 航向
const pitchG = new THREE.Group(); posG.add(pitchG);      // 竖直 <-> 平飞
const spinG = new THREE.Group(); pitchG.add(spinG);      // 自旋 + 坡度
const body = new THREE.Group(); spinG.add(body);
body.position.x = -0.775;                                 // 让机体中心大致在原点

const noseG = buildNose(body);
const fuseG = buildFuselage(body);
const boomM = buildBoom(body);
const wingO = buildWing(body);
const tailG = buildTail(body);
const propO = buildPropulsion(body);
const legO = buildLegs(body);
const skidG = buildSkids(body);
const podO = buildPod(body);
const intG = buildInternals(body);

/* 轨迹线 */
const trailMat = new THREE.LineBasicMaterial({ color: 0x39d0d8, transparent: true, opacity: 0.65 });
const trailGeo = new THREE.BufferGeometry();
const trailPts = new Float32Array(3 * 900);
trailGeo.setAttribute('position', new THREE.BufferAttribute(trailPts, 3));
const trail = new THREE.Line(trailGeo, trailMat); scene.add(trail);

/* ---------------- 关键帧 ---------------- */
const K = {
  alt: [[0, 0], [3, 0], [14, 80], [17, 80], [21, 88], [28, 150], [38, 165], [45, 175], [52, 175], [58, 60], [62, 12], [63, 0], [70, 0]],
  spd: [[0, 0], [3, 0], [8, 14], [14, 16], [17, 16], [21, 21], [28, 28], [38, 28], [45, 23], [52, 23], [58, 20], [62, 15], [63, 3], [70, 0]],
  spin: [[0, 0], [3, 0], [4.2, 2.5], [14, 2.5], [15.2, 0.55], [16.6, 0.0], [70, 0]],
  fold: [[0, 92], [16.6, 92], [20.8, 0], [70, 0]],
  pitch: [[0, 90], [17, 90], [21, 12], [28, 2], [58, 2], [62, 10], [63, 16], [70, 16]],
  bank: [[0, 0], [38, 0], [40, 19.7], [52, 19.7], [54, 0], [70, 0]],
  rpm: [[0, 0], [3, 1200], [14, 5200], [17, 5200], [21, 4000], [28, 3050], [45, 2600], [58, 2200], [62, 900], [63, 0], [70, 0]],
  legs: [[0, 1], [15, 1], [17, 0], [70, 0]],
  podOut: [[0, 0], [64, 0], [67, 1], [70, 1]],
  crush: [[0, 0], [62.2, 0], [63.0, 0.55], [70, 0.55]],
};
function interp(fr, t) {
  if (t <= fr[0][0]) return fr[0][1];
  for (let i = 1; i < fr.length; i++) {
    const [t1, v1] = fr[i], [t0, v0] = fr[i - 1];
    if (t <= t1) {
      let u = (t - t0) / Math.max(1e-6, t1 - t0);
      u = u * u * (3 - 2 * u);                    // smoothstep
      return v0 + (v1 - v0) * u;
    }
  }
  return fr[fr.length - 1][1];
}
/* 前进距离（视觉单位）预积分 */
const S_FR = (() => {
  const out = []; let s = 0, dt = 0.05;
  for (let t = 0; t <= T_END + 1e-6; t += dt) {
    out.push([t, s]);
    s += interp(K.spd, t) * ALT_VIS * dt;
  }
  return out;
})();
const R_TURN_V = 150 * ALT_VIS;

const PHASES = [
  { t0: 0, t1: 3, n: '0 · 待发（尾坐竖立）', d: '机翼折叠、起落架展开；4 电机待转' },
  { t0: 3, t1: 14, n: '1 · 自旋垂直起飞', d: '机翼折叠自旋 2.5 Hz，爬升到 80 m（陀螺刚度抗阵风）' },
  { t0: 14, t1: 17, n: '2 · 80 m 消旋', d: '尾翼反舵 20°，0.7 s 内 2.5 Hz → 0（必须先消旋）' },
  { t0: 17, t1: 21, n: '3 · 展开机翼并锁定', d: '扭簧被动展开 → 锥形销锁入 FR-3，双微动开关确认' },
  { t0: 21, t1: 28, n: '4 · 过渡转平飞', d: '重力转弯 + 差动推力 + Q_ASSIST，预留 ≥60 m 掉高' },
  { t0: 28, t1: 38, n: '5 · 地形跟随巡航', d: '28 m/s @ 620 W，L/D 11.6' },
  { t0: 38, t1: 52, n: '6 · 盘旋高清成像', d: '23 m/s、坡度 19.7°、半径 150 m；GSD 6.5 cm @ 250 m' },
  { t0: 52, t1: 63, n: '7 · 软地迫降', d: '拉平 → 机头 EPP 压溃 → 腹滑橇滑行；软地是前提条件' },
  { t0: 63, t1: 70, n: '8 · 快拆取舱', d: '无工具 10 s 取出数据舱 → microSD 离线拷出' },
];

const STATE = { t: 0, playing: true, speed: 1, xray: false, explode: 0, labels: true, follow: true, cone: false, trail: true };

/* ---------------- 姿态求解 ---------------- */
function solve(t) {
  const alt = interp(K.alt, t), spd = interp(K.spd, t);
  const spin = interp(K.spin, t), fold = interp(K.fold, t);
  const pitch = interp(K.pitch, t), bank = interp(K.bank, t);
  const rpm = interp(K.rpm, t), legs = interp(K.legs, t);
  const podOut = interp(K.podOut, t), crush = interp(K.crush, t);
  const s = interp(S_FR, t);
  const hv = alt * ALT_VIS;

  let x = s, y = hv, z = 0, yaw = 0;
  const sTurn = interp(S_FR, 38);
  if (t >= 38 && t <= 52) {                     // 盘旋：圆心在航线右侧
    const u = (t - 38) / (52 - 38);
    const ang = Math.PI - u * Math.PI * 2.6;
    x = sTurn + R_TURN_V + Math.cos(ang) * R_TURN_V;
    z = Math.sin(ang) * R_TURN_V;
    yaw = -Math.atan2(-Math.sin(ang) * R_TURN_V, -R_TURN_V * Math.sin(ang) * 0 - 1) - u * Math.PI * 2.6 + Math.PI * 1.0;
    yaw = u * Math.PI * 2.6 + Math.PI * 0.5;    // 简化：航向跟圆周角
  } else if (t > 52) {                          // 返航 + 迫降：回到红布十字标
    const u = Math.min(1, (t - 52) / (63 - 52));
    const x0 = sTurn + R_TURN_V + Math.cos(Math.PI - Math.PI * 2.6) * R_TURN_V;
    const z0 = Math.sin(Math.PI - Math.PI * 2.6) * R_TURN_V;
    const tx = LZ_X + 3.0, tz = 0;
    x = x0 + (tx - x0) * u; z = z0 + (tz - z0) * u;
    yaw = Math.PI * 0.0;
  }
  return { alt, spd, spin, fold, pitch, bank, rpm, legs, podOut, crush, x, y, z, yaw };
}

/* ---------------- 每帧应用 ---------------- */
let spinAng = 0, propAng = 0;
function apply(t, dt) {
  const s = solve(t);
  posG.position.set(s.x, s.y, s.z);
  posG.rotation.y = s.yaw;
  pitchG.rotation.z = THREE.MathUtils.degToRad(s.pitch);      // 90° = 机头朝上（尾坐）
  spinAng += dt * s.spin * Math.PI * 2;
  spinG.rotation.x = spinAng - THREE.MathUtils.degToRad(s.bank);

  const f = THREE.MathUtils.degToRad(s.fold);
  wingO.hingeL.rotation.x = f;
  wingO.hingeR.rotation.x = f;

  propAng += dt * (s.rpm / 60) * Math.PI * 2 * 0.06;
  propO.props.forEach((p, i) => { p.rotation.x = (i % 2 === 0 ? 1 : -1) * propAng * 6; });

  legO.legs.forEach((lg) => { lg.scale.y = 0.02 + 0.98 * s.legs; lg.visible = s.legs > 0.03; });

  // 机头压溃（耗材变形）
  const c = s.crush;
  noseG.scale.x = 1 - 0.45 * c;
  noseG.position.x = 0.10 * c;
  noseG.traverse(o => { if (o.material && o.material.color) o.material.emissive && o.material.emissive.setRGB(0.25 * c, 0.05 * c, 0); });

  // 数据舱取出
  podO.shell.position.y = -L.fuse.r * 0.35 - s.podOut * 0.55;
  podO.cam.position.y = -L.fuse.r - 0.035 - s.podOut * 0.55;
  podO.cone.visible = STATE.cone || (t > 38 && t < 52);
  podO.cone.position.y = -L.fuse.r - 0.035 - 0.60;

  // 爆炸
  const e = STATE.explode;
  PARTS.forEach((m) => {
    const d = m.userData.expDir;
    if (d) m.position.copy(m.userData.basePos).addScaledVector(d, e);
  });

  return s;
}

/* ---------------- 标签 ---------------- */
const LABELS = [
  ['吸能机头（EPP 三层 · 空腔）', () => new THREE.Vector3(0.18, 0, 0)],
  ['快拆数据舱 STA 860~1080', () => new THREE.Vector3(0.97, -0.09, 0)],
  ['主翼 2.00 m（折叠机构）', () => new THREE.Vector3(0.90, 0.10, 0.85)],
  ['4 × 电机 + 24″ 桨', () => new THREE.Vector3(1.38, 0.16, 0)],
  ['尾翼 4 片（cant 4.5°）', () => new THREE.Vector3(1.47, 0.10, 0)],
  ['尾坐起落架（展开半径 0.55 m）', () => new THREE.Vector3(1.47, -0.40, 0)],
  ['腹滑橇（EPP，高出镜头 25 mm）', () => new THREE.Vector3(0.95, -0.16, 0.10)],
];
const labelBox = document.getElementById('labels');
const labelEls = LABELS.map(([txt]) => {
  const d = document.createElement('div'); d.className = 'lbl'; d.textContent = txt;
  labelBox.appendChild(d); return d;
});
const _v = new THREE.Vector3();
function updateLabels() {
  const show = STATE.labels;
  LABELS.forEach(([, fn], i) => {
    const el = labelEls[i];
    if (!show) { el.style.display = 'none'; return; }
    body.localToWorld(_v.copy(fn()));
    _v.project(camera);
    if (_v.z > 1) { el.style.display = 'none'; return; }
    el.style.display = 'block';
    el.style.left = ((_v.x * 0.5 + 0.5) * innerWidth) + 'px';
    el.style.top = ((-_v.y * 0.5 + 0.5) * innerHeight) + 'px';
  });
}

/* ---------------- 相机（手动轨道） ---------------- */
const cam = { theta: 1.05, phi: 1.15, dist: 4.6, tgt: new THREE.Vector3(0, 0.4, 0) };
let drag = null;
renderer.domElement.addEventListener('pointerdown', e => { drag = { x: e.clientX, y: e.clientY, moved: 0 }; });
addEventListener('pointerup', e => { if (drag && drag.moved < 5) pick(e); drag = null; });
addEventListener('pointermove', e => {
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  drag.moved += Math.abs(dx) + Math.abs(dy);
  cam.theta -= dx * 0.006; cam.phi = Math.max(0.08, Math.min(1.55, cam.phi - dy * 0.005));
  drag.x = e.clientX; drag.y = e.clientY;
});
renderer.domElement.addEventListener('wheel', e => {
  e.preventDefault();
  cam.dist = Math.max(0.6, Math.min(60, cam.dist * (1 + Math.sign(e.deltaY) * 0.09)));
}, { passive: false });
function updateCam(dt) {
  if (STATE.follow) {
    body.getWorldPosition(_v);
    cam.tgt.lerp(_v, Math.min(1, dt * 3.0));
  }
  const r = cam.dist;
  camera.position.set(
    cam.tgt.x + r * Math.sin(cam.phi) * Math.cos(cam.theta),
    cam.tgt.y + r * Math.cos(cam.phi),
    cam.tgt.z + r * Math.sin(cam.phi) * Math.sin(cam.theta));
  camera.lookAt(cam.tgt);
}

/* ---------------- 拾取 ---------------- */
const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
let hl = null;
function pick(e) {
  ptr.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(ptr, camera);
  const hit = ray.intersectObjects(body.children, true).filter(h => h.object.userData.part)[0];
  const box = document.getElementById('part-info');
  if (hl) { hl.material.emissiveIntensity = 0; hl = null; }
  if (!hit) { box.style.display = 'none'; return; }
  hl = hit.object;
  if (hl.material.emissive) { hl.material.emissive.setHex(0x2b6c78); hl.material.emissiveIntensity = 0.9; }
  const p = hl.userData.part;
  box.innerHTML = '<b>' + p.name + '</b><div>' + (p.desc || '') + '</div>';
  box.style.display = 'block';
}

/* ---------------- UI ---------------- */
const ui = document.getElementById('ui');
const ro = {};
function buildUI() {
  ui.innerHTML = `
  <div class="hd">
    <div class="tt">HDRS-1「迅鸢」· 构型与任务动画</div>
    <div class="sb">谨以此祭奠 2026 年吉隆特大泥石流罹难者 · AI 辅助设计，未经实飞验证</div>
  </div>
  <div class="grp" id="phases"></div>
  <div class="grp">
    <div class="lbl2">读数</div>
    <div class="rd"><span>T+</span><b id="ro-t">0.0 s</b></div>
    <div class="rd"><span>阶段</span><b id="ro-ph">—</b></div>
    <div class="rd"><span>高度</span><b id="ro-alt">0 m</b></div>
    <div class="rd"><span>空速</span><b id="ro-spd">0 m/s</b></div>
    <div class="rd"><span>自旋</span><b id="ro-spin">0.00 Hz</b></div>
    <div class="rd"><span>桨转速</span><b id="ro-rpm">0 rpm</b></div>
    <div class="rd"><span>机翼折叠</span><b id="ro-fold">92°</b></div>
    <div class="rd"><span>姿态</span><b id="ro-att">竖直 90°</b></div>
  </div>
  <div class="grp">
    <div class="lbl2">显示</div>
    <label><input type="checkbox" id="sw-xray"> 剖切 / 透视内部</label>
    <label><input type="checkbox" id="sw-labels" checked> 部件标签</label>
    <label><input type="checkbox" id="sw-follow" checked> 相机跟随</label>
    <label><input type="checkbox" id="sw-cone"> 相机视锥</label>
    <label><input type="checkbox" id="sw-trail" checked> 航迹</label>
    <label>爆炸 <input type="range" id="sw-exp" min="0" max="100" value="0"></label>
  </div>
  <div class="grp">
    <div class="lbl2">视角</div>
    <div class="btns">
      <button data-v="0">全景</button><button data-v="1">机头</button>
      <button data-v="2">折叠机构</button><button data-v="3">尾部动力</button>
      <button data-v="4">数据舱</button><button data-v="5">迫降姿态</button>
    </div>
  </div>
  <div class="grp note">
    螺旋桨网格复用自 <b>eanswer/LearningToFly</b>（MIT 许可），按 24″ 缩放。<br>
    机身 / 折叠翼 / 尾坐起落架 / 数据舱为本项目自建。
  </div>`;

  const ph = document.getElementById('phases');
  PHASES.forEach((p, i) => {
    const b = document.createElement('button');
    b.className = 'ph'; b.dataset.i = i;
    b.innerHTML = '<b>' + p.n + '</b><i>' + p.d + '</i>';
    b.onclick = () => { STATE.t = p.t0 + 0.01; STATE.playing = true; syncBtn(); };
    ph.appendChild(b);
  });
  ['t', 'ph', 'alt', 'spd', 'spin', 'rpm', 'fold', 'att'].forEach(k => ro[k] = document.getElementById('ro-' + k));

  document.getElementById('sw-xray').onchange = e => setXray(e.target.checked);
  document.getElementById('sw-labels').onchange = e => STATE.labels = e.target.checked;
  document.getElementById('sw-follow').onchange = e => STATE.follow = e.target.checked;
  document.getElementById('sw-cone').onchange = e => STATE.cone = e.target.checked;
  document.getElementById('sw-trail').onchange = e => { STATE.trail = e.target.checked; trail.visible = e.target.checked; };
  document.getElementById('sw-exp').oninput = e => setExplode(e.target.value / 100);
  document.querySelectorAll('.btns button').forEach(b => b.onclick = () => setView(+b.dataset.v));
}
function syncBtn() {
  document.querySelectorAll('.ph').forEach((b, i) => {
    b.classList.toggle('on', STATE.t >= PHASES[i].t0 && STATE.t < PHASES[i].t1);
  });
}
function setXray(on) {
  STATE.xray = on;
  PARTS.forEach(m => {
    if (!m.userData.solid) m.userData.solid = m.material;
    m.material = on ? (m.userData.xray || (m.userData.xray = xrayOf(m.userData.solid))) : m.userData.solid;
  });
  boomM.visible = on; intG.visible = on;
  if (!on) { boomM.visible = false; intG.visible = false; }
}
function setExplode(v) {
  STATE.explode = v;
  PARTS.forEach(m => {
    if (!m.userData.basePos) m.userData.basePos = m.position.clone();
    if (!m.userData.expDir) {
      const c = new THREE.Vector3();
      m.getWorldPosition(c); body.worldToLocal(c);
      m.userData.expDir = new THREE.Vector3(0, c.y >= 0 ? 1 : -1, c.z >= 0 ? 1 : -1).normalize()
        .multiplyScalar(0.10 + Math.random() * 0.10);
    }
    m.position.copy(m.userData.basePos).addScaledVector(m.userData.expDir, v);
  });
}
const VIEWS = [
  { d: 4.6, th: 1.05, ph: 1.15 }, { d: 1.5, th: 1.9, ph: 1.25 },
  { d: 1.8, th: 0.7, ph: 0.9 }, { d: 1.6, th: 1.4, ph: 1.2 },
  { d: 1.2, th: 0.3, ph: 1.5 }, { d: 2.6, th: 2.4, ph: 1.35 },
];
function setView(i) { const v = VIEWS[i]; cam.dist = v.d; cam.theta = v.th; cam.phi = v.ph; STATE.follow = false; document.getElementById('sw-follow').checked = false; }

/* 底部控制条 */
const bar = document.getElementById('bar');
bar.innerHTML = `
  <button id="b-play">⏸ 暂停</button>
  <button id="b-reset">⟲ 重播</button>
  <input type="range" id="s-t" min="0" max="${T_END}" step="0.05" value="0" style="flex:1">
  <span class="sp">速度</span>
  <select id="s-spd"><option value="0.5">0.5×</option><option value="1" selected>1×</option><option value="2">2×</option><option value="4">4×</option></select>`;
document.getElementById('b-play').onclick = e => { STATE.playing = !STATE.playing; e.target.textContent = STATE.playing ? '⏸ 暂停' : '▶ 播放'; };
document.getElementById('b-reset').onclick = () => { STATE.t = 0; STATE.playing = true; document.getElementById('b-play').textContent = '⏸ 暂停'; };
const sT = document.getElementById('s-t');
sT.oninput = e => { STATE.t = +e.target.value; };
document.getElementById('s-spd').onchange = e => STATE.speed = +e.target.value;

/* ---------------- 主循环 ---------------- */
let last = performance.now(), ti = 0;
function loop(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  if (STATE.playing) {
    STATE.t += dt * STATE.speed;
    if (STATE.t > T_END) STATE.t = 0;
    sT.value = STATE.t;
  }
  const s = apply(STATE.t, dt);

  // 航迹
  if (STATE.trail) {
    const i = ti % 900;
    body.getWorldPosition(_v);
    trailPts[i * 3] = _v.x; trailPts[i * 3 + 1] = Math.max(0.02, _v.y); trailPts[i * 3 + 2] = _v.z;
    if (STATE.t < 0.1) { for (let k = 0; k < 2700; k++) trailPts[k] = 0; ti = 0; }
    trailGeo.attributes.position.needsUpdate = true;
    trailGeo.setDrawRange(0, Math.min(900, ti + 1));
    ti++;
  }

  ro.t.textContent = STATE.t.toFixed(1) + ' s';
  const cur = PHASES.find(p => STATE.t >= p.t0 && STATE.t < p.t1) || PHASES[PHASES.length - 1];
  ro.ph.textContent = cur.n.split('·')[1] || cur.n;
  ro.alt.textContent = Math.round(s.alt) + ' m';
  ro.spd.textContent = s.spd.toFixed(1) + ' m/s';
  ro.spin.textContent = s.spin.toFixed(2) + ' Hz';
  ro.rpm.textContent = Math.round(s.rpm) + ' rpm';
  ro.fold.textContent = s.fold.toFixed(0) + '°';
  ro.att.textContent = s.pitch > 60 ? '竖直 ' + s.pitch.toFixed(0) + '°' : '平飞 ' + s.pitch.toFixed(0) + '°';
  syncBtn();

  updateCam(dt); updateLabels();
  renderer.render(scene, camera);
  requestAnimationFrame(loop);
}
buildUI();
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
requestAnimationFrame(loop);

window.API = { THREE, scene, camera, renderer, STATE, PARTS, body, setXray, setExplode, setView };
