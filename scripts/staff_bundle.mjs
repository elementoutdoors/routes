// Staff only files for the EO Crew staff app (Ride Guide manual, EO-HI-10): each ride's route code, private link and the
// Ride Guide screenshots. They are locked with EO Crew's public key (config/staff-key.pem, from
// https://element-crew-connect.base44.app/functions/rideGuide), so the published files can only be opened by EO Crew's
// server. A public key can only lock, never open, so it is safe in this repo. Nothing here is readable on the site.
// Usage: node scripts/staff_bundle.mjs screens <dir> <out.enc.json>   (seal the screenshots taken by staff_screens.py)
//        node scripts/staff_bundle.mjs booklet <booklet.pdf> <meta.json> <out.enc.json>   (seal a ride sheet or the booklet, ride-sheets/build.py)
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const KEY = path.join(ROOT, 'config', 'staff-key.pem');

export function seal(obj) {
  const pub = fs.readFileSync(KEY, 'utf8');
  const aes = crypto.randomBytes(32), iv = crypto.randomBytes(12);
  const c = crypto.createCipheriv('aes-256-gcm', aes, iv);
  const data = Buffer.concat([c.update(JSON.stringify(obj)), c.final(), c.getAuthTag()]);
  const key = crypto.publicEncrypt({ key: pub, padding: crypto.constants.RSA_PKCS1_OAEP_PADDING, oaepHash: 'sha256' }, aes);
  return { v: 1, alg: 'RSA-OAEP-256 + A256GCM', for: 'EO Crew', key: key.toString('base64'), iv: iv.toString('base64'), data: data.toString('base64') };
}

// Called by build.mjs: route codes and links for every live ride.
export function writeStaffFile(dist, built, links, codes, builtAt) {
  if (!fs.existsSync(KEY)) return 'staff file not written: config/staff-key.pem is missing';
  const rides = built.map(({ route: r }) => ({ slug: r.slug, name: r.name, brand: (r.brand && r.brand.id) || '', type: r.type || '',
    code: codes[r.slug] || '', link: links[r.slug] || '', test: /test/i.test(r.slug) }));
  fs.writeFileSync(path.join(dist, 'staff.enc.json'), JSON.stringify(seal({ built: builtAt, rides })));
  return null;
}

if (process.argv[2] === 'screens') {
  const dir = process.argv[3], outFile = process.argv[4];
  const m = JSON.parse(fs.readFileSync(path.join(dir, 'screens.json'), 'utf8'));
  m.screens = m.screens.map((s) => ({ ...s, type: 'jpeg', b64: fs.readFileSync(path.join(dir, s.file)).toString('base64') }));
  fs.writeFileSync(outFile, JSON.stringify(seal(m)));
  console.log(`sealed ${m.screens.length} screenshots into ${outFile}`);
}

// The ride sheets and booklet (ride-sheets/build.py): the PDF as base64 with what it was built from, in the same envelope.
// Usage: node scripts/staff_bundle.mjs booklet <booklet.pdf> <meta.json> <out.enc.json>
if (process.argv[2] === 'booklet') {
  const [pdf, metaFile, outFile] = process.argv.slice(3);
  const m = JSON.parse(fs.readFileSync(metaFile, 'utf8'));
  const b64 = fs.readFileSync(pdf).toString('base64');
  fs.writeFileSync(outFile, JSON.stringify(seal({ ...m, kind: m.kind || 'booklet', type: 'application/pdf', b64 })));
  console.log(`sealed the rides booklet (${Math.round(b64.length * 3 / 4 / 1024)} KB) into ${outFile}`);
}
