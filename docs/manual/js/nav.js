/* New Phone Platform — Manual Navigation
   Sidebar toggle, scroll-spy, dark mode, mobile menu, client-side search */
(function () {
  "use strict";

  // ── Dark mode ──────────────────────────────────────────────────────
  const THEME_KEY = "np-manual-theme";

  function getPreferred() {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored) return stored;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
    const btn = document.getElementById("theme-toggle");
    if (btn) btn.setAttribute("aria-label", theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
  }

  applyTheme(getPreferred());

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.addEventListener("click", function () {
        var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
        applyTheme(next);
      });
    }

    // ── Mobile sidebar toggle ──────────────────────────────────────
    var sidebar = document.getElementById("sidebar");
    var hamburger = document.getElementById("hamburger");
    var overlay = document.getElementById("sidebar-overlay");

    function openSidebar() {
      if (sidebar) sidebar.classList.add("open");
      if (overlay) overlay.classList.add("visible");
      document.body.classList.add("sidebar-open");
    }
    function closeSidebar() {
      if (sidebar) sidebar.classList.remove("open");
      if (overlay) overlay.classList.remove("visible");
      document.body.classList.remove("sidebar-open");
    }

    if (hamburger) hamburger.addEventListener("click", function () {
      sidebar && sidebar.classList.contains("open") ? closeSidebar() : openSidebar();
    });
    if (overlay) overlay.addEventListener("click", closeSidebar);

    // Close sidebar on link click (mobile)
    if (sidebar) {
      sidebar.querySelectorAll("a").forEach(function (a) {
        a.addEventListener("click", function () {
          if (window.innerWidth < 768) closeSidebar();
        });
      });
    }

    // ── Mark current page in sidebar ───────────────────────────────
    var currentPath = window.location.pathname;
    var currentFile = currentPath.split("/").pop() || "index.html";
    var parentDir = currentPath.split("/").slice(-2, -1)[0] || "";

    sidebar && sidebar.querySelectorAll("a").forEach(function (a) {
      var href = a.getAttribute("href");
      if (!href) return;
      // Normalize href for comparison
      var hrefFile = href.split("/").pop() || "index.html";
      var hrefDir = href.split("/").slice(-2, -1)[0] || "";
      if (hrefFile === currentFile && (hrefDir === parentDir || href.indexOf("../") !== -1)) {
        a.classList.add("active");
      }
    });

    // ── Scroll-spy for page TOC ────────────────────────────────────
    var tocLinks = document.querySelectorAll(".page-toc a");
    var headings = [];

    tocLinks.forEach(function (link) {
      var id = link.getAttribute("href");
      if (id && id.startsWith("#")) {
        var el = document.getElementById(id.slice(1));
        if (el) headings.push({ el: el, link: link });
      }
    });

    if (headings.length > 0) {
      var scrollTimer;
      window.addEventListener("scroll", function () {
        clearTimeout(scrollTimer);
        scrollTimer = setTimeout(function () {
          var scrollY = window.scrollY + 100;
          var current = headings[0];
          for (var i = 0; i < headings.length; i++) {
            if (headings[i].el.offsetTop <= scrollY) current = headings[i];
          }
          tocLinks.forEach(function (l) { l.classList.remove("active"); });
          if (current) current.link.classList.add("active");
        }, 50);
      });
    }

    // ── Collapsible sidebar groups ─────────────────────────────────
    document.querySelectorAll(".sidebar-group-label").forEach(function (label) {
      label.addEventListener("click", function () {
        var group = this.parentElement;
        if (group) group.classList.toggle("collapsed");
      });
    });

    // ── Simple client-side search ──────────────────────────────────
    var searchInput = document.getElementById("manual-search");
    var searchResults = document.getElementById("search-results");

    if (searchInput && searchResults) {
      var searchIndex = null;

      function loadSearchIndex() {
        if (searchIndex) return Promise.resolve(searchIndex);
        // Determine base path
        var base = "";
        if (currentPath.indexOf("/admin/") !== -1 || currentPath.indexOf("/user/") !== -1) base = "../";
        return fetch(base + "search-index.json")
          .then(function (r) { return r.json(); })
          .then(function (data) { searchIndex = data; return data; })
          .catch(function () { searchIndex = []; return []; });
      }

      searchInput.addEventListener("focus", function () { loadSearchIndex(); });

      searchInput.addEventListener("input", function () {
        var q = this.value.trim().toLowerCase();
        if (q.length < 2) { searchResults.innerHTML = ""; searchResults.classList.remove("visible"); return; }

        loadSearchIndex().then(function (idx) {
          var matches = idx.filter(function (entry) {
            return entry.title.toLowerCase().indexOf(q) !== -1 ||
                   (entry.keywords && entry.keywords.toLowerCase().indexOf(q) !== -1);
          }).slice(0, 8);

          if (matches.length === 0) {
            searchResults.innerHTML = '<div class="search-no-results">No results</div>';
          } else {
            var base = "";
            if (currentPath.indexOf("/admin/") !== -1 || currentPath.indexOf("/user/") !== -1) base = "../";
            searchResults.innerHTML = matches.map(function (m) {
              return '<a class="search-result" href="' + base + m.url + '">' +
                '<span class="search-result-title">' + m.title + '</span>' +
                '<span class="search-result-section">' + m.section + '</span>' +
              '</a>';
            }).join("");
          }
          searchResults.classList.add("visible");
        });
      });

      // Close search on click outside
      document.addEventListener("click", function (e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
          searchResults.classList.remove("visible");
        }
      });

      // Close on Escape
      searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
          searchResults.classList.remove("visible");
          this.blur();
        }
      });
    }
  });
})();
