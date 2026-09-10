/* HDRS-1「迅鸢」— 核心建模（独有件全部参数化自建，螺旋桨复用 MIT 开源网格） */

const L = {
  // 站位：STA(mm) -> m，X 轴沿机身轴，机头 STA0 在 x=0
  len: 1.55,
  nose: { len: 0.40, r: 0.120, layers: [0.13, 0.13, 0.14] },   // A 区：三层变密度 EPP
  fuse: { r: 0.070, x0: 0.40, x1: 1.25 },                       // B/C 段 ⌀140
  tailCone: { x0: 1.25, x1: 1.55, r1: 0.045 },                  // G 段
  boom: { r: 0.0275, x0: 0.40, x1: 1.40 },                      // 主承力杆 ⌀55
  wing: {
    span: 2.00, cr: 0.39, ct: 0.23, xLE: 0.821, yOff: 0.060,
    dihedral: 3 * Math.PI / 180, tc: 0.09,
    hingeX: 0.900, fold: 92 * Math.PI / 180,
    tipBlock: { len: 0.30, th: 0.025 },
  },
  tail: { x: 1.44, span: 0.17, chord: 0.084, cant: 4.5 * Math.PI / 180 },
  motor: { x: 1.32, arm: 0.155, r: 0.028, len: 0.055 },
  prop: { x: 1.42, d: 0.6096 },
  legs: { x: 1.47, radius: 0.55, n: 4 },
  skid: { x0: 0.70, x1: 1.20, w: 0.060, h: 0.120 },
  pod: { x0: 0.86, x1: 1.08, r: 0.062 },                        // D 区快拆数据舱
  batt: { x0: 0.52, x1: 0.90, xcg: 0.60, r: 0.050 },
  avionics: { x0: 1.10, x1: 1.25, r: 0.052 },
};

const PG = window.PROP_GEOM || null;

const MAT = {
  carbon: () => new THREE.MeshStandardMaterial({ color: 0x30363d, roughness: 0.55, metalness: 0.35 }),
  carbonDark: () => new THREE.MeshStandardMaterial({ color: 0x21262d, roughness: 0.6, metalness: 0.3 }),
  skin: () => new THREE.MeshStandardMaterial({ color: 0x4a525c, roughness: 0.45, metalness: 0.3 }),
  epp1: () => new THREE.MeshStandardMaterial({ color: 0xe9e4d8, roughness: 0.95, metalness: 0.0 }),
  epp2: () => new THREE.MeshStandardMaterial({ color: 0xd6cfbe, roughness: 0.95, metalness: 0.0 }),
  epp3: () => new THREE.MeshStandardMaterial({ color: 0xbfb7a4, roughness: 0.95, metalness: 0.0 }),
  wing: () => new THREE.MeshStandardMaterial({ color: 0x9aa4b0, roughness: 0.5, metalness: 0.15 }),
  wingX: () => new THREE.MeshStandardMaterial({ color: 0x7c8694, roughness: 0.5, metalness: 0.15 }),
  metal: () => new THREE.MeshStandardMaterial({ color: 0x6b7280, roughness: 0.35, metalness: 0.85 }),
  prop: () => new THREE.MeshStandardMaterial({ color: 0x16191d, roughness: 0.6, metalness: 0.2, transparent: true, opacity: 0.95 }),
  pod: () => new THREE.MeshStandardMaterial({ color: 0x22d3ee, roughness: 0.35, metalness: 0.3, emissive: 0x0b3b45, emissiveIntensity: 0.4 }),
  batt: () => new THREE.MeshStandardMaterial({ color: 0xf5c542, roughness: 0.5, metalness: 0.2 }),
  fcu: () => new THREE.MeshStandardMaterial({ color: 0x4ade80, roughness: 0.5, metalness: 0.2 }),
  lens: () => new THREE.MeshStandardMaterial({ color: 0x0b0f14, roughness: 0.1, metalness: 0.9, emissive: 0x0a2a33, emissiveIntensity: 0.6 }),
  alu: () => new THREE.MeshStandardMaterial({ color: 0xb8bec7, roughness: 0.3, metalness: 0.9 }),
};

