  // update values, examples, cards and the save bar in place, so nothing is rebuilt mid-typing
  function refresh() {
    refs.forEach(function (r) {
      var v = val(draft, r.g, r.it.k), orig = val(saved, r.g, r.it.k);
      r.row.classList.toggle("changed", !!saved && v !== orig);
      if (r.it.toggle) { r.row.querySelector(".switch").setAttribute("aria-checked", String(!!v)); return; }
      var inp = r.row.querySelector("input"); if (Number(inp.value) !== v) inp.value = v;
      inp.setAttribute("aria-valuetext", v + " " + (r.it.unit || ""));
      r.row.querySelector(".val").textContent = v + (r.it.unit ? " " + r.it.unit : "");
      var h = r.row.querySelector(".hearText"); if (h) h.textContent = r.it.hear(v);
    });
    document.querySelectorAll("#cards .ride").forEach(function (row) {
      var slug = row.dataset.slug; if (!draftCards[slug]) return;
      row.classList.toggle("changed", cardDirty(slug));
      renderPills(slug);
      var body = row.querySelector(".rbody");
      if (body && body._miss) { var m = isTest(slug) ? [] : missing(draftCards[slug]); body._miss.hidden = !m.length; body._miss.textContent = "Still to fill in: " + m.join(", ") + "."; }
    });
    document.querySelectorAll("#offers .offer").forEach(function (row) {
      var o = draft.offers[Number(row.dataset.idx)]; if (!o) return;
      var sw = row.querySelector("[data-offer-on]"); if (sw) sw.setAttribute("aria-checked", String(!!o.active));
      var asw = row.querySelector("[data-offer-all]"); if (asw) asw.setAttribute("aria-checked", String(!!o.allRoutes));
      var before = (stripMeta(saved).offers || []).filter(function (x) { return x.id === o.id; })[0];
      row.classList.toggle("changed", !!saved && !same(before, o));
    });
    var nCards = dirtyCards().length, setDirty = saved && !same(stripMeta(saved), draft), dirty = !!(setDirty || nCards), problem = offerProblem() || cardProblem();
    document.getElementById("save").disabled = !dirty || !canEdit || !!problem;
    document.getElementById("barMsg").textContent = problem && dirty ? problem : dirty ? (nCards ? (nCards === 1 ? "1 ride card" : nCards + " ride cards") + (setDirty ? " and settings" : "") + " not saved." : "You have unsaved changes.") : "No changes yet.";
    renderStatus(dirty);
  }
  // a ride switched on for the Ride Guide needs these, or its map cannot be built
  function cardProblem() {
    var bad = dirtyCards().filter(function (s) { var c = draftCards[s]; return c.live && (!c.brand || !c.type || !str(c.appName)); })[0];
    return bad ? cardName(bad) + " is switched on, so it needs a name in the app, a brand and a type." : "";
  }
  // the rider settings and offers (each ride's own settings are on its card)
  function stripMeta(o) {
    var c = {}; GROUPS.forEach(function (g) { c[g.id] = {}; g.items.forEach(function (it) { c[g.id][it.k] = val(o, g.id, it.k); }); });
    c.offers = clone((o && Array.isArray(o.offers) ? o.offers : siteOffers.map(offerFields)) || []);
    return c;
  }

  function save() {
    if (!db || !canEdit) return;
    var btn = document.getElementById("save"); btn.disabled = true;
    var rev = (saved && saved.rev || 0) + 1, at = new Date().toISOString(), slugs = dirtyCards();
    document.getElementById("barMsg").textContent = "Saving…";
    var chain = Promise.resolve();
    slugs.forEach(function (slug) {
      chain = chain.then(function () {
        var e = editable(draftCards[slug]);
        // trimmed text, and a card Ben has saved is no longer new
        ["appName", "title", "category", "sellLine", "level", "surface", "terrain", "bike", "bikeNote", "sheetNote", "description"].forEach(function (k) { e[k] = e[k].trim(); });
        e.highlights = e.highlights.map(function (h) { return h.trim(); }); STAFF.forEach(function (k) { e.staff[k] = e.staff[k].trim(); });
        if (e.photo.url) e.photo.url = e.photo.url.trim();
        e.status = "ready";
        var doc = Object.assign({}, savedCards[slug] || {}, e, { rev: rev, savedAt: at });
        return db.doc("rides/" + slug).set(doc);
      });
    });
    chain.then(function () {
      var doc = clone(draft); doc.rev = rev; doc.savedAt = at; doc.firing = "none"; doc.cards = slugs;
      return db.doc("settings/current").set(doc);
    }).then(function () {
      document.getElementById("barMsg").textContent = "Saved. Updating the live site…";
      return applyNow(rev);
    }).catch(function (e) {
      document.getElementById("barMsg").textContent = "Could not save (" + (e && e.code || "error") + "). Check your connection and try again.";
      btn.disabled = false;
    });
  }
  function applyNow(rev) {
    if (!mcp || !config || !config.triggerId) {
      document.getElementById("barMsg").textContent = "Saved. It goes live with tonight’s 3am update.";
      return Promise.resolve();
    }
    return mcp.callTool(TRIGGER_SERVER, "fire_trigger", { trigger_id: config.triggerId, text: "Ride Desk rev " + rev + " saved." })
      .then(function () {
        db.doc("settings/current").update({ firing: "queued" }).catch(function () {});
        document.getElementById("barMsg").textContent = "Saved. Usually live within 10 minutes.";
      }, function (e) {
        var code = e && e.code;
        var why = code === "server_not_connected" ? " (Claude Code Remote is not connected for you)" : code === "not_in_manifest" ? " (you did not allow it to start the update)" : "";
        document.getElementById("barMsg").textContent = "Saved. It goes live with tonight’s 3am update" + why + ".";
      });
  }

  document.getElementById("save").addEventListener("click", save);
  document.getElementById("undo").addEventListener("click", function () {
    draft = stripMeta(saved || recommended()); draftCards = {}; Object.keys(savedCards).forEach(function (s) { draftCards[s] = editable(savedCards[s]); });
    renderCards(); renderOffers(); refresh();
  });
  document.getElementById("addOffer").addEventListener("click", function () {
    var id = "offer-" + Date.now().toString(36);
    draft.offers.push(offerFields({ id: id, active: true, radius: 500, hideOn: [] })); renderOffers(); refresh();
    var rows = document.querySelectorAll("#offers .offer"); var last = rows[rows.length - 1]; if (last) { last.scrollIntoView({ behavior: "smooth", block: "start" }); var f = last.querySelector("input[type=text]"); if (f) f.focus(); }
  });
  document.getElementById("reset").addEventListener("click", function () { var ro = draft.offers; draft = recommended(); draft.offers = ro; refresh(); document.getElementById("barMsg").textContent = "Recommended rider settings loaded. Press Save to use them."; });
  document.querySelectorAll("#rideTools .chip").forEach(function (b) { b.addEventListener("click", function () { filter = b.dataset.f; renderCards(); refresh(); }); });
  document.getElementById("rideSearch").addEventListener("input", function (e) { search = e.target.value.toLowerCase().trim(); renderCards(); refresh(); });

  // first frame: recommended values, read only until the store answers
  draft = recommended(); draft.offers = []; render(); renderCards(); renderOffers();

  if (window.claude && window.claude.use) {
    window.claude.use("user").then(function (u) { canEdit = !!(u && u.canEdit && u.canEdit()); document.body.classList.toggle("readonly", !canEdit); refresh(); });
    window.claude.use("mcp").then(function (m) { mcp = m; });
    window.claude.use("assets").then(function (a) { assets = a; });
    window.claude.use("db").then(function (d) {
      db = d;
      if (!db) { renderCards(); refresh(); return; }
      db.doc("settings/current").onSnapshot(function (s) {
        var wasDirty = saved && !same(stripMeta(saved), draft);
        saved = s.exists ? s.data() : recommended();
        if (!wasDirty) { draft = stripMeta(saved); renderOffers(); }
        refresh();
      }, function () { refresh(); });
      db.doc("settings/status").onSnapshot(function (s) { status = s.exists ? s.data() : null; refresh(); }, function () {});
      db.doc("settings/config").onSnapshot(function (s) { config = s.exists ? s.data() : null; }, function () {});
      // the ride cards: a card someone else saved replaces this view's copy unless it has changes here
      db.collection("rides").limit(500).onSnapshot(function (q) {
        var next = {};
        q.docs.forEach(function (d) { if (d.exists) next[d.id] = d.data(); });
        Object.keys(next).forEach(function (s) { if (!draftCards[s] || !cardDirty(s) || canonCard(next[s]) === canonCard(draftCards[s])) draftCards[s] = editable(next[s]); });
        Object.keys(draftCards).forEach(function (s) { if (!next[s] && savedCards[s]) delete draftCards[s]; });
        savedCards = next;
        renderCards(); renderOffers(); renderCountsTotal(); refresh();
      }, function () { renderCards(); });
      db.doc("published/rides").onSnapshot(function (s) { published = s.exists ? s.data() : null; renderCards(); refresh(); }, function () {});
      db.doc("published/stories").onSnapshot(function (s) { pubStories = s.exists ? (s.data().stories || {}) : {}; }, function () {});
      db.doc("published/thumbs").onSnapshot(function (s) { thumbs = s.exists ? (s.data().rides || {}) : {}; renderCards(); refresh(); }, function () {});
      db.doc("routes/counts").onSnapshot(function (s) { counts = s.exists ? s.data() : null; renderCountsTotal(); renderCards(); refresh(); }, function () {});
      db.doc("routes/links").onSnapshot(function (s) { links = s.exists && s.data().links ? s.data().links : {}; renderCards(); refresh(); }, function () {});
      db.doc("routes/offers").onSnapshot(function (s) {
        var wasDirty = saved && !same(stripMeta(saved), draft);
        siteOffers = s.exists && Array.isArray(s.data().offers) ? s.data().offers : [];
        if (!wasDirty) draft = stripMeta(saved || recommended());
        renderOffers(); refresh();
      }, function () {});
    });
  } else { render(); }
})();
