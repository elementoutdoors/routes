// Minimal Mapbox Vector Tile decoder (no dependencies). Used by scripts/toilets.mjs to read the base map tiles.
export function decodeTile(buf) {
  let p = 0;
  const varint = () => { let r = 0, s = 0, b; do { b = buf[p++]; r += (b & 0x7f) * 2 ** s; s += 7; } while (b & 0x80); return r; };
  const readMsg = (end, fn) => { while (p < end) { const k = varint(), f = Math.floor(k / 8), w = k & 7; if (w === 2) { const l = varint(), e = p + l; fn(f, w, e); p = e; } else if (w === 0) fn(f, w, varint()); else if (w === 1) { fn(f, w, buf.readDoubleLE(p)); p += 8; } else if (w === 5) { fn(f, w, buf.readFloatLE(p)); p += 4; } } };
  const str = e => buf.toString('utf8', p, e);
  const packed = e => { const a = []; while (p < e) a.push(varint()); return a; };
  const layers = [];
  readMsg(buf.length, (f, w, e) => {
    if (f !== 3) return;
    const L = { name: '', keys: [], values: [], features: [], extent: 4096 };
    readMsg(e, (f2, w2, e2) => {
      if (f2 === 1) L.name = str(e2);
      else if (f2 === 3) L.keys.push(str(e2));
      else if (f2 === 5) L.extent = e2;
      else if (f2 === 4) { let v = null; readMsg(e2, (f3, w3, e3) => { if (f3 === 1) v = str(e3); else if (f3 === 6) v = (e3 >>> 1) ^ -(e3 & 1); else if (f3 === 7) v = !!e3; else if (w3 !== 2) v = e3; }); L.values.push(v); }
      else if (f2 === 2) { const F = { tags: [], geom: [], type: 0 }; readMsg(e2, (f3, w3, e3) => { if (f3 === 2) F.tags = packed(e3); else if (f3 === 4) F.geom = packed(e3); else if (f3 === 3) F.type = e3; }); L.features.push(F); }
    });
    layers.push(L);
  });
  return layers.map(L => ({ name: L.name, extent: L.extent, features: L.features.map(F => {
    const props = {}; for (let i = 0; i < F.tags.length; i += 2) props[L.keys[F.tags[i]]] = L.values[F.tags[i + 1]];
    const pts = []; let x = 0, y = 0, i = 0;
    while (i < F.geom.length) { const c = F.geom[i++], id = c & 7, n = c >> 3; if (id === 7) continue; for (let j = 0; j < n; j++) { const dx = F.geom[i++], dy = F.geom[i++]; x += (dx >>> 1) ^ -(dx & 1); y += (dy >>> 1) ^ -(dy & 1); pts.push([x, y]); } }
    return { type: F.type, props, pts };
  }) }));
}
