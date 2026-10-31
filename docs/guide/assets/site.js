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

  function reducedMotion() {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function initLiveStage() {
    var stage = document.querySelector(".live-stage");
    if (!stage) return;
    var scenes = Array.prototype.slice.call(stage.querySelectorAll("[data-live-scene]"));
    var dots = Array.prototype.slice.call(stage.querySelectorAll("[data-live-goto]"));
    var steps = Array.prototype.slice.call(document.querySelectorAll("section[data-live-step]"));
    if (!scenes.length || !steps.length) return;

    function activate(stepId) {
      scenes.forEach(function (scene) {
        var match = scene.getAttribute("data-live-scene") === stepId;
        scene.classList.toggle("is-active", match);
      });
      dots.forEach(function (dot) {
        var match = dot.getAttribute("data-live-goto") === stepId;
        dot.classList.toggle("is-active", match);
        dot.setAttribute("aria-pressed", match ? "true" : "false");
      });
    }

    dots.forEach(function (dot) {
      dot.addEventListener("click", function () {
        var targetId = dot.getAttribute("data-live-goto");
        if (!targetId) return;
        activate(targetId);
        var section = document.querySelector('section[data-live-step="' + targetId + '"]');
        if (section && section.scrollIntoView) {
          section.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
        }
      });
    });

    if (reducedMotion()) {
      var finalStep = steps[steps.length - 1].getAttribute("data-live-step");
      if (finalStep) activate(finalStep);
    }

    if ("IntersectionObserver" in window && !reducedMotion()) {
      var observer = new window.IntersectionObserver(
        function (entries) {
          var visible = entries.filter(function (entry) { return entry.isIntersecting; });
          if (!visible.length) return;
          visible.sort(function (a, b) { return a.boundingClientRect.top - b.boundingClientRect.top; });
          var stepId = visible[0].target.getAttribute("data-live-step");
          if (stepId) activate(stepId);
        },
        { rootMargin: "-18% 0px -52% 0px", threshold: [0, 0.25, 0.5] }
      );
      steps.forEach(function (step) { observer.observe(step); });
    }
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
        setTheme(current === "dark" ? "light" : "light" === current ? "dark" : "light");
      });
    }
    initLiveStage();
  });
})();
