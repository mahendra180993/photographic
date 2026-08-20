/* =========================================================================
   MS Photo Studio - core UI behaviour (navigation, toasts, utilities)
   ========================================================================= */
(function () {
  "use strict";

  const doc = document;

  /* ---- helpers --------------------------------------------------------- */
  window.LA = window.LA || {};

  LA.getCookie = function (name) {
    const match = doc.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return match ? decodeURIComponent(match.pop()) : "";
  };

  LA.csrf = function () {
    const input = doc.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : LA.getCookie("csrftoken");
  };

  LA.postJSON = function (url, payload) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": LA.csrf(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(payload || {}),
    }).then(function (response) {
      return response.json().catch(function () {
        return { ok: false, error: "Unexpected server response." };
      });
    });
  };

  LA.toast = function (message, tone) {
    let stack = doc.getElementById("toast-stack");
    if (!stack) {
      stack = doc.createElement("div");
      stack.id = "toast-stack";
      stack.className =
        "pointer-events-none fixed right-5 top-24 z-[80] flex w-[min(360px,90vw)] flex-col gap-3";
      doc.body.appendChild(stack);
    }
    const palette = {
      success: "border-emerald-200 bg-emerald-50 text-emerald-800",
      error: "border-rose-200 bg-rose-50 text-rose-800",
      warning: "border-amber-200 bg-amber-50 text-amber-900",
      info: "border-slate-200 bg-white text-slate-700",
    };
    const el = doc.createElement("div");
    el.className =
      "toast pointer-events-auto rounded-xl border px-4 py-3 text-sm shadow-lift " +
      (palette[tone] || palette.info);
    el.textContent = message;
    stack.appendChild(el);
    window.setTimeout(function () {
      el.classList.add("is-leaving");
      window.setTimeout(function () {
        el.remove();
      }, 400);
    }, 4200);
  };

  /* ---- page reveal ----------------------------------------------------- */
  window.requestAnimationFrame(function () {
    doc.body.classList.add("is-ready");
  });

  /* ---- sticky / hiding header ------------------------------------------ */
  const header = doc.getElementById("site-header");
  const progress = doc.getElementById("scroll-progress");

  const getScrollY = function () {
    if (window.LA && window.LA.lenis && typeof window.LA.lenis.scroll === "number") {
      return window.LA.lenis.scroll;
    }
    return window.scrollY || doc.documentElement.scrollTop || 0;
  };

  const getScrollMax = function () {
    const docHeight = Math.max(
      doc.body.scrollHeight,
      doc.documentElement.scrollHeight,
      doc.body.offsetHeight,
      doc.documentElement.offsetHeight
    );
    return Math.max(1, docHeight - window.innerHeight);
  };

  if (header) {
    const darkHero = doc.body.dataset.headerTheme === "dark";
    let ticking = false;

    if (darkHero) header.classList.add("is-dark");
    // Always keep the navbar visible for navigation (including at the footer)
    header.classList.remove("is-hidden");

    const updateHeader = function () {
      const y = getScrollY();

      if (y > 48) {
        header.classList.add("is-solid");
      } else {
        header.classList.remove("is-solid");
      }

      header.classList.remove("is-hidden");

      if (progress) {
        progress.style.width = Math.min(100, (y / getScrollMax()) * 100) + "%";
      }

      ticking = false;
    };

    const onScroll = function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(updateHeader);
    };

    updateHeader();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    window.LA = window.LA || {};
    window.LA.onScroll = onScroll;
  }

  /* ---- mobile menu ----------------------------------------------------- */
  const menu = doc.getElementById("mobile-menu");
  const openBtn = doc.getElementById("menu-toggle");
  const closeBtn = doc.getElementById("menu-close");

  const setMenu = function (open) {
    if (!menu) return;
    menu.classList.toggle("hidden", !open);
    doc.documentElement.classList.toggle("no-scroll", open);
    doc.body.classList.toggle("no-scroll", open);
    if (openBtn) openBtn.setAttribute("aria-expanded", open ? "true" : "false");

    if (window.LA && window.LA.lenis) {
      if (open && typeof window.LA.lenis.stop === "function") window.LA.lenis.stop();
      if (!open && typeof window.LA.lenis.start === "function") window.LA.lenis.start();
    }
  };

  if (openBtn) {
    openBtn.addEventListener("click", function () {
      const isOpen = openBtn.getAttribute("aria-expanded") === "true";
      setMenu(!isOpen);
    });
  }
  if (closeBtn) closeBtn.addEventListener("click", function () { setMenu(false); });
  if (menu) {
    menu.querySelectorAll("[data-menu-backdrop], a").forEach(function (el) {
      el.addEventListener("click", function () { setMenu(false); });
    });
  }
  doc.addEventListener("keydown", function (event) {
    if (event.key === "Escape") setMenu(false);
  });
  window.addEventListener("resize", function () {
    if (window.innerWidth >= 1024) setMenu(false);
  });

  /* ---- toasts ---------------------------------------------------------- */
  doc.addEventListener("click", function (event) {
    const close = event.target.closest(".toast-close");
    if (!close) return;
    const toast = close.closest(".toast");
    if (!toast) return;
    toast.classList.add("is-leaving");
    window.setTimeout(function () { toast.remove(); }, 400);
  });

  doc.querySelectorAll("#toast-stack .toast").forEach(function (toast, index) {
    window.setTimeout(function () {
      toast.classList.add("is-leaving");
      window.setTimeout(function () { toast.remove(); }, 400);
    }, 5200 + index * 400);
  });

  /* ---- copy-to-clipboard buttons --------------------------------------- */
  doc.addEventListener("click", function (event) {
    const btn = event.target.closest("[data-copy]");
    if (!btn) return;
    const value = btn.getAttribute("data-copy");
    if (!navigator.clipboard) {
      LA.toast("Clipboard unavailable in this browser.", "warning");
      return;
    }
    navigator.clipboard.writeText(value).then(function () {
      LA.toast("Copied to clipboard.", "success");
    });
  });

  /* ---- filter/search auto-submit --------------------------------------- */
  doc.querySelectorAll("[data-autosubmit]").forEach(function (field) {
    field.addEventListener("change", function () {
      const form = field.closest("form");
      if (form) form.submit();
    });
  });

  /* ---- accordions ------------------------------------------------------ */
  doc.querySelectorAll("[data-accordion]").forEach(function (root) {
    root.querySelectorAll("[data-accordion-trigger]").forEach(function (trigger) {
      trigger.addEventListener("click", function () {
        const item = trigger.closest("[data-accordion-item]");
        if (!item) return;
        const panel = item.querySelector("[data-accordion-panel]");
        const isOpen = item.classList.contains("is-open");
        root.querySelectorAll("[data-accordion-item]").forEach(function (other) {
          other.classList.remove("is-open");
          const otherPanel = other.querySelector("[data-accordion-panel]");
          if (otherPanel) otherPanel.style.maxHeight = null;
        });
        if (!isOpen) {
          item.classList.add("is-open");
          if (panel) panel.style.maxHeight = panel.scrollHeight + "px";
        }
      });
    });
  });
})();