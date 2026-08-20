/* =========================================================================
   Lumina Atelier - client gallery: lightbox, selection, bulk actions
   ========================================================================= */
(function () {
  "use strict";

  const root = document.getElementById("client-gallery");
  if (!root) return;

  const selectUrl = root.dataset.selectUrl;
  const limit = parseInt(root.dataset.selectionLimit || "0", 10);
  const counter = document.querySelectorAll("[data-selected-count]");
  const submitBar = document.getElementById("selection-bar");

  const updateCount = function (count) {
    counter.forEach(function (el) { el.textContent = count; });
    if (submitBar) {
      submitBar.classList.toggle("translate-y-32", count === 0);
      submitBar.classList.toggle("opacity-0", count === 0);
    }
    const progress = document.getElementById("selection-progress");
    if (progress && limit > 0) {
      progress.style.width = Math.min(100, (count / limit) * 100) + "%";
    }
  };

  /* ---- selection toggles ------------------------------------------------ */
  root.addEventListener("click", function (event) {
    const button = event.target.closest("[data-select-image]");
    if (!button) return;
    event.preventDefault();

    const card = button.closest(".photo-card");
    const imageId = button.getAttribute("data-select-image");
    if (!card || !imageId || !selectUrl) return;

    card.classList.add("is-busy");
    window.LA.postJSON(selectUrl, { image: imageId })
      .then(function (data) {
        card.classList.remove("is-busy");
        if (!data.ok) {
          window.LA.toast(data.error || "Could not update your selection.", "error");
          if (typeof data.count === "number") updateCount(data.count);
          return;
        }
        card.classList.toggle("is-selected", data.selected);
        const label = button.querySelector("[data-select-label]");
        if (label) label.textContent = data.selected ? "Selected" : "Select";
        updateCount(data.count);
      })
      .catch(function () {
        card.classList.remove("is-busy");
        window.LA.toast("Network error - please try again.", "error");
      });
  });

  /* ---- filter: all / selected ------------------------------------------ */
  document.querySelectorAll("[data-filter]").forEach(function (tab) {
    tab.addEventListener("click", function () {
      const mode = tab.getAttribute("data-filter");
      document.querySelectorAll("[data-filter]").forEach(function (other) {
        const active = other === tab;
        other.classList.toggle("is-active", active);
        other.classList.toggle("text-gold", active);
        other.classList.toggle("text-paper/50", !active);
      });
      root.querySelectorAll(".photo-card").forEach(function (card) {
        const selected = card.classList.contains("is-selected");
        const show = mode === "all" || (mode === "selected" && selected);
        card.classList.toggle("hidden", !show);
      });
    });
  });

  /* ---- lightbox --------------------------------------------------------- */
  const initLightbox = function () {
    if (typeof window.lightGallery !== "function") return;
    const container = document.getElementById("lightgallery");
    if (!container) return;
    const plugins = [];
    if (window.lgZoom) plugins.push(window.lgZoom);
    if (window.lgThumbnail) plugins.push(window.lgThumbnail);
    window.lightGallery(container, {
      selector: "a[data-lg]",
      plugins: plugins,
      speed: 420,
      download: root.dataset.allowDownload === "1",
      counter: true,
      thumbnail: true,
      zoom: true,
      licenseKey: "0000-0000-000-0000",
    });
  };

  if (document.readyState === "complete") {
    initLightbox();
  } else {
    window.addEventListener("load", initLightbox);
  }

  /* ---- submit confirmation ---------------------------------------------- */
  const submitForm = document.getElementById("selection-submit-form");
  if (submitForm) {
    submitForm.addEventListener("submit", function (event) {
      const count = parseInt(document.querySelector("[data-selected-count]").textContent || "0", 10);
      if (count === 0) {
        event.preventDefault();
        window.LA.toast("Select at least one photograph first.", "warning");
        return;
      }
      if (!window.confirm("Send " + count + " photograph(s) to the studio?")) {
        event.preventDefault();
      }
    });
  }

  /* ---- selection panel toggle -------------------------------------------- */
  const panel = document.getElementById("submit-panel");
  document.querySelectorAll("[data-toggle-submit-panel]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (panel) panel.classList.toggle("hidden");
    });
  });

  updateCount(parseInt(root.dataset.selectedCount || "0", 10));
})();