  // ---------- the Ride Desk: one card per ride (Ben, 18/10/2026) ----------
  // Cards live in the page's "rides" records, one per ride. The "Ride Guide settings apply" task copies them into the Ride
  // Guide (config/ride-desk.json and a sealed file for the staff section) and fills "published" with what the build worked
  // out (numbers, places in ride order, Story Library stories, photo thumbnails). Keep these field lists the same as
  // scripts/ride-desk.mjs in github.com/elementoutdoors/routes.
  var PUB = ["live", "ipad", "status", "brand", "type", "stories", "gpx", "appName", "title", "category", "sellLine", "highlights", "level", "surface", "terrain", "bike", "bikeNote", "sheetNote", "description", "photo"];
  var STAFF = ["suits", "notFor", "timeToAllow", "soldAs", "bikes", "startFinish", "staffNotes"];
  var LABELS = { appName: "Name in the app", title: "Title", category: "Category", sellLine: "Sell line", highlights: "Highlights", level: "Level", surface: "Surface",
    bike: "Recommended bike", bikeNote: "Bike, second line", sheetNote: "Note on the sheet", description: "Ride description", photo: "Photo", brand: "Brand", type: "Type",
    suits: "Who it suits", notFor: "Not for", timeToAllow: "Time to allow", soldAs: "Sold as", bikes: "Bikes to hire", startFinish: "Start and finish", staffNotes: "Staff notes" };
  var NEEDED_LIVE = ["appName", "description", "brand", "type", "suits", "notFor", "timeToAllow", "soldAs", "bikes", "startFinish", "staffNotes"];
  var NEEDED_IPAD = ["title", "category", "sellLine", "highlights", "level", "surface", "bike", "bikeNote", "sheetNote", "description"];
  var TYPES = [["scenic", "Scenic e-bike ride"], ["mtb", "Mountain bike ride from the shop"], ["gravel", "Gravel ride from the shop"], ["road", "Road ride from the shop"],
    ["hinterlandMtb", "Hinterland mountain bike ride"], ["hinterlandGravel", "Hinterland gravel ride"], ["walk", "Walk"], ["kayak", "Paddle"]];
  var CATEGORIES = ["Scenic from the shop", "Beach from the shop", "Mountain bike from the shop", "Gravel from the shop", "Road from the shop",
    "Hinterland gravel · point to point", "Hinterland mountain bike · point to point"];
  var LEVELS = ["Family", "Relaxed", "Moderate", "Intermediate", "Challenging", "Advanced"];
  var LIBRARY = "https://elementoutdoors.github.io/routes/library.html#";
  var savedCards = {}, draftCards = {}, published = null, pubStories = {}, thumbs = {}, assets = null, openCards = {}, filter = "all", search = "";

  function str(v) { return typeof v === "string" ? v.trim() : ""; }
  function editable(c) {
    c = c || {};
    var o = { live: c.live === true, ipad: c.ipad === true, status: c.status === "new" ? "new" : "ready", brand: c.brand === "beo" || c.brand === "bikeon" ? c.brand : "",
      type: c.type || "", stories: c.stories === true, gpx: c.gpx === true };
    ["appName", "title", "category", "sellLine", "level", "surface", "terrain", "bike", "bikeNote", "sheetNote", "description"].forEach(function (k) { o[k] = typeof c[k] === "string" ? c[k] : ""; });
    var hl = Array.isArray(c.highlights) ? c.highlights : []; o.highlights = [0, 1, 2, 3].map(function (i) { return typeof hl[i] === "string" ? hl[i] : ""; });
    var p = c.photo && typeof c.photo === "object" ? c.photo : {}, src = ["website", "upload", "link", "ride"].indexOf(p.source) >= 0 ? p.source : "website";
    o.photo = { source: src }; if (src === "upload") o.photo.asset = p.asset || ""; if (src === "link" || src === "ride") o.photo.url = p.url || "";
    var s = c.staff || {}; o.staff = {}; STAFF.forEach(function (k) { o.staff[k] = typeof s[k] === "string" ? s[k] : ""; });
    return o;
  }
  // trimmed, for comparing (a stray space is not a change)
  function canonCard(c) { var e = editable(c); return JSON.stringify(e, function (k, v) { return typeof v === "string" ? v.trim() : v; }); }
  function cardDirty(slug) { return !savedCards[slug] || canonCard(draftCards[slug]) !== canonCard(savedCards[slug]); }
  function dirtyCards() { return Object.keys(draftCards).filter(cardDirty); }
  function missing(c) {
    var out = [], e = editable(c);
    function empty(k) { if (k === "highlights") return e.highlights.some(function (h) { return !str(h); }); return !str(e[k] !== undefined ? e[k] : e.staff[k]); }
    if (e.live) NEEDED_LIVE.forEach(function (k) { if (empty(k)) out.push(LABELS[k]); });
    if (e.ipad) NEEDED_IPAD.forEach(function (k) { if (empty(k) && out.indexOf(LABELS[k]) < 0) out.push(LABELS[k]); });
    if (e.ipad && e.photo.source === "upload" && !e.photo.asset) out.push("Photo");
    if (e.ipad && (e.photo.source === "link" || e.photo.source === "ride") && !/^https:\/\//.test(e.photo.url || "")) out.push("Photo");
    return out;
  }
  function cardName(slug) { var c = draftCards[slug] || savedCards[slug] || {}; return str(c.title) || str(c.appName) || str(c.rwgpsName) || slug; }
  function isTest(slug) { return /test/i.test(slug); }
  function pubRide(slug) { return published && published.rides && published.rides[slug] || null; }
  function rideMins(m) { if (!m) return "-"; var h = Math.floor(m / 60), r = m % 60; return h ? h + " h " + r + " min" : r + " min"; }
  // live maps for the offers ("leave it off some maps") and the totals
  function liveMaps() { return Object.keys(savedCards).filter(function (s) { return savedCards[s].live; }).map(function (s) { return { slug: s, name: str(savedCards[s].appName) || s }; }); }
  function order(slugs) {
    var tix = {}; TYPES.forEach(function (t, i) { tix[t[0]] = i; });
    function rank(s) { var c = draftCards[s]; return [c.status === "new" ? 0 : c.live ? 1 : 2, c.brand === "bikeon" ? 0 : 1, tix[c.type] === undefined ? 9 : tix[c.type], cardName(s).toLowerCase()]; }
    return slugs.sort(function (a, b) { var x = rank(a), y = rank(b); for (var i = 0; i < x.length; i++) { if (x[i] < y[i]) return -1; if (x[i] > y[i]) return 1; } return 0; });
  }
  function shown(slug) {
    var c = draftCards[slug];
    if (filter === "new" && c.status !== "new") return false;
    if (filter === "live" && !c.live) return false;
    if (filter === "hidden" && c.live) return false;
    if (filter === "todo" && !(missing(c).length && !isTest(slug)) && !cardDirty(slug)) return false;
    if (search && (cardName(slug) + " " + (c.appName || "") + " " + slug).toLowerCase().indexOf(search) < 0) return false;
    return true;
  }

  function field(box, label, help, value, onInput, kind, id, opts) {
    var f = el("div", "fld"), l = el("label", null, label); l.htmlFor = id; f.appendChild(l);
    var inp;
    if (kind === "area" || kind === "long") { inp = el("textarea"); if (kind === "long") inp.className = "long"; }
    else if (kind === "select") { inp = el("select"); (opts || []).forEach(function (o) { var op = el("option", null, o[1]); op.value = o[0]; inp.appendChild(op); }); }
    else { inp = el("input"); inp.type = kind || "text"; if (opts && opts.list) inp.setAttribute("list", opts.list); }
    inp.id = id; inp.value = value || "";
    if (kind === "select" && value && !(opts || []).some(function (o) { return o[0] === value; })) { var op = el("option", null, value); op.value = value; inp.insertBefore(op, inp.firstChild); inp.value = value; }
    inp.addEventListener(kind === "select" ? "change" : "input", function () { onInput(inp.value); });
    f.appendChild(inp); if (help) f.appendChild(el("small", null, help)); box.appendChild(f);
    return inp;
  }
  function switchRow(box, label, help, get, set, id) {
    var r = el("div", "gpxrow"), t = el("div"), l = el("p", "lbl", label); l.id = id + "-l"; t.appendChild(l); if (help) t.appendChild(el("p", "help", help)); r.appendChild(t);
    var sw = el("button", "switch"); sw.type = "button"; sw.setAttribute("role", "switch"); sw.setAttribute("aria-labelledby", l.id); sw.id = id;
    sw.setAttribute("aria-checked", String(!!get()));
    sw.addEventListener("click", function () { set(!get()); sw.setAttribute("aria-checked", String(!!get())); refresh(); });
    r.appendChild(sw); box.appendChild(r); return sw;
  }

  function renderCards() {
    var box = document.getElementById("cards"); box.innerHTML = "";
    var slugs = order(Object.keys(draftCards));
    var counts = { all: slugs.length, "new": 0, live: 0, hidden: 0, todo: 0 };
    slugs.forEach(function (s) { var c = draftCards[s]; if (c.status === "new") counts["new"]++; if (c.live) counts.live++; else counts.hidden++; if (missing(c).length && !isTest(s)) counts.todo++; });
    document.querySelectorAll("#rideTools .chip").forEach(function (b) { var k = b.dataset.f; b.textContent = b.dataset.label + " (" + counts[k] + ")"; b.setAttribute("aria-pressed", String(filter === k)); });
    if (!slugs.length) { box.appendChild(el("p", "empty", db ? "No rides yet. New routes in the By Earth and Ocean account on Ride with GPS show up here by themselves." : "The rides could not be loaded in this view.")); return; }
    var any = false;
    slugs.forEach(function (slug) { if (!shown(slug)) return; any = true; box.appendChild(rideCard(slug)); });
    if (!any) box.appendChild(el("p", "empty", "No rides match."));
  }

  function rideCard(slug) {
    var c = draftCards[slug], raw = savedCards[slug] || {}, pr = pubRide(slug), id = "r-" + slug;
    var row = el("article", "ride"); row.dataset.slug = slug;
    var head = el("div", "rhead"), who = el("div", "who");
    var nm = el("p", "rname", cardName(slug)); who.appendChild(nm);
    var sub = []; if (str(c.appName) && str(c.appName) !== cardName(slug)) sub.push("In the app: " + str(c.appName));
    if (pr) sub.push(pr.distance_km + " km, " + (Math.round((pr.gain_m || 0) / 10) * 10) + " m climbing, " + rideMins(pr.riding_minutes) + " riding");
    else if (raw.rwgpsDistance) sub.push(Math.round(raw.rwgpsDistance / 100) / 10 + " km on Ride with GPS");
    if (sub.length) who.appendChild(el("p", "rsub", sub.join(" · ")));
    var pills = el("div", "pills"); who.appendChild(pills); head.appendChild(who);
    var tg = el("button", "btn ghost otoggle"); tg.type = "button"; head.appendChild(tg);
    row.appendChild(head);
    var body = el("div", "rbody"); row.appendChild(body);
    function setOpen(on) { body.hidden = !on; tg.textContent = on ? "Close" : "Open"; tg.setAttribute("aria-expanded", String(on)); if (on) openCards[slug] = 1; else delete openCards[slug]; if (on && !body.childNodes.length) fill(); }
    tg.addEventListener("click", function () { setOpen(body.hidden); });
    row._pills = pills; row._name = nm;
    function fill() { cardBody(body, slug); refresh(); }
    setOpen(!!openCards[slug]);
    return row;
  }

  function cardBody(body, slug) {
    var c = draftCards[slug], raw = savedCards[slug] || {}, pr = pubRide(slug), id = "r-" + slug;
    var miss = el("p", "missing"); miss.hidden = true; body.appendChild(miss); body._miss = miss;
    if (raw.status === "new" || c.status === "new") {
      var b = el("p", "banner", "New on Ride with GPS" + (raw.found ? " on " + new Date(raw.found + "T00:00:00").toLocaleDateString("en-AU", { day: "numeric", month: "long" }) : "") + ": “" + (raw.rwgpsName || slug) + "”. It stays hidden until you switch it on. Fill in the card, switch it on and press Save, or keep it hidden.");
      body.appendChild(b);
      var kh = el("button", "btn ghost act", "Keep it hidden for now"); kh.type = "button";
      kh.addEventListener("click", function () { c.status = "ready"; kh.disabled = true; kh.textContent = "Kept hidden (press Save)"; refresh(); renderPills(slug); });
      body.appendChild(kh);
    } else if (raw.deskNote) body.appendChild(el("p", "banner info", raw.deskNote));

    body.appendChild(el("h3", null, "Where it shows"));
    switchRow(body, "Live in the Ride Guide", "On: riders can open it from its link, QR code or route code. Off: its link stops working.", function () { return c.live; }, function (v) { c.live = v; if (v) c.status = "ready"; renderPills(slug); }, id + "-live");
    switchRow(body, "Show on the hire desk iPad and in the booklet", "Off for private guide rides: no ride sheet, not in the booklet or EO Crew's customer lists. Staff still see it.", function () { return c.ipad; }, function (v) { c.ipad = v; renderPills(slug); }, id + "-ipad");

    body.appendChild(el("h3", null, "In the Ride Guide app"));
    field(body, "Name in the app", "The ride's name on its Ride Guide page.", c.appName, function (v) { c.appName = v; refresh(); }, "text", id + "-appName");
    var fs = el("fieldset", "brandpick"); fs.appendChild(el("legend", null, "Brand"));
    BRANDS.forEach(function (b) {
      var bid = id + "-brand-" + b.id, r = el("input"); r.type = "radio"; r.name = id + "-brand"; r.id = bid; r.value = b.id; r.checked = c.brand === b.id;
      r.addEventListener("change", function () { c.brand = b.id; refresh(); renderPills(slug); });
      var lab = el("label"); lab.htmlFor = bid; var img = el("img"); img.src = b.logo; img.alt = ""; lab.appendChild(img);
      var t = el("div"); t.appendChild(el("span", null, b.name)); var sw = el("div", "swatches"); b.colours.forEach(function (cc) { var i = el("i"); i.style.background = cc; sw.appendChild(i); }); t.appendChild(sw); lab.appendChild(t);
      fs.appendChild(r); fs.appendChild(lab);
    });
    var bf = el("div", "fld"); bf.appendChild(el("span", "lbl", "Brand")); bf.appendChild(fs); bf.appendChild(el("small", null, "The map shows this brand's logo and colours, and its sheet goes in that brand's half of the booklet.")); body.appendChild(bf);
    field(body, "Type", "Sets the riding speed behind its riding time (speeds are under Riding time estimates below).", c.type, function (v) { c.type = v; refresh(); }, "select", id + "-type", [["", "Choose a type"]].concat(TYPES));
    switchRow(body, "Point of interest stories on by default", "On: riders hear each point of interest as they reach it. Off: points of interest stay on the map but are not announced.", function () { return c.stories; }, function (v) { c.stories = v; }, id + "-stories");
    switchRow(body, "Riders can download a GPX file", "In the map's Settings; the route line only.", function () { return c.gpx; }, function (v) { c.gpx = v; }, id + "-gpx");

    body.appendChild(el("h3", null, "Ride description"));
    field(body, "Ride description", "The ride's story everywhere: its Ride Guide page, its ride sheet and the EO Crew manual. This is the master now; the description in Ride with GPS is no longer used.", c.description, function (v) { c.description = v; refresh(); }, "long", id + "-description");

    body.appendChild(el("h3", null, "Ride sheet, iPad and booklet"));
    field(body, "Title", "Big on the ride sheet and in the booklet. Changing it redraws the sheet's 3D map overnight.", c.title, function (v) { c.title = v; refresh(); var n = document.querySelector('[data-slug="' + slug + '"] .rname'); if (n) n.textContent = cardName(slug); }, "text", id + "-title");
    field(body, "Category", "The pill above the title, and the group the sheet sits in in the booklet.", c.category, function (v) { c.category = v; refresh(); }, "select", id + "-category", [["", "Choose a category"]].concat(CATEGORIES.map(function (x) { return [x, x]; })));
    field(body, "Sell line", "One line under the title. Keep it short.", c.sellLine, function (v) { c.sellLine = v; refresh(); }, "text", id + "-sellLine");
    var hf = el("div", "fld"); hf.appendChild(el("span", "lbl", "Four highlights")); var hb = el("div", "hl4");
    [0, 1, 2, 3].forEach(function (i) { var inp = el("input"); inp.type = "text"; inp.id = id + "-hl" + i; inp.value = c.highlights[i] || ""; inp.setAttribute("aria-label", "Highlight " + (i + 1)); inp.addEventListener("input", function () { c.highlights[i] = inp.value; refresh(); }); hb.appendChild(inp); });
    hf.appendChild(hb); body.appendChild(hf);
    var two = el("div", "two"); body.appendChild(two);
    field(two, "Level", null, c.level, function (v) { c.level = v; refresh(); }, "text", id + "-level", { list: "levels" });
    field(two, "Surface", null, c.surface, function (v) { c.surface = v; refresh(); }, "text", id + "-surface");
    var two2 = el("div", "two"); body.appendChild(two2);
    field(two2, "Recommended bike", "Big on the sheet, like “e-Bike”.", c.bike, function (v) { c.bike = v; refresh(); }, "text", id + "-bike");
    field(two2, "Bike, second line", "Under it, like “Cruiser”.", c.bikeNote, function (v) { c.bikeNote = v; refresh(); }, "text", id + "-bikeNote");
    field(body, "Terrain (optional)", "Shown in place of the climbing, like “Flat”. Leave empty to show the climbing.", c.terrain, function (v) { c.terrain = v; refresh(); }, "text", id + "-terrain");
    field(body, "Note on the sheet", "Small print under the numbers.", c.sheetNote, function (v) { c.sheetNote = v; refresh(); }, "area", id + "-sheetNote");
    photoBlock(body, slug);

    body.appendChild(el("h3", null, "For staff"));
    var sf = [["suits", "Who it suits"], ["notFor", "Not for"], ["timeToAllow", "Time to allow"], ["soldAs", "Sold as"], ["bikes", "Bikes to hire"], ["startFinish", "Start and finish"], ["staffNotes", "Staff notes"]];
    sf.forEach(function (x) { field(body, x[1], null, c.staff[x[0]], function (v) { c.staff[x[0]] = v; refresh(); }, "area", id + "-" + x[0]); });
    body.appendChild(el("p", "help", "Staff only. EO Crew shows these in the Ride Guide manual; they never go on the public site."));

    body.appendChild(el("h3", null, "Worked out from the route"));
    if (pr) {
      var nb = el("div", "numbers");
      [[pr.distance_km + " km", "Distance"], [(Math.round((pr.gain_m || 0) / 10) * 10).toLocaleString("en-AU") + " m", "Climbing"], [rideMins(pr.riding_minutes), "Riding time"]].forEach(function (x) { var d = el("div"); d.appendChild(el("b", null, x[0])); d.appendChild(el("span", null, x[1])); nb.appendChild(d); });
      body.appendChild(nb);
      body.appendChild(el("p", "help", "From the route line in Ride with GPS and the riding speed for its type."));
    } else body.appendChild(el("p", "help", c.live ? "Shown after the next Ride Guide build." : "Shown once the ride is live in the Ride Guide."));
    var rc = rideCount(slug); if (rc && pr) body.appendChild(el("p", "ridecount", rc));

    body.appendChild(el("h3", null, "Places the ride passes"));
    if (pr && pr.places && pr.places.length) {
      var ul = el("ol", "places");
      pr.places.forEach(function (p) {
        var li = el("li"); li.appendChild(el("span", "km", p.km.toFixed(1) + " km"));
        var d = el("div"); var pn = el("p", "pn" + (p.k === "caution" ? " warn" : ""), (p.k === "caution" ? "Warning: " : "") + p.n); d.appendChild(pn);
        if (p.line) d.appendChild(el("p", "pl", p.line));
        var st = p.key && pubStories[p.key];
        if (st && st.story && st.story.length) { var det = el("details"); det.appendChild(el("summary", null, "Spoken story")); st.story.forEach(function (t) { det.appendChild(el("p", null, t)); }); d.appendChild(det); }
        if (p.key) { var a = el("a", null, "Open in the Story Library"); a.href = LIBRARY + p.key; a.target = "_blank"; a.rel = "noopener"; d.appendChild(a); }
        else if (p.k !== "caution") d.appendChild(el("p", "pl", "Not in the Story Library yet."));
        li.appendChild(d); ul.appendChild(li);
      });
      body.appendChild(ul);
      body.appendChild(el("p", "help", "Which places a ride passes is set in Ride with GPS (POI Library pins). The words come from the Story Library: to change a story, ask Claude to change it in the Story Library and every copy follows."));
    } else body.appendChild(el("p", "help", c.live ? "Listed after the next Ride Guide build." : "Listed once the ride is live in the Ride Guide."));

    var l = links[slug];
    if (l && l.link) {
      body.appendChild(el("h3", null, "Link, route code and QR code"));
      shareBox(body, slug, l.link, l.code, "Link for emails and texts", "QR code for " + cardName(slug), false);
      var cl = l.link.replace(/\/?#/, "/?check#").replace("//?check", "/?check");
      shareBox(body, slug, cl, null, "Staff check link", "Staff check QR code for " + cardName(slug), true);
    }
  }

  function shareBox(body, slug, link, code, title, aria, check) {
    var d = el("details", "share"); d.appendChild(el("summary", null, check ? "Staff check link and QR code" : "Link, route code and QR code for this map"));
    var sb = el("div", "sharebox"), cv = el("canvas"); cv.width = 240; cv.height = 240; cv.setAttribute("role", "img"); cv.setAttribute("aria-label", aria); sb.appendChild(cv);
    var info = el("div");
    if (check) info.appendChild(el("p", "help", "Staff only, not for riders. Opens this map in check view: Next and Back step through every direction, warning and stop, a red ring marks where each one is, and each is spoken as you reach it."));
    info.appendChild(el("p", "k", title)); info.appendChild(el("p", "v", link));
    if (check) { var op = el("a", "copy", "Open check view"); op.href = link; op.target = "_blank"; op.rel = "noopener"; op.style.display = "inline-flex"; op.style.alignItems = "center"; op.style.textDecoration = "none"; op.style.marginRight = "8px"; info.appendChild(op); }
    var cp = el("button", "copy", "Copy link"); cp.type = "button";
    cp.addEventListener("click", function () { var done = function () { cp.textContent = "Copied"; setTimeout(function () { cp.textContent = "Copy link"; }, 1800); }; try { navigator.clipboard.writeText(link).then(done, function () { cp.textContent = "Select the link above to copy"; }); } catch (e) { cp.textContent = "Select the link above to copy"; } });
    info.appendChild(cp);
    if (code) { info.appendChild(el("p", "k", "Route code")); info.appendChild(el("p", "v code", code)); }
    sb.appendChild(info); d.appendChild(sb);
    d.addEventListener("toggle", function () { if (d.open) drawQr(cv, link, slug); });
    body.appendChild(d);
  }

  function photoBlock(body, slug) {
    var c = draftCards[slug], pr = pubRide(slug), id = "r-" + slug, th = thumbs[slug];
    var f = el("div", "fld"); f.appendChild(el("span", "lbl", "Photo")); body.appendChild(f);
    var wrap = el("div", "photo"); f.appendChild(wrap);
    var pv = el("div", "pv"); wrap.appendChild(pv);
    var opts = el("div", "opts"); wrap.appendChild(opts);
    function preview() {
      pv.innerHTML = "";
      var p = c.photo;
      if (p.source === "upload" && p.asset) { var i = el("img"); i.src = "/_blob/" + p.asset; i.alt = "Uploaded photo"; pv.appendChild(i); return; }
      var same = th && th.img && ((p.source === "website" && th.source === "website") || ((p.source === "link" || p.source === "ride") && th.src === p.url));
      if (same) { var j = el("img"); j.src = th.img; j.alt = "The photo on the ride sheet"; pv.appendChild(j); return; }
      pv.textContent = p.source === "website" ? (th && th.source === "placeholder" ? "The website page has no photo" : "Website photo, shown after the next build") : "Shown after the next build";
    }
    function opt(val, label) {
      var lab = el("label", "opt"), r = el("input"); r.type = "radio"; r.name = id + "-photo"; r.id = id + "-photo-" + val; r.value = val; r.checked = c.photo.source === val;
      r.addEventListener("change", function () { if (!r.checked) return; var old = c.photo; c.photo = { source: val }; if (val === "upload") c.photo.asset = old.asset || ""; if (val === "link" || val === "ride") c.photo.url = old.source === val ? old.url : ""; preview(); refresh(); showSubs(); });
      lab.appendChild(r); lab.appendChild(document.createTextNode(label)); opts.appendChild(lab); return lab;
    }
    opt("website", "The photo on its Bike On website page (default)");
    opt("ride", "One of the ride's own photos");
    var subRide = el("div", "sub"); opts.appendChild(subRide);
    var list = (pr && pr.photos) || [];
    if (!list.length) subRide.appendChild(el("small", null, "None yet: photos on the ride's stops in Ride with GPS show here after the next build."));
    else { var pk = el("div", "picks"); list.forEach(function (u, i) { var lb = el("label"), r = el("input"); r.type = "radio"; r.name = id + "-pick"; r.id = id + "-pick-" + i; r.checked = c.photo.url === u; r.addEventListener("change", function () { c.photo = { source: "ride", url: u }; preview(); refresh(); }); lb.appendChild(r); lb.appendChild(document.createTextNode("Photo " + (i + 1) + " ")); var a = el("a", null, "view"); a.href = u; a.target = "_blank"; a.rel = "noopener"; lb.appendChild(a); pk.appendChild(lb); }); subRide.appendChild(pk); }
    opt("upload", "Upload a photo");
    var subUp = el("div", "sub"); opts.appendChild(subUp);
    var fi = el("input"); fi.type = "file"; fi.accept = "image/jpeg,image/png,image/webp"; fi.id = id + "-upload"; subUp.appendChild(fi);
    var upMsg = el("small", null, assets ? "A landscape photo works best. It is made smaller before it uploads." : "Uploading needs edit access to this page."); subUp.appendChild(upMsg);
    fi.addEventListener("change", function () {
      var file = fi.files && fi.files[0]; if (!file || !assets) return;
      upMsg.textContent = "Uploading…";
      shrink(file).then(function (blob) { return assets.upload(blob, { type: "image/jpeg" }); }).then(function (res) {
        c.photo = { source: "upload", asset: res.id }; upMsg.textContent = "Uploaded. Press Save to use it."; var rr = document.getElementById(id + "-photo-upload"); if (rr) rr.checked = true; preview(); refresh();
      }).catch(function (e) { upMsg.textContent = "That photo did not upload (" + (e && e.code || "error") + "). Try a JPEG or PNG under 20 MB."; });
    });
    opt("link", "A link to a photo");
    var subLink = el("div", "sub"); opts.appendChild(subLink);
    var li = el("input"); li.type = "url"; li.id = id + "-photo-url"; li.placeholder = "https://"; li.value = c.photo.source === "link" ? c.photo.url || "" : ""; li.setAttribute("aria-label", "Photo link");
    li.addEventListener("input", function () { c.photo = { source: "link", url: li.value.trim() }; var rr = document.getElementById(id + "-photo-link"); if (rr) rr.checked = true; preview(); refresh(); });
    subLink.appendChild(li); subLink.appendChild(el("small", null, "An image address starting with https://, such as a photo on the website."));
    function showSubs() { subRide.hidden = c.photo.source !== "ride"; subUp.hidden = c.photo.source !== "upload"; subLink.hidden = c.photo.source !== "link"; }
    showSubs(); preview();
  }
  // a photo made no wider than 2000 px before it uploads, as a JPEG
  function shrink(file) {
    return new Promise(function (resolve, reject) {
      var img = new Image(), url = URL.createObjectURL(file);
      img.onload = function () {
        var s = Math.min(1, 2000 / img.naturalWidth), cv = document.createElement("canvas"); cv.width = Math.round(img.naturalWidth * s); cv.height = Math.round(img.naturalHeight * s);
        cv.getContext("2d").drawImage(img, 0, 0, cv.width, cv.height); URL.revokeObjectURL(url);
        cv.toBlob(function (b) { b ? resolve(b) : reject({ code: "not_an_image" }); }, "image/jpeg", 0.86);
      };
      img.onerror = function () { reject({ code: "not_an_image" }); }; img.src = url;
    });
  }

  function renderPills(slug) {
    var row = document.querySelector('#cards [data-slug="' + slug + '"]'); if (!row || !row._pills) return;
    var c = draftCards[slug], p = row._pills; p.innerHTML = "";
    if (c.status === "new") p.appendChild(el("span", "pill new", "New"));
    p.appendChild(el("span", "pill" + (c.live ? " on" : ""), c.live ? "Live in the Ride Guide" : "Hidden"));
    if (c.ipad) p.appendChild(el("span", "pill on", "On the iPad"));
    if (c.brand) p.appendChild(el("span", "pill brand", c.brand === "beo" ? "By Earth and Ocean" : "Bike On"));
    var m = missing(c); if (m.length && !isTest(slug)) p.appendChild(el("span", "pill todo", m.length + " to fill in"));
    if (cardDirty(slug)) p.appendChild(el("span", "pill todo", "Not saved"));
  }
