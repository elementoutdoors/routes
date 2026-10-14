// Turn directions read as full, natural sentences (config/cue-wording.json). Ride with GPS keeps its cue sheet wording;
// the app shows and speaks the tidied version. Used by the build for every cue.
import fs from 'node:fs';
import path from 'node:path';

let W = { fixes: {}, rules: [] };
export function loadCueWording(root) {
  try { W = JSON.parse(fs.readFileSync(path.join(root, 'config', 'cue-wording.json'), 'utf8')); } catch (e) { W = { fixes: {}, rules: [] }; }
  W.fixes = W.fixes || {};
  W.rules = (W.rules || []).map(r => { try { return { re: new RegExp(r.find, 'g'), say: r.say }; } catch (e) { return null; } }).filter(Boolean);
  return W;
}
// $1..$9 groups, with \u (capitalise) and \l (lower case) before a group
function apply(text, re, say) {
  return text.replace(re, (...m) => say.replace(/(\\[ul])?\$(\d)/g, (_, cs, n) => {
    const g = m[Number(n)] == null ? '' : m[Number(n)];
    return cs === '\\u' ? g.charAt(0).toUpperCase() + g.slice(1) : cs === '\\l' ? g.toLowerCase() : g;
  }));
}
export function wordCue(text) {
  const t = String(text || '');
  if (Object.prototype.hasOwnProperty.call(W.fixes, t)) return W.fixes[t];
  let out = t;
  for (const r of W.rules) out = apply(out, r.re, r.say);
  return out;
}
// cue sheet shorthand still left after the rules: a lower case thing with no "the" after a direction word
const SHORT = /\b(along|onto|into|through|across|over|under|past|follow|following|cross|towards)\s+(?!the\b|a\b|an\b|your\b|this\b|that\b|it\b|all\b)[a-z]+/;
export function looksShort(text) { return SHORT.test(text) || /^[a-z]/.test(text); }
