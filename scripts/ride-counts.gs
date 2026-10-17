/**
 * Ride Guide ride counts (17/10/2026).
 *
 * Bound to the Google Sheet "Ride Guide ride counts" (admin@elementoutdoors.com.au) and deployed as a web app
 * (execute as me, anyone can call). This copy in the repo is for reference; the live code is in the sheet's
 * Extensions > Apps Script.
 *
 * @OnlyCurrentDoc  (the script can reach this one sheet and nothing else in Drive)
 *
 * POST: phones send a JSON list of ticks {s: route slug, e: "open" | "finish", d: "YYYY-MM-DD", id}. Each valid tick is
 *       added as one row. Nothing else can be written, and nothing is ever read back through POST.
 * GET: the totals per route only (unique ids only, so resent ticks never count twice). Open on purpose (Ben, 17/10/2026):
 *      route names and ride numbers, nothing about any rider, and the sheet itself stays private.
 */
var SHEET = 'Ticks';

function sheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(SHEET);
  if (!sh) {
    sh = ss.insertSheet(SHEET);
    sh.appendRow(['Received', 'Ride date', 'Route', 'Event', 'Id']);
    sh.setFrozenRows(1);
  }
  return sh;
}

function out_(obj) {
  return ContentService.createTextOutput(typeof obj === 'string' ? obj : JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  var body = (e && e.postData && e.postData.contents) || '';
  if (!body || body.length > 20000) return out_('"ignored"');
  var list;
  try { list = JSON.parse(body); } catch (x) { return out_('"ignored"'); }
  if (!Array.isArray(list)) list = [list];
  var now = new Date(), rows = [];
  list.slice(0, 50).forEach(function (t) {
    if (!t || typeof t !== 'object') return;
    if (!/^[a-z0-9-]{1,60}$/.test(t.s || '')) return;
    if (t.e !== 'open' && t.e !== 'finish') return;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(t.d || '')) return;
    if (!/^[of][a-z0-9]{6,30}$/.test(t.id || '')) return;
    rows.push([now, t.d, t.s, t.e, t.id]);
  });
  if (!rows.length) return out_('"ok"');
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var sh = sheet_();
    sh.getRange(sh.getLastRow() + 1, 1, rows.length, 5).setValues(rows);
  } finally {
    lock.releaseLock();
  }
  return out_('"ok"');
}

function doGet(e) {
  var tz = 'Australia/Brisbane';
  var todayStr = Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd');
  var since = Utilities.formatDate(new Date(Date.now() - 30 * 86400000), tz, 'yyyy-MM-dd');
  var tomorrow = Utilities.formatDate(new Date(Date.now() + 86400000), tz, 'yyyy-MM-dd');
  var sh = sheet_();
  var n = sh.getLastRow() - 1;
  var vals = n > 0 ? sh.getRange(2, 1, n, 5).getValues() : [];
  var seen = {}, routes = {};
  vals.forEach(function (r) {
    var id = String(r[4]), ev = String(r[3]), slug = String(r[2]);
    if (seen[id]) return;
    seen[id] = true;
    // the date the phone gave, unless it is clearly wrong (then the date it arrived)
    var d = String(r[1] instanceof Date ? Utilities.formatDate(r[1], tz, 'yyyy-MM-dd') : r[1]);
    var got = r[0] instanceof Date ? Utilities.formatDate(r[0], tz, 'yyyy-MM-dd') : todayStr;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(d) || d > tomorrow || d < '2026-10-01') d = got;
    var c = routes[slug] || (routes[slug] = { phones: 0, phones30: 0, rides: 0, rides30: 0, lastRide: '' });
    if (ev === 'open') { c.phones++; if (d >= since) c.phones30++; }
    if (ev === 'finish') { c.rides++; if (d >= since) c.rides30++; if (d > c.lastRide) c.lastRide = d; }
  });
  return out_({ asOf: new Date().toISOString(), ticks: vals.length, routes: routes });
}
