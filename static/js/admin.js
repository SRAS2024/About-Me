/* ── Admin JS: CRUD + Live Preview ─────────────────────────────── */
(function () {
  "use strict";

  var S = window.__INITIAL__;
  var github = (S.github || []).map(function (l) { return Object.assign({}, l); });
  var website = (S.website || []).map(function (l) { return Object.assign({}, l); });
  var accomplishments = (S.accomplishments || []).map(function (a) { return Object.assign({}, a); });
  var photoExists = S.photoExists;
  var photoPreviewURL = photoExists ? "/assets/photo?" + Date.now() : null;
  var resumes = S.resumes || [];

  /* ── DOM refs ─────────────────────────────────────────────────── */
  var $id = function (id) { return document.getElementById(id); };
  var githubEditor = $id("githubEditor");
  var websiteEditor = $id("websiteEditor");
  var accompEditor = $id("accompEditor");
  var addGithubBtn = $id("addGithubBtn");
  var addWebsiteBtn = $id("addWebsiteBtn");
  var addAccompBtn = $id("addAccompBtn");
  var saveBtn = $id("saveBtn");
  var saveStatus = $id("saveStatus");
  var photoInput = $id("photoInput");
  var photoInputHidden = $id("photoInputHidden");
  var photoDeleteBtn = $id("photoDeleteBtn");
  var resumeInput = $id("resumeInput");
  var resumeLocale = $id("resumeLocale");
  var resumeListHint = $id("resumeListHint");

  // Preview refs
  var previewPhoto = $id("previewPhoto");
  var previewPlaceholder = $id("previewPhotoPlaceholder");
  var previewPortfolio = $id("previewPortfolio");
  var previewPortfolioSection = $id("previewPortfolioSection");
  var previewResumeSection = $id("previewResumeSection");
  var previewResumeBtn = $id("previewResumeBtn");
  var previewAccomplishments = $id("previewAccomplishments");
  var previewAccompSection = $id("previewAccompSection");

  /* ── Helpers ──────────────────────────────────────────────────── */
  function fetchJson(url, options) {
    var opts = Object.assign(
      {
        credentials: "same-origin",
        headers: {}
      },
      options || {}
    );

    return fetch(url, opts).then(function (r) {
      return r.text().then(function (txt) {
        var data = null;
        try { data = txt ? JSON.parse(txt) : null; } catch (_e) { data = null; }
        if (!r.ok) {
          var msg = (data && (data.detail || data.error)) ? (data.detail || data.error) : ("HTTP " + r.status);
          var err = new Error(msg);
          err.status = r.status;
          err.payload = data;
          err.raw = txt;
          throw err;
        }
        return data;
      });
    });
  }

  function resetFileInput(inputEl) {
    if (!inputEl) return;
    try { inputEl.value = ""; } catch (_e) {}
  }

  function showError(prefix, err) {
    var detail = err && err.message ? err.message : "Unknown error";
    alert(prefix + " " + detail);
  }

  /* ── Render link editors ──────────────────────────────────────── */
  function renderLinkEditor(container, list, kind) {
    container.innerHTML = "";
    list.forEach(function (item, i) {
      var row = document.createElement("div");
      row.className = "link-editor-row";

      var idx = document.createElement("span");
      idx.className = "pair-index";
      idx.textContent = (i + 1);

      var labelIn = document.createElement("input");
      labelIn.type = "text";
      labelIn.placeholder = "Label";
      labelIn.value = item.label || "";
      labelIn.addEventListener("input", function () { item.label = labelIn.value; renderPreview(); });

      var urlIn = document.createElement("input");
      urlIn.type = "text";
      urlIn.placeholder = "URL";
      urlIn.value = item.url || "";
      urlIn.addEventListener("input", function () { item.url = urlIn.value; renderPreview(); });

      var rm = document.createElement("button");
      rm.type = "button";
      rm.className = "remove-link";
      rm.textContent = "\u00d7";
      rm.addEventListener("click", function () {
        list.splice(i, 1);
        renderLinkEditor(container, list, kind);
        renderPreview();
      });

      row.append(idx, labelIn, urlIn, rm);
      container.appendChild(row);
    });
  }

  function addLink(list, container, kind) {
    if (list.length >= 5) return;
    list.push({ label: "", url: "", kind: kind, sort_order: list.length });
    renderLinkEditor(container, list, kind);
    renderPreview();
  }

  addGithubBtn.addEventListener("click", function () { addLink(github, githubEditor, "github"); });
  addWebsiteBtn.addEventListener("click", function () { addLink(website, websiteEditor, "website"); });

  /* ── Render accomplishment editor ───────────────────────────── */
  function renderAccompEditor() {
    accompEditor.innerHTML = "";
    accomplishments.forEach(function (item, i) {
      var row = document.createElement("div");
      row.className = "link-editor-row";

      var idx = document.createElement("span");
      idx.className = "pair-index";
      idx.textContent = (i + 1);

      var textIn = document.createElement("textarea");
      textIn.placeholder = "Accomplishment text";
      textIn.value = item.text || "";
      textIn.addEventListener("input", function () { item.text = textIn.value; renderPreview(); });

      var rm = document.createElement("button");
      rm.type = "button";
      rm.className = "remove-link";
      rm.textContent = "\u00d7";
      rm.addEventListener("click", function () {
        accomplishments.splice(i, 1);
        renderAccompEditor();
        renderPreview();
      });

      row.append(idx, textIn, rm);
      accompEditor.appendChild(row);
    });
  }

  addAccompBtn.addEventListener("click", function () {
    if (accomplishments.length >= 20) return;
    accomplishments.push({ text: "", sort_order: accomplishments.length });
    renderAccompEditor();
    renderPreview();
  });

  /* ── Render live preview ──────────────────────────────────────── */
  function renderPreview() {
    // Photo
    if (photoPreviewURL) {
      previewPhoto.src = photoPreviewURL;
      previewPhoto.classList.remove("hidden");
      previewPlaceholder.classList.add("hidden");
    } else {
      previewPhoto.classList.add("hidden");
      previewPlaceholder.classList.remove("hidden");
    }

    // Resume section
    if (resumes.length > 0) {
      previewResumeSection.classList.remove("hidden");
    } else {
      previewResumeSection.classList.add("hidden");
    }

    // Portfolio (only existing links, no empty slots)
    var gf = github.filter(function (l) { return l.label && l.url; });
    var wf = website.filter(function (l) { return l.label && l.url; });
    if (gf.length > 0 || wf.length > 0) {
      previewPortfolioSection.classList.remove("hidden");
      previewPortfolio.innerHTML = "";

      var ghCol = document.createElement("div");
      ghCol.innerHTML = '<div class="portfolio-col-title">GitHub</div>';
      gf.forEach(function (l) { ghCol.appendChild(makeLinkCard(l)); });

      var wsCol = document.createElement("div");
      wsCol.innerHTML = '<div class="portfolio-col-title">Websites</div>';
      wf.forEach(function (l) { wsCol.appendChild(makeLinkCard(l)); });

      previewPortfolio.appendChild(ghCol);
      previewPortfolio.appendChild(wsCol);
    } else {
      previewPortfolioSection.classList.add("hidden");
    }

    // Accomplishments
    var af = accomplishments.filter(function (a) { return a.text && a.text.trim(); });
    if (af.length > 0) {
      previewAccompSection.classList.remove("hidden");
      previewAccomplishments.innerHTML = "";
      af.forEach(function (a) {
        var item = document.createElement("div");
        item.className = "accomplishment-item";
        item.innerHTML = '<span class="accomplishment-bullet"></span><span>' + escHtml(a.text) + "</span>";
        previewAccomplishments.appendChild(item);
      });
    } else {
      previewAccompSection.classList.add("hidden");
    }
  }

  function makeLinkCard(l) {
    var a = document.createElement("a");
    a.className = "link-card";
    a.href = l.url || "#";
    a.target = "_blank";
    a.rel = "noreferrer";
    a.innerHTML =
      '<span class="link-card-label">' + escHtml(l.label) + "</span>" +
      '<span class="link-card-url">' + escHtml(l.url) + "</span>";
    return a;
  }

  function escHtml(s) {
    var d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
  }

  /* ── Photo upload ─────────────────────────────────────────────── */
  function handlePhotoFile(file, inputToReset) {
    if (!file) return;
    var fd = new FormData();
    fd.append("photo", file);

    fetchJson("/admin/api/photo", { method: "POST", body: fd })
      .then(function (_data) {
        photoExists = true;
        photoPreviewURL = "/assets/photo?" + Date.now();
        rebuildAdminPhoto();
        renderPreview();
      })
      .catch(function (err) {
        showError("Photo upload failed.", err);
      })
      .finally(function () {
        resetFileInput(inputToReset);
      });
  }

  if (photoInput) photoInput.addEventListener("change", function (e) { handlePhotoFile(e.target.files[0], photoInput); });
  if (photoInputHidden) photoInputHidden.addEventListener("change", function (e) { handlePhotoFile(e.target.files[0], photoInputHidden); });

  function deletePhoto() {
    fetchJson("/admin/api/photo", { method: "DELETE" })
      .then(function (_data) {
        photoExists = false;
        photoPreviewURL = null;
        rebuildAdminPhoto();
        renderPreview();
      })
      .catch(function (err) {
        showError("Delete failed.", err);
      });
  }

  if (photoDeleteBtn) photoDeleteBtn.addEventListener("click", deletePhoto);

  function rebuildAdminPhoto() {
    var wrap = document.querySelector(".admin-photo-frame");
    if (!wrap) return;
    wrap.innerHTML = "";
    if (photoExists && photoPreviewURL) {
      var del = document.createElement("button");
      del.className = "photo-delete";
      del.type = "button";
      del.setAttribute("aria-label", "Delete photo");
      del.textContent = "\u00d7";
      del.addEventListener("click", deletePhoto);

      var img = document.createElement("img");
      img.className = "profile-photo";
      img.src = photoPreviewURL;
      img.alt = "Profile photo";
      wrap.append(del, img);
    } else {
      var ph = document.createElement("div");
      ph.className = "photo-placeholder";
      ph.innerHTML = '<span class="muted">No photo</span>';

      var lbl = document.createElement("label");
      lbl.className = "btn-outline btn-sm file-btn";
      lbl.textContent = "Add photo";

      var inp = document.createElement("input");
      inp.type = "file";
      inp.accept = "image/*";
      inp.hidden = true;
      inp.addEventListener("change", function (e) { handlePhotoFile(e.target.files[0], inp); });

      lbl.appendChild(inp);
      ph.appendChild(lbl);
      wrap.appendChild(ph);
    }
  }

  /* ── Resume upload ────────────────────────────────────────────── */
  if (resumeInput) {
    resumeInput.addEventListener("change", function (e) {
      var file = e.target.files[0];
      if (!file) return;

      var locale = resumeLocale.value;
      var fd = new FormData();
      fd.append("resume", file);
      fd.append("locale", locale);

      fetchJson("/admin/api/resume", { method: "POST", body: fd })
        .then(function (_data) { refreshState(); })
        .catch(function (err) { showError("Resume upload failed.", err); })
        .finally(function () { resetFileInput(resumeInput); });
    });
  }

  function renderResumeList() {
    if (!resumeListHint) return;
    if (!resumes.length) {
      resumeListHint.innerHTML = "No resumes uploaded yet.";
      return;
    }
    var html = '<div class="resume-list">';
    resumes.forEach(function (r) {
      html +=
        '<div class="resume-list-item">' +
        '<span class="resume-locale-tag">' + escHtml(r.locale) + "</span>" +
        "<span>" + escHtml(r.filename) + "</span>" +
        '<button type="button" class="remove-link" data-locale="' + escHtml(r.locale) + '">\u00d7</button>' +
        "</div>";
    });
    html += "</div>";
    resumeListHint.innerHTML = html;

    resumeListHint.querySelectorAll("button[data-locale]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var loc = btn.dataset.locale;
        fetchJson("/admin/api/resume?locale=" + encodeURIComponent(loc), { method: "DELETE" })
          .then(function (_data) { refreshState(); })
          .catch(function (err) { showError("Delete failed.", err); });
      });
    });
  }

  /* ── Save all ─────────────────────────────────────────────────── */
  saveBtn.addEventListener("click", function () {
    saveStatus.textContent = "Saving\u2026";

    var p1 = fetchJson("/admin/api/links", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ github: github, website: website })
    });

    var p2 = fetchJson("/admin/api/accomplishments", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accomplishments: accomplishments })
    });

    Promise.all([p1, p2])
      .then(function () {
        saveStatus.textContent = "Saved!";
        setTimeout(function () { saveStatus.textContent = ""; }, 2000);
      })
      .catch(function (err) {
        saveStatus.textContent = "Error saving.";
        console.error(err);
      });
  });

  /* ── Refresh full state ───────────────────────────────────────── */
  function refreshState() {
    fetchJson("/admin/api/state", { method: "GET" })
      .then(function (data) {
        photoExists = data.photo_exists;
        photoPreviewURL = photoExists ? "/assets/photo?" + Date.now() : null;
        resumes = data.resumes || [];
        github = data.github_links || [];
        website = data.website_links || [];
        accomplishments = data.accomplishments || [];

        renderLinkEditor(githubEditor, github, "github");
        renderLinkEditor(websiteEditor, website, "website");
        renderAccompEditor();
        renderResumeList();
        rebuildAdminPhoto();
        renderPreview();
      })
      .catch(function (err) {
        console.error(err);
        showError("Failed to refresh admin state.", err);
      });
  }

  /* ── Init ──────────────────────────────────────────────────────── */
  renderLinkEditor(githubEditor, github, "github");
  renderLinkEditor(websiteEditor, website, "website");
  renderAccompEditor();
  renderResumeList();
  renderPreview();
})();
