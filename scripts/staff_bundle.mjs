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

// Called by build.mjs: route codes and links for every live ride, with each ride's Ride Desk staff section (who it suits,
// not for, time to allow, sold as, bikes, start and finish, staff notes), its title and whether it is on the hire desk iPad
// (18/10/2026). Every live ride is here, iPad or not; rides.json only lists the iPad ones.
export function writeStaffFile(dist, built, links, codes, builtAt, deskOf = () => ({})) {
  if (!fs.existsSync(KEY)) return 'staff file not written: config/staff-key.pem is missing';
  const rides = built.map(({ route: r }) => {
    const d = deskOf(r.slug) || {};
    return { slug: r.slug, name: r.name, brand: (r.brand && r.brand.id) || '', type: r.type || '',
      code: codes[r.slug] || '', link: links[r.slug] || '', test: /test/i.test(r.slug),
      title: d.title || '', ipad: !!d.ipad, staff: d.staff || null };
  });
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

// Any small JSON document (the ride sheets index, ride-sheets/build.py), locked as it is.
// Usage: node scripts/staff_bundle.mjs json <in.json> <out.enc.json>
if (process.argv[2] === 'json') {
  const [inFile, outFile] = process.argv.slice(3);
  fs.writeFileSync(outFile, JSON.stringify(seal(JSON.parse(fs.readFileSync(inFile, 'utf8')))));
  console.log(`sealed ${path.basename(inFile)} into ${outFile}`);
}

// Envelope v2 for big files (the rides booklet, ride-sheets/build.py): the PDF's raw AES-256-GCM ciphertext with the
// 16 byte tag on the end (as WebCrypto gives it), no base64, plus a small key file with the AES key wrapped by EO Crew's
// public key (RSA-OAEP, SHA-256). EO Crew can stream the file instead of holding base64 in base64 in memory.
// Before anything is written it proves the round trip: the same AES key is also wrapped with a throwaway key pair,
// unwrapped, and the published ciphertext decrypted; the SHA-256 must match the PDF's.
// Usage: node scripts/staff_bundle.mjs v2 <in.pdf> <meta.json> <out.pdf.enc> <out.key.json>
export function sealV2(bytes, meta, pubKey) {
  const aes = crypto.randomBytes(32), iv = crypto.randomBytes(12);
  const c = crypto.createCipheriv('aes-256-gcm', aes, iv);
  const enc = Buffer.concat([c.update(bytes), c.final(), c.getAuthTag()]);
  const wrap = (pub) => crypto.publicEncrypt({ key: pub, padding: crypto.constants.RSA_PKCS1_OAEP_PADDING, oaepHash: 'sha256' }, aes);
  const sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
  // self check with a throwaway key pair
  const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
  const back = crypto.privateDecrypt({ key: privateKey, padding: crypto.constants.RSA_PKCS1_OAEP_PADDING, oaepHash: 'sha256' }, wrap(publicKey));
  const d = crypto.createDecipheriv('aes-256-gcm', back, iv);
  d.setAuthTag(enc.subarray(enc.length - 16));
  const plain = Buffer.concat([d.update(enc.subarray(0, enc.length - 16)), d.final()]);
  if (crypto.createHash('sha256').update(plain).digest('hex') !== sha256) throw new Error('v2 self check failed: decrypted bytes differ');
  const key = { v: 2, alg: 'RSA-OAEP-256+A256GCM', for: 'EO Crew', key: wrap(pubKey).toString('base64'), iv: iv.toString('base64'),
    bytes: bytes.length, sha256, ...meta };
  return { enc, key };
}

if (process.argv[2] === 'v2') {
  const [pdf, metaFile, outEnc, outKey] = process.argv.slice(3);
  const { enc, key } = sealV2(fs.readFileSync(pdf), JSON.parse(fs.readFileSync(metaFile, 'utf8')), fs.readFileSync(KEY, 'utf8'));
  fs.writeFileSync(outEnc, enc);
  fs.writeFileSync(outKey, JSON.stringify(key));
  console.log(`sealed ${path.basename(pdf)} (v2): ${enc.length} bytes, key file ${Buffer.byteLength(JSON.stringify(key))} bytes, self check passed`);
}
