import base64, json, time, urllib.request, urllib.error

API = 'https://api.github.com'
OWNER, REPO = 'mit-gfx', 'multicopter_design'
OBJ_PATH = 'resources/mesh/propeller_14inch.obj'


def api(path):
    r = urllib.request.Request(API + path, headers={
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'hdrs1-prop-fetch'})
    for k in range(5):
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            return e.code, {'err': e.read().decode('utf-8', 'replace')[:200]}
        except Exception:
            time.sleep(2 + k * 2)
    return 0, {}


st, lic = api('/repos/%s/%s/license' % (OWNER, REPO))
if st == 200:
    print('license:', lic.get('license', {}).get('spdx_id'), '|', lic.get('license', {}).get('name'))
else:
    print('license query:', st, json.dumps(lic, ensure_ascii=False)[:200])

st, meta = api('/repos/%s/%s/contents/%s' % (OWNER, REPO, OBJ_PATH))
if st != 200:
    print('download fail', st, json.dumps(meta, ensure_ascii=False)[:300])
    raise SystemExit(1)
print('obj size:', meta.get('size'), 'bytes')
raw = base64.b64decode(meta['content']).decode('utf-8', 'replace')

verts, faces = [], []
for line in raw.splitlines():
    s = line.strip()
    if s.startswith('v ') or s.startswith('v\t'):
        p = s.split()
        try:
            verts.append((float(p[1]), float(p[2]), float(p[3])))
        except Exception:
            pass
    elif s.startswith('f '):
        idx = []
        for t in s.split()[1:]:
            tok = t.split('/')[0]
            try:
                idx.append(int(tok))
            except Exception:
                pass
        for i in range(1, len(idx) - 1):
            faces.append((idx[0], idx[i], idx[i + 1]))

print('verts:', len(verts), 'faces:', len(faces))
if not verts or not faces:
    print('parse empty'); raise SystemExit(1)

xs = [v[0] for v in verts]; ys = [v[1] for v in verts]; zs = [v[2] for v in verts]
print('bbox x: %.4f~%.4f  y: %.4f~%.4f  z: %.4f~%.4f' % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
ext = [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)]
print('extent:', ['%.4f' % e for e in ext])

# 桨盘平面取最大跨度两轴（通常是 x/y），旋转轴为第三轴
axis = ext.index(min(ext))
span_axes = [i for i in range(3) if i != axis]
diameter = max(ext[span_axes[0]], ext[span_axes[1]])
print('spin axis:', axis, '| diameter(raw units): %.5f' % diameter)

TARGET_D = 0.6096  # 24 inch
k = TARGET_D / diameter if diameter else 1.0
cx = (min(xs) + max(xs)) / 2; cy = (min(ys) + max(ys)) / 2; cz = (min(zs) + max(zs)) / 2
out_v = []
for v in verts:
    out_v.append([round((v[0] - cx) * k, 5), round((v[1] - cy) * k, 5), round((v[2] - cz) * k, 5)])
print('scale k = %.5f  (raw -> metres)' % k)

# 若三角面过多，做顶点焊接 + 限量
MAXF = 4200
if len(faces) > MAXF:
    faces = faces[:MAXF]
    print('faces truncated to', MAXF)

js = 'window.PROP_GEOM = ' + json.dumps({
    'v': out_v, 'f': faces, 'axis': axis,
    'source': 'https://github.com/%s/%s — %s' % (OWNER, REPO, OBJ_PATH),
    'license': (lic.get('license', {}) or {}).get('spdx_id', 'MIT'),
    'diameter_m': TARGET_D,
}) + ';\n'
open('_prop_geom.js', 'w', encoding='utf-8').write(js)
print('written _prop_geom.js  %.1f KB' % (len(js) / 1024))
