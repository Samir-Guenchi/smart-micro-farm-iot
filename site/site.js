// Wires the shop, booking and contact sections to the tools set in config.js.
(function () {
  var cfg = window.GREENLOOP || {};
  document.getElementById("year").textContent = new Date().getFullYear();

  function sendMessage(subject, body, hintEl) {
    if (cfg.whatsapp) {
      window.open("https://wa.me/" + cfg.whatsapp + "?text=" + encodeURIComponent(subject + "\n\n" + body), "_blank", "noopener");
      hintEl.textContent = "WhatsApp opened with your message. Press send there and we'll reply to confirm.";
    } else if (cfg.email) {
      window.location.href = "mailto:" + cfg.email + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
      hintEl.textContent = "Your email app opened with the message. Send it and we'll reply to confirm.";
    } else {
      hintEl.textContent = "Online requests open soon. Until then, please contact us directly.";
    }
  }

  function formText(form, labels) {
    var data = new FormData(form);
    return labels
      .map(function (pair) {
        var value = data.getAll(pair[0]).filter(Boolean).join(", ");
        return value ? pair[1] + ": " + value : "";
      })
      .filter(Boolean)
      .join("\n");
  }

  // Shop: link out to a ready-made shop, or fall back to a simple order form.
  var orderForm = document.getElementById("order-form");
  if (cfg.shopUrl) {
    var a = document.createElement("a");
    a.className = "btn primary big";
    a.href = cfg.shopUrl;
    a.rel = "noopener";
    a.textContent = "Open the farm shop →";
    document.getElementById("shop-cta").appendChild(a);
  } else {
    orderForm.hidden = false;
    orderForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var body = formText(orderForm, [["name", "Name"], ["contact", "Contact"], ["items", "Items"], ["details", "Details"]]);
      sendMessage("Order from the website", body, orderForm.querySelector("[data-hint]"));
    });
  }

  // Visits: Cal.com inline embed, or a request form.
  var visitForm = document.getElementById("visit-form");
  if (cfg.calLink) {
    var el = document.getElementById("cal-embed");
    el.hidden = false;
    // Official Cal.com embed loader (https://cal.com/docs/core-features/embed).
    (function (C, A, L) {
      var p = function (a, ar) { a.q.push(ar); };
      var d = C.document;
      C.Cal = C.Cal || function () {
        var cal = C.Cal, ar = arguments;
        if (!cal.loaded) { cal.ns = {}; cal.q = cal.q || []; d.head.appendChild(d.createElement("script")).src = A; cal.loaded = true; }
        if (ar[0] === L) {
          var api = function () { p(api, arguments); };
          var namespace = ar[1];
          api.q = api.q || [];
          if (typeof namespace === "string") { cal.ns[namespace] = cal.ns[namespace] || api; p(cal.ns[namespace], ar); p(cal, ["initNamespace", namespace]); }
          else p(cal, ar);
          return;
        }
        p(cal, ar);
      };
    })(window, "https://app.cal.com/embed/embed.js", "init");
    window.Cal("init", { origin: "https://cal.com" });
    window.Cal("inline", { elementOrSelector: "#cal-embed", calLink: cfg.calLink, layout: "month_view" });
  } else {
    visitForm.hidden = false;
    visitForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var body = formText(visitForm, [["name", "Name"], ["contact", "Contact"], ["type", "Visit"], ["date", "Date"], ["people", "People"]]);
      sendMessage("Farm visit request", body, visitForm.querySelector("[data-hint]"));
    });
  }

  // Contact links.
  var links = [];
  if (cfg.email) links.push('<a class="btn" href="mailto:' + cfg.email + '">✉️ ' + cfg.email + "</a>");
  if (cfg.whatsapp) links.push('<a class="btn" href="https://wa.me/' + cfg.whatsapp + '" rel="noopener">💬 WhatsApp</a>');
  links.push('<a class="btn" href="https://github.com/Samir-Guenchi/smart-micro-farm-iot" rel="noopener">GitHub</a>');
  document.getElementById("contact-links").innerHTML = links.join(" ");
})();