function xrayOf(m) {
  return new THREE.MeshStandardMaterial({
    color: m.color.getHex(), roughness: 0.9, metalness: 0.0,
    transparent: true, opacity: 0.18, depthWrite: false, side: THREE.DoubleSide,
  });
}

/* ---------- 通用：把 mesh 登记进 PARTS（用于标签 / 高亮 / 爆炸） ---------- */
const PARTS = [];
function reg(mesh, name, desc, opt = {}) {
  mesh.userData.part = { name, desc, ...opt };
  PARTS.push(mesh);
  return mesh;
}

/* ---------- A 区：吸能机头（tangent ogive，三层变密度 EPP，内部空腔） ---------- */
function buildNose(parent) {
  const g = new THREE.Group();
  const y = 0, z = 0;
  const seg = 26;
  // ogive 母线：从头尖 (x=0, r=0) 到根 (x=noseLen, r=noseR)
  const prof = [];
  for (let i = 0; i <= seg; i++) {
    const t = i / seg;                       // 0=尖 1=根
    const x = t * L.nose.len;
    // tangent ogive 近似：r = R * sqrt(t*(2-t)) 平滑收尖
    const r = L.nose.r * Math.sqrt(Math.max(0, t * (2 - t) * 0.92 + 0.08 * t));
    prof.push(new THREE.Vector2(Math.max(0.0001, r), x));
  }
  // 三层：按轴向厚度切分
  let cum = 0;
  L.nose.layers.forEach((th, li) => {
    const a = cum, b = cum + th;
    cum = b;
    const sub = prof.filter(p => p.y >= a - 1e-6 && p.y <= b + 1e-6);
    if (sub.length < 2) return;
    const pts = [new THREE.Vector2(0.0001, a), ...sub, new THREE.Vector2(L.nose.r * Math.sqrt(1), b)];
    const geo = new THREE.LatheGeometry(pts, 40);
    geo.rotateZ(-Math.PI / 2);                 // Lathe 默认绕 Y -> 绕 X
    const m = new THREE.Mesh(geo, [MAT.epp1(), MAT.epp2(), MAT.epp3()][li]);
    m.castShadow = true;
    reg(m, li === 0 ? 'EPP 25 kg/m³' : li === 1 ? 'EPP 45 kg/m³' : 'EPP 70 kg/m³',
      li === 0 ? '撞击最先压溃的一段（耗材）' : li === 1 ? '中段吸能' : '根部（靠近隔框 FR-1），密度最高');
    g.add(m);
  });
  // 铝止挡环 ⌀180（限制泡沫过压）
  const ringGeo = new THREE.TorusGeometry(0.090, 0.006, 8, 32);
  const ring = new THREE.Mesh(ringGeo, MAT.alu());
  ring.rotation.y = Math.PI / 2;
  ring.position.x = 0.30;
  reg(ring, '铝止挡环 ⌀180', '限制泡沫压溃行程，防止过压后直接顶到 FR-1');
  g.add(ring);
  parent.add(g);
  return g;
}

