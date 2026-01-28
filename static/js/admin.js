/* ── Admin JS: CRUD + Live Preview ─────────────────────────────── */
(function () {
  "use strict";

  const S = window.__INITIAL__;
  let github = (S.github || []).map(l => ({ ...l }));
  let website = (S.website || []).map(l => ({ ...l }));
  let photoExists = S.photoExists;
  let photoPreviewURL = photoExists ? "/assets/photo?" + Date.now() : null;
  let resumes = (S.resumes || []);

  /* ── DOM refs ─────────────────────────────────────────────────── */
  const $id = id => document.getElementById(id);
  const githubEditor   = $id("githubEditor");
  const websiteEditor  = $id("websiteEditor");
  const addGithubBtn   = $id("addGithubBtn");
  const addWebsiteBtn  = $id("addWebsiteBtn");
  const saveBtn        = $id("saveBtn");
  const saveStatus     = $id("saveStatus");
  const photoInput     = $id("photoInput");
  const photoInputHidden = $id("photoInputHidden");
  const photoDeleteBtn = $id("photoDeleteBtn");
  const resumeInput    = $id("resumeInput");
  const resumeLocale   = $id("resumeLocale");
  const resumeListHint = $id("resumeListHint");

  // Preview refs
  const previewPhoto       = $id("previewPhoto");
  const previewPlaceholder = $id("previewPhotoPlaceholder");
  const previewPairedLinks = $id("previewPairedLinks");
  const previewResumeBtn   = $id("previewResumeBtn");

  /* ── Render link editors ──────────────────────────────────────── */
  function renderEditor(container, list, kind) {
    container.innerHTML = "";
    list.forEach((item, i) => {
      const row = document.createElement("div");
      row.className = "link-editor-row";

      const idx = document.createElement("span");
      idx.className = "pair-index";
      idx.textContent = (i + 1);

      const labelIn = document.createElement("input");
      labelIn.type = "text";
      labelIn.placeholder = "Label";
      labelIn.value = item.label || "";
      labelIn.addEventListener("input", () => { item.label = labelIn.value; renderPreview(); });

      const urlIn = document.createElement("input");
      urlIn.type = "text";
      urlIn.placeholder = "URL";
      urlIn.value = item.url || "";
      urlIn.addEventListener("input", () => { item.url = urlIn.value; renderPreview(); });

      const rm = document.createElement("button");
      rm.type = "button";
      rm.className = "remove-link";
      rm.textContent = "×";
      rm.addEventListener("click", () => {
        list.splice(i, 1);
        renderEditor(container, list, kind);
        renderPreview();
      });

      row.append(idx, labelIn, urlIn, rm);
      container.appendChild(row);
    });
  }

  function addLink(list, container, kind) {
    if (list.length >= 5) return;
    list.push({ label: "", url: "", kind: kind, sort_order: list.length });
    renderEditor(container, list, kind);
    renderPreview();
  }

  addGithubBtn.addEventListener("click", () => addLink(github, githubEditor, "github"));
  addWebsiteBtn.addEventListener("click", () => addLink(website, websiteEditor, "website"));

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

    // Resume btn
    if (resumes.length > 0) {
      previewResumeBtn.classList.remove("hidden");
      previewResumeBtn.href = "/assets/resume";
    } else {
      previewResumeBtn.classList.add("hidden");
    }

    // Links - paired display
    renderPairedPreview();
  }

  function renderPairedPreview() {
    previewPairedLinks.innerHTML = "";
    const gf = github.filter(l => l.label || l.url);
    const wf = website.filter(l => l.label || l.url);
    const max = Math.max(gf.length, wf.length);
    if (!max) {
      previewPairedLinks.innerHTML = '<div class="muted">No links saved.</div>';
      return;
    }
    for (let i = 0; i < max; i++) {
      const row = document.createElement("div");
      row.className = "paired-row";
      row.appendChild(makeLinkCell(gf[i]));
      row.appendChild(makeLinkCell(wf[i]));
      previewPairedLinks.appendChild(row);
    }
  }

  function makeLinkCell(l) {
    const div = document.createElement("div");
    if (!l) { div.innerHTML = '<div class="link-item" style="visibility:hidden">&nbsp;</div>'; return div; }
    const a = document.createElement("a");
    a.className = "link-item";
    a.href = l.url || "#";
    a.target = "_blank";
    a.rel = "noreferrer";
    a.innerHTML =
      '<div class="link-label">' + escHtml(l.label) + '</div>' +
      '<div class="link-url">' + escHtml(l.url) + '</div>';
    div.appendChild(a);
    return div;
  }

  function escHtml(s) {
    const d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
  }

  /* ── Photo upload ─────────────────────────────────────────────── */
  function handlePhotoFile(file) {
    if (!file) return;
    const fd = new FormData();
    fd.append("photo", file);
    fetch("/admin/api/photo", { method: "POST", body: fd })
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(() => {
        photoExists = true;
        photoPreviewURL = "/assets/photo?" + Date.now();
        rebuildAdminPhoto();
        renderPreview();
      })
      .catch(() => alert("Photo upload failed."));
  }

  if (photoInput) photoInput.addEventListener("change", e => handlePhotoFile(e.target.files[0]));
  if (photoInputHidden) photoInputHidden.addEventListener("change", e => handlePhotoFile(e.target.files[0]));

  /* Delete photo */
  function deletePhoto() {
    fetch("/admin/api/photo", { method: "DELETE" })
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(() => {
        photoExists = false;
        photoPreviewURL = null;
        rebuildAdminPhoto();
        renderPreview();
      })
      .catch(() => alert("Delete failed."));
  }

  if (photoDeleteBtn) photoDeleteBtn.addEventListener("click", deletePhoto);

  function rebuildAdminPhoto() {
    const wrap = document.querySelector(".admin-photo-frame");
    if (!wrap) return;
    wrap.innerHTML = "";
    if (photoExists && photoPreviewURL) {
      const del = document.createElement("button");
      del.className = "photo-delete";
      del.type = "button";
      del.setAttribute("aria-label", "Delete photo");
      del.textContent = "×";
      del.addEventListener("click", deletePhoto);
      const img = document.createElement("img");
      img.className = "profile-photo";
      img.id = "adminPhotoPreview";
      img.src = photoPreviewURL;
      img.alt = "Profile photo";
      wrap.append(del, img);
    } else {
      const ph = document.createElement("div");
      ph.className = "photo-placeholder";
      ph.id = "adminPhotoPlaceholder";
      ph.innerHTML = '<div class="muted">No photo uploaded</div>';
      const lbl = document.createElement("label");
      lbl.className = "btn-outline file-btn";
      lbl.textContent = "Add photo";
      const inp = document.createElement("input");
      inp.id = "photoInput";
      inp.type = "file";
      inp.accept = "image/*";
      inp.setAttribute("capture", "environment");
      inp.hidden = true;
      inp.addEventListener("change", e => handlePhotoFile(e.target.files[0]));
      lbl.appendChild(inp);
      ph.appendChild(lbl);
      wrap.appendChild(ph);
    }
  }

  /* ── Resume upload ────────────────────────────────────────────── */
  if (resumeInput) {
    resumeInput.addEventListener("change", e => {
      const file = e.target.files[0];
      if (!file) return;
      const locale = resumeLocale.value;
      const fd = new FormData();
      fd.append("resume", file);
      fd.append("locale", locale);
      fetch("/admin/api/resume", { method: "POST", body: fd })
        .then(r => { if (!r.ok) throw new Error(); return r.json(); })
        .then(() => { refreshState(); })
        .catch(() => alert("Resume upload failed."));
    });
  }

  function renderResumeList() {
    if (!resumeListHint) return;
    if (!resumes.length) {
      resumeListHint.innerHTML = "No resumes uploaded yet.";
      return;
    }
    let html = '<div class="resume-list">';
    resumes.forEach(r => {
      html += '<div class="resume-list-item">' +
        '<span class="resume-locale-tag">' + escHtml(r.locale) + '</span>' +
        '<span>' + escHtml(r.filename) + '</span>' +
        '<button type="button" class="remove-link" data-locale="' + escHtml(r.locale) + '">×</button>' +
        '</div>';
    });
    html += '</div>';
    resumeListHint.innerHTML = html;

    // Bind delete
    resumeListHint.querySelectorAll("button[data-locale]").forEach(btn => {
      btn.addEventListener("click", () => {
        const loc = btn.dataset.locale;
        fetch("/admin/api/resume?locale=" + encodeURIComponent(loc), { method: "DELETE" })
          .then(r => { if (!r.ok) throw new Error(); return r.json(); })
          .then(() => refreshState())
          .catch(() => alert("Delete failed."));
      });
    });
  }

  /* ── Save links ───────────────────────────────────────────────── */
  saveBtn.addEventListener("click", () => {
    saveStatus.textContent = "Saving…";
    fetch("/admin/api/links", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ github: github, website: website })
    })
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(() => { saveStatus.textContent = "Saved!"; setTimeout(() => saveStatus.textContent = "", 2000); })
      .catch(() => { saveStatus.textContent = "Error saving."; });
  });

  /* ── Refresh full state ───────────────────────────────────────── */
  function refreshState() {
    fetch("/admin/api/state")
      .then(r => r.json())
      .then(data => {
        photoExists = data.photo_exists;
        photoPreviewURL = photoExists ? "/assets/photo?" + Date.now() : null;
        resumes = data.resumes || [];
        github = data.github_links || [];
        website = data.website_links || [];
        renderEditor(githubEditor, github, "github");
        renderEditor(websiteEditor, website, "website");
        renderResumeList();
        rebuildAdminPhoto();
        renderPreview();
      });
  }

  /* ── Init ──────────────────────────────────────────────────────── */
  renderEditor(githubEditor, github, "github");
  renderEditor(websiteEditor, website, "website");
  renderResumeList();
  renderPreview();
})();
