// Wires the shop, booking and contact sections to the tools set in config.js.
(function () {
  var cfg = window.GREENLOOP || {};
  document.getElementById("year").textContent = new Date().getFullYear();

  // Text the script writes, per page language (<html lang>). English is the fallback.
  var TEXT = {
    en: {
      whatsappSent: "WhatsApp opened with your message. Press send there and we'll reply to confirm.",
      emailSent: "Your email app opened with the message. Send it and we'll reply to confirm.",
      noContact: "Online requests open soon. Until then, please contact us directly.",
      openShop: "Open the farm shop →",
      orderSubject: "Order from the website",
      visitSubject: "Farm visit request",
      name: "Name", contact: "Contact", items: "Items", details: "Details", visit: "Visit", date: "Date", people: "People",
    },
    fr: {
      whatsappSent: "WhatsApp s'est ouvert avec votre message. Appuyez sur envoyer et nous vous répondrons pour confirmer.",
      emailSent: "Votre messagerie s'est ouverte avec le message. Envoyez-le et nous vous répondrons pour confirmer.",
      noContact: "Les demandes en ligne arrivent bientôt. En attendant, contactez-nous directement.",
      openShop: "Ouvrir la boutique de la ferme →",
      orderSubject: "Commande depuis le site",
      visitSubject: "Demande de visite de la ferme",
      name: "Nom", contact: "Contact", items: "Produits", details: "Détails", visit: "Visite", date: "Date", people: "Personnes",
    },
    ar: {
      whatsappSent: "فُتح واتساب برسالتك. اضغط إرسال وسنرد عليك للتأكيد.",
      emailSent: "فُتح تطبيق البريد برسالتك. أرسلها وسنرد عليك للتأكيد.",
      noContact: "الطلبات عبر الإنترنت قريبًا. إلى ذلك الحين، تواصل معنا مباشرة.",
      openShop: "افتح متجر المزرعة ←",
      orderSubject: "طلب من الموقع",
      visitSubject: "طلب زيارة المزرعة",
      name: "الاسم", contact: "التواصل", items: "المنتجات", details: "التفاصيل", visit: "الزيارة", date: "التاريخ", people: "عدد الأشخاص",
    },
  };
  var T = TEXT[(document.documentElement.lang || "en").slice(0, 2)] || TEXT.en;

  function sendMessage(subject, body, hintEl) {
    if (cfg.whatsapp) {
      window.open("https://wa.me/" + cfg.whatsapp + "?text=" + encodeURIComponent(subject + "\n\n" + body), "_blank", "noopener");
      hintEl.textContent = T.whatsappSent;
    } else if (cfg.email) {
      window.location.href = "mailto:" + cfg.email + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
      hintEl.textContent = T.emailSent;
    } else {
      hintEl.textContent = T.noContact;
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
    a.textContent = T.openShop;
    document.getElementById("shop-cta").appendChild(a);
  } else {
    orderForm.hidden = false;
    orderForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var body = formText(orderForm, [["name", T.name], ["contact", T.contact], ["items", T.items], ["details", T.details]]);
      sendMessage(T.orderSubject, body, orderForm.querySelector("[data-hint]"));
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
      var body = formText(visitForm, [["name", T.name], ["contact", T.contact], ["type", T.visit], ["date", T.date], ["people", T.people]]);
      sendMessage(T.visitSubject, body, visitForm.querySelector("[data-hint]"));
    });
  }

  // Contact links.
  var links = [];
  if (cfg.email) links.push('<a class="btn" href="mailto:' + cfg.email + '">✉️ ' + cfg.email + "</a>");
  if (cfg.whatsapp) links.push('<a class="btn" href="https://wa.me/' + cfg.whatsapp + '" rel="noopener">💬 WhatsApp</a>');
  links.push('<a class="btn" href="https://github.com/Samir-Guenchi/smart-micro-farm-iot" rel="noopener">GitHub</a>');
  document.getElementById("contact-links").innerHTML = links.join(" ");
})();