/* ---------- B/C 段机身 + 尾锥 ---------- */
function buildFuselage(parent) {
  const g = new THREE.Group();
  const len = L.fuse.x1 - L.fuse.x0;
  const body = new THREE.Mesh(
    new THREE.CylinderGeometry(L.fuse.r, L.fuse.r, len, 36, 1, true), MAT.skin());
  body.rotation.z = Math.PI / 2;
  body.position.x = L.fuse.x0 + len / 2;
  reg(body, '机身 B/C 段 ⌀140', '3K 碳纤管，直接作为承力外壳');
  g.add(body);

  const cone = new THREE.Mesh(
    new THREE.CylinderGeometry(L.fuse.r, L.tailCone.r1, L.tailCone.x1 - L.tailCone.x0, 36, 1, true), MAT.skin());
  cone.rotation.z = Math.PI / 2;
  cone.position.x = (L.tailCone.x0 + L.tailCone.x1) / 2;
  reg(cone, '尾锥 G 段', '3D 打印 PA-CF 2.5 mm，含电机座与尾翼座');
  g.add(cone);

  // 二级吸能锥形过渡筒 STA 380~520（建议件）
  const trans = new THREE.Mesh(
    new THREE.CylinderGeometry(L.nose.r, L.fuse.r, 0.14, 32, 1, true), MAT.alu());
  trans.rotation.z = Math.PI / 2;
  trans.position.x = 0.45;
  trans.material = new THREE.MeshStandardMaterial({ color: 0xd9b26a, roughness: 0.5, metalness: 0.6, transparent: true, opacity: 0.5 });
  reg(trans, '二级吸能过渡筒', '铝蜂窝/碳纤锥筒，STA 380~520，屈曲吸能 ≈300 J（建议实施）');
  g.add(trans);
  parent.add(g);
  return g;
}

/* ---------- 主承力杆 ⌀55（仅在剖切/爆炸时显示） ---------- */
function buildBoom(parent) {
  const m = new THREE.Mesh(
    new THREE.CylinderGeometry(L.boom.r, L.boom.r, L.boom.x1 - L.boom.x0, 20), MAT.carbonDark());
  m.rotation.z = Math.PI / 2;
  m.position.x = (L.boom.x0 + L.boom.x1) / 2;
  reg(m, '主承力杆 ⌀55×2.5', '碳纤缠绕管 T700，STA 400~1400，破坏弯矩 ≥900 N·m');
  m.visible = false;
  parent.add(m);
  return m;
}

