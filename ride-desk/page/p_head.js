  var saved = null, draft = null, status = null, config = null, db = null, mcp = null, canEdit = false, siteOffers = [], links = {}, counts = null;

  function recommended() {
    var o = {}; GROUPS.forEach(function (g) { o[g.id] = {}; g.items.forEach(function (it) { o[g.id][it.k] = it.rec; }); }); return o;
  }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function val(src, g, k) { return src && src[g] && src[g][k] !== undefined ? src[g][k] : find(g, k).rec; }
  function find(g, k) { var gr = GROUPS.filter(function (x) { return x.id === g; })[0]; return gr.items.filter(function (x) { return x.k === k; })[0]; }
  function ebikeMs() { return (val(draft, "speeds", "scenic") || 15) / 3.6; }
  function secs(m) { var s = Math.round(m / ebikeMs()); return s < 60 ? s + " seconds" : dur(s); }
  function dur(s) { if (s < 60) return s + " seconds"; var m = Math.floor(s / 60), r = s % 60; return m + (m === 1 ? " minute" : " minutes") + (r ? " " + r + " seconds" : ""); }
  function sayDist(m) { var r = m < 100 ? Math.max(10, Math.round(m / 10) * 10) : Math.round(m / 50) * 50; return r + " metres"; }
  function rideTime(km, kmh) { var min = Math.round(km / kmh * 60); if (min < 60) return min + " min"; return Math.floor(min / 60) + " h " + (min % 60) + " min"; }
  function same(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }

  var refs = [];
  function render() {
    var root = document.getElementById("groups"); root.innerHTML = ""; refs = [];
    GROUPS.forEach(function (g) {
      var s = el("section"); s.setAttribute("aria-labelledby", "h-" + g.id);
      var h = el("h2", null, g.title); h.id = "h-" + g.id; s.appendChild(h);
      s.appendChild(el("p", "sect", g.intro));
      g.items.forEach(function (it) {
        var id = g.id + "-" + it.k, v = val(draft, g.id, it.k), orig = val(saved, g.id, it.k);
        var row = el("div", "set");
        var top = el("div", "top");
        if (it.toggle) {
          var lbl = el("span", "lbl", it.label); lbl.id = id + "-l"; top.appendChild(lbl);
          var sw = el("button", "switch"); sw.type = "button"; sw.id = id; sw.setAttribute("role", "switch");
          sw.setAttribute("aria-checked", String(!!v)); sw.setAttribute("aria-labelledby", id + "-l");
          sw.addEventListener("click", function () { draft[g.id][it.k] = !val(draft, g.id, it.k); refresh(); });
          top.appendChild(sw); row.appendChild(top);
          if (it.help) row.appendChild(el("p", "help", it.help));
        } else {
          var l = el("label", null, it.label); l.htmlFor = id; top.appendChild(l);
          top.appendChild(el("span", "val", v + (it.unit ? " " + it.unit : "")));
          row.appendChild(top);
          if (it.help) row.appendChild(el("p", "help", it.help));
          var r = el("input"); r.type = "range"; r.id = id; r.min = it.min; r.max = it.max; r.step = it.step; r.value = v;
          r.setAttribute("aria-valuetext", v + " " + (it.unit || ""));
          r.addEventListener("input", function () { draft[g.id][it.k] = Number(r.value); refresh(); });
          row.appendChild(r);
          var sc = el("div", "scale"); sc.appendChild(el("span", null, it.min + " " + (it.unit || ""))); sc.appendChild(el("span", null, "Recommended " + it.rec)); sc.appendChild(el("span", null, it.max + " " + (it.unit || ""))); row.appendChild(sc);
          if (it.hear) { var p = el("p", "hear"); p.appendChild(el("b", null, "Riders get")); p.appendChild(el("span", "hearText")); row.appendChild(p); }
        }
        refs.push({ g: g.id, it: it, row: row });
        s.appendChild(row);
      });
      root.appendChild(s);
    });
    refresh();
  }
