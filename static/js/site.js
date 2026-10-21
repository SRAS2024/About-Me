/* ── Public site JS: navigation, skills filter, GitHub API, contact form ── */
(function () {
  "use strict";

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  /* ── Mobile navigation toggle ─────────────────────────────────── */
  function initNavToggle() {
    var btn = $(".nav-toggle");
    var nav = $("#site-nav");
    if (!btn || !nav) return;

    function setOpen(open) {
      nav.classList.toggle("is-open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    }

    btn.addEventListener("click", function () {
      setOpen(!nav.classList.contains("is-open"));
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("is-open")) {
        setOpen(false);
        btn.focus();
      }
    });
  }

  /* ── Skills filter (category buttons + search box) ────────────── */
  function initSkillsFilter() {
    var table = $("#skills-table");
    if (!table) return;

    var rows = $$("tbody tr[data-category]", table);
    var chips = $$(".chip[data-filter]");
    var search = $("#skill-search");
    var count = $("#skill-count");
    var empty = $("#skills-empty");
    var active = "all";

    function apply() {
      var q = search ? search.value.trim().toLowerCase() : "";
      var shown = 0;
      rows.forEach(function (row) {
        var inCategory = active === "all" || row.getAttribute("data-category") === active;
        var matches = !q || row.textContent.toLowerCase().indexOf(q) !== -1;
        row.hidden = !(inCategory && matches);
        if (!row.hidden) shown++;
      });
      if (count) {
        count.textContent = shown === rows.length
          ? "Showing all " + rows.length + " skills"
          : "Showing " + shown + " of " + rows.length + " skills";
      }
      if (empty) empty.hidden = shown !== 0;
    }

    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        active = chip.getAttribute("data-filter");
        chips.forEach(function (c) { c.setAttribute("aria-pressed", c === chip ? "true" : "false"); });
        apply();
      });
    });
    if (search) search.addEventListener("input", apply);
    apply();
  }

  /* ── GitHub REST API: public repositories ─────────────────────── */
  function initGitHubRepos() {
    var list = $("#repo-list");
    if (!list) return;

    var user = list.getAttribute("data-github-user");
    var status = $("#repo-status");
    var sortSelect = $("#repo-sort");
    var cacheKey = "gh-repos:" + user;
    var cacheMs = 10 * 60 * 1000;
    var repos = [];

    function formatDate(iso) {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
    }

    function makeCard(repo) {
      var card = document.createElement("a");
      card.className = "link-card repo-card";
      card.href = repo.html_url;
      card.target = "_blank";
      card.rel = "noopener noreferrer";

      var name = document.createElement("span");
      name.className = "link-card-label";
      name.textContent = repo.name;

      var desc = document.createElement("span");
      desc.className = "repo-desc";
      desc.textContent = repo.description || "No description yet.";

      var meta = document.createElement("span");
      meta.className = "repo-meta";
      if (repo.language) {
        var lang = document.createElement("span");
        lang.className = "repo-lang";
        lang.textContent = repo.language;
        meta.appendChild(lang);
      }
      var updated = document.createElement("span");
      updated.textContent = "Updated " + formatDate(repo.pushed_at);
      meta.appendChild(updated);
      if (repo.stargazers_count > 0) {
        var stars = document.createElement("span");
        stars.textContent = repo.stargazers_count + (repo.stargazers_count === 1 ? " star" : " stars");
        meta.appendChild(stars);
      }

      card.appendChild(name);
      card.appendChild(desc);
      card.appendChild(meta);
      return card;
    }

    function render() {
      var by = sortSelect ? sortSelect.value : "updated";
      var sorted = repos.slice().sort(function (a, b) {
        if (by === "name") return a.name.localeCompare(b.name, "en", { sensitivity: "base" });
        if (by === "created") return new Date(b.created_at) - new Date(a.created_at);
        return new Date(b.pushed_at) - new Date(a.pushed_at);
      });
      list.innerHTML = "";
      sorted.forEach(function (repo) { list.appendChild(makeCard(repo)); });
      if (status) {
        status.textContent = repos.length
          ? repos.length + " public " + (repos.length === 1 ? "repository" : "repositories") + ", loaded live from the GitHub API."
          : "No public repositories to show yet.";
      }
    }

    function showError() {
      list.innerHTML = "";
      if (!status) return;
      status.textContent = "GitHub couldn't be reached right now. You can still browse my work at ";
      var link = document.createElement("a");
      link.href = "https://github.com/" + user;
      link.textContent = "github.com/" + user;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      status.appendChild(link);
      status.appendChild(document.createTextNode("."));
    }

    // Keep only the fields the cards use, so the cached copy stays small.
    function slim(repo) {
      return {
        name: repo.name,
        html_url: repo.html_url,
        description: repo.description,
        language: repo.language,
        stargazers_count: repo.stargazers_count || 0,
        pushed_at: repo.pushed_at,
        created_at: repo.created_at
      };
    }

    if (sortSelect) {
      sortSelect.addEventListener("change", function () {
        if (repos.length) render();
      });
    }

    // A short session cache keeps repeat visits fast and well under GitHub's rate limit.
    try {
      var cached = JSON.parse(sessionStorage.getItem(cacheKey) || "null");
      if (cached && Array.isArray(cached.data) && Date.now() - cached.savedAt < cacheMs) {
        repos = cached.data;
        render();
        return;
      }
    } catch (_e) { /* storage blocked: just fetch */ }

    fetch("https://api.github.com/users/" + encodeURIComponent(user) + "/repos?per_page=100&sort=pushed", {
      headers: { Accept: "application/vnd.github+json" }
    })
      .then(function (res) {
        if (!res.ok) throw new Error("GitHub responded with HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        if (!Array.isArray(data)) throw new Error("Unexpected response from GitHub");
        repos = data
          .filter(function (r) { return !r.fork && !r.archived && !r.private; })
          .map(slim);
        try {
          sessionStorage.setItem(cacheKey, JSON.stringify({ savedAt: Date.now(), data: repos }));
        } catch (_e) { /* storage full or blocked */ }
        render();
      })
      .catch(function (err) {
        if (window.console) console.warn(err);
        showError();
      });
  }

  /* ── Contact form validation and submission ───────────────────── */
  function initContactForm() {
    var form = $("#contact-form");
    if (!form) return;

    var status = $("#form-status");
    var submitBtn = $("#contact-submit");
    var counter = $("#message-count");
    // Same patterns as app.py: no mailto-breaking characters before the @, a real hostname after it.
    var EMAIL_RE = /^[^\s@?#&=%\/]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*\.[A-Za-z]{2,}$/;
    var CONTROL_CHARS_RE = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g;
    var MIN_MESSAGE = 20;
    var MAX_MESSAGE = 2000;
    var FIELDS = ["name", "email", "company", "reason", "message", "consent"];
    var touched = {};

    // Count characters the way Python does (an emoji is one character, not two).
    function charCount(s) { return Array.from(s).length; }

    // Same rules as validate_contact() in app.py. Each returns an error message or "".
    var rules = {
      name: function (v) {
        if (!v) return "Please enter your name.";
        if (charCount(v) < 2) return "Your name should be at least 2 characters.";
        if (charCount(v) > 80) return "Please keep your name under 80 characters.";
        if (/\d/.test(v)) return "Names can't include numbers.";
        return "";
      },
      email: function (v) {
        if (!v) return "Please enter your email address.";
        if (v.length > 254 || !EMAIL_RE.test(v)) return "Please enter a valid email address, like name@example.com.";
        return "";
      },
      company: function (v) {
        return charCount(v) > 100 ? "Please keep the company name under 100 characters." : "";
      },
      reason: function (v) {
        return v ? "" : "Please choose a reason for reaching out.";
      },
      message: function (v) {
        if (!v) return "Please write a short message.";
        if (charCount(v) < MIN_MESSAGE) return "Please write at least 20 characters so I know how to help.";
        if (charCount(v) > MAX_MESSAGE) return "Please keep your message under 2,000 characters.";
        return "";
      },
      consent: function (checked) {
        return checked ? "" : "Please confirm it's okay to store your message so I can reply.";
      }
    };

    function el(name) { return form.elements[name]; }

    function value(name) {
      var field = el(name);
      if (field.type === "checkbox") return field.checked;
      return (field.value || "").replace(CONTROL_CHARS_RE, "").trim();
    }

    function setFieldError(name, message) {
      var field = el(name);
      var error = $("#" + name + "-error");
      if (message) {
        field.setAttribute("aria-invalid", "true");
        field.classList.add("is-invalid");
        field.classList.remove("is-valid");
      } else {
        field.removeAttribute("aria-invalid");
        field.classList.remove("is-invalid");
        var hasValue = field.type === "checkbox" ? field.checked : !!field.value.trim();
        field.classList.toggle("is-valid", hasValue && field.type !== "checkbox");
      }
      if (error) error.textContent = message || "";
    }

    function check(name) {
      var message = rules[name](value(name));
      setFieldError(name, message);
      return message;
    }

    function setStatus(kind, message) {
      if (!status) return;
      status.hidden = !message;
      status.className = "form-status" + (kind ? " is-" + kind : "");
      status.textContent = message || "";
    }

    function updateCounter() {
      if (!counter) return;
      var len = charCount(value("message"));
      if (len === 0) {
        counter.textContent = "At least " + MIN_MESSAGE + " characters";
      } else if (len < MIN_MESSAGE) {
        counter.textContent = (MIN_MESSAGE - len) + " more " + (MIN_MESSAGE - len === 1 ? "character" : "characters") + " needed";
      } else {
        counter.textContent = len + " / " + MAX_MESSAGE + " characters";
      }
      counter.classList.toggle("is-over", len > MAX_MESSAGE);
    }

    // Check a field when the visitor leaves it, then live while they fix it.
    FIELDS.forEach(function (name) {
      var field = el(name);
      if (!field) return;
      var liveEvent = field.type === "checkbox" || field.tagName === "SELECT" ? "change" : "input";
      field.addEventListener("blur", function () {
        touched[name] = true;
        check(name);
      });
      field.addEventListener(liveEvent, function () {
        if (name === "message") updateCounter();
        if (touched[name] || field.getAttribute("aria-invalid") === "true") check(name);
      });
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();

      var firstInvalid = null;
      var problems = 0;
      FIELDS.forEach(function (name) {
        touched[name] = true;
        if (check(name)) {
          problems++;
          if (!firstInvalid) firstInvalid = el(name);
        }
      });

      if (problems) {
        setStatus("error", problems === 1
          ? "Please fix the highlighted field and try again."
          : "Please fix the " + problems + " highlighted fields and try again.");
        firstInvalid.focus();
        return;
      }

      var payload = {
        name: value("name"),
        email: value("email"),
        company: value("company"),
        reason: value("reason"),
        message: value("message"),
        consent: value("consent"),
        website: el("website") ? el("website").value : ""
      };

      submitBtn.disabled = true;
      submitBtn.textContent = "Sending…";
      setStatus("", "");

      fetch(form.getAttribute("data-api"), {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload)
      })
        .then(function (res) {
          return res.json()
            .catch(function () { return {}; })
            .then(function (data) { return { ok: res.ok, data: data || {} }; });
        })
        .then(function (result) {
          if (result.ok && result.data.ok) {
            var firstName = payload.name.split(/\s+/)[0];
            form.reset();
            setStatus("success", "Thanks, " + firstName + "! Your message was sent. I'll get back to you soon.");
            return;
          }
          var serverErrors = result.data.errors || {};
          var names = Object.keys(serverErrors).filter(function (n) { return rules[n]; });
          names.forEach(function (n) { setFieldError(n, serverErrors[n]); });
          if (names.length) el(names[0]).focus();
          setStatus("error", result.data.error || "Something went wrong. Please try again or email me directly.");
        })
        .catch(function () {
          setStatus("error", "Your message couldn't be sent. Check your connection and try again, or email me directly.");
        })
        .then(function () {
          submitBtn.disabled = false;
          submitBtn.textContent = "Send message";
        });
    });

    // "Clear form" resets the fields; clear the messages and highlights too.
    form.addEventListener("reset", function () {
      setTimeout(function () {
        touched = {};
        FIELDS.forEach(function (name) {
          var field = el(name);
          if (!field) return;
          field.removeAttribute("aria-invalid");
          field.classList.remove("is-invalid", "is-valid");
          var error = $("#" + name + "-error");
          if (error) error.textContent = "";
        });
        if (status && status.classList.contains("is-error")) setStatus("", "");
        updateCounter();
      }, 0);
    });

    updateCounter();
  }

  /* ── Resume: draw every PDF page into the page with PDF.js ────── */
  function initResumeViewer() {
    var doc = $("#resume-doc");
    var pages = $("#resume-pages");
    if (!doc || !pages) return;

    var src = doc.getAttribute("data-src");
    var lib = window.pdfjsLib;
    var pdf = null;
    var renderedWidth = 0;
    var busy = false;

    function showFallback() {
      pages.innerHTML = "";
      var p = document.createElement("p");
      p.className = "resume-status";
      p.appendChild(document.createTextNode("The resume preview couldn't load here. "));
      var a = document.createElement("a");
      a.href = src;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = "Open the PDF instead";
      p.appendChild(a);
      p.appendChild(document.createTextNode("."));
      pages.appendChild(p);
    }

    // Render at the container's current width (times the screen's pixel density so text stays sharp).
    function render() {
      if (!pdf || busy) return;
      var width = pages.clientWidth;
      if (!width || Math.abs(width - renderedWidth) < 2) return;
      busy = true;
      renderedWidth = width;
      var density = Math.min(window.devicePixelRatio || 1, 3);
      var loads = [];
      for (var n = 1; n <= pdf.numPages; n++) loads.push(pdf.getPage(n));

      Promise.all(loads)
        .then(function (list) {
          var canvases = [];
          var draws = list.map(function (page, i) {
            var base = page.getViewport({ scale: 1 });
            var viewport = page.getViewport({ scale: (width / base.width) * density });
            var canvas = document.createElement("canvas");
            canvas.className = "resume-page";
            canvas.width = Math.floor(viewport.width);
            canvas.height = Math.floor(viewport.height);
            canvas.setAttribute("role", "img");
            canvas.setAttribute("aria-label", "Resume of Samuel Ryan Andrew Simonds, page " + (i + 1) + " of " + list.length);
            canvases.push(canvas);
            return page.render({ canvasContext: canvas.getContext("2d"), viewport: viewport }).promise;
          });
          return Promise.all(draws).then(function () {
            // Swap in the finished pages at once so there is no flicker.
            pages.innerHTML = "";
            canvases.forEach(function (c) { pages.appendChild(c); });
          });
        })
        .catch(function (err) {
          if (window.console) console.warn(err);
          showFallback();
        })
        .then(function () {
          busy = false;
          if (Math.abs(pages.clientWidth - renderedWidth) >= 2) render();
        });
    }

    if (!lib || !src) { showFallback(); return; }
    lib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
    lib.getDocument(src).promise
      .then(function (loaded) { pdf = loaded; render(); })
      .catch(function (err) {
        if (window.console) console.warn(err);
        showFallback();
      });

    var timer = null;
    window.addEventListener("resize", function () {
      clearTimeout(timer);
      timer = setTimeout(render, 150);
    });
  }

  /* ── Footer year ──────────────────────────────────────────────── */
  function initYear() {
    $$("[data-year]").forEach(function (node) { node.textContent = String(new Date().getFullYear()); });
  }

  initNavToggle();
  initSkillsFilter();
  initGitHubRepos();
  initContactForm();
  initResumeViewer();
  initYear();
})();
