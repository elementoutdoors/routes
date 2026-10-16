/* Ride Guide: public route viewer for Element Outdoors.
   Plain JS, no build step. Route data comes from r/<key>.json, made by scripts/build.mjs. */
(function () {
  'use strict';

  var BUILD = '__BUILD__';
  var LS = window.localStorage;
  var $ = function (id) { return document.getElementById(id); };

  // ---------- storage (never throws) ----------
  function lsGet(k, d) { try { var v = LS.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
  function lsSet(k, v) { try { LS.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  function lsDel(k) { try { LS.removeItem(k); } catch (e) {} }

  // ---------- settings ----------
  var LANGS = [
    ['en', 'English'], ['de', 'Deutsch'], ['fr', 'Français'], ['es', 'Español'], ['it', 'Italiano'],
    ['nl', 'Nederlands'], ['zh', '中文'], ['ja', '日本語'], ['ko', '한국어']
  ];
  var SPEECH_LANG = { en: 'en-AU', de: 'de-DE', fr: 'fr-FR', es: 'es-ES', it: 'it-IT', nl: 'nl-NL', zh: 'zh-CN', ja: 'ja-JP', ko: 'ko-KR' };
  function defaultLang() {
    var l = ((navigator.language || 'en') + '').slice(0, 2).toLowerCase();
    return SPEECH_LANG[l] ? l : 'en';
  }
  function defaultUnits() {
    // phones in Australia and New Zealand often run US English; they still get kilometres
    var tz = ''; try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
    if (/^(Australia|Pacific\/Auckland)/.test(tz)) return 'metric';
    return /^en-(US|GB|LR|MM)/i.test(navigator.language || '') ? 'imperial' : 'metric';
  }
  // Only the settings a rider changed are stored; everything else follows the business defaults in each route.
  var touched = lsGet('rg.touched', null);
  var savedS = lsGet('rg.settings', {});
  if (!touched) touched = Object.keys(savedS);
  // Point of interest stories are chosen per ride (Ben, 15/10/2026): each ride has its own default, and a rider's own
  // switch is kept for that ride only. An older phone-wide choice no longer applies.
  touched = touched.filter(function (k) { return k !== 'stories'; });
  var storyPick = lsGet('rg.stories', {});
  var S = Object.assign({ units: defaultUnits(), lang: defaultLang(), voice: true, natural: true, chime: true, stories: true, wake: true, saver: false, sat: false }, savedS);
  function saveSettings(key) {
    if (key && touched.indexOf(key) < 0) touched.push(key);
    var out = {}; touched.forEach(function (k) { out[k] = S[k]; });
    lsSet('rg.settings', out); lsSet('rg.touched', touched);
  }
  // business settings (config/settings.json), with the same defaults the build uses
  var CFG = { announce: { firstWarningMetres: 160, turnMetres: 35, cautionWarningMetres: 120, skipFirstWarningIfCuesCloserThanMetres: 110, mergeNextCueWithinMetres: 90 },
    offRoute: { metres: 50, readings: 3, repeatSeconds: 60 }, stops: { triggerMetres: 60, cautionWarningMetres: 90 },
    screen: { wakeBeforeTurnMetres: 250, blackoutAfterSeconds: 20 } };
  function applyRouteSettings() {
    var rs = R.settings || {};
    ['announce', 'offRoute', 'stops', 'screen'].forEach(function (g) { if (rs[g]) Object.keys(CFG[g]).forEach(function (k) { if (typeof rs[g][k] === 'number') CFG[g][k] = rs[g][k]; }); });
    if (rs.speeds) Object.keys(rs.speeds).forEach(function (k) { SPEED[k] = rs.speeds[k] / 3.6; });
    var sc = rs.screen || {};
    [['wake', 'keepScreenOn'], ['saver', 'batterySaver']].forEach(function (p) {
      if (touched.indexOf(p[0]) < 0 && typeof sc[p[1]] === 'boolean') S[p[0]] = sc[p[1]];
    });
    var def = typeof R.stories === 'boolean' ? R.stories : typeof sc.readStoriesAloud === 'boolean' ? sc.readStoriesAloud : true;
    S.stories = typeof storyPick[R.slug] === 'boolean' ? storyPick[R.slug] : def;
  }
  function saveStoryPick() { if (!R) return; storyPick[R.slug] = S.stories; lsSet('rg.stories', storyPick); }

  // ---------- translation ----------
  var UI = {};        // { lang: { english: translated } }
  var R = null;       // current route
  function tu(s) { var m = UI[S.lang]; return (m && m[s]) || s; }
  function tc(s) { if (!s) return s; var m = R && R.i18n && R.i18n[S.lang]; return (m && m[s]) || s; }
  function fmt(s, o) { return s.replace(/\{(\w+)\}/g, function (_, k) { return o[k] != null ? o[k] : ''; }); }
  function applyStaticText() {
    document.documentElement.lang = S.lang;
    Array.prototype.forEach.call(document.querySelectorAll('[data-t]'), function (el) { el.textContent = tu(el.getAttribute('data-t')); });
  }

  // ---------- units ----------
  function distParts(m) {
    if (S.units === 'imperial') {
      var mi = m / 1609.344;
      if (mi < 0.1) { var ft = Math.max(10, Math.round(m * 3.28084 / 10) * 10); return { v: ft, u: 'ft', say: fmt(tu('{n} feet'), { n: ft }) }; }
      var v = mi < 10 ? (Math.round(mi * 10) / 10) : Math.round(mi);
      return { v: v, u: 'mi', say: fmt(tu(v === 1 ? '{n} mile' : '{n} miles'), { n: v }) };
    }
    if (m < 1000) {
      var r = m < 100 ? Math.max(10, Math.round(m / 10) * 10) : Math.round(m / 50) * 50;
      if (r >= 1000) return { v: 1, u: 'km', say: fmt(tu('{n} kilometre'), { n: 1 }) };
      return { v: r, u: 'm', say: fmt(tu('{n} metres'), { n: r }) };
    }
    var k = m < 10000 ? Math.round(m / 100) / 10 : Math.round(m / 1000);
    return { v: k, u: 'km', say: fmt(tu(k === 1 ? '{n} kilometre' : '{n} kilometres'), { n: k }) };
  }
  function distText(m) { var p = distParts(m); return p.v + ' ' + p.u; }
  function climbText(m) { return S.units === 'imperial' ? Math.round(m * 3.28084) + ' ft' : Math.round(m) + ' m'; }
  function timeText(sec) {
    var min = Math.max(1, Math.round(sec / 60));
    if (min < 60) return fmt(tu('{n} min'), { n: min });
    var h = Math.floor(min / 60), mm = min % 60;
    return fmt(tu('{h} h {m} min'), { h: h, m: mm });
  }
  var SPEED = { ebike: 15 / 3.6, bike: 13 / 3.6, walk: 4.5 / 3.6, kayak: 5 / 3.6 };

  // ---------- geo ----------
  var DEG = Math.PI / 180;
  function hav(lat1, lng1, lat2, lng2) {
    var dLat = (lat2 - lat1) * DEG, dLng = (lng2 - lng1) * DEG;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(lat1 * DEG) * Math.cos(lat2 * DEG) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 6371000 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }
  // project onto segment i..i+1 in a local metric frame
  function projSeg(T, i, lat, lng) {
    var kx = 111320 * Math.cos(lat * DEG), ky = 110540;
    var ax = (T.lng[i] - lng) * kx, ay = (T.lat[i] - lat) * ky;
    var bx = (T.lng[i + 1] - lng) * kx, by = (T.lat[i + 1] - lat) * ky;
    var dx = bx - ax, dy = by - ay, len2 = dx * dx + dy * dy;
    var t = len2 > 0 ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / len2)) : 0;
    var px = ax + t * dx, py = ay + t * dy;
    return { dist: Math.sqrt(px * px + py * py), d: T.d[i] + t * (T.d[i + 1] - T.d[i]), i: i };
  }
  // all local minima of distance to the route within maxDist
  function candidates(lat, lng, maxDist) {
    var T = R.track, n = T.lat.length, best = [], run = null, nearest = null;
    for (var i = 0; i < n - 1; i++) {
      var p = projSeg(T, i, lat, lng);
      if (!nearest || p.dist < nearest.dist) nearest = p;
      if (p.dist <= maxDist) { if (!run || p.dist < run.dist) run = p; }
      else if (run) { best.push(run); run = null; }
    }
    if (run) best.push(run);
    return { list: best, nearest: nearest };
  }
  function pointAt(d) {
    var T = R.track, lo = 0, hi = T.d.length - 1;
    if (d <= 0) return [T.lng[0], T.lat[0]];
    if (d >= T.d[hi]) return [T.lng[hi], T.lat[hi]];
    while (hi - lo > 1) { var mid = (lo + hi) >> 1; if (T.d[mid] <= d) lo = mid; else hi = mid; }
    var f = (d - T.d[lo]) / ((T.d[hi] - T.d[lo]) || 1);
    return [T.lng[lo] + f * (T.lng[hi] - T.lng[lo]), T.lat[lo] + f * (T.lat[hi] - T.lat[lo])];
  }
  function idxAt(d) {
    var T = R.track, lo = 0, hi = T.d.length - 1;
    while (hi - lo > 1) { var mid = (lo + hi) >> 1; if (T.d[mid] <= d) lo = mid; else hi = mid; }
    return lo;
  }

  // ---------- icons ----------
  var IC = {
    left: '<path d="M16 20v-8a3 3 0 0 0-3-3H5"/><path d="M9 5L5 9l4 4"/>',
    right: '<path d="M8 20v-8a3 3 0 0 1 3-3h8"/><path d="M15 5l4 4-4 4"/>',
    'slight-left': '<path d="M14 21V11L8 5"/><path d="M8 10V5h5"/>',
    'slight-right': '<path d="M10 21V11l6-6"/><path d="M16 10V5h-5"/>',
    'sharp-left': '<path d="M15 21V8l-9 9"/><path d="M6 11v6h6"/>',
    'sharp-right': '<path d="M9 21V8l9 9"/><path d="M18 11v6h-6"/>',
    straight: '<path d="M12 21V4"/><path d="M7 9l5-5 5 5"/>',
    uturn: '<path d="M8 21V9a4 4 0 0 1 8 0v4"/><path d="M12 10l4 4 4-4"/>',
    danger: '<path d="M12 3l9.5 17h-19z"/><path d="M12 10v4M12 17.5v.5"/>',
    generic: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
    finish: '<path d="M5 21V4"/><path d="M5 4h12l-2 4 2 4H5"/>',
    pause: '<path d="M9 5v14M15 5v14"/>',
    pin: '<path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
    view: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    caution: '<path d="M12 3l9.5 17h-19z"/><path d="M12 10v4M12 17.5v.5"/>',
    toilet: '<path d="M7 4v16M17 4v16M4 9h6M14 9h6"/>',
    food: '<path d="M4 8h13v5a6 6 0 0 1-6 6H10a6 6 0 0 1-6-6z"/><path d="M17 10h1.5a2.5 2.5 0 0 1 0 5H17"/>',
    park: '<path d="M12 3l6 9H6z"/><path d="M12 8l7 10H5z"/><path d="M12 18v3"/>',
    turn: '<path d="M8 21V9a4 4 0 0 1 8 0v4"/><path d="M12 10l4 4 4-4"/>',
    drink: '<path d="M6 3h12l-1.5 18h-9z"/><path d="M6.5 8h11"/>',
    service: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M12 8v8M8 12h8"/>',
    offer: '<path d="M3 9V6a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v3a3 3 0 0 0 0 6v3a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-3a3 3 0 0 0 0-6z"/>',
    start: '<path d="M7 4l12 8-12 8z"/>',
    ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    vol: '<path d="M11 5L6 9H3v6h3l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/>',
    mute: '<path d="M11 5L6 9H3v6h3l5 4V5z"/><path d="M22 9l-6 6M16 9l6 6"/>',
    phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>',
    star: '<path d="M12 3l2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9z"/>'
  };
  function svg(name, cls) { return '<svg viewBox="0 0 24 24" aria-hidden="true"' + (cls ? ' class="' + cls + '"' : '') + '>' + (IC[name] || IC.info) + '</svg>'; }
  function cueIcon(t) { return IC[t] ? t : (t === 'generic' ? 'generic' : 'straight'); }

  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === 'text') e.textContent = attrs[k];
      else if (k === 'class') e.className = attrs[k];
      else if (k.slice(0, 2) === 'on') e.addEventListener(k.slice(2), attrs[k]);
      else e.setAttribute(k, attrs[k]);
    });
    if (html != null) e.innerHTML = html;
    return e;
  }
  function safeUrl(u) { return /^https?:\/\//i.test(u || '') ? u : null; }

  // ---------- views ----------
  function show(view) {
    document.body.className = 'view-' + view;
    if (map) setTimeout(function () { map.resize(); }, 30);
  }

  // ---------- data loading ----------
  var routeIndex = lsGet('rg.routes', {});   // key -> {name, slug, saved}
  // Staff check mode: opened from a check link (...?check#KEY). Lets staff step through every direction and stop on the map.
  // Lasts until the page is closed; riders never see it.
  var CHECK = /[?&]check\b/.test(location.search);
  function keyFromUrl() {
    var h = (location.hash || '').replace(/^#\/?/, '');
    var q = (location.search.match(/[?&]r=([A-Za-z0-9_-]{8,})/) || [])[1];
    var k = q || h;
    return /^[A-Za-z0-9_-]{8,64}$/.test(k) ? k : null;
  }
  function scrubUrl() {
    // Remove the route key from the address bar so a copied link does not open the route.
    try { history.replaceState(null, '', location.pathname.replace(/index\.html$/, '')); } catch (e) {}
  }
  function fetchJson(url) {
    return fetch(url, { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
  }
  function loadUi() {
    var cached = lsGet('rg.ui', null);
    if (cached) UI = cached;
    var v = lsGet('rg.voice', null); if (v) setVoiceManifest(v);
    fetchJson('voice.json?v=' + BUILD).then(function (m) { setVoiceManifest(m); lsSet('rg.voice', m); pruneVoiceCache(); if (R) precacheVoice(); }).catch(function () {});
    return fetchJson('ui.json?v=' + BUILD).then(function (u) { UI = u; lsSet('rg.ui', u); }).catch(function () {});
  }
  function storeRoute(key, data) {
    if (!lsSet('rg.route.' + key, data)) {
      // storage full: drop the oldest other routes and retry
      Object.keys(routeIndex).sort(function (a, b) { return routeIndex[a].saved - routeIndex[b].saved; }).forEach(function (k) {
        if (k !== key) { lsDel('rg.route.' + k); delete routeIndex[k]; }
      });
      lsSet('rg.route.' + key, data);
    }
    routeIndex[key] = { name: data.name, slug: data.slug, saved: Date.now(), brand: data.brand && data.brand.id };
    lsSet('rg.routes', routeIndex);
  }
  function getRoute(key) {
    var local = lsGet('rg.route.' + key, null);
    return fetchJson('r/' + key + '.json').then(function (data) {
      storeRoute(key, data); return data;
    }, function (err) {
      if (local) return local;
      throw err;
    });
  }

  // ---------- map ----------
  var map = null, mapReady = false, markers = [], meMarker = null, styleCache = {};
  var STYLE = 'https://tiles.openfreemap.org/styles/liberty';
  function satStyle() {
    return {
      version: 8,
      glyphs: 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf',
      sources: { sat: { type: 'raster', tileSize: 256, maxzoom: 19,
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
        attribution: 'Imagery © Esri, Maxar, Earthstar Geographics' } },
      layers: [{ id: 'sat', type: 'raster', source: 'sat' }]
    };
  }
  function initMap() {
    if (map || !window.maplibregl) return;
    map = new maplibregl.Map({
      container: 'map', style: S.sat ? satStyle() : STYLE, attributionControl: { compact: true },
      center: [R.track.lng[0], R.track.lat[0]], zoom: 13, pitchWithRotate: false, dragRotate: false, touchPitch: false
    });
    map.touchZoomRotate.disableRotation();
    map.on('load', function () { mapReady = true; addRouteLayers(); fitRoute(); });
    map.on('style.load', function () { if (mapReady) addRouteLayers(); });
    map.on('dragstart', function () { if (ride.active) { ride.follow = false; updateFollowBtn(); } });
    map.on('zoomend', function (e) { if (ride.active && e.originalEvent) ride.zoom = map.getZoom(); });
  }
  function routeGeo(fromD, toD) {
    var T = R.track, coords = [], i0 = idxAt(Math.max(0, fromD)), i1 = idxAt(Math.min(toD, R.distance));
    coords.push(pointAt(fromD));
    for (var i = i0 + 1; i <= i1; i++) coords.push([T.lng[i], T.lat[i]]);
    coords.push(pointAt(toD));
    return { type: 'Feature', geometry: { type: 'LineString', coordinates: coords } };
  }
  function addRouteLayers() {
    if (!map || !R) return;
    ['route-done', 'route-casing', 'route-line', 'route-arrows'].forEach(function (id) { if (map.getLayer(id)) map.removeLayer(id); });
    ['route', 'done'].forEach(function (id) { if (map.getSource(id)) map.removeSource(id); });
    map.addSource('route', { type: 'geojson', data: routeGeo(0, R.distance) });
    map.addSource('done', { type: 'geojson', data: routeGeo(0, 0) });
    map.addLayer({ id: 'route-casing', type: 'line', source: 'route', layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: { 'line-color': '#ffffff', 'line-width': ['interpolate', ['linear'], ['zoom'], 11, 6, 16, 12] } });
    map.addLayer({ id: 'route-line', type: 'line', source: 'route', layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: { 'line-color': R.brand.colors.line, 'line-width': ['interpolate', ['linear'], ['zoom'], 11, 3.5, 16, 7] } });
    map.addLayer({ id: 'route-done', type: 'line', source: 'done', layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: { 'line-color': '#8A9099', 'line-width': ['interpolate', ['linear'], ['zoom'], 11, 3.5, 16, 7] } });
    map.addLayer({ id: 'route-arrows', type: 'symbol', source: 'route',
      layout: { 'symbol-placement': 'line', 'symbol-spacing': 90, 'text-field': '›', 'text-size': 22, 'text-keep-upright': false,
        'text-font': ['Noto Sans Bold'], 'text-allow-overlap': true, 'text-offset': [0, -0.1] },
      paint: { 'text-color': '#ffffff' } });
    if (ride.d > 0) updateDone();
  }
  function fitRoute() {
    if (!map) return;
    var T = R.track, b = new maplibregl.LngLatBounds();
    for (var i = 0; i < T.lat.length; i += 5) b.extend([T.lng[i], T.lat[i]]);
    map.fitBounds(b, { padding: { top: 70, bottom: 40, left: 30, right: 30 }, duration: 0, maxZoom: 15 });
  }
  function clearMarkers() { markers.forEach(function (m) { m.remove(); }); markers = []; }
  function addMarkers() {
    clearMarkers();
    if (!map) return;
    var start = el('div', { class: 'mk start', title: tu('Start') }, svg('start'));
    markers.push(new maplibregl.Marker({ element: start }).setLngLat([R.track.lng[0], R.track.lat[0]]).addTo(map));
    R.stops.forEach(function (s) {
      if (s.kind === 'finish') return;
      var b = el('button', { class: 'mk ' + s.kind, type: 'button', 'aria-label': tc(s.name) }, svg(s.kind));
      b.addEventListener('click', function (e) { e.stopPropagation(); openStop(s); });
      markers.push(new maplibregl.Marker({ element: b }).setLngLat([s.lng, s.lat]).addTo(map));
    });
    offerPlaces().forEach(function (g) {
      if (g[0].fin && !(ride.active && ride.shown.finOffers)) return;   // an offer for the end of the ride only shows near the end
      var b = el('button', { class: 'mk offer', type: 'button', 'aria-label': g[0].partner }, svg('offer'));
      b.addEventListener('click', function (e) { e.stopPropagation(); openOffers(g); });
      markers.push(new maplibregl.Marker({ element: b }).setLngLat([g[0].lng, g[0].lat]).addTo(map));
    });
  }
  function setSatellite(on) {
    S.sat = on; saveSettings('sat');
    if (map) map.setStyle(on ? satStyle() : STYLE);
  }

  // ---------- offline (cache the map around the route) ----------
  function lng2tile(lng, z) { return Math.floor((lng + 180) / 360 * Math.pow(2, z)); }
  function lat2tile(lat, z) { var r = lat * DEG; return Math.floor((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * Math.pow(2, z)); }
  function saveOffline() {
    var note = $('offline-note'), txt = $('offline-text');
    var doneKey = 'rg.offline.' + R.key + '.' + R.version;
    function done(ok) {
      note.classList.toggle('done', ok);
      txt.textContent = tu(ok ? 'Saved to your phone. Works with no signal.' : 'Saved to your phone. Map detail needs signal.');
    }
    if (lsGet(doneKey, false)) { done(true); return; }
    if (!('serviceWorker' in navigator) || !navigator.onLine) { done(false); return; }
    note.classList.remove('done'); txt.textContent = tu('Saving the route to your phone');
    navigator.serviceWorker.ready.then(function () {
      return fetchJson(STYLE);
    }).then(function (style) {
      var urls = [STYLE];
      var srcUrl = style.sources && style.sources.openmaptiles && style.sources.openmaptiles.url;
      var spr = style.sprite;
      if (typeof spr === 'string') [spr + '.json', spr + '.png', spr + '@2x.json', spr + '@2x.png'].forEach(function (u) { urls.push(u); });
      if (style.glyphs) ['Noto Sans Regular', 'Noto Sans Bold', 'Noto Sans Italic'].forEach(function (f) {
        ['0-255', '256-511', '8192-8447'].forEach(function (rg) { urls.push(style.glyphs.replace('{fontstack}', encodeURIComponent(f)).replace('{range}', rg)); });
      });
      return (srcUrl ? fetchJson(srcUrl) : Promise.resolve(null)).then(function (tj) {
        urls.push(srcUrl);
        var tpl = tj && tj.tiles && tj.tiles[0];
        if (tpl) {
          var T = R.track, minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;
          for (var i = 0; i < T.lat.length; i++) { minLat = Math.min(minLat, T.lat[i]); maxLat = Math.max(maxLat, T.lat[i]); minLng = Math.min(minLng, T.lng[i]); maxLng = Math.max(maxLng, T.lng[i]); }
          var seen = {};
          for (var z = 9; z <= 14; z++) {
            if (z <= 12) {
              for (var x = lng2tile(minLng - 0.01, z); x <= lng2tile(maxLng + 0.01, z); x++)
                for (var y = lat2tile(maxLat + 0.01, z); y <= lat2tile(minLat - 0.01, z); y++) seen[z + '/' + x + '/' + y] = 1;
            } else {
              // corridor: tiles touching the route plus neighbours
              for (var j = 0; j < T.lat.length; j += 3) {
                var tx = lng2tile(T.lng[j], z), ty = lat2tile(T.lat[j], z);
                for (var a = -1; a <= 1; a++) for (var c = -1; c <= 1; c++) seen[z + '/' + (tx + a) + '/' + (ty + c)] = 1;
              }
            }
          }
          Object.keys(seen).forEach(function (k) { var p = k.split('/'); urls.push(tpl.replace('{z}', p[0]).replace('{x}', p[1]).replace('{y}', p[2])); });
        }
        R.stops.forEach(function (s) { (s.photos || []).forEach(function (u) { urls.push(u); }); });
        R.offers.forEach(function (o) { if (o.logo) urls.push(o.logo); });
        return fetchAll(urls);
      });
    }).then(function (failed) {
      if (failed < 5) { lsSet(doneKey, true); done(true); } else done(false);
    }).catch(function () { done(false); });
  }
  function fetchAll(urls) {
    var i = 0, failed = 0;
    function next() {
      if (i >= urls.length) return Promise.resolve();
      var u = urls[i++];
      return fetch(u, { mode: /arcgisonline|ridewithgps/.test(u) ? 'no-cors' : 'cors' }).then(function (r) { if (!r.ok && r.type !== 'opaque') failed++; }, function () { failed++; }).then(next);
    }
    var workers = []; for (var w = 0; w < 6; w++) workers.push(next());
    return Promise.all(workers).then(function () { return failed; });
  }

  // ---------- speech ----------
  var voices = [];
  function loadVoices() { try { voices = window.speechSynthesis ? speechSynthesis.getVoices() : []; } catch (e) { voices = []; } }
  if (window.speechSynthesis) { loadVoices(); speechSynthesis.onvoiceschanged = loadVoices; }
  function pickVoice(lang) {
    var want = SPEECH_LANG[lang] || 'en-AU', base = want.slice(0, 2);
    var exact = voices.filter(function (v) { return v.lang && v.lang.replace('_', '-').toLowerCase() === want.toLowerCase(); });
    var near = voices.filter(function (v) { return v.lang && v.lang.slice(0, 2).toLowerCase() === base; });
    var pool = exact.length ? exact : near;
    return pool.filter(function (v) { return v.localService; })[0] || pool[0] || null;
  }
  // Natural voice: lines recorded at build time (Google Chirp 3 HD) play as audio; anything without a recording,
  // or when Natural voice is off, uses the phone's own voice. One queue keeps both in order.
  // voiceHash must match scripts/voice.mjs.
  function voiceHash(str) {
    var a = 0x811c9dc5, b = 0x01000193 ^ 0x5bd1e995;
    for (var i = 0; i < str.length; i++) {
      var c = str.charCodeAt(i);
      a ^= c; a = Math.imul(a, 0x01000193) >>> 0;
      b ^= c; b = Math.imul(b, 0x01000193) >>> 0; b ^= b >>> 13;
    }
    return ('0000000' + (a >>> 0).toString(16)).slice(-8) + ('0000000' + (b >>> 0).toString(16)).slice(-8);
  }
  var VOICE = {};   // { lang: { tag, h: Set, pre: [] } }
  var SAY = { rules: [], names: {} };   // how written text is said aloud (config/speech.json), for the phone voice
  function setVoiceManifest(m) {
    VOICE = {};
    Object.keys(m || {}).forEach(function (l) { if (l.charAt(0) !== '_') VOICE[l] = { tag: m[l].tag, h: new Set(m[l].h || []), pre: m[l].pre || [] }; });
    if (m && m._say) SAY = m._say;
  }
  function speakable(lang, text) {
    var t = String(text || '');
    (SAY.rules || []).forEach(function (r) { if (r.langs && r.langs.indexOf(lang) < 0) return; try { t = t.replace(new RegExp(r.find, 'g'), r.say); } catch (e) {} });
    Object.keys(SAY.names || {}).forEach(function (n) { t = t.replace(new RegExp('\\b' + n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'g'), SAY.names[n]); });
    return t.trim();
  }
  var routeClips = {};
  function setRouteClips() { routeClips = {}; var v = (R && R.voice) || {}; Object.keys(v).forEach(function (l) { routeClips[l] = new Set(v[l]); }); }
  function clipFor(lang, text) {
    var vm = VOICE[lang]; if (!vm || !text) return null;
    var h = voiceHash(lang + '|' + String(text).trim());
    return (vm.h.has(h) || (routeClips[lang] && routeClips[lang].has(h))) ? 'v/' + vm.tag + '/' + h + '.mp3' : null;
  }
  var aud = null, queue = [], speaking = false, phoneTimer = null, curItem = null, storyFor = null;
  function audioEl() {
    if (!aud) {
      aud = new Audio(); aud.preload = 'auto';
      aud.addEventListener('ended', nextLine);
      aud.addEventListener('error', function () { var it = aud._item; if (it && !it.fell) clipFailed(it); });
    }
    return aud;
  }
  function stopSpeech() {
    queue = []; speaking = false; clearTimeout(phoneTimer); curItem = null;
    if (storyFor) { storyFor = null; updateStoryBtn(); }
    try { if (aud) { aud._item = null; aud.pause(); } } catch (e) {}
    try { if (window.speechSynthesis) speechSynthesis.cancel(); } catch (e) {}
  }
  // A recording that will not load usually means the site has just moved the recordings to a new address (a change to how
  // lines are said). Fetch the current list once, then play the same line from its new address. Only if that fails too
  // does the phone's own voice read it, so a ride never switches voice just because the site was updated mid ride.
  var voiceRefresh = null, voiceRefreshAt = 0;
  function refreshVoice() {
    if (voiceRefresh) return voiceRefresh;
    if (Date.now() - voiceRefreshAt < 60000 || !navigator.onLine) return Promise.resolve(false);
    voiceRefreshAt = Date.now();
    var before = JSON.stringify(Object.keys(VOICE).map(function (l) { return VOICE[l].tag; }));
    voiceRefresh = fetch('voice.json?v=' + BUILD + '&t=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (m) {
      setVoiceManifest(m); lsSet('rg.voice', m);
      var changed = JSON.stringify(Object.keys(VOICE).map(function (l) { return VOICE[l].tag; })) !== before;
      if (changed && R) { pruneVoiceCache(); precacheVoice(); }
      return changed;
    }).catch(function () { return false; }).then(function (c) { voiceRefresh = null; return c; });
    return voiceRefresh;
  }
  function clipFailed(it) {
    if (it.chime) { it.fell = true; nextLine(); return; }
    if (it.retried) { it.fell = true; phoneLine(it); return; }
    it.retried = true;
    refreshVoice().then(function () {
      if (aud && aud._item !== it) return;   // something else is playing now
      var u = clipFor(it.lang, it.text);
      if (u && u !== it.url) { it.url = u; var a = audioEl(); a.src = u; try { var p = a.play(); if (p && p.catch) p.catch(function () { it.fell = true; phoneLine(it); }); } catch (e) { it.fell = true; phoneLine(it); } }
      else { it.fell = true; phoneLine(it); }
    });
  }
  function phoneLine(it) {
    if (!window.speechSynthesis) { nextLine(); return; }
    var finished = false;
    function fin() { if (finished) return; finished = true; clearTimeout(phoneTimer); nextLine(); }
    try {
      var u = new SpeechSynthesisUtterance(speakable(it.lang, it.text)), v = pickVoice(it.lang);
      u.lang = SPEECH_LANG[it.lang] || 'en-AU'; if (v) u.voice = v; u.rate = 1; u.pitch = 1;
      u.onend = fin; u.onerror = fin;
      speechSynthesis.speak(u);
      phoneTimer = setTimeout(fin, Math.max(4000, it.text.length * 110));   // some phones never fire onend
    } catch (e) { fin(); }
  }
  function nextLine() {
    var it = queue.shift();
    while (it && it.grp && it.grp.stale && it.grp.stale()) { var g = it.grp; it = queue.shift(); while (it && it.grp === g) it = queue.shift(); }
    curItem = it || null;
    if (!it) { speaking = false; if (storyFor) { storyFor = null; updateStoryBtn(); } return; }
    speaking = true;
    if (it.url) {
      var a = audioEl(); a._item = it; a.src = it.url;
      var p; try { p = a.play(); } catch (e) { p = null; it.fell = true; phoneLine(it); return; }
      if (p && p.catch) p.catch(function (e) { if (!it.fell && !(e && e.name === 'AbortError')) clipFailed(it); });
    } else phoneLine(it);
  }
  function enqueue(items, interrupt, urgent) {
    // a full story gives way to anything else (a direction, a caution, the next stop): the rider can tap it again
    var storyOn = (curItem && curItem.story) || queue.some(function (q) { return q.story; });
    if (interrupt || (storyOn && !(items[0] && items[0].story))) stopSpeech();
    // a direction or warning cuts in over a stop being read out; the stop's line starts again straight after it
    if (urgent && speaking && curItem && curItem.stop) {
      var rest = [curItem].concat(queue).filter(function (q) { return q.stop; }).map(function (q) { return Object.assign({}, q, { retried: false, fell: false }); });
      var other = queue.filter(function (q) { return !q.stop; });
      stopSpeech();
      queue = other.concat(items, rest);
      nextLine();
      return;
    }
    if (urgent) {
      // ahead of any stop lines still waiting
      var at = queue.findIndex(function (q) { return q.stop; });
      if (at < 0) items.forEach(function (it) { queue.push(it); });
      else queue.splice.apply(queue, [at, 0].concat(items));
    } else items.forEach(function (it) { queue.push(it); });
    if (!speaking) nextLine();
  }
  // parts: [{ text, lang }]. All recorded: play the recordings. Otherwise speak with the phone voice,
  // joining parts in the same language so it reads as one sentence.
  var CHIME_URL = 'assets/ding.mp3';
  function speakParts(parts, opts) {
    opts = opts || {};
    parts = parts.filter(function (p) { return p && p.text; });
    if (!parts.length) return;
    var chime = opts.chime && S.chime ? [{ text: '', lang: S.lang, url: CHIME_URL, chime: true, grp: opts.grp }] : [];
    if (!S.voice && !opts.force) { if (chime.length) enqueue(chime, false, true); return; }   // directions off: the ding still marks the turn
    lastSaid = parts.map(function (p) { return p.text; }).join(' ');
    var urls = S.natural ? parts.map(function (p) { return clipFor(p.lang, p.text); }) : [];
    var items, base = { story: !!opts.story, stop: !!opts.stop, grp: opts.grp };
    if (S.natural && urls.every(Boolean)) items = parts.map(function (p, i) { return Object.assign({ text: p.text, lang: p.lang, url: urls[i] }, base); });
    else {
      items = [];
      parts.forEach(function (p) {
        var last = items[items.length - 1];
        if (last && last.lang === p.lang) last.text += (/^(zh|ja)$/.test(p.lang) ? '' : ' ') + p.text;
        else items.push(Object.assign({ text: p.text, lang: p.lang, url: null }, base));
      });
    }
    enqueue(chime.concat(items), opts.interrupt, opts.urgent);
  }
  var lastSaid = '';
  function say(text, opts) {
    opts = opts || {};
    speakParts([{ text: text, lang: opts.lang || S.lang }], opts);
  }
  // A cue or story that has not been translated yet is spoken in English with an English voice.
  function sayContent(english, prefix, opts) {
    var m = R.i18n && R.i18n[S.lang], tr = S.lang === 'en' ? english : (m && m[english]);
    var parts = [].concat(prefix == null ? [] : prefix).map(function (p) { return { text: p, lang: S.lang }; });
    parts.push(tr ? { text: tr, lang: S.lang } : { text: english, lang: 'en' });
    speakParts(parts, opts);
  }
  // The full story of a place (written to be heard), played on a tap. Directions and other stops cut in over it.
  function playStory(s) {
    if (storyFor === s.id) { stopSpeech(); return; }
    stopSpeech();
    var was = S.voice; S.voice = true;
    s.story.forEach(function (p) { sayContent(p, null, { story: true }); });
    S.voice = was;
    storyFor = s.id; updateStoryBtn();
  }
  function updateStoryBtn() {
    var b = document.getElementById('story-btn'); if (!b) return;
    var on = storyFor && storyFor === b.dataset.stop;
    b.querySelector('span').textContent = tu(on ? 'Stop the story' : 'Hear the full story');
    b.classList.toggle('playing', !!on);
  }
  // Save this route's recordings and the common lines to the phone so the voice works with no signal.
  function precacheVoice() {
    if (!R || !navigator.onLine || !S.natural) return;
    var l = S.lang, vm = VOICE[l], urls = [];
    if (!vm) return;
    (R.voice && R.voice[l] || []).forEach(function (h) { urls.push('v/' + vm.tag + '/' + h + '.mp3'); });
    (vm.pre || []).forEach(function (h) { urls.push('v/' + vm.tag + '/' + h + '.mp3'); });
    if (l !== 'en' && VOICE.en && R.voice && R.voice.en) {
      // English recordings for lines not yet translated
      var m = (R.i18n && R.i18n[l]) || {};
      var texts = R.cues.map(function (c) { return c.n; }).concat(R.stops.map(function (x) { return x.name; }), R.stops.map(function (x) { return x.text; }),
        [].concat.apply([], R.stops.map(function (x) { return x.story || []; })));
      texts.forEach(function (t) { if (t && !m[t]) { var u = clipFor('en', t); if (u) urls.push(u); } });
    }
    var stamp = 'rg.vsave.' + R.key + '.' + R.version + '.' + l + '.' + urls.length + '.' + vm.tag;
    if (lsGet(stamp, false)) return;
    fetchAll(urls).then(function (failed) { if (failed < 3) lsSet(stamp, true); });
  }

  // ---------- keeping the phone up to date ----------
  // Recordings live under a folder tag that changes whenever how they are said changes, so a recording saved under an
  // old tag is never played again; clear those out so the phone does not fill up.
  function pruneVoiceCache() {
    if (!window.caches) return;
    var keep = {}; Object.keys(VOICE).forEach(function (l) { keep[VOICE[l].tag] = 1; });
    if (!Object.keys(keep).length) return;
    caches.open('rg-data-v1').then(function (c) {
      return c.keys().then(function (reqs) {
        reqs.forEach(function (q) { var m = /\/v\/([0-9a-f]+)\/[0-9a-f]+\.mp3$/.exec(new URL(q.url).pathname); if (m && !keep[m[1]]) c.delete(q); });
      });
    }).catch(function () {});
  }
  // When the app comes back to the screen (a home screen app can sit in the background for days), and no ride is under
  // way, fetch the latest route and recordings, and load a new version of the app if one has been published.
  // Never during a ride: nothing changes under a rider.
  var lastFresh = Date.now();
  function refreshFromServer() {
    if (!navigator.onLine || ride.active || Date.now() - lastFresh < 10 * 60 * 1000) return;
    lastFresh = Date.now();
    fetch('./', { cache: 'no-cache' }).then(function (r) { return r.ok ? r.text() : ''; }).then(function (html) {
      var m = /app\.js\?v=(\w+)/.exec(html);
      if (m && m[1] !== BUILD && m[1] !== '__BUILD__' && !ride.active) {
        try { sessionStorage.setItem('rg.reopen', R ? R.key : ''); } catch (e) {}
        location.reload();
        return true;
      }
    }).catch(function () {}).then(function (reloading) {
      if (reloading) return;
      fetchJson('voice.json?v=' + BUILD).then(function (m) { setVoiceManifest(m); lsSet('rg.voice', m); pruneVoiceCache(); }).catch(function () {}).then(function () {
        if (!R || ride.active) return;
        var key = R.key, before = JSON.stringify(lsGet('rg.route.' + key, null));
        return fetchJson('r/' + key + '.json').then(function (data) {
          if (ride.active || !R || R.key !== key) return;
          var changed = JSON.stringify(data) !== before;
          storeRoute(key, data);
          if (changed) {
            R = data; R.key = key;
            setRouteClips(); applyRouteSettings(); applyBrand(); applyStaticText();
            addRouteLayers(); addMarkers(); renderRoute(); saveOffline();
          }
          precacheVoice();
        });
      }).catch(function () {});
    });
  }
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'visible') refreshFromServer(); });

  // ---------- wake lock ----------
  var wakeLock = null;
  function wantWake() { return ride.active && !ride.paused && S.wake; }
  function requestWake() {
    if (!wantWake() || !('wakeLock' in navigator) || document.visibilityState !== 'visible') return;
    navigator.wakeLock.request('screen').then(function (l) { wakeLock = l; l.addEventListener('release', function () { wakeLock = null; }); }).catch(function () {});
  }
  function releaseWake() { if (wakeLock) { try { wakeLock.release(); } catch (e) {} wakeLock = null; } }
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'visible') requestWake(); });
  // Back from a locked screen or another app mid ride: say plainly that directions stopped while it was away.
  var hiddenAt = 0;
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') { hiddenAt = Date.now(); return; }
    if (hiddenAt && ride.active && !ride.paused && Date.now() - hiddenAt > 15000) {
      var t = tu('Directions stopped while your phone was locked. Keep this screen open while you ride.');
      banner(t, 'caution', 12000); say(t, { interrupt: true });
    }
    hiddenAt = 0;
  });

  // ---------- riding engine ----------
  var ride = { active: false, zoom: 16, d: 0, locked: false, off: false, offCount: 0, onCount: 0, lastOffSay: 0, follow: true,
    paused: false, cueState: {}, shown: {}, watch: null, fix: null, backCount: 0, lastTouch: Date.now(), sim: null, finished: false };

  function progressKey() { return 'rg.progress.' + R.key; }
  function saveProgress() { lsSet(progressKey(), { d: ride.d, ts: Date.now(), shown: ride.shown, cueState: ride.cueState, version: R.version, paused: ride.paused }); }

  function startRide(resume) {
    ride.active = true; ride.finished = false; ride.follow = true; ride.off = false; ride.offCount = 0; ride.onCount = 0; ride.backCount = 0;
    var p = resume ? lsGet(progressKey(), null) : null;
    ride.prevD = null; ride.saidStart = false; ride.paused = false;
    if (p && p.version === R.version) { ride.d = p.d; ride.shown = p.shown || {}; ride.cueState = p.cueState || {}; ride.locked = false; ride.paused = !!p.paused; }
    else { ride.d = 0; ride.shown = {}; ride.cueState = {}; ride.locked = false; }
    show('ride');
    updateFollowBtn(); updateVoiceBtn();
    // Speaking once inside the tap unlocks speech on iPhone.
    say(ride.paused ? tu('Your ride is paused. Tap Resume when you are ready to keep going.')
      : tu(resume ? 'Welcome back. Picking up where you left off.' : "Let's ride. Follow the line on the map and listen for directions."), { interrupt: true });
    // The browser stops GPS and speech when the phone locks (Ben, 16/10/2026: make this clear to riders)
    if (!ride.paused) say(tu('Keep this screen open while you ride. Locking your phone stops the directions.'));
    updatePauseBtn();
    requestWake();
    startGps();
    renderRide();
    saveProgress();
    ride.zoom = 16;
    if (map) setTimeout(function () { map.jumpTo({ center: ride.fix ? [ride.fix.lng, ride.fix.lat] : pointAt(ride.d), zoom: 16 }); }, 80);
  }
  function endRide() {
    ride.active = false; ride.paused = false; stopGps(); stopSim(); releaseWake(); hideSaver(); updatePauseBtn();
    stopSpeech();
    lsDel(progressKey());
    ride.d = 0; updateDone();
    openRoute();
  }
  // Pause: the rider is taking a break or leaving the route on purpose. Position still shows on the map,
  // but directions, off route warnings, stops, offers and the finish are all held, and the screen may sleep.
  function pauseRide() {
    if (!ride.active || ride.paused) return;
    ride.paused = true; ride.off = false; ride.offCount = 0; ride.onCount = 0;
    stopSpeech();
    say(tu('Ride paused. Directions are off until you tap Resume.'), { interrupt: true });
    releaseWake(); hideSaver(); updatePauseBtn(); renderRide(); saveProgress();
  }
  function resumeRide() {
    if (!ride.active || !ride.paused) return;
    ride.paused = false; ride.off = false; ride.offCount = 0; ride.onCount = 0; ride.backCount = 0; ride.lastTouch = Date.now();
    say(tu('Ride resumed.'), { interrupt: true });
    requestWake(); updatePauseBtn(); renderRide(); saveProgress();
    ride.follow = true; updateFollowBtn();
    if (map && ride.fix) map.easeTo({ center: [ride.fix.lng, ride.fix.lat], zoom: ride.zoom, duration: 600 });
  }
  function updatePauseBtn() {
    var b = $('pause-btn'); if (!b) return;
    b.classList.toggle('resume', !!ride.paused);
    $('pause-label').textContent = ride.paused ? tu('Resume') : tu('Pause');
    $('pause-ico').innerHTML = ride.paused ? '<path d="M7 4l12 8-12 8z"/>' : '<path d="M9 5v14M15 5v14"/>';
  }
  function startGps() {
    stopGps();
    if (!('geolocation' in navigator)) { banner(tu('This phone cannot share its location, so directions will not follow you.'), 'caution'); return; }
    ride.watch = navigator.geolocation.watchPosition(onFix, function (err) {
      if (err.code === 1) banner(tu('Location is turned off for this page. Turn on location for your browser in your phone settings, then reopen the route.'), 'caution', 0);
    }, { enableHighAccuracy: true, maximumAge: 1000, timeout: 20000 });
  }
  function stopGps() { if (ride.watch != null) { try { navigator.geolocation.clearWatch(ride.watch); } catch (e) {} ride.watch = null; } }

  function onFix(pos) {
    if (!ride.active) return;
    var c = pos.coords, acc = c.accuracy || 30;
    ride.fix = { lat: c.latitude, lng: c.longitude, acc: acc, heading: c.heading, speed: c.speed, t: Date.now() };
    updateMe();
    if (ride.paused) { if (ride.follow && map) map.easeTo({ center: [c.longitude, c.latitude], zoom: ride.zoom, duration: 800 }); return; }
    if (acc > 80) return;   // too vague to use
    // single track stretches (R.loose, from the build): hand-drawn lines through twisty trails can sit well off the
    // real trail, so allow more room before "off route" and never call switchbacks "riding backwards"
    var trail = ride.locked && (R.loose || []).some(function (s) { return ride.d >= s[0] && ride.d <= s[1]; });
    var tol = trail ? TRAIL_ROOM : Math.max(CFG.offRoute.metres * 0.7, Math.min(CFG.offRoute.metres, acc + 15));
    var cand = candidates(c.latitude, c.longitude, tol);
    var pick = null;
    if (cand.list.length) {
      var expect = ride.d + 15;
      cand.list.forEach(function (p) {
        var cost = p.d >= ride.d - 30 ? Math.abs(p.d - expect) : (ride.d - p.d) * 4;
        if (!ride.locked && ride.d === 0) cost = p.d;   // first fix: earliest point of the route
        p.cost = cost;
        if (!pick || cost < pick.cost) pick = p;
      });
    }
    if (pick) {
      if (pick.d < ride.d - 60 && !trail) ride.backCount++; else ride.backCount = 0;
      ride.d = pick.d; ride.locked = true;
      ride.offCount = 0;
      if (ride.off) { ride.onCount++; if (ride.onCount >= 2) { ride.off = false; ride.onCount = 0; say(tu('Back on route.'), { interrupt: true }); } }
      if (ride.backCount === 3) say(tu('You may be riding the route backwards. Check the arrows on the line.'));
    } else if (!ride.locked) {
      // not on the route yet: guide to the start instead of calling it "off route"
      var toStart = hav(c.latitude, c.longitude, R.track.lat[0], R.track.lng[0]);
      if (!ride.saidStart) {
        ride.saidStart = true;
        say(fmt(tu('The start of the route is {dist} away. Head to the green marker.'), { dist: distParts(toStart).say }));
        if (toStart > 3000 && !ride.sim) banner(tu('You are a long way from this route.'), 'caution', 12000);
      }
    } else {
      ride.onCount = 0;
      ride.offCount++;
      var away = cand.nearest ? cand.nearest.dist : 0;
      if (!ride.off && ride.offCount >= CFG.offRoute.readings) {
        ride.off = true; ride.lastOffSay = Date.now();
        say(tu("You're off the route. Please use the map on your screen to make your way back to the route line. If you're taking a break, tap Pause."), { interrupt: true });
      } else if (ride.off && Date.now() - ride.lastOffSay > CFG.offRoute.repeatSeconds * 1000) {
        ride.lastOffSay = Date.now();
        say(fmt(tu("You're still off the route. The route line is {dist} away."), { dist: distParts(away).say }));
      }
      ride.offAway = away;
    }
    checkCues(); checkStops(); checkOffers(); checkFinish();
    renderRide();
    if (ride.follow && map) map.easeTo({ center: [c.longitude, c.latitude], zoom: ride.zoom, duration: 800 });
    saveProgress();
    saverTick();
  }

  function nextCueIndex() {
    for (var i = 0; i < R.cues.length; i++) if (R.cues[i].d > ride.d - 8 && !(ride.cueState[i] >= 2 && R.cues[i].d < ride.d + 5)) return i;
    return -1;
  }
  function checkCues() {
    if (ride.off || !ride.locked) return;
    // a cue passed between two fixes (fast riding or a slow GPS) is still announced if it was only just passed
    var prev = ride.prevD == null ? ride.d : ride.prevD;
    ride.prevD = ride.d;
    R.cues.forEach(function (c, k) {
      if ((ride.cueState[k] || 0) >= 2 || c.d > ride.d - 8 || c.d < prev - 8) return;
      ride.cueState[k] = 2;
      // on single track the position can jump forward when the rider comes back onto the drawn line: still say the turn
      var late = (R.loose || []).some(function (s) { return c.d >= s[0] && c.d <= s[1]; }) ? 150 : 45;
      if (ride.d - c.d < late) turnCall(c, k);
    });
    var i = nextCueIndex(); if (i < 0) return;
    var c = R.cues[i], dist = c.d - ride.d, st = ride.cueState[i] || 0;
    var prevD = i > 0 ? R.cues[i - 1].d : -1000;
    var danger = c.t === 'danger';
    var A = CFG.announce, prepAt = danger ? A.cautionWarningMetres : A.firstWarningMetres;
    if (c.after && st < 1 && dist <= prepAt && dist > A.turnMetres + 25) { ride.cueState[i] = 1; return; }   // a turn around at a stop: no early warning
    if (st < 1 && dist <= prepAt && dist > A.turnMetres + 25 && (c.d - prevD) > A.skipFirstWarningIfCuesCloserThanMetres) {
      ride.cueState[i] = 1;
      var said = Math.max(dist, 20);
      var pre = fmt(tu('In {dist},'), { dist: distParts(said).say });
      // dropped if, by the time it would be spoken, the distance is well out or the turn is close (the turn call covers it)
      var grp = { stale: function () { var left = c.d - ride.d; return (ride.cueState[i] || 0) >= 2 || left <= A.turnMetres + 10 || Math.abs(said - left) > Math.max(40, said * 0.35); } };
      sayContent(c.n, danger ? [tu('Caution.'), pre] : pre, { urgent: true, grp: grp });
    } else if (st < 2 && dist <= A.turnMetres) {
      ride.cueState[i] = 2;
      // turning around at a stop: read the stop first, so the turn around is the next thing the rider hears
      if (c.after && !ride.shown[c.after]) { var at = R.stops.filter(function (x) { return x.id === c.after; })[0]; if (at) announceStop(at); }
      turnCall(c, i);
      var nx = R.cues[i + 1];
      if (nx && !nx.after && nx.d - c.d < A.mergeNextCueWithinMetres) { ride.cueState[i + 1] = 1; sayContent(nx.n, tu('Then'), { urgent: true }); }
    }
  }
  // At the turn: a soft ding, then the "here" version of the direction ("Turn right here onto Flynn Road."). A language
  // without a translation of the "here" version says the direction as written. Dropped if the rider is already well past.
  function turnLine(c) {
    if (!c.h) return c.n;
    if (S.lang === 'en') return c.h;
    var m = R.i18n && R.i18n[S.lang];
    return m && m[c.h] ? c.h : c.n;
  }
  function turnCall(c, i) {
    var danger = c.t === 'danger';
    var grp = { stale: function () { return ride.d - c.d > 40; } };
    // the ding marks a turn: not the opening line, a finish line or a note
    var turn = !danger && (!!c.h || (c.t && c.t !== 'generic'));
    sayContent(danger ? c.n : turnLine(c), danger ? tu('Caution.') : null, { urgent: true, chime: turn, grp: grp });
    return grp;
  }
  var FACILITY = { toilet: 1, food: 1, drink: 1, service: 1 };   // on the map and in the Stops list, never popped up or spoken
  var TRAIL_ROOM = 150;   // metres from the line allowed on single track before "off route" (15/10/2026)
  function checkStops() {
    if (!ride.fix) return;
    R.stops.forEach(function (s) {
      if (FACILITY[s.kind] || s.kind === 'finish') return;
      var near = hav(ride.fix.lat, ride.fix.lng, s.lat, s.lng);
      var cw = CFG.stops.cautionWarningMetres, tr = CFG.stops.triggerMetres;
      var key = s.id, trigger = false;
      if (s.kind === 'caution') {
        // a caution is read on each pass the build chose (s.ds: every pass, or only the downhill ones for a hill warning)
        (s.ds || [s.d]).forEach(function (d, k) {
          var kk = k ? s.id + ':' + k : s.id;
          if (!trigger && !ride.shown[kk] && d - ride.d < cw && d - ride.d > -30 && near < cw + 50) { trigger = true; key = kk; }
        });
      } else if (!ride.shown[s.id]) {
        var along = Math.abs(s.d - ride.d);   // s.d is the one pass this stop is read on
        trigger = s.off ? (along < 40 && s.off < 1000)      // a stop off the route: show it as the rider passes the nearest point
          : (near < tr && along < tr * 2);
      }
      if (!trigger) return;
      ride.shown[key] = 1;
      if (s.kind === 'caution') {
        // a caution with notes (ferry, beach access) opens its card so the notes are on screen, even over another stop
        banner(tc(s.name), 'caution', 12000, s.text ? function () { openStop(s); } : null);
        if (s.text) openStop(s, true);
        sayContent(s.name, tu('Caution.'), { urgent: true });
        if (s.text) sayContent(s.text, null, { stop: true });   // a warning's details are always read, even with stop stories turned off; a direction can cut in
      } else announceStop(s);
    });
  }
  function announceStop(s) {
    ride.shown[s.id] = 1;
    var poi = !s.plain && s.kind !== 'turn';
    // Point of interest stories off: points of interest are not announced at all, no card and nothing spoken. They stay
    // on the map and in the Stops list. Welcome or briefing pins and turnarounds are not points of interest and are
    // always read; cautions never come here (Ben, 15/10/2026).
    if (poi && !S.stories) return;
    if (!sheetOpen()) openStop(s, true);
    // welcome pins and turnarounds are read as they are; other stops get "You have reached a point of interest."
    if (poi) say(tu('You have reached a point of interest.'), { stop: true });
    sayContent(s.name, null, { stop: true });
    if (s.text) sayContent(s.text, null, { stop: true });
  }
  // A short pop-up over the current screen, closed with OK or a tap outside it
  function notice(title, paras) {
    var old = document.getElementById('notice'); if (old) old.remove();
    var ov = el('div', { class: 'notice-scrim', id: 'notice' });
    var card = el('div', { class: 'notice', role: 'alertdialog', 'aria-modal': 'true', 'aria-labelledby': 'notice-title' });
    card.appendChild(el('h3', { id: 'notice-title', text: title }));
    paras.forEach(function (p) { card.appendChild(el('p', { text: p })); });
    var ok = el('button', { class: 'btn primary full', type: 'button', text: tu('OK') });
    function close() { ov.remove(); }
    ok.addEventListener('click', close);
    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
    card.appendChild(ok); ov.appendChild(card); document.body.appendChild(ov);
    setTimeout(function () { ok.focus(); }, 50);
  }
  function explainStories() {
    if (S.stories) notice(tu('Point of interest stories on'), [
      tu('As you reach each point of interest, its card opens and you hear its name and a short overview.'),
      tu('Want more? Tap Hear the full story on the card, where there is one, for the longer story of that place.'),
      tu('Directions and safety warnings are always spoken.')]);
    else notice(tu('Point of interest stories off'), [
      tu('Points of interest are no longer announced: no card pops up and nothing is read out as you pass them.'),
      tu('They stay on the map and in the Stops list. Tap one any time to read about it or hear its story.'),
      tu('Directions and safety warnings are still spoken.')]);
  }
  function checkOffers() {
    if (!ride.fix) return;
    offerPlaces().forEach(function (g) {
      var o = g[0], id = 'offer-' + o.id;
      if (o.fin) {
        // for the end of the ride: brought up in the last 1.5 km, never at the start
        if (ride.shown[id] || R.distance - ride.d > 1500 || ride.d < R.distance * 0.5) return;
        ride.shown[id] = 1; ride.shown.finOffers = 1; addMarkers();
        banner(fmt(tu('Rider offer when you get back: {name}'), { name: o.partner }), 'offer', 15000, function () { openOffers(g); });
        say(fmt(tu('Rider offer when you get back: {name}'), { name: o.partner }));
        return;
      }
      if (ride.shown[id] || o.d == null || o.d < 300) return;
      if (hav(ride.fix.lat, ride.fix.lng, o.lat, o.lng) < 150) {
        ride.shown[id] = 1;
        banner(fmt(tu('Rider offer nearby: {name}'), { name: o.partner }), 'offer', 15000, function () { openOffers(g); });
        say(fmt(tu('Rider offer nearby: {name}'), { name: o.partner }));
      }
    });
  }
  function checkFinish() {
    if (ride.finished || R.distance - ride.d > 40 || ride.d < R.distance * 0.6) return;
    ride.finished = true;
    say(tu('You have finished the ride. Thanks for riding with us.'), { interrupt: true });
    var f = R.stops.filter(function (s) { return s.kind === 'finish'; })[0];
    openFinish(f);
    lsDel(progressKey());
  }

  // ---------- ride rendering ----------
  function renderRide() {
    if (!R) return;
    var card = $('cue-card');
    var rem = Math.max(0, R.distance - ride.d);
    $('remain').innerHTML = '';
    $('remain').appendChild(document.createTextNode(distText(rem) + ' '));
    $('remain').appendChild(el('span', { style: 'font-size:15px;font-weight:600;color:var(--muted)', text: tu('to go') }));
    $('remain-sub').textContent = fmt(tu('About {time} at an easy pace'), { time: timeText(rem / (SPEED[R.activity] || SPEED.ebike)) });
    $('progress-bar').style.width = Math.min(100, ride.d / R.distance * 100).toFixed(1) + '%';
    card.classList.remove('off', 'done');
    var i = nextCueIndex();
    card.classList.remove('paused');
    if (ride.paused) {
      card.classList.add('paused');
      $('cue-icon').innerHTML = svg('pause');
      $('cue-dist').textContent = tu('Ride paused');
      $('cue-text').textContent = tu('Directions and off route warnings are off. Tap Resume when you are ready to keep going.');
      $('cue-next-text').textContent = '';
    } else if (ride.off) {
      card.classList.add('off');
      $('cue-icon').innerHTML = svg('danger');
      $('cue-dist').textContent = tu('Off route');
      $('cue-text').textContent = fmt(tu('Use the map to make your way back to the route line. It is {dist} away. Taking a break? Tap Pause.'), { dist: distText(ride.offAway || 0) });
      $('cue-next-text').textContent = '';
    } else if (!ride.locked && ride.fix) {
      var st = hav(ride.fix.lat, ride.fix.lng, R.track.lat[0], R.track.lng[0]);
      $('cue-icon').innerHTML = svg('pin');
      $('cue-dist').textContent = distText(st);
      $('cue-text').textContent = tu('Head to the start of the route, shown by the green marker.');
      $('cue-next-text').textContent = '';
    } else if (!ride.fix) {
      $('cue-icon').innerHTML = svg('pin');
      $('cue-dist').textContent = '';
      $('cue-text').textContent = tu('Finding your location');
      $('cue-next-text').textContent = '';
    } else if (i < 0 || ride.finished) {
      card.classList.add('done');
      $('cue-icon').innerHTML = svg('finish');
      $('cue-dist').textContent = distText(rem);
      $('cue-text').textContent = tu('Follow the line to the finish.');
      $('cue-next-text').textContent = '';
    } else {
      var c = R.cues[i];
      $('cue-icon').innerHTML = svg(cueIcon(c.t));
      $('cue-dist').textContent = distText(Math.max(0, c.d - ride.d));
      $('cue-text').textContent = tc(c.n);
      var nx = R.cues[i + 1];
      $('cue-next-text').textContent = nx ? fmt(tu('Then: {text}'), { text: tc(nx.n) }) + ' (' + distText(nx.d - c.d) + ')' : tu('Then: the finish');
    }
    updateDone();
    updateSaverText();
    updateViewerCue();
  }
  var doneTimer = 0;
  function updateDone() {
    if (!map || !mapReady || !map.getSource('done')) return;
    var now = Date.now(); if (now - doneTimer < 1500 && ride.d > 0) return; doneTimer = now;
    map.getSource('done').setData(routeGeo(0, ride.d));
  }
  function updateMe() {
    if (!map || !ride.fix) return;
    if (!meMarker) { var e = el('div', { class: 'me' }); meMarker = new maplibregl.Marker({ element: e }).setLngLat([ride.fix.lng, ride.fix.lat]).addTo(map); }
    meMarker.setLngLat([ride.fix.lng, ride.fix.lat]);
    var me = meMarker.getElement();
    if (ride.fix.heading != null && !isNaN(ride.fix.heading) && (ride.fix.speed || 0) > 1) { me.classList.add('heading'); me.style.setProperty('--hd', ride.fix.heading + 'deg'); }
    else me.classList.remove('heading');
  }
  function updateFollowBtn() { $('btn-follow').classList.toggle('on', ride.follow); }
  function updateVoiceBtn() { var b = $('btn-voice'); b.innerHTML = svg(S.voice ? 'vol' : 'mute'); b.classList.toggle('on', S.voice); b.setAttribute('aria-pressed', S.voice); }

  var bannerTimer = 0;
  function banner(text, kind, ms, onTap) {
    var b = $('banner');
    b.className = 'banner' + (kind === 'offer' ? ' offer' : kind === 'info' ? ' info' : '');
    b.innerHTML = svg(kind === 'offer' ? 'offer' : kind === 'info' ? 'info' : 'caution');
    b.appendChild(el('span', { text: text }));
    b.hidden = false;
    b.onclick = function () { b.hidden = true; if (onTap) onTap(); };
    b.setAttribute('role', onTap ? 'button' : 'status');
    clearTimeout(bannerTimer);
    if (ms !== 0) bannerTimer = setTimeout(function () { b.hidden = true; }, ms || 10000);
    wakeSaver();
  }

  // ---------- battery saver ----------
  function saverTick() {
    if (!S.saver || !ride.active || ride.paused) { hideSaver(); return; }
    var i = nextCueIndex(), dist = i >= 0 ? R.cues[i].d - ride.d : 9999;
    if (dist < CFG.screen.wakeBeforeTurnMetres || ride.off || sheetOpen() || !$('viewer').hidden || Date.now() - ride.lastTouch < CFG.screen.blackoutAfterSeconds * 1000) hideSaver();
    else $('saver').hidden = false;
  }
  function updateSaverText() {
    if ($('saver').hidden) return;
    $('saver-dist').textContent = $('cue-dist').textContent;
    $('saver-text').textContent = $('cue-text').textContent;
  }
  function hideSaver() { $('saver').hidden = true; }
  function wakeSaver() { ride.lastTouch = Date.now(); hideSaver(); }

  // ---------- sheets ----------
  // small non-interactive map used on offer cards: the route line and where the offer is
  var miniMap = null;
  function dropMiniMap() { if (miniMap) { try { miniMap.remove(); } catch (e) {} miniMap = null; } }
  function addMiniMap(box, o) {
    if (!window.maplibregl) { box.remove(); return; }
    dropMiniMap();
    var T = R.track, b = new maplibregl.LngLatBounds();
    for (var i = 0; i < T.lat.length; i += 5) b.extend([T.lng[i], T.lat[i]]);
    b.extend([o.lng, o.lat]);
    try {
      miniMap = new maplibregl.Map({ container: box, style: STYLE, interactive: false, attributionControl: { compact: true },
        bounds: b, fitBoundsOptions: { padding: 22, maxZoom: 15 } });
    } catch (e) { box.remove(); return; }
    miniMap.on('load', function () {
      Array.prototype.forEach.call(box.querySelectorAll('.maplibregl-compact-show'), function (n) { n.classList.remove('maplibregl-compact-show'); n.removeAttribute('open'); });
      miniMap.addSource('route', { type: 'geojson', data: routeGeo(0, R.distance) });
      miniMap.addLayer({ id: 'casing', type: 'line', source: 'route', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': '#ffffff', 'line-width': 6 } });
      miniMap.addLayer({ id: 'line', type: 'line', source: 'route', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': R.brand.colors.line, 'line-width': 3.5 } });
    });
    new maplibregl.Marker({ element: el('div', { class: 'mk offer' }, svg('offer')) }).setLngLat([o.lng, o.lat]).addTo(miniMap);
  }
  function sheetOpen() { return !$('sheet').hidden; }
  function openSheet(build, cls) {
    dropMiniMap();
    var body = $('sheet-body'); body.innerHTML = ''; body.className = 'sheet-body' + (cls ? ' ' + cls : '');
    build(body);
    $('sheet').hidden = false; $('scrim').hidden = false;
    body.scrollTop = 0;
    hideSaver();
    setTimeout(function () { $('sheet-close').focus(); }, 50);
  }
  function closeSheet() { dropMiniMap(); $('sheet').hidden = true; $('scrim').hidden = true; if (ride.keepOpen) { ride.keepOpen = false; scrubUrl(); } }

  function linkRow(href, label, icon, frame) {
    var a = el('a', { class: 'linkrow needs-net', href: href, target: '_blank', rel: 'noopener' });
    if (frame) a.addEventListener('click', function (e) {
      e.preventDefault();
      if (a.dataset.checking) return;
      // phones can say they are online with no real signal: check the page can be reached before opening it
      a.dataset.checking = '1'; a.classList.add('checking');
      canReach(href).then(function (ok) {
        delete a.dataset.checking; a.classList.remove('checking');
        if (ok) openViewer(href);
        else { a.classList.add('no-net'); noSignal(); }
      });
    });
    var lab = el('span', { class: 'lr-label' });
    lab.appendChild(el('span', { text: label }));
    lab.appendChild(el('small', { class: 'net-note', text: tu('Needs mobile signal') }));
    lab.appendChild(el('small', { class: 'net-check', text: tu('Checking for signal...') }));
    a.appendChild(lab); a.insertAdjacentHTML('beforeend', svg(icon || 'ext'));
    if (!navigator.onLine) a.classList.add('no-net');
    return a;
  }
  // ---------- no signal (Ben, 16/10/2026): pages that need signal are greyed out, and nothing a rider taps ever
  // takes them out of the ride ----------
  function canReach(url) {
    if (!navigator.onLine) return Promise.resolve(false);
    return new Promise(function (resolve) {
      var done = false, t = setTimeout(function () { if (!done) { done = true; resolve(false); } }, 4000);
      try {
        fetch(url, { method: 'HEAD', mode: 'no-cors', cache: 'no-store' }).then(function () { if (!done) { done = true; clearTimeout(t); resolve(true); } })
          .catch(function () { if (!done) { done = true; clearTimeout(t); resolve(false); } });
      } catch (e) { done = true; clearTimeout(t); resolve(false); }
    });
  }
  function noSignal() { banner(tu('No signal here. This page needs mobile signal. Your ride carries on.'), 'info', 6000); }
  function markNet() {
    var off = !navigator.onLine;
    Array.prototype.forEach.call(document.querySelectorAll('.needs-net'), function (a) { a.classList.toggle('no-net', off); });
    if (off && !$('viewer').hidden) viewerOffline(true);
    if (!off) viewerOffline(false);
  }
  window.addEventListener('online', markNet);
  window.addEventListener('offline', markNet);
  // any web link tapped with no signal stays in the app instead of opening a browser error page
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href^="http"]') : null;
    if (!a || navigator.onLine) return;
    e.preventDefault(); e.stopPropagation(); a.classList.add('no-net'); noSignal();
  }, true);
  function openStop(s, auto) {
    openSheet(function (b) {
      if (s.photos && s.photos.length) {
        var strip = el('div', { class: 'photo-strip' });
        s.photos.forEach(function (u) { strip.appendChild(el('img', { src: u, alt: '', loading: 'lazy' })); });
        b.appendChild(strip);
      }
      b.appendChild(el('div', { class: 'kicker', text: kindLabel(s.kind) + (s.d > 0 ? '  ·  ' + distText(s.d) : '') }));
      b.appendChild(el('h2', { id: 'sheet-title', text: tc(s.name) }));
      if (s.text) b.appendChild(el('p', { text: tc(s.text) }));
      var acts = el('div', { class: 'sheet-actions' });
      if (s.text || s.name) {
        var listen = el('button', { class: 'btn primary full', type: 'button' }, svg('vol') + '<span></span>');
        listen.querySelector('span').textContent = tu('Listen');
        listen.addEventListener('click', function () { stopSpeech(); var was = S.voice; S.voice = true; sayContent(s.name); if (s.text) sayContent(s.text); S.voice = was; });
        acts.appendChild(listen);
      }
      if (s.story && s.story.length) {
        var sb = el('button', { class: 'btn outline full story-btn', type: 'button', id: 'story-btn' }, svg('vol') + '<span></span>');
        sb.dataset.stop = s.id;
        sb.addEventListener('click', function () { playStory(s); });
        acts.appendChild(sb);
        setTimeout(updateStoryBtn, 0);
      }
      var u = safeUrl(s.url);
      if (u) acts.appendChild(linkRow(u, /review|g\.page/i.test(u) ? tu('Leave us a review') : /surfline|tide/i.test(u) ? tu('Check the tide times') : tu('More about this place'), /review|g\.page/i.test(u) ? 'star' : 'ext', s.frame));
      var back = el('button', { class: 'btn outline full', type: 'button', text: ride.active ? tu('Back to my ride') : tu('Close') });
      back.addEventListener('click', closeSheet);
      acts.appendChild(back);
      b.appendChild(acts);
    });
  }
  function kindLabel(k) {
    return tu({ caution: 'Take care', view: 'Lookout', toilet: 'Toilets', food: 'Food and drink', park: 'Park', turn: 'Turnaround point', drink: 'Food and drink', service: 'Facilities', finish: 'Finish' }[k] || 'Point of interest');
  }
  function openOffer(o) {
    openSheet(function (b) {
      var v = el('div', { class: 'voucher' });
      var card = el('div', { class: 'v-card' });
      var mbox = el('div', { class: 'v-map' }); card.appendChild(mbox);
      var top = el('div', { class: 'v-top' });
      if (o.logo) {
        var lg = el('img', { class: 'v-logo', src: o.logo, alt: o.partner });
        lg.addEventListener('error', function () { lg.replaceWith(el('div', { class: 'v-partner', text: o.partner })); });
        top.appendChild(lg);
      } else top.appendChild(el('div', { class: 'v-partner', text: o.partner }));
      top.appendChild(el('h2', { id: 'sheet-title', class: 'v-head', text: tc(o.headline) }));
      if (o.alt) top.appendChild(el('div', { class: 'v-alt', text: tc(o.alt) }));
      if (o.about) top.appendChild(el('p', { class: 'v-about', text: tc(o.about) }));
      card.appendChild(top);
      card.appendChild(el('div', { class: 'v-tear' }, '<span></span>'));
      var rows = el('div', { class: 'v-rows' });
      if (o.how) rows.appendChild(el('div', { class: 'v-how', text: tc(o.how) }));
      if (o.conditions) {
        var cr = el('div', { class: 'v-conds' });
        cr.appendChild(el('div', { class: 'v-conds-k', text: tu('Conditions') }));
        [].concat(o.conditions).forEach(function (c) { cr.appendChild(el('div', { class: 'v-cond', text: tc(c) })); });
        rows.appendChild(cr);
      }
      if (o.address) { var r2 = el('div', { class: 'v-row' }, '<span></span><span></span>'); r2.firstChild.textContent = tu('Where'); r2.lastChild.textContent = o.address; rows.appendChild(r2); }
      if (o.validUntil) { var r3 = el('div', { class: 'v-row' }, '<span></span><span></span>'); r3.firstChild.textContent = tu('Valid until'); r3.lastChild.textContent = new Date(o.validUntil + 'T00:00:00').toLocaleDateString(S.lang); rows.appendChild(r3); }
      card.appendChild(rows);
      v.appendChild(el('div', { class: 'kicker', style: 'color:var(--accent);text-align:center;padding:0 52px 10px', text: tu('Rider offer') }));
      v.appendChild(card);
      b.appendChild(v);
      var acts = el('div', { class: 'sheet-actions' });
      var showMap = el('button', { class: 'btn primary full', type: 'button' }, svg('pin') + '<span></span>');
      showMap.querySelector('span').textContent = tu('Show on the map');
      showMap.addEventListener('click', function () { closeSheet(); if (map) { ride.follow = false; updateFollowBtn(); map.easeTo({ center: [o.lng, o.lat], zoom: 16 }); } });
      acts.appendChild(showMap);
      if (o.phone) {
        var call = el('a', { class: 'btn outline full', href: 'tel:' + String(o.phone).replace(/[^+0-9]/g, '') }, svg('phone') + '<span></span>');
        call.querySelector('span').textContent = fmt(tu('Call {name}'), { name: o.partner });
        acts.appendChild(call);
      }
      var u = safeUrl(o.url); if (u) acts.appendChild(linkRow(u, fmt(tu('Visit {name}'), { name: o.partner }), 'ext', o.frame));
      b.appendChild(acts);
      setTimeout(function () { addMiniMap(mbox, o); }, 30);
    });
  }
  // Finish: how was your ride? Every rider can reach the review links (Google does not allow asking only happy
  // customers); a rider who was not happy is first offered a direct way to tell us.
  var FACES = {
    good: '<circle cx="12" cy="12" r="9.5"/><path d="M8 14.5c1 1.4 2.4 2 4 2s3-.6 4-2"/><path d="M9 9.5v.5M15 9.5v.5"/>',
    ok: '<circle cx="12" cy="12" r="9.5"/><path d="M8.5 15h7"/><path d="M9 9.5v.5M15 9.5v.5"/>',
    bad: '<circle cx="12" cy="12" r="9.5"/><path d="M8 16.5c1-1.4 2.4-2 4-2s3 .6 4 2"/><path d="M9 9.5v.5M15 9.5v.5"/>'
  };
  function reviewLinks(box) {
    var rv = (R.brand && R.brand.reviews) || {};
    var g = safeUrl(rv.google), t = safeUrl(rv.tripadvisor);
    if (g) box.appendChild(linkRow(g, tu('Review us on Google'), 'star'));
    if (t) box.appendChild(linkRow(t, tu('Review us on Tripadvisor'), 'star'));
    return !!(g || t);
  }
  function openFinish(f) {
    var key = 'rg.rating.' + R.key + '.' + R.version;
    openSheet(function (b) {
      b.appendChild(el('div', { class: 'kicker', text: tu('Finish') }));
      b.appendChild(el('h2', { id: 'sheet-title', text: tu('You made it. Thanks for riding with us.') }));
      var fo = R.offers.slice();   // every rider offer again at the finish (Ben, 16/10/2026)
      var area = el('div', { class: 'rate' });
      b.appendChild(area);
      function ask() {
        area.innerHTML = '';
        area.appendChild(el('div', { class: 'rate-q', text: tu('How was your ride?') }));
        var row = el('div', { class: 'rate-faces' });
        [['good', tu('Loved it')], ['ok', tu('It was OK')], ['bad', tu('Not great')]].forEach(function (x) {
          var bt = el('button', { class: 'face ' + x[0], type: 'button' }, '<svg viewBox="0 0 24 24" aria-hidden="true">' + FACES[x[0]] + '</svg><span></span>');
          bt.querySelector('span').textContent = x[1];
          bt.addEventListener('click', function () { lsSet(key, x[0]); answer(x[0]); });
          row.appendChild(bt);
        });
        area.appendChild(row);
      }
      function answer(r) {
        area.innerHTML = '';
        if (r === 'good') {
          area.appendChild(el('div', { class: 'rate-q', text: tu('Thanks, we are so glad you enjoyed it!') }));
          area.appendChild(el('p', { text: tu('We would really love a review. It only takes a minute and helps other riders find us.') }));
          var lk = el('div', { class: 'sheet-actions' }); reviewLinks(lk); area.appendChild(lk);
        } else {
          area.appendChild(el('div', { class: 'rate-q', text: tu('Thanks for telling us.') }));
          area.appendChild(el('p', { text: tu('We would love to hear what we could do better, so we can put it right.') }));
          var c = el('div', { class: 'sheet-actions' });
          var em = R.brand && R.brand.email;
          if (em) {
            var subj = fmt(tu('Feedback on {ride}'), { ride: tc(R.name) });
            var mail = el('a', { class: 'btn primary full', href: 'mailto:' + em + '?subject=' + encodeURIComponent(subj) }, svg('ext') + '<span></span>');
            mail.querySelector('span').textContent = tu('Email us');
            c.appendChild(mail);
          }
          if (R.brand && R.brand.phoneHref) {
            var call = el('a', { class: 'btn outline full', href: R.brand.phoneHref }, svg('phone') + '<span></span>');
            call.querySelector('span').textContent = fmt(tu('Call us on {phone}'), { phone: R.brand.phone });
            c.appendChild(call);
          }
          area.appendChild(c);
          var more = el('div', { class: 'rate-more' });
          more.appendChild(el('div', { class: 'rate-small', text: tu('You can also leave a review.') }));
          if (reviewLinks(more)) area.appendChild(more);
        }
        var again = el('button', { class: 'rate-change', type: 'button', text: tu('Change my answer') });
        again.addEventListener('click', ask);
        area.appendChild(again);
      }
      var prev = lsGet(key, null);
      if (prev) answer(prev); else ask();
      if (fo.length) {
        b.appendChild(el('div', { class: 'kicker', text: tu('Before you go') }));
        fo.forEach(function (o) { b.appendChild(offerStrip(o)); });
      }
      var acts = el('div', { class: 'sheet-actions' });
      var end = el('button', { class: 'btn outline full', type: 'button', text: tu('End ride') });
      end.addEventListener('click', function () { closeSheet(); endRide(); });
      acts.appendChild(end);
      b.appendChild(acts);
    });
  }
  function openCues() {
    openSheet(function (b) {
      b.appendChild(el('h2', { id: 'sheet-title', text: tu('Directions') }));
      var list = el('div', { class: 'list' }), cur = ride.active ? nextCueIndex() : -1, curEl = null;
      R.cues.forEach(function (c, i) {
        var it = el('div', { class: 'list-item' + (ride.active && i < cur ? ' past' : '') + (i === cur ? ' current' : '') });
        it.appendChild(el('div', { class: 'cue-li-icon' + (c.t === 'danger' ? ' danger' : '') }, svg(cueIcon(c.t))));
        var m = el('div', { class: 'li-main' }); m.appendChild(el('div', { class: 'li-title', text: tc(c.n) })); it.appendChild(m);
        it.appendChild(el('div', { class: 'li-dist', text: distText(c.d) }));
        list.appendChild(it); if (i === cur) curEl = it;
      });
      b.appendChild(list);
      if (curEl) setTimeout(function () { curEl.scrollIntoView({ block: 'center' }); }, 60);
    });
  }
  function openStops() {
    openSheet(function (b) {
      b.appendChild(el('h2', { id: 'sheet-title', text: tu('Stops') }));
      var list = el('div', { class: 'list' });
      R.stops.filter(function (s) { return (s.kind !== 'caution' || s.text) && s.kind !== 'finish'; }).forEach(function (s) {
        var it = el('button', { class: 'list-item', type: 'button' });
        it.appendChild(el('div', { class: 'li-icon' }, svg(s.kind)));
        var m = el('div', { class: 'li-main' }); m.appendChild(el('div', { class: 'li-title', text: tc(s.name) }));
        m.appendChild(el('div', { class: 'li-sub', text: kindLabel(s.kind) })); it.appendChild(m);
        it.appendChild(el('div', { class: 'li-dist', text: distText(s.d) }));
        it.addEventListener('click', function () { openStop(s); });
        list.appendChild(it);
      });
      b.appendChild(list);
    });
  }
  // offers grouped by partner and place, so a partner with two offers gets one map marker and one nearby alert
  function offerPlaces() {
    var g = {};
    R.offers.forEach(function (o) { var k = o.partner + '|' + o.lat.toFixed(4) + '|' + o.lng.toFixed(4); (g[k] = g[k] || []).push(o); });
    return Object.keys(g).map(function (k) { return g[k]; });
  }
  function offerStrip(o) {
    var b = el('button', { class: 'offer-strip', type: 'button' });
    b.appendChild(el('div', { class: 'os-icon' }, svg('offer')));
    var m = el('div');
    m.appendChild(el('div', { class: 'os-k', text: tu('Rider offer') }));
    m.appendChild(el('div', { class: 'os-t', text: o.partner + ': ' + tc(o.headline) }));
    m.appendChild(el('div', { class: 'os-s', text: tu('Tap to see how to claim it') }));
    b.appendChild(m);
    b.addEventListener('click', function () { openOffer(o); });
    return b;
  }
  function openOffers(list) {
    var offers = Array.isArray(list) ? list : R.offers;
    if (offers.length === 1) return openOffer(offers[0]);
    openSheet(function (b) {
      b.appendChild(el('h2', { id: 'sheet-title', text: tu('Rider offers') }));
      var list = el('div', { class: 'list' });
      if (!offers.length) b.appendChild(el('p', { text: tu('There are no rider offers on this route.') }));
      offers.forEach(function (o) {
        var it = el('button', { class: 'list-item', type: 'button' });
        it.appendChild(o.logo ? el('img', { class: 'li-logo', src: o.logo, alt: '' }) : el('div', { class: 'li-icon' }, svg('offer')));
        var m = el('div', { class: 'li-main' }); m.appendChild(el('div', { class: 'li-title', text: tc(o.headline) }));
        m.appendChild(el('div', { class: 'li-sub', text: o.fin ? o.partner + '  \u00b7  ' + tu('When you get back') : o.partner })); it.appendChild(m);
        it.addEventListener('click', function () { openOffer(o); });
        list.appendChild(it);
      });
      b.appendChild(list);
    });
  }
  function openSettings() {
    openSheet(function (b) {
      b.appendChild(el('h2', { id: 'sheet-title', text: tu('Settings') }));
      function group(label) { var g = el('div', { class: 'set-group' }); g.appendChild(el('div', { class: 'set-label', text: label })); b.appendChild(g); return g; }
      function seg(g, opts, val, onPick) {
        var s = el('div', { class: 'seg' });
        opts.forEach(function (o) {
          var bt = el('button', { type: 'button', 'aria-pressed': String(o[0] === val), text: o[1] });
          bt.addEventListener('click', function () { onPick(o[0]); openSettings(); });
          s.appendChild(bt);
        });
        g.appendChild(s);
      }
      seg(group(tu('Units')), [['metric', tu('Metric (km)')], ['imperial', tu('Imperial (miles)')]], S.units, function (v) { S.units = v; saveSettings('units'); refreshAll(); });
      var lg = group(tu('Language')), grid = el('div', { class: 'lang-grid' });
      LANGS.forEach(function (l) {
        var bt = el('button', { type: 'button', 'aria-pressed': String(l[0] === S.lang), lang: l[0], text: l[1] });
        bt.addEventListener('click', function () { S.lang = l[0]; saveSettings('lang'); refreshAll(); precacheVoice(); openSettings(); });
        grid.appendChild(bt);
      });
      lg.appendChild(grid);
      if (S.lang !== 'en' && !(S.natural && VOICE[S.lang]) && !pickVoice(S.lang) && voices.length) lg.appendChild(el('p', { class: 'note', text: tu('This phone has no voice for this language, so directions are shown on screen and spoken in English.') }));
      var vg = group(tu('Voice and screen')), cl = el('div', { class: 'card-list' });
      function toggle(title, sub, key, after) {
        var row = el('div', { class: 'toggle-row' }), t = el('div');
        t.appendChild(el('div', { class: 'tr-t', text: title })); if (sub) t.appendChild(el('div', { class: 'tr-s', text: sub }));
        var sw = el('button', { class: 'switch', type: 'button', 'aria-pressed': String(!!S[key]), 'aria-label': title });
        sw.addEventListener('click', function () { S[key] = !S[key]; if (key === 'stories') saveStoryPick(); else saveSettings(key); sw.setAttribute('aria-pressed', String(S[key])); if (after) after(); });
        row.appendChild(t); row.appendChild(sw); cl.appendChild(row);
      }
      toggle(tu('Spoken directions'), null, 'voice', updateVoiceBtn);
      toggle(tu('Natural voice'), tu("Clearer recorded voice. Turn off to use your phone's own voice."), 'natural', function () { stopSpeech(); precacheVoice(); });
      toggle(tu('Chime at turns'), tu('A short ding as you reach each turn'), 'chime', function () { if (S.chime) { var a = new Audio(CHIME_URL); try { var p = a.play(); if (p && p.catch) p.catch(function () {}); } catch (e) {} } });
      toggle(tu('Point of interest stories'), tu('Hear a short overview as you reach each point of interest'), 'stories', explainStories);
      toggle(tu('Keep screen on'), tu('Stops the phone locking while you ride'), 'wake', function () { if (S.wake) requestWake(); else releaseWake(); });
      toggle(tu('Battery saver'), tu('Blacks out the map between turns'), 'saver', saverTick);
      vg.appendChild(cl);
      seg(group(tu('Map')), [[false, tu('Standard')], [true, tu('Satellite')]], S.sat, function (v) { setSatellite(v); });
      var mg = b.lastChild; mg.appendChild(el('p', { class: 'note', text: tu('Satellite view needs signal.') }));
      if (R && CHECK) {
        var chkBtn = el('button', { class: 'btn primary full', type: 'button', text: 'Check directions step by step' });
        chkBtn.addEventListener('click', function () { closeSheet(); openCheck(); });
        b.appendChild(chkBtn);
        var demo = el('button', { class: 'btn outline full', type: 'button', text: tu('Test drive: watch the route play through') });
        demo.addEventListener('click', function () { closeSheet(); startSim(); });
        b.appendChild(demo);
      }
      if (R && R.gpx) {
        var gg = group(tu('Bike computer'));
        var dl = el('a', { class: 'btn outline full', href: R.gpx, download: R.slug + '.gpx', text: tu('Download this ride as a GPX file') });
        gg.appendChild(dl);
        gg.appendChild(el('p', { class: 'note', text: tu('For Garmin, Wahoo and other bike computers. The file holds the route line only.') }));
      }
      b.appendChild(el('div', { class: 'ver', text: 'Ride Guide ' + BUILD + (R ? ' · ' + R.version : '') }));
    });
  }

  // ---------- staff check: step through every direction and stop ----------
  var chk = { i: 0, items: null, ring: null, box: null };
  function checkItems() {
    var out = [];
    R.cues.forEach(function (c) { out.push({ d: c.d, cue: c }); });
    R.stops.forEach(function (s) {
      if (FACILITY[s.kind] || s.kind === 'finish') return;
      if (s.kind === 'caution') (s.ds || [s.d]).forEach(function (d, k, all) { out.push({ d: d, stop: s, pass: all.length > 1 ? k + 1 : 0, of: all.length }); });
      else out.push({ d: s.d, stop: s });
    });
    // a direction given at a stop (turn around, or leaving an arrival stop) is heard after the stop, so list it after it
    var at = {}; R.stops.forEach(function (s) { at[s.id] = s.d; });
    out.forEach(function (it) { it.o = it.d; if (it.cue && it.cue.after && at[it.cue.after] !== undefined) it.o = Math.max(it.d, at[it.cue.after] + 0.01); });
    out.sort(function (a, b) { return a.o - b.o || (a.cue ? -1 : 1); });
    return out;
  }
  function openCheck() {
    if (!R || !map) return;
    if (ride.active) { ride.active = false; stopGps(); stopSim(); }
    closeSheet();
    chk.items = checkItems();
    show('check');
    if (!chk.box) {
      chk.box = el('div', { id: 'check-panel' });
      document.body.appendChild(chk.box);
    }
    if (!chk.ring) { var rw = el('div', { class: 'check-ring-wrap' }); rw.appendChild(el('div', { class: 'check-ring' })); chk.ring = new maplibregl.Marker({ element: rw }).setLngLat(pointAt(0)).addTo(map); }
    stepCheck(Math.min(chk.i, chk.items.length - 1));
  }
  function closeCheck() {
    stopSpeech();
    if (chk.ring) { chk.ring.remove(); chk.ring = null; }
    openRoute();
  }
  function hearCheck(it) {
    stopSpeech();
    var was = S.voice; S.voice = true;
    if (it.cue) sayContent(it.cue.n, it.cue.t === 'danger' ? tu('Caution.') : null, { interrupt: true });
    else if (it.stop.kind === 'caution') { sayContent(it.stop.name, tu('Caution.'), { interrupt: true }); if (it.stop.text) sayContent(it.stop.text); }
    else {
      // exactly what a rider hears on arrival (name, then the pin's words)
      if (!it.stop.plain && it.stop.kind !== 'turn') say(tu('You have reached a point of interest.'), { interrupt: true });
      sayContent(it.stop.name);
      if (it.stop.text) sayContent(it.stop.text);
    }
    S.voice = was;
  }
  function stepCheck(i) {
    var items = chk.items; if (!items || !items.length) return;
    chk.i = i = Math.max(0, Math.min(items.length - 1, i));
    var it = items[i], p = pointAt(it.d), b = chk.box;
    chk.ring.setLngLat(p);
        b.innerHTML = '';
    var top = el('div', { class: 'ck-top' });
    var back = el('button', { class: 'ck-link', type: 'button', text: 'Back to route' });
    back.addEventListener('click', closeCheck);
    top.appendChild(back);
    top.appendChild(el('span', { class: 'ck-count', text: (i + 1) + ' of ' + items.length }));
    b.appendChild(top);
    var kind, icon, text, sub;
    var km = distText(it.d);
    if (it.cue) {
      kind = it.cue.t === 'danger' ? 'Caution (direction)' : 'Direction';
      icon = cueIcon(it.cue.t); text = it.cue.n;
      var prev = items.slice(0, i).reverse().filter(function (x) { return x.cue; })[0];
      sub = 'At ' + km + (prev ? ', ' + distText(it.d - prev.d) + ' after the last direction' : '') + '. The ring is where the turn is.';
    } else {
      var s = it.stop;
      kind = s.kind === 'caution' ? 'Caution' + (it.pass ? ' (pass ' + it.pass + ' of ' + it.of + ')' : '') : 'Stop: ' + kindLabel(s.kind);
      icon = s.kind; text = s.name;
      sub = 'At ' + km + (s.kind === 'caution' ? '. Read about ' + CFG.stops.cautionWarningMetres + ' m before the ring.' : '. Read when the rider reaches it.') + (s.off ? ' Pin is ' + s.off + ' m off the route.' : '');
    }
    var row = el('div', { class: 'ck-row' });
    row.appendChild(el('div', { class: 'ck-icon' + (it.cue ? '' : ' ' + it.stop.kind) }, svg(icon)));
    var m = el('div', { class: 'ck-main' });
    m.appendChild(el('div', { class: 'ck-kind', text: kind }));
    m.appendChild(el('div', { class: 'ck-text', text: text }));
    m.appendChild(el('div', { class: 'ck-sub', text: sub }));
    row.appendChild(m); b.appendChild(row);
    var nav = el('div', { class: 'ck-nav' });
    var pv = el('button', { class: 'btn outline', type: 'button', text: '‹ Back' });
    var hr = el('button', { class: 'btn outline', type: 'button', text: 'Hear it' });
    var nx = el('button', { class: 'btn primary', type: 'button', text: 'Next ›' });
    pv.disabled = i === 0; nx.disabled = i === items.length - 1;
    // each step is spoken as soon as it is shown (a tap, so phones allow the sound); Hear it repeats it
    pv.addEventListener('click', function () { stepCheck(chk.i - 1); hearCheck(chk.items[chk.i]); });
    nx.addEventListener('click', function () { stepCheck(chk.i + 1); hearCheck(chk.items[chk.i]); });
    hr.addEventListener('click', function () { hearCheck(it); });
    nav.appendChild(pv); nav.appendChild(hr); nav.appendChild(nx);
    b.appendChild(nav);
    // fixes are made in Ride with GPS (the master); the app picks them up within the hour
    var links = el('div', { class: 'ck-links' });
    if (!it.cue) {
      var op = el('button', { class: 'ck-link', type: 'button', text: 'Open the stop card' });
      op.addEventListener('click', function () { openStop(it.stop); });
      links.appendChild(op);
    }
    var cueNo = it.cue ? R.cues.indexOf(it.cue) + 1 : 0;
    var fix = el('a', { class: 'ck-link', target: '_blank', rel: 'noopener',
      href: it.cue ? 'https://ridewithgps.com/routes/' + R.rwgps + '/edit' : 'https://ridewithgps.com/organizations/15663-by-earth-and-ocean/poi_library',
      text: it.cue ? 'Fix in Ride with GPS (cue ' + cueNo + ')' : 'Fix in the POI Library' });
    if (R.rwgps || !it.cue) links.appendChild(fix);
    b.appendChild(links);
    map.easeTo({ center: p, zoom: Math.max(map.getZoom(), 17), duration: 500, offset: [0, -Math.round((b.offsetHeight || 240) / 2)] });
  }

  // ---------- simulator (test drive) ----------
  function startSim() {
    if (!ride.active) startRide(false);
    stopGps(); stopSim();
    var d = 0, step = 12;
    ride.sim = setInterval(function () {
      d += step;
      if (d > R.distance + 20) { stopSim(); return; }
      var p = pointAt(Math.min(d, R.distance));
      onFix({ coords: { latitude: p[1], longitude: p[0], accuracy: 8, heading: null, speed: 5 } });
    }, 400);
    banner(tu('Test drive running. Tap End ride to stop.'), 'caution', 6000);
  }
  function stopSim() { if (ride.sim) { clearInterval(ride.sim); ride.sim = null; } }

  // ---------- route page ----------
  function applyBrand() {
    var c = R.brand.colors, root = document.documentElement.style;
    ['primary', 'primary2', 'accent', 'line', 'ground', 'surface', 'sand', 'ink', 'muted'].forEach(function (k) { if (c[k]) root.setProperty('--' + k, c[k]); });
    var m = document.querySelector('meta[name=theme-color]'); if (m) m.setAttribute('content', c.primary);
    var wm = $('route-wordmark'); wm.innerHTML = ''; wm.classList.toggle('has-logo', !!R.brand.logo);
    if (R.brand.logo) wm.appendChild(el('img', { src: R.brand.logo, alt: R.brand.name }));
    else R.brand.wordmark.forEach(function (w) { wm.appendChild(el('span', { text: w })); });
    document.title = R.name + ' | ' + R.brand.name;
    var call = $('call-link'); call.href = R.brand.phoneHref || '#';
  }
  function renderRoute() {
    $('route-name').textContent = tc(R.name);
    $('st-dist').textContent = S.units === 'imperial' ? (R.distance / 1609.344).toFixed(1) + ' mi' : (R.distance / 1000).toFixed(1) + ' km';
    $('st-gain').textContent = climbText(R.gain);
    $('st-time').textContent = timeText(R.distance / (SPEED[R.activity] || SPEED.ebike));
    var stops = R.stops.filter(function (s) { return (s.kind !== 'caution' || s.text) && s.kind !== 'finish'; }).length;
    $('route-stops-n').textContent = fmt(tu(stops === 1 ? '{n} stop' : '{n} stops'), { n: stops });
    var desc = tc(R.description || '');
    $('route-desc').textContent = desc;
    $('route-desc-wrap').hidden = !desc;
    $('route-desc-more').hidden = desc.length < 220;
    // Ben, 16/10/2026: no offer card on the ride page (it read like an ad). Offers live in the Offers list while
    // riding, come up near partners, and are shown again on the finish card.
    var ow = $('route-offers'); ow.innerHTML = ''; ow.hidden = true;
    $('b-offers-label').textContent = R.offers.length ? fmt(tu('Offers {n}'), { n: R.offers.length }) : tu('Offers');
    $('route-lang').textContent = S.lang.toUpperCase();
    $('route-units').textContent = S.units === 'imperial' ? 'mi' : 'km';
    var p = lsGet(progressKey(), null);
    var resumable = p && p.version === R.version && p.d > 150 && Date.now() - p.ts < 8 * 3600 * 1000;
    $('start-label').textContent = tu(resumable ? 'Continue my ride' : 'Start riding');
    $('start-btn').dataset.resume = resumable ? '1' : '';
    $('route-back').hidden = Object.keys(routeIndex).length < 2;
  }
  function refreshAll() {
    applyStaticText();
    if (R) { renderRoute(); addMarkers(); if (ride.active) renderRide(); }
    renderHome();
  }
  function openRoute() {
    closeSheet();
    show('route');
    renderRoute();
    if (map) { fitRoute(); }
  }
  function useRoute(key, data) {
    R = data; R.key = key;
    setRouteClips();
    applyRouteSettings();
    applyBrand();
    applyStaticText();
    if (!map) initMap(); else { addRouteLayers(); fitRoute(); }
    addMarkers();
    openRoute();
    if (CHECK) openCheck();
    saveOffline();
    precacheVoice();
  }

  // ---------- in-app page viewer (the ride keeps running underneath) ----------
  function viewerOffline(on) {
    var bar = document.getElementById('viewer-offline');
    if (!on) { if (bar) bar.hidden = true; return; }
    if (!bar) {
      bar = el('div', { class: 'viewer-offline', id: 'viewer-offline', role: 'status' });
      bar.appendChild(el('span', { text: tu('No signal. This page needs mobile signal.') }));
      var bk = el('button', { class: 'btn accent small', type: 'button', text: tu(ride.active ? 'Back to my ride' : 'Back to the route') });
      bk.addEventListener('click', function () { closeViewer(false); });
      bar.appendChild(bk);
      $('viewer').insertBefore(bar, $('viewer').children[1] || null);
    }
    bar.hidden = false;
  }
  function openViewer(url) {
    viewerOffline(false);
    closeSheet();
    $('viewer-frame').src = url;
    $('viewer-ext').href = url;
    $('viewer-back-label').textContent = tu(ride.active ? 'Back to my ride' : 'Back to the route');
    $('viewer').hidden = false;
    updateViewerCue();
    try { history.pushState({ rgViewer: 1 }, ''); } catch (e) {}
  }
  function closeViewer(fromPop) {
    if ($('viewer').hidden) return;
    $('viewer').hidden = true;
    $('viewer-frame').src = 'about:blank';
    if (!fromPop) { try { if (history.state && history.state.rgViewer) history.back(); } catch (e) {} }
  }
  function updateViewerCue() {
    var v = $('viewer-cue');
    if (!v || $('viewer').hidden) return;
    v.textContent = ride.active && ride.fix ? ($('cue-dist').textContent ? $('cue-dist').textContent + ': ' : '') + $('cue-text').textContent : '';
  }

  // ---------- getting back to a route ----------
  var installEvt = null;
  window.addEventListener('beforeinstallprompt', function (e) { e.preventDefault(); installEvt = e; });
  function isStandalone() { return (window.matchMedia && matchMedia('(display-mode: standalone)').matches) || navigator.standalone === true; }
  function isIOS() { return /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1); }
  function siteAddress() { return location.origin + location.pathname.replace(/index\.html$/, ''); }
  function openKeep() {
    // While this sheet is open the address carries the route, so "Add to Home Screen" opens this route.
    try { history.replaceState(null, '', location.pathname + '#' + R.key); } catch (e) {}
    openSheet(function (b) {
      b.appendChild(el('div', { class: 'kicker', text: tu('Route code') }));
      b.appendChild(el('h2', { id: 'sheet-title', text: tu('Getting back to this route') }));
      b.appendChild(el('p', { text: tu('This route is saved on this phone. If you close the page, open the same web address again, or type this route code at the address below.') }));
      if (R.code) b.appendChild(el('div', { class: 'code-big', text: R.code, 'aria-label': tu('Route code') + ' ' + R.code.split('').join(' ') }));
      var ad = el('p'); ad.appendChild(el('span', { class: 'addr', text: siteAddress() })); b.appendChild(ad);
      var acts = el('div', { class: 'sheet-actions' });
      if (!isStandalone()) {
        if (installEvt) {
          var ins = el('button', { class: 'btn primary full', type: 'button' }, svg('pin') + '<span></span>');
          ins.querySelector('span').textContent = tu('Add to my home screen');
          ins.addEventListener('click', function () { installEvt.prompt(); installEvt = null; });
          acts.appendChild(ins);
        } else {
          b.appendChild(el('div', { class: 'set-label', text: tu('Add it to your home screen') }));
          var ol = el('ol', { class: 'steps' });
          (isIOS() ? [tu('Tap the Share button in Safari.'), tu('Choose Add to Home Screen.'), tu('Tap Add. The route opens from the new icon.')]
                   : [tu('Open your browser menu.'), tu('Choose Add to Home screen or Install app.'), tu('The route opens from the new icon.')])
            .forEach(function (t) { ol.appendChild(el('li', { text: t })); });
          b.appendChild(ol);
        }
      }
      var done = el('button', { class: 'btn outline full', type: 'button', text: tu('Done') });
      done.addEventListener('click', closeSheet);
      acts.appendChild(done);
      b.appendChild(acts);
    });
    ride.keepOpen = true;
  }
  function openCode(raw) {
    var err = $('code-error');
    var k = (raw || '').match(/#([A-Za-z0-9_-]{8,64})/);
    if (k) { err.hidden = true; return openKey(k[1]); }   // a whole link pasted in
    var code = (raw || '').toUpperCase().replace(/[^A-Z0-9]/g, '').replace(/O/g, '0').replace(/[IL]/g, '1');
    if (code.length !== 6) { err.textContent = tu('Route codes have 6 letters and numbers.'); err.hidden = false; return; }
    fetchJson('c/' + code + '.json').then(function (j) { err.hidden = true; openKey(j.k); }, function () {
      err.textContent = navigator.onLine ? tu("That code doesn't match a route. Check it with our team.") : tu('Opening a new route needs signal. Try again when you have reception.');
      err.hidden = false;
    });
  }

  // ---------- home ----------
  function renderHome() {
    var keys = Object.keys(routeIndex).sort(function (a, b) { return routeIndex[b].saved - routeIndex[a].saved; });
    $('home-list-wrap').hidden = !keys.length;
    $('home-empty').hidden = !!keys.length;
    var list = $('home-list'); list.innerHTML = '';
    keys.forEach(function (k) {
      var it = el('button', { class: 'list-item', type: 'button' });
      it.appendChild(el('div', { class: 'li-icon' }, svg('pin')));
      var m = el('div', { class: 'li-main' }); m.appendChild(el('div', { class: 'li-title', text: routeIndex[k].name })); it.appendChild(m);
      it.addEventListener('click', function () { openKey(k); });
      list.appendChild(it);
    });
  }
  function openHome() { R = null; renderHome(); applyStaticText(); show('home'); }

  function openKey(key) {
    show('loading');
    getRoute(key).then(function (data) { useRoute(key, data); }).catch(function () {
      delete routeIndex[key]; lsSet('rg.routes', routeIndex);
      openHome();
      $('home-empty').hidden = false;
      $('home-empty-title').textContent = tu('This route link is no longer active');
      $('home-empty-text').textContent = tu('Please ask our team for a new QR code.');
    });
  }

  // ---------- wiring ----------
  function wire() {
    $('start-btn').addEventListener('click', function () { startRide(!!this.dataset.resume); });
    $('end-btn').addEventListener('click', endRide);
    $('pause-btn').addEventListener('click', function () { if (ride.paused) resumeRide(); else pauseRide(); });
    $('route-stops-btn').addEventListener('click', openStops);
    $('route-cues-btn').addEventListener('click', openCues);
    $('b-cues').addEventListener('click', openCues);
    $('b-stops').addEventListener('click', openStops);
    $('b-offers').addEventListener('click', openOffers);
    $('route-settings').addEventListener('click', openSettings);
    $('home-settings').addEventListener('click', openSettings);
    $('btn-ride-settings').addEventListener('click', openSettings);
    $('route-lang').addEventListener('click', openSettings);
    $('route-units').addEventListener('click', function () { S.units = S.units === 'imperial' ? 'metric' : 'imperial'; saveSettings('units'); refreshAll(); });
    $('route-back').addEventListener('click', openHome);
    $('route-desc-more').addEventListener('click', function () { $('route-desc').classList.remove('clamp'); this.hidden = true; });
    $('sheet-close').addEventListener('click', closeSheet);
    $('scrim').addEventListener('click', closeSheet);
    $('btn-voice').addEventListener('click', function () { S.voice = !S.voice; saveSettings('voice'); updateVoiceBtn(); if (!S.voice) { stopSpeech(); } else say(tu('Voice on.')); });
    $('btn-follow').addEventListener('click', function () { ride.follow = true; updateFollowBtn(); if (map && ride.fix) map.easeTo({ center: [ride.fix.lng, ride.fix.lat], zoom: Math.max(map.getZoom(), 15.5) }); });
    $('cue-repeat').addEventListener('click', function () {
      if (ride.paused) { stopSpeech(); var w = S.voice; S.voice = true; say(tu('Ride paused. Directions are off until you tap Resume.')); S.voice = w; return; }
      var i = nextCueIndex(); if (i < 0) return;
      stopSpeech();
      var was = S.voice; S.voice = true;
      sayContent(R.cues[i].n, fmt(tu('In {dist},'), { dist: distParts(Math.max(R.cues[i].d - ride.d, 10)).say }));
      S.voice = was;
    });
    $('saver').addEventListener('click', wakeSaver);
    ['touchstart', 'mousedown'].forEach(function (ev) { document.addEventListener(ev, function () { ride.lastTouch = Date.now(); }, { passive: true }); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && sheetOpen()) closeSheet(); });
    window.addEventListener('hashchange', function () { if (ride.keepOpen) return; var k = keyFromUrl(); if (k) { scrubUrl(); openKey(k); } });
    $('keep-btn').addEventListener('click', openKeep);
    $('viewer-back').addEventListener('click', function () { closeViewer(false); });
    window.addEventListener('popstate', function () { closeViewer(true); });
    $('code-form').addEventListener('submit', function (e) { e.preventDefault(); openCode($('code-input').value); });
  }

  function boot() {
    wire();
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js?v=' + BUILD).catch(function () {});
    var key = keyFromUrl();
    if (key) scrubUrl();
    if (!key) { try { var again = sessionStorage.getItem('rg.reopen'); sessionStorage.removeItem('rg.reopen'); if (again && routeIndex[again]) key = again; } catch (e) {} }
    loadUi().then(function () {
      applyStaticText();
      if (key) return openKey(key);
      var keys = Object.keys(routeIndex);
      if (keys.length === 1) return openKey(keys[0]);
      openHome();
    });
  }
  boot();
})();