/* ---------- 翼型 + 机翼（自建，独有件） ---------- */
function naca(t, xi) {
  // 对称翼型半厚度
  return 5 * t * (0.2969 * Math.sqrt(xi) - 0.1260 * xi - 0.3516 * xi * xi
    + 0.2843 * xi ** 3 - 0.1015 * xi ** 4);
}
function buildWingHalf(side) {   // side: +1 = 右翼(沿 +Z)，-1 = 左翼
  const W = L.wing;
  const N = 14, M = 20;
  const half = W.span / 2;
  const pos = [], idx = [];
  for (let i = 0; i <= N; i++) {
    const s = i / N;                       // 0 根 -> 1 尖
    const y = s * half;
    const chord = W.cr + (W.ct - W.cr) * s;
    const yOff = y * Math.tan(W.dihedral);
    for (let j = 0; j <= M; j++) {
      const xi = j / M;
      const th = naca(W.tc, xi) * chord;
      const x = W.xLE + xi * chord;
      const yy = yOff + th;
      pos.push(x, yy, side * y);
    }
    for (let j = 0; j <= M; j++) {
      const xi = j / M;
      const th = -naca(W.tc, xi) * chord;
      const x = W.xLE + xi * chord;
      const yy = yOff + th;
      pos.push(x, yy, side * y);
    }
  }
  const row = (M + 1) * 2;
  // 上表面（j=0..M）与下表面（j=M+1..2M+1）分别放样，避免跨面连接
  for (let i = 0; i < N; i++) {
    for (let j = 0; j < M; j++) {
      const a = i * row + j, b = a + 1, c = (i + 1) * row + j, d = c + 1;
      idx.push(a, b, c, b, d, c);                    // 上表面
    }
    for (let j = 0; j < M; j++) {
      const a = i * row + (M + 1) + j, b = a + 1, c = (i + 1) * row + (M + 1) + j, d = c + 1;
      idx.push(a, c, b, b, c, d);                    // 下表面（反向绕序）
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setIndex(idx);
  geo.computeVertexNormals();
  const m = new THREE.Mesh(geo, MAT.wing());
  m.castShadow = true;
  return m;
}
function buildWing(parent) {
  const W = L.wing;
  const root = new THREE.Group();
  root.position.set(0, 0, 0);
  const hingeL = new THREE.Group(), hingeR = new THREE.Group();
  hingeL.position.set(W.hingeX, W.yOff, 0);
  hingeR.position.set(W.hingeX, W.yOff, 0);
  // 翼面原点移到铰链
  const wl = buildWingHalf(-1), wr = buildWingHalf(1);
  wl.position.set(-W.hingeX, -W.yOff, 0);
  wr.position.set(-W.hingeX, -W.yOff, 0);
  hingeL.add(wl); hingeR.add(wr);
  reg(wl, '左翼（含折叠机构）', `展长半 1.00 m，根弦 0.39 / 梢弦 0.23，上反 3°，绕 STA ${(W.hingeX * 1000) | 0} 轴后折 92°`);
  reg(wr, '右翼（含折叠机构）', `上单翼，安装线高于机身轴 60 mm；全展长升降副翼，弦向 25%`);

  // 翼尖 EPP 滑块
  [[-1, hingeL], [1, hingeR]].forEach(([sd, hg]) => {
    const blk = new THREE.Mesh(
      new THREE.BoxGeometry(W.tipBlock.len, W.tipBlock.th, 0.10), MAT.epp2());
    const yTip = (W.span / 2) * Math.tan(W.dihedral);
    blk.position.set(-W.hingeX + W.xLE + 0.16, -W.yOff + yTip, sd * (W.span / 2 - 0.10));
    reg(blk, '翼尖 EPP 滑块', '长 300 mm 厚 25 mm，迫降擦地磨损件，可更换');
    hg.add(blk);
  });

  // 转轴座 + 锁销（示意）
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, 0.10, 16), MAT.metal());
  hub.rotation.z = Math.PI / 2;
  hub.position.set(W.hingeX, W.yOff + 0.02, 0);
  reg(hub, '折叠转轴座', '抱夹主梁根部，不打断纤维；钢套 + 铜衬套');
  root.add(hub);

  root.add(hingeL, hingeR);
  parent.add(root);
  return { root, hingeL, hingeR };
}

/* ---------- 尾翼 4 片 X 型（cant 4.5°） ---------- */
function buildTail(parent) {
  const g = new THREE.Group();
  const T = L.tail;
  for (let i = 0; i < 4; i++) {
    const a = Math.PI / 4 + i * Math.PI / 2;
    const fin = new THREE.Group();
    const blade = new THREE.Mesh(new THREE.BoxGeometry(T.chord, 0.006, T.span), MAT.wing());
    blade.position.set(T.x + T.chord / 2, Math.sin(a) * (T.span / 2 + 0.03), Math.cos(a) * (T.span / 2 + 0.03));
    blade.rotation.x = a;
    // cant：绕展向轴偏转 4.5°
    blade.rotateOnAxis(new THREE.Vector3(1, 0, 0), 0);
    const piv = new THREE.Group();
    piv.position.set(T.x, 0, 0);
    piv.rotation.x = a;
    const b2 = new THREE.Mesh(new THREE.BoxGeometry(T.chord, 0.006, T.span), MAT.wing());
    b2.position.set(T.chord / 2, T.span / 2 + 0.045, 0);
    b2.rotation.y = -T.cant;                 // cant 角
    piv.add(b2);
    reg(b2, '尾翼 #' + (i + 1), '单翼面积 0.0143 m²，cant 4.5° 产生自旋力矩；消旋时反舵 20°');
    g.add(piv);
  }
  parent.add(g);
  return g;
}

