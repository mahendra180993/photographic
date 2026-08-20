/* =========================================================================
   Lumina Atelier - studio dashboard interactions
   ========================================================================= */
(function () {
  "use strict";

  const doc = document;

  /* ---- sidebar (mobile) -------------------------------------------------- */
  const sidebar = doc.getElementById("dash-sidebar");
  const backdrop = doc.getElementById("dash-backdrop");
  const setSidebar = function (open) {
    if (!sidebar) return;
    sidebar.classList.toggle("-translate-x-full", !open);
    if (backdrop) backdrop.classList.toggle("hidden", !open);
    doc.documentElement.classList.toggle("no-scroll", open);
    doc.body.classList.toggle("no-scroll", open);
  };
  doc.querySelectorAll("[data-sidebar-open]").forEach(function (btn) {
    btn.addEventListener("click", function () { setSidebar(true); });
  });
  doc.querySelectorAll("[data-sidebar-close]").forEach(function (btn) {
    btn.addEventListener("click", function () { setSidebar(false); });
  });
  window.addEventListener("resize", function () {
    if (window.innerWidth >= 1024) setSidebar(false);
  });
  doc.addEventListener("keydown", function (event) {
    if (event.key === "Escape") setSidebar(false);
  });

  /* ---- confirm destructive actions --------------------------------------- */
  doc.addEventListener("submit", function (event) {
    const form = event.target;
    const message = form.getAttribute("data-confirm");
    if (message && !window.confirm(message)) {
      event.preventDefault();
    }
  });

  /* ---- bulk upload: preview + progress ------------------------------------ */
  const uploadInput = doc.getElementById("gallery-upload-input");
  const uploadForm = doc.getElementById("gallery-upload-form");
  const uploadInfo = doc.getElementById("upload-info");
  const uploadProgress = doc.getElementById("upload-progress");

  if (uploadInput && uploadInfo) {
    uploadInput.addEventListener("change", function () {
      const files = uploadInput.files;
      if (!files || !files.length) {
        uploadInfo.textContent = "No files selected.";
        return;
      }
      let bytes = 0;
      for (let i = 0; i < files.length; i += 1) bytes += files[i].size;
      const mb = (bytes / (1024 * 1024)).toFixed(1);
      uploadInfo.textContent = files.length + " file(s) selected - " + mb + " MB";
    });
  }

  if (uploadForm) {
    uploadForm.addEventListener("submit", function () {
      if (uploadProgress) {
        uploadProgress.classList.remove("hidden");
      }
      const button = uploadForm.querySelector("[type=submit]");
      if (button) {
        button.disabled = true;
        button.textContent = "Uploading...";
      }
    });
  }

  /* ---- drag & drop zone ---------------------------------------------------- */
  const dropzone = doc.getElementById("dropzone");
  if (dropzone && uploadInput) {
    ["dragenter", "dragover"].forEach(function (type) {
      dropzone.addEventListener(type, function (event) {
        event.preventDefault();
        dropzone.classList.add("border-gold", "bg-amber-50/40");
      });
    });
    ["dragleave", "drop"].forEach(function (type) {
      dropzone.addEventListener(type, function (event) {
        event.preventDefault();
        dropzone.classList.remove("border-gold", "bg-amber-50/40");
      });
    });
    dropzone.addEventListener("drop", function (event) {
      if (event.dataTransfer && event.dataTransfer.files.length) {
        uploadInput.files = event.dataTransfer.files;
        uploadInput.dispatchEvent(new Event("change"));
      }
    });
    dropzone.addEventListener("click", function () { uploadInput.click(); });
  }

  /* ---- image reordering (simple drag & drop) -------------------------------- */
  const grid = doc.getElementById("image-grid");
  if (grid && grid.dataset.reorderUrl) {
    let dragged = null;

    grid.querySelectorAll("[draggable=true]").forEach(function (item) {
      item.addEventListener("dragstart", function () {
        dragged = item;
        item.classList.add("opacity-40");
      });
      item.addEventListener("dragend", function () {
        item.classList.remove("opacity-40");
        dragged = null;
        persistOrder();
      });
      item.addEventListener("dragover", function (event) {
        event.preventDefault();
        if (!dragged || dragged === item) return;
        const rect = item.getBoundingClientRect();
        const after = (event.clientX - rect.left) / rect.width > 0.5;
        grid.insertBefore(dragged, after ? item.nextSibling : item);
      });
    });

    const persistOrder = function () {
      const order = Array.prototype.map.call(
        grid.querySelectorAll("[data-image-id]"),
        function (el) { return el.getAttribute("data-image-id"); }
      );
      window.LA.postJSON(grid.dataset.reorderUrl, { order: order }).then(function (data) {
        if (data.ok) window.LA.toast("Order saved.", "success");
      });
    };
  }

  /* ---- searchable tables ---------------------------------------------------- */
  const quickFilter = doc.getElementById("quick-filter");
  if (quickFilter) {
    quickFilter.addEventListener("input", function () {
      const term = quickFilter.value.toLowerCase();
      doc.querySelectorAll("[data-filter-row]").forEach(function (row) {
        row.classList.toggle("hidden", term && row.textContent.toLowerCase().indexOf(term) === -1);
      });
    });
  }
})();