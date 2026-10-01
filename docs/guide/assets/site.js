/* pythonx-compose guide: language and theme toggles.
 * The initial language and theme are applied by a tiny inline script in each page's <head>
 * (so nothing flashes); this file wires the buttons and keeps the document title in step. */
(function () {
  "use strict";
  var root = document.documentElement;

  function load(key) { try { return window.localStorage.getItem(key); } catch (e) { return null; } }
  function save(key, value) { try { window.localStorage.setItem(key, value); } catch (e) { /* private mode */ } }

  function syncTitle() {
    var body = document.body;
    var title = body && body.getAttribute("data-title-" + root.lang);
    if (title) document.title = title + " · pythonx-compose";
  }

  function setLang(lang) {
    root.lang = lang;
    save("pxc-lang", lang);
    syncTitle();
  }

  function systemDark() {
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }

  function setTheme(theme) {
    root.setAttribute("data-theme", theme);
    save("pxc-theme", theme);
  }

  document.addEventListener("DOMContentLoaded", function () {
    syncTitle();
    var langButton = document.getElementById("lang-toggle");
    if (langButton) {
      langButton.addEventListener("click", function () { setLang(root.lang === "ko" ? "en" : "ko"); });
    }
    var themeButton = document.getElementById("theme-toggle");
    if (themeButton) {
      themeButton.addEventListener("click", function () {
        var current = root.getAttribute("data-theme") || (systemDark() ? "dark" : "light");
        setTheme(current === "dark" ? "light" : "dark");
      });
    }
  });
})();
