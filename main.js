/* ============================================================
   main.js — dynamic rendering of publications, conferences,
   projects and experiences from JSON files.
   Add a new paper → edit data/publications.json, nothing else.
   ============================================================ */

(function () {
  "use strict";

  // -----------------------------
  // Small helpers
  // -----------------------------
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  // Minimal HTML escaper for fields that must be treated as plain text
  // (title, bibtex, abstract). Fields containing HTML (role, description)
  // are injected as-is on purpose.
  const escapeHTML = (s) =>
    String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");

  async function loadJSON(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
    return res.json();
  }

  // -----------------------------
  // Renderers
  // -----------------------------
  function renderPublication(pub) {
    const absId = `abs-${pub.id}`;
    const bibId = `bib-${pub.id}`;

    // Support both the new enriched schema (venueFull) and simple `venue`
    const venue = pub.venueFull || pub.venue || "";

    // Authors list (if present, renders a dedicated line)
    const authorsLine = Array.isArray(pub.authors) && pub.authors.length > 0
      ? `<p class="pub-authors">${pub.authors.map(escapeHTML).join(", ")}</p>`
      : "";

    const doiBlock = pub.doiUrl
      ? `<span class="pub-doi">${escapeHTML(pub.doiLabel || "DOI")}:
           <a href="${pub.doiUrl}" target="_blank" rel="noopener noreferrer">${escapeHTML(pub.doiText || pub.doiUrl)}</a>
         </span>`
      : (pub.doiText
          ? `<span class="pub-doi">${escapeHTML(pub.doiLabel || "DOI")}: ${escapeHTML(pub.doiText)}</span>`
          : "");

    const pdfLink = pub.pdfUrl
      ? `<a href="${pub.pdfUrl}" ${pub.pdfExternal ? 'target="_blank" rel="noopener noreferrer"' : ""}>
           <i class="fa-solid fa-file-pdf"></i> Download PDF
         </a>`
      : "";

    const pageLink = pub.pageUrl
      ? `<a href="${pub.pageUrl}">
           <i class="fa-solid fa-file-lines"></i> Paper page
         </a>`
      : "";

    const links = [pageLink, pdfLink].filter(Boolean).join('<span class="pub-sep">·</span>');

    return `
      <li class="publication">
        <div class="pub-header">
          <span class="pub-year">${escapeHTML(pub.year)}</span>
          <h3>${escapeHTML(pub.title)}</h3>
        </div>

        ${authorsLine}

        <p class="pub-meta">
          ${escapeHTML(venue)}.
          ${doiBlock}
        </p>

        <div class="pub-actions">
          <button type="button" class="toggle-btn" data-target="${absId}">Show abstract</button>
          <button type="button" class="toggle-btn" data-target="${bibId}">Show BibTeX</button>
        </div>

        <div id="${absId}" class="pub-panel" hidden>
          <p class="pub-abstract">${escapeHTML(pub.abstract)}</p>
        </div>

        <div id="${bibId}" class="pub-panel" hidden>
          <pre class="pub-bibtex">${escapeHTML(pub.bibtex)}</pre>
        </div>

        ${links ? `<p class="pub-links">${links}</p>` : ""}
      </li>
    `;
  }

  function renderPublications(data) {
    const papersHTML = (data.papers || []).map(renderPublication).join("");
    const thesesHTML = (data.theses || []).map(renderPublication).join("");

    const container = $("#publications .section-container");
    container.innerHTML = `
      <h2>Publications</h2>

      ${papersHTML ? `
        <h3 class="pub-subtitle">Papers</h3>
        <ol class="pub-list">${papersHTML}</ol>
      ` : ""}

      ${thesesHTML ? `
        <h3 class="pub-subtitle">Theses</h3>
        <ol class="pub-list">${thesesHTML}</ol>
      ` : ""}
    `;
  }

  function renderConferences(list) {
    const container = $("#conferences .section-container");
    const items = list.map((c) => `
      <div class="experience">
        <h3>
          <a href="${c.url}" target="_blank" rel="noopener noreferrer">
            ${escapeHTML(c.name)}
            <i class="fa-solid fa-arrow-up-right-from-square" aria-hidden="true"></i>
          </a>
        </h3>
        <p><strong>Role:</strong> ${c.role}</p>
        <p><strong>Location:</strong> ${escapeHTML(c.location)} · <strong>Dates:</strong> ${escapeHTML(c.dates)}</p>
      </div>
    `).join("");

    container.innerHTML = `<h2>Attended Conferences</h2>${items}`;
  }

  function renderProjects(list) {
    const container = $("#projects .section-container");
    const items = list.map((p) => `
      <div class="project">
        <h3>${escapeHTML(p.title)}</h3>
        <p><strong>Period:</strong> ${escapeHTML(p.period)}</p>
        <p>${p.description}</p>
        ${p.tech ? `<p><strong>Technologies &amp; Skills:</strong> ${escapeHTML(p.tech)}</p>` : ""}
      </div>
    `).join("");

    container.innerHTML = `<h2>Projects</h2>${items}`;
  }

  function renderExperiences(list) {
    const container = $("#experience .section-container");
    const items = list.map((e) => `
      <div class="experience">
        <h3>${escapeHTML(e.title)}</h3>
        <p><strong>Period:</strong> ${escapeHTML(e.period)}</p>
        <p>${e.description}</p>
      </div>
    `).join("");

    container.innerHTML = `<h2>Experiences</h2>${items}`;
  }

  // -----------------------------
  // UI wiring
  // -----------------------------
  function wireSidebar() {
    const menuToggle = $(".menu-toggle");
    const sidebar = $(".sidebar");
    const closeSidebar = $(".close-sidebar");
    const sidebarOverlay = $(".sidebar-overlay");
    const sidebarLinks = $$(".sidebar-link");

    const open = () => {
      sidebar.classList.add("active");
      sidebarOverlay.classList.add("active");
      sidebar.setAttribute("aria-hidden", "false");
    };
    const close = () => {
      sidebar.classList.remove("active");
      sidebarOverlay.classList.remove("active");
      sidebar.setAttribute("aria-hidden", "true");
    };

    menuToggle && menuToggle.addEventListener("click", open);
    closeSidebar && closeSidebar.addEventListener("click", close);
    sidebarOverlay && sidebarOverlay.addEventListener("click", close);
    sidebarLinks.forEach((link) => link.addEventListener("click", close));
  }

  function wireSmoothScroll() {
    // Delegate on document so links added dynamically also work
    document.addEventListener("click", (e) => {
      const link = e.target.closest('a[href^="#"]');
      if (!link) return;
      const targetId = link.getAttribute("href");
      if (targetId.length <= 1) return;

      const targetEl = document.querySelector(targetId);
      if (!targetEl) return;

      e.preventDefault();
      const headerOffset = 80;
      const elementPosition = targetEl.getBoundingClientRect().top + window.scrollY;
      window.scrollTo({
        top: elementPosition - headerOffset,
        behavior: "smooth",
      });
    });
  }

  function wireToggleButtons() {
    // One global listener: works for any button, including those rendered later
    document.addEventListener("click", (e) => {
      const btn = e.target.closest(".toggle-btn");
      if (!btn) return;

      const id = btn.getAttribute("data-target");
      const panel = document.getElementById(id);
      if (!panel) return;

      const wasHidden = panel.hasAttribute("hidden");
      panel.toggleAttribute("hidden");

      const base = btn.textContent.replace(/^(Hide|Show)\s+/, "");
      btn.textContent = (wasHidden ? "Hide " : "Show ") + base;
    });
  }

  // -----------------------------
  // Boot
  // -----------------------------
  async function init() {
    wireSidebar();
    wireSmoothScroll();
    wireToggleButtons();

    // Load all data in parallel; each section renders as soon as its
    // data arrives, so a slow file doesn't block the others.
    const loaders = [
      loadJSON("data/publications.json").then(renderPublications),
      loadJSON("data/conferences.json").then(renderConferences),
      loadJSON("data/projects.json").then(renderProjects),
      loadJSON("data/experiences.json").then(renderExperiences),
    ];

    const results = await Promise.allSettled(loaders);
    results.forEach((r, i) => {
      if (r.status === "rejected") {
        const files = ["publications", "conferences", "projects", "experiences"];
        console.error(`[main.js] Failed to render ${files[i]}:`, r.reason);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
