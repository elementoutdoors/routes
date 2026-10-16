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
const SHORT = /\b(along|onto|into|through|across|over|under|past|follow|following|cross|towards)\s+(?!the\b|a\b|an\b|your\b|this\b|that\b|it\b|all\b|to\b|safely\b|carefully\b|with\b|at\b|here\b)[a-z]+/;
export function looksShort(text) { return SHORT.test(text) || /^[a-z]/.test(text); }

// The "here" version of a direction, said at the turn itself after a soft ding (Ben, 16/10/2026):
// "Turn right onto Flynn Road." -> "Turn right here onto Flynn Road."; "Cross Goodchap Street and ..." -> "Now, cross
// Goodchap Street and ...". Returns null when the direction is said as written (a start or finish line, a caution, or a
// direction that already says "here").
const TURN_WORDS = /^((?:(?:turn|bear|keep|veer|fork|make a)\s+)?(?:(?:sharp|slight|hard)\s+)?(?:left|right|u[ -]?turn))\b/i;
const ACTION = /^(cross|continue|follow|take|ride|go|head|enter|exit|join|leave|stay|use|walk|dismount|carry|pass|merge|climb|descend|roll|join|at|after|before|ignore|stick|swing|hop)\b/i;
export function hereCue(c, isFirst) {
  const t = String(c.n || '').trim();
  if (!t || c.t === 'danger' || /\bhere\b/i.test(t)) return null;
  if (isFirst && c.d < 40) return null;   // the opening line is said at the start
  const m = TURN_WORDS.exec(t);
  if (m) return m[1] + ' here' + t.slice(m[1].length);
  if (ACTION.test(t)) return 'Now, ' + t.charAt(0).toLowerCase() + t.slice(1);
  return null;
}
