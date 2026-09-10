import base64, json, time, urllib.request, urllib.error

API = 'https://api.github.com'
OWNER, REPO = 'eanswer', 'LearningToFly'
OBJ_PATH = 'SimulationUI/data/config/propeller.obj'
TARGET_D = 0.6096  # 24 inch


def api(path):
    r = urllib.request.Request(API + path, headers={
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'hdrs1-prop-fetch'})
    for k in range(5):
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            return e.code, {}
        except Exception:
            time.sleep(2 + k * 2)
    return 0, {}


st, lic = api('/repos/%s/%s/license' % (OWNER, REPO))
lic_id = (lic.get('license') or {}).get('spdx_id', 'MIT') if st == 200 else 'MIT'

st, meta = api('/repos/%s/%s/contents/%s' % (OWNER, REPO, OBJ_PATH))
raw = base64.b64decode(meta['content']).decode('utf-8', 'replace')

verts, faces = [], []
for s in raw.splitlines():
    s = s.strip()
    if s.startswith('v '):
        p = s.split()
        try:
            verts.append((float(p[1]), float(p[2]), float(p[3])))
        except Exception:
            pass
    elif s.startswith('f '):
        idx = []
        for t in s.split()[1:]:
            try:
                idx.append(int(t.split('/')[0]))
            except Exception:
                pass
        for i in range(1, len(idx) - 1):
            faces.append((idx[0], idx[i], idx[i + 1]))

xs = [v[0] for v in verts]; ys = [v[1] for v in verts]; zs = [v[2] for v in verts]
ext = [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)]
axis = ext.index(min(ext))
diameter = max(ext[i] for i in range(3) if i != axis)
k = TARGET_D / diameter
cx = (min(xs) + max(xs)) / 2; cy = (min(ys) + max(ys)) / 2; cz = (min(zs) + max(zs)) / 2

out_v = [[round((v[0] - cx) * k, 5), round((v[1] - cy) * k, 5), round((v[2] - cz) * k, 5)] for v in verts]

js = 'window.PROP_GEOM = ' + json.dumps({
    'v': out_v,
    'f': faces,
    'spinAxis': axis,
    'diameter_m': TARGET_D,
    'source': 'https://github.com/%s/%s — %s' % (OWNER, REPO, OBJ_PATH),
    'license': lic_id,
}, separators=(',', ':')) + ';\n'

open('_prop_geom.js', 'w', encoding='utf-8').write(js)
print('license     :', lic_id)
print('verts/faces :', len(out_v), '/', len(faces))
print('scale k     : %.4f' % k)
print('final dia   : %.4f m' % TARGET_D)
print('output      : _prop_geom.js  %.1f KB' % (len(js) / 1024))
