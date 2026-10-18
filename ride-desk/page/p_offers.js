  function drawQr(cv, text, slug) {
    if (typeof qrcode !== "function") return;
    var q = qrcode(0, "M"); q.addData(text); q.make();
    var n = q.getModuleCount(), cell = Math.floor(cv.width / (n + 4)), off = Math.floor((cv.width - cell * n) / 2);
    var ctx = cv.getContext("2d"); ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, cv.width, cv.height);
    var brand = (draftCards[slug] && draftCards[slug].brand) || "beo";
    ctx.fillStyle = brand === "bikeon" ? "#0C5AA9" : "#182B3D";
    for (var r = 0; r < n; r++) for (var c = 0; c < n; c++) if (q.isDark(r, c)) ctx.fillRect(off + c * cell, off + r * cell, cell, cell);
  }
  var OFFER_KEYS = ["id", "active", "allRoutes", "showAt", "partner", "logo", "headline", "alt", "about", "how", "conditions", "phone", "where", "url", "radius", "validUntil", "hideOn"];
  function offerFields(o) {
    var r = {};
    OFFER_KEYS.forEach(function (k) { r[k] = o[k] === undefined || o[k] === null ? (k === "hideOn" ? [] : k === "active" ? true : k === "allRoutes" ? false : k === "radius" ? 500 : k === "showAt" ? "anywhere" : "") : o[k]; });
    if (!r.where) r.where = o.address || "";
    if (Array.isArray(r.conditions)) r.conditions = r.conditions.join("\n");
    return r;
  }
  function slugify(t) { return String(t || "offer").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "offer"; }
  function siteOffer(id) { return siteOffers.filter(function (x) { return x.id === id; })[0]; }
  function mapName(slug) { var m = liveMaps().filter(function (x) { return x.slug === slug; })[0]; return m ? m.name : slug; }
  var openOffer = {};   // offers shown open, kept across redraws
  function renderOffers() {
    var box = document.getElementById("offers"); box.innerHTML = "";
    if (!draft.offers || !draft.offers.length) { box.appendChild(el("p", "empty", "No offers yet.")); return; }
    draft.offers.forEach(function (o, idx) {
      var row = el("div", "set offer"); row.dataset.idx = idx;
      var top = el("div", "top"); var title = el("span", "lbl", o.partner || "New offer"); title.id = "offer-" + idx + "-l"; top.appendChild(title);
      var sw = el("button", "switch"); sw.type = "button"; sw.setAttribute("role", "switch"); sw.setAttribute("aria-labelledby", title.id); sw.dataset.offerOn = idx;
      sw.addEventListener("click", function () { o.active = !o.active; refresh(); }); top.appendChild(sw); row.appendChild(top);
      function field(key, label, hint, kind) {
        var f = el("div", "fld"), id = "offer-" + idx + "-" + key, l = el("label", null, label); l.htmlFor = id; f.appendChild(l);
        var inp = kind === "area" ? el("textarea") : el("input"); if (kind !== "area") inp.type = kind || "text"; inp.id = id; inp.value = o[key] || "";
        inp.addEventListener("input", function () { o[key] = inp.value; if (key === "partner") { title.textContent = inp.value || "New offer"; } refresh(); });
        f.appendChild(inp); if (hint) f.appendChild(el("small", null, hint)); row.appendChild(f);
      }
      field("partner", "Partner", null);
      if (o.logo) row.appendChild(el("p", "help", "The card shows this partner's logo. To change the logo, send it to Claude."));
      field("headline", "The deal", "Short, like \u201c2 for 1 gin, beer or vodka\u201d.");
      field("alt", "Second deal (optional)", "Shown as \u201cor ...\u201d under the deal.");
      field("about", "About the partner (optional)", "One or two lines under the deal.", "area");
      field("how", "How riders claim it", null, "area");
      field("conditions", "Conditions (optional)", "One per line.", "area");
      field("phone", "Phone (optional)", "Adds a Call button to the card.");
      field("where", "Where the partner is", "An address, or paste a Google Maps link.");
      field("url", "Partner website (optional)", null, "url");
      var ar = el("div", "gpxrow"), at = el("div"), al = el("p", "lbl", "Show on every map"); al.id = "offer-" + idx + "-all-l"; at.appendChild(al);
      at.appendChild(el("p", "help", "Use for a partner riders reach from the shop, so every map shows the offer even if the ride never passes it."));
      ar.appendChild(at); var asw = el("button", "switch"); asw.type = "button"; asw.setAttribute("role", "switch"); asw.setAttribute("aria-labelledby", al.id); asw.dataset.offerAll = idx;
      asw.addEventListener("click", function () { o.allRoutes = !o.allRoutes; refresh(); }); ar.appendChild(asw); row.appendChild(ar);
      var wf = el("div", "fld"), wl = el("label", null, "When riders see it"); wf.appendChild(wl);
      var wseg = el("div", "whenseg");
      [["anywhere", "Anywhere on the ride"], ["finish", "Near the end only"]].forEach(function (opt) {
        var lab = el("label"), rb = el("input"); rb.type = "radio"; rb.name = "offer-" + idx + "-when"; rb.value = opt[0]; rb.checked = (o.showAt || "anywhere") === opt[0];
        rb.addEventListener("change", function () { if (rb.checked) { o.showAt = opt[0]; refresh(); } });
        lab.appendChild(rb); lab.appendChild(document.createTextNode(" " + opt[1])); wseg.appendChild(lab);
      });
      wf.appendChild(wseg);
      wf.appendChild(el("small", null, "Near the end only: not shown on the route page or at the start. Riders hear about it in the last 1.5 km and see it on the finish card. Use it for a partner near the shop."));
      row.appendChild(wf);
      var rf = el("div", "fld"), rid = "offer-" + idx + "-radius"; var rl = el("label", null, "Pops up within " + (o.radius || 500) + " m"); rl.htmlFor = rid; rf.appendChild(rl);
      var r = el("input"); r.type = "range"; r.id = rid; r.min = 100; r.max = 2000; r.step = 50; r.value = o.radius || 500;
      r.addEventListener("input", function () { o.radius = Number(r.value); rl.textContent = "Pops up within " + o.radius + " m"; refresh(); });
      rf.appendChild(r); rf.appendChild(el("small", null, "Riders passing closer than this get the offer card. Maps whose line comes this close show it.")); row.appendChild(rf);
      field("validUntil", "Ends on (optional)", "Leave empty if it has no end date. It hides itself the day after.", "date");
      var so = siteOffer(o.id), found = el("p", "found");
      if (!so) found.textContent = "New. Its location and maps are worked out when you save.";
      else if (typeof so.lat !== "number") { found.classList.add("bad"); found.textContent = "The location could not be found. Try a fuller address or a Google Maps link."; }
      else { var on = so.onRoutes || []; found.textContent = "Showing on " + on.length + (on.length === 1 ? " map" : " maps") + (on.length && on.length <= 6 ? ": " + on.map(mapName).join(", ") + "." : "."); if (!on.length) found.classList.add("bad"); }
      row.appendChild(found);
      var d = el("details"); d.appendChild(el("summary", null, "Leave it off some maps" + (o.hideOn && o.hideOn.length ? " (" + o.hideOn.length + " left off)" : "")));
      var hl = el("div", "hide-list");
      liveMaps().forEach(function (m) {
        var lab = el("label"), cb = el("input"); cb.type = "checkbox"; cb.checked = (o.hideOn || []).indexOf(m.slug) >= 0;
        cb.addEventListener("change", function () { o.hideOn = (o.hideOn || []).filter(function (x) { return x !== m.slug; }); if (cb.checked) o.hideOn.push(m.slug); d.querySelector("summary").textContent = "Leave it off some maps" + (o.hideOn.length ? " (" + o.hideOn.length + " left off)" : ""); refresh(); });
        lab.appendChild(cb); lab.appendChild(document.createTextNode(m.name)); hl.appendChild(lab);
      });
      d.appendChild(hl); row.appendChild(d);
      var r2 = el("div", "row2"); var rm = el("button", "btn ghost rmoffer", "Remove this offer"); rm.type = "button";
      rm.addEventListener("click", function () { if (rm.dataset.sure) { draft.offers.splice(idx, 1); renderOffers(); refresh(); } else { rm.dataset.sure = "1"; rm.textContent = "Tap again to remove"; } });
      r2.appendChild(rm); row.appendChild(r2);
      // fold everything under the title into a body that opens and closes
      var body = el("div", "obody"), kids = Array.prototype.slice.call(row.children).filter(function (c) { return c !== top; });
      kids.forEach(function (c) { body.appendChild(c); }); row.appendChild(body);
      var sum = el("p", "osum", (o.headline || "No deal yet") + (o.showAt === "finish" ? " \u00b7 near the end only" : "") + (o.active ? "" : " \u00b7 off")); row.insertBefore(sum, body);
      var tg = el("button", "btn ghost otoggle"); tg.type = "button"; tg.setAttribute("aria-expanded", "false");
      function setOpen(on) { body.hidden = !on; tg.textContent = on ? "Hide details" : "Show details"; tg.setAttribute("aria-expanded", String(on)); if (on) openOffer[o.id] = 1; else delete openOffer[o.id]; }
      tg.addEventListener("click", function () { setOpen(body.hidden); });
      row.insertBefore(tg, body);
      setOpen(!!openOffer[o.id] || !o.partner);
      box.appendChild(row);
    });
  }
  function offerProblem() {
    var bad = (draft.offers || []).filter(function (o) { return o.active && (!String(o.partner || "").trim() || !String(o.headline || "").trim() || !String(o.where || "").trim()); })[0];
    return bad ? "Each offer that is switched on needs a partner, a deal and where it is." : "";
  }
  // Ride counts (17/10/2026): indicative only. Rides = reached the finish card (75% ridden); phones = phones the map was opened on.
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }
  function rideCount(slug) {
    if (!counts) return "";
    var c = (counts.routes || {})[slug] || { rides: 0, rides30: 0, phones: 0 };
    return "Ridden " + plural(c.rides || 0, "time", "times") + " (" + (c.rides30 || 0) + " in the last 30 days). Opened on " + plural(c.phones || 0, "phone", "phones") + ".";
  }
  function renderCountsTotal() {
    var box = document.getElementById("countsTotal"); if (!box) return;
    if (!counts) { box.textContent = ""; box.hidden = true; return; }
    var r = 0, r30 = 0, ph = 0;
    liveMaps().forEach(function (m) { var c = (counts.routes || {})[m.slug]; if (!c) return; r += c.rides || 0; r30 += c.rides30 || 0; ph += c.phones || 0; });
    var when = counts.asOf ? new Date(counts.asOf).toLocaleString("en-AU", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }) : "";
    box.textContent = "All maps: ridden " + plural(r, "time", "times") + ", " + r30 + " in the last 30 days, opened on " + plural(ph, "phone", "phones") + ". A ride counts once the rider reaches the finish (75% of the ride). Indicative only" + (when ? "; counted " + when : "") + ".";
    box.hidden = false;
  }