/* ---------- 螺旋桨：复用 MIT 开源网格（eanswer/LearningToFly，缩放至 24"） ---------- */
function propGeometry() {
  if (!PG) {
    // 回退：程序化双叶桨
    const g = new THREE.BoxGeometry(0.02, 0.05, L.prop.d);
    return g;
  }
  const pos = new Float32Array(PG.v.length * 3);
  PG.v.forEach((p, i) => { pos[i * 3] = p[0]; pos[i * 3 + 1] = p[1]; pos[i * 3 + 2] = p[2]; });
  const idx = [];
  for (const f of PG.f) idx.push(f[0] - 1, f[1] - 1, f[2] - 1);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  g.rotateY(Math.PI / 2);      // OBJ 旋转轴 z -> 机体 X
  return g;
}
function buildPropulsion(parent) {
  const g = new THREE.Group();
  const propGeo = propGeometry();
  const props = [];
  for (let i = 0; i < 4; i++) {
    const a = Math.PI / 4 + i * Math.PI / 2;
    const arm = new THREE.Group();
    // 电机座支臂
    const armMesh = new THREE.Mesh(
      new THREE.CylinderGeometry(0.012, 0.012, L.motor.arm, 12), MAT.carbonDark());
    armMesh.rotation.z = Math.PI / 2;
    armMesh.rotation.y = -a + Math.PI / 2;
    armMesh.position.set(L.motor.x, Math.sin(a) * L.motor.arm / 2, Math.cos(a) * L.motor.arm / 2);
    arm.add(armMesh);
    const my = Math.sin(a) * L.motor.arm, mz = Math.cos(a) * L.motor.arm;
    // 电机
    const mot = new THREE.Mesh(
      new THREE.CylinderGeometry(L.motor.r, L.motor.r, L.motor.len, 20), MAT.metal());
    mot.rotation.z = Math.PI / 2;
    mot.position.set(L.motor.x, my, mz);
    reg(mot, '电机 #' + (i + 1), '4 × 尾部电机，X 型布置，STA 1320；PA-CF 座 + 4 mm 铝背板');
    arm.add(mot);
    // 桨
    const hub = new THREE.Group();
    hub.position.set(L.prop.x, my, mz);
    const p = new THREE.Mesh(propGeo, MAT.prop());
    p.userData.spin = (i % 2 === 0) ? 1 : -1;
    reg(p, '螺旋桨 24″ #' + (i + 1), PG
      ? '网格复用自 eanswer/LearningToFly（MIT），按 24″ 缩放；为垂起优化，巡航时偏离设计点'
      : '24″ 双叶桨（程序化回退）');
    hub.add(p);
    props.push(p);
    arm.add(hub);
    g.add(arm);
  }
  parent.add(g);
  return { group: g, props };
}

/* ---------- 尾坐起落架：4 条可折叠支腿（独有件，展开半径 0.55 m） ---------- */
function buildLegs(parent) {
  const g = new THREE.Group();
  const legs = [];
  for (let i = 0; i < L.legs.n; i++) {
    const a = Math.PI / 4 + i * Math.PI / 2;
    const piv = new THREE.Group();
    piv.position.set(L.legs.x, 0, 0);
    piv.rotation.x = a;
    const strut = new THREE.Mesh(
      new THREE.CylinderGeometry(0.010, 0.008, L.legs.radius, 10), MAT.carbonDark());
    strut.position.set(0, L.legs.radius / 2, 0);
    strut.rotation.z = -Math.PI / 2 + 0.0;
    strut.rotation.x = Math.PI / 2;
    // 让支腿从机身径向张开
    const holder = new THREE.Group();
    const s2 = new THREE.Mesh(new THREE.CylinderGeometry(0.010, 0.008, L.legs.radius, 10), MAT.carbonDark());
    s2.position.set(0, L.legs.radius / 2, 0);
    const foot = new THREE.Mesh(new THREE.SphereGeometry(0.028, 12, 10), MAT.epp1());
    foot.position.set(0, L.legs.radius, 0);
    holder.add(s2); holder.add(foot);
    holder.rotation.z = -0.0;
    piv.add(holder);
    reg(s2, '尾坐支腿 #' + (i + 1), '碳纤支腿，展开半径 0.55 m，抗 6 m/s 侧风；末端 EPP 脚垫');
    legs.push(piv);
    g.add(piv);
  }
  parent.add(g);
  return { group: g, legs };
}

