/* Ride Guide service worker: keeps the app, the route and the map around it working with no signal. */
var BUILD = '__BUILD__';
var SHELL = 'rg-shell-' + BUILD;
var MAP = 'rg-map-v1';
var DATA = 'rg-data-v1';
var SHELL_FILES = ['./', 'index.html', 'app.js?v=' + BUILD, 'app.css?v=' + BUILD, 'ui.json?v=' + BUILD,
  'manifest.webmanifest', 'icon.svg', 'icon-180.png', 'icon-512.png', 'assets/logo-beo.png', 'assets/logo-bikeon.png',
  'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js', 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css'];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(SHELL).then(function (c) { return c.addAll(SHELL_FILES); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k.indexOf('rg-shell-') === 0 && k !== SHELL; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

function cacheFirst(req, name) {
  return caches.open(name).then(function (c) {
    return c.match(req).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (res) { if (res.ok || res.type === 'opaque') c.put(req, res.clone()).catch(function () {}); return res; });
    });
  });
}
function networkFirst(req, name) {
  return caches.open(name).then(function (c) {
    return fetch(req).then(function (res) { if (res.ok) c.put(req, res.clone()).catch(function () {}); return res; })
      .catch(function () { return c.match(req, { ignoreSearch: false }).then(function (hit) { if (hit) return hit; throw new Error('offline'); }); });
  });
}

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).catch(function () { return caches.match('index.html', { ignoreSearch: true }); }));
    return;
  }
  if (url.origin === location.origin) {
    if (/\/r\/[^/]+\.json$/.test(url.pathname) || /health\.json$/.test(url.pathname)) { e.respondWith(networkFirst(req, DATA)); return; }
    if (/(ui|voice)\.json$/.test(url.pathname)) { e.respondWith(networkFirst(req, SHELL)); return; }
    if (/\/v\/[0-9a-f]+\/[0-9a-f]+\.mp3$/.test(url.pathname)) { e.respondWith(caches.match(req).then(function (hit) { return hit || cacheFirst(req, DATA); })); return; }   // natural voice recordings
    if (/\/assets\//.test(url.pathname)) { e.respondWith(caches.match(req).then(function (hit) { return hit || cacheFirst(req, DATA); })); return; }   // partner logos, kept for offline
    e.respondWith(caches.match(req).then(function (hit) { return hit || fetch(req); }));
    return;
  }
  var h = url.hostname;
  if (h === 'tiles.openfreemap.org') {
    // styles and tile indexes can change; tiles, fonts and sprites are versioned
    if (/\/styles\/|\/planet$|\/planet\/?$/.test(url.pathname)) e.respondWith(networkFirst(req, MAP));
    else e.respondWith(cacheFirst(req, MAP));
    return;
  }
  if (h === 'unpkg.com' || h === 'fonts.gstatic.com' || h === 'server.arcgisonline.com' || /ridewithgps\.com$/.test(h)) {
    e.respondWith(cacheFirst(req, MAP));
    return;
  }
  if (h === 'fonts.googleapis.com') { e.respondWith(networkFirst(req, MAP)); return; }
});
