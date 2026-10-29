// Crop calendar: reads data/crop-calendar.json (issue #16) and falls back to
// the 10-row sample.json next to this page until the full dataset is merged.
// Row schema: {"country": "LV", "crop": "potato", "month": 4, "action": "plant", "notes": "..."}
(function () {
  var COUNTRIES = { LV: "Latvia", DZ: "Algeria", FR: "France", SE: "Sweden", MA: "Morocco" };
  var ACTIONS = {
    sow: { label: "Sow", icon: "🌱" },
    plant: { label: "Plant", icon: "🪴" },
    harvest: { label: "Harvest", icon: "🧺" },
    prepare: { label: "Prepare", icon: "🪓" },
    prune: { label: "Prune", icon: "✂️" },
  };
  var ACTION_ORDER = ["prepare", "sow", "plant", "prune", "harvest"];
  var MONTHS = Array.from({ length: 12 }, function (_, i) {
    return new Date(2026, i, 1).toLocaleString("en", { month: "long" });
  });

  var el = function (id) { return document.getElementById(id); };
  var rows = [];

  function cropName(crop) {
    var s = String(crop).replace(/_/g, " ");
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function option(value, text) {
    var o = document.createElement("option");
    o.value = value;
    o.textContent = text;
    return o;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  async function load() {
    var sources = [["../data/crop-calendar.json", "full dataset"], ["sample.json", "sample data (10 rows) until the full dataset is published"]];
    for (var i = 0; i < sources.length; i++) {
      try {
        var res = await fetch(sources[i][0], { cache: "no-cache" });
        if (!res.ok) continue;
        var data = await res.json();
        if (Array.isArray(data) && data.length) {
          el("source").textContent = "Showing " + sources[i][1] + ".";
          return data;
        }
      } catch (e) {
        // try the next source
      }
    }
    throw new Error("no calendar data");
  }

  function readState() {
    var q = new URLSearchParams(location.search);
    var month = Number(q.get("month")) || new Date().getMonth() + 1;
    return { country: q.get("country") || "", month: month, crop: q.get("crop") || "" };
  }

  function writeState(state) {
    var q = new URLSearchParams();
    if (state.country) q.set("country", state.country);
    q.set("month", state.month);
    if (state.crop) q.set("crop", state.crop);
    history.replaceState(null, "", "?" + q.toString());
  }

  function current() {
    return { country: el("country").value, month: Number(el("month").value), crop: el("crop").value };
  }

  function setup(state) {
    var countries = Object.keys(COUNTRIES).filter(function (c) { return rows.some(function (r) { return r.country === c; }); });
    rows.forEach(function (r) { if (!COUNTRIES[r.country] && countries.indexOf(r.country) < 0) countries.push(r.country); });
    el("country").appendChild(option("", "All countries"));
    countries.forEach(function (c) { el("country").appendChild(option(c, COUNTRIES[c] || c)); });

    MONTHS.forEach(function (m, i) { el("month").appendChild(option(i + 1, m)); });

    var crops = Array.from(new Set(rows.map(function (r) { return r.crop; }))).sort();
    el("crop").appendChild(option("", "All crops"));
    crops.forEach(function (c) { el("crop").appendChild(option(c, cropName(c))); });

    var strip = el("month-strip");
    MONTHS.forEach(function (m, i) {
      var b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "tab");
      b.dataset.month = i + 1;
      b.textContent = m.slice(0, 3);
      b.addEventListener("click", function () {
        el("month").value = i + 1;
        render();
      });
      strip.appendChild(b);
    });

    el("country").value = countries.indexOf(state.country) >= 0 ? state.country : "";
    el("month").value = state.month;
    el("crop").value = crops.indexOf(state.crop) >= 0 ? state.crop : "";
    el("filters").addEventListener("change", render);
  }

  function render() {
    var state = current();
    writeState(state);
    Array.prototype.forEach.call(el("month-strip").children, function (b) {
      var active = Number(b.dataset.month) === state.month;
      b.classList.toggle("active", active);
      b.setAttribute("aria-selected", active);
      if (active) b.scrollIntoView({ block: "nearest", inline: "center" });
    });

    var matches = rows.filter(function (r) {
      return Number(r.month) === state.month && (!state.country || r.country === state.country) && (!state.crop || r.crop === state.crop);
    });

    var where = state.country ? COUNTRIES[state.country] || state.country : "all countries";
    el("status").textContent =
      matches.length === 0
        ? "Nothing listed for " + MONTHS[state.month - 1] + " in " + where + " yet."
        : matches.length + (matches.length === 1 ? " task" : " tasks") + " for " + MONTHS[state.month - 1] + " in " + where + ".";

    var html = "";
    ACTION_ORDER.concat(Object.keys(ACTIONS).filter(function (a) { return ACTION_ORDER.indexOf(a) < 0; })).forEach(function (action) {
      var group = matches.filter(function (r) { return r.action === action; });
      if (!group.length) return;
      var a = ACTIONS[action] || { label: action, icon: "•" };
      html += '<section class="group group-' + escapeHtml(action) + '"><h2><span aria-hidden="true">' + a.icon + "</span> " + escapeHtml(a.label) + "</h2>";
      group
        .sort(function (x, y) { return x.crop.localeCompare(y.crop) || x.country.localeCompare(y.country); })
        .forEach(function (r) {
          html +=
            '<article class="item"><header><h3>' + escapeHtml(cropName(r.crop)) + "</h3>" +
            (state.country ? "" : '<span class="tag">' + escapeHtml(COUNTRIES[r.country] || r.country) + "</span>") +
            "</header>" + (r.notes ? "<p>" + escapeHtml(r.notes) + "</p>" : "") + "</article>";
        });
      html += "</section>";
    });
    el("results").innerHTML = html;
  }

  load()
    .then(function (data) {
      rows = data.filter(function (r) { return r && r.country && r.crop && r.month && r.action; });
      setup(readState());
      render();
    })
    .catch(function () {
      el("status").textContent = "Could not load the crop calendar. Please try again later.";
    });
})();