/* ---------- 腹滑橇（EPP，比镜头突出 25 mm） ---------- */
function buildSkids(parent) {
  const g = new THREE.Group();
  const S = L.skid;
  [-1, 1].forEach(sd => {
    const m = new THREE.Mesh(
      new THREE.BoxGeometry(S.x1 - S.x0, S.h, S.w), MAT.epp2());
    m.position.set((S.x0 + S.x1) / 2, -L.fuse.r - S.h / 2 + 0.02, sd * 0.055);
    reg(m, '腹滑橇（EPP）', '长 500 mm，截面 60×120，STA 700~1200；比相机镜头突出 25 mm，兼二级吸能');
    g.add(m);
  });
  parent.add(g);
  return g;
}

/* ---------- D 区快拆数据舱（独有件，可取出） ---------- */
function buildPod(parent) {
  const g = new THREE.Group();
  const P = L.pod;
  const shell = new THREE.Mesh(
    new THREE.BoxGeometry(P.x1 - P.x0, 0.115, 0.115), MAT.pod());
  shell.position.set((P.x0 + P.x1) / 2, -L.fuse.r * 0.35, 0);
  reg(shell, '快拆数据舱', 'STA 860~1080：12 MP 下视相机 + 视觉 MCU + microSD；2 卡扣 + 防脱销，无工具 10 s 取出');
  g.add(shell);
  // 相机 + 视锥
  const cam = new THREE.Mesh(new THREE.CylinderGeometry(0.020, 0.024, 0.045, 16), MAT.lens());
  cam.rotation.x = Math.PI;
  cam.position.set(P.x0 + 0.06, -L.fuse.r - 0.035, 0);
  reg(cam, '下视相机 12 MP', '6 mm 镜头，GSD 6.5 cm @ 250 m AGL；窗口凹入 6 mm，由腹滑橇保护');
  g.add(cam);
  const cone = new THREE.Mesh(
    new THREE.ConeGeometry(0.42, 1.2, 24, 1, true),
    new THREE.MeshBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.10, side: THREE.DoubleSide, depthWrite: false }));
  cone.position.set(P.x0 + 0.06, -L.fuse.r - 0.035 - 0.60, 0);
  cone.rotation.x = Math.PI;
  cone.visible = false;
  g.add(cone);
  parent.add(g);
  return { group: g, shell, cam, cone };
}

/* ---------- 内部件（剖切时显示）：电池 / 航电 / 主杆 ---------- */
function buildInternals(parent) {
  const g = new THREE.Group();
  const B = L.batt;
  const batt = new THREE.Mesh(
    new THREE.CylinderGeometry(B.r, B.r, B.x1 - B.x0, 24), MAT.batt());
  batt.rotation.z = Math.PI / 2;
  batt.position.set(B.xcg, 0, 0);
  reg(batt, '电池 12S4P（778 Wh）', 'STA 520~900 无级可调；初飞 STA 600（静稳定裕度 +12%），AutoTune 后后移减阻');
  g.add(batt);
  const A = L.avionics;
  const fcu = new THREE.Mesh(
    new THREE.BoxGeometry(A.x1 - A.x0, 0.070, 0.090), MAT.fcu());
  fcu.position.set((A.x0 + A.x1) / 2, 0, 0);
  reg(fcu, '航电舱 E 区', '飞控 / IMU / GNSS / 数传 / 配电，STA 1100~1250');
  g.add(fcu);
  g.visible = false;
  parent.add(g);
  return g;
}
