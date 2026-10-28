// Prints the wallet signing keys (cards/wallet/keys.enc.json) for cards/wallet.py. Only works in the GitHub build,
// which has ROUTE_SECRETS (its keySalt makes the build key the file is sealed to). Never writes them anywhere.
import fs from 'node:fs';
import { buildKeys, unseal } from '../scripts/ride-desk.mjs';

const s = JSON.parse(process.env.ROUTE_SECRETS || '{}');
if (!s.keySalt) { console.error('no ROUTE_SECRETS keySalt'); process.exit(1); }
const env = JSON.parse(fs.readFileSync(new URL('./wallet/keys.enc.json', import.meta.url), 'utf8'));
process.stdout.write(JSON.stringify(unseal(env, buildKeys(s.keySalt).priv)));
