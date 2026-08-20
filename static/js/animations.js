/* =========================================================================
   MS Photo Studio - cinematic motion (Lenis smooth scroll + GSAP reveals)
   ========================================================================= */
(function () {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const skipSmooth = document.body.dataset.lenis === "off";

  /* ---- graceful fallback: IntersectionObserver reveals ------------------ */
  const fallbackReveal = function () {
    const items = document.querySelectorAll("[data-reveal]");
    if (!("IntersectionObserver" in window)) {
      items.forEach(function (el) { el.classList.add("is-visible"); });
      return;
    }
    const observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );
    items.forEach(function (el) { observer.observe(el); });
  };

  const start = function () {
    if (reduceMotion || typeof window.gsap === "undefined" || skipSmooth) {
      fallbackReveal();
      return;
    }

    const gsap = window.gsap;
    if (window.ScrollTrigger) gsap.registerPlugin(window.ScrollTrigger);

    /* ---- Lenis smooth scrolling ---------------------------------------- */
    let lenis = null;
    const LenisCtor = window.Lenis || (window.lenis && window.lenis.default);
    if (typeof LenisCtor === "function") {
      lenis = new LenisCtor({
        duration: 1.15,
        easing: function (t) { return Math.min(1, 1.001 - Math.pow(2, -10 * t)); },
        smoothWheel: true,
        syncTouch: false,
      });
      lenis.on("scroll", function () {
        if (window.ScrollTrigger) window.ScrollTrigger.update();
        if (window.LA && typeof window.LA.onScroll === "function") window.LA.onScroll();
      });
      gsap.ticker.add(function (time) { lenis.raf(time * 1000); });
      gsap.ticker.lagSmoothing(0);
      window.LA = window.LA || {};
      window.LA.lenis = lenis;

      // Smooth in-page anchors via Lenis
      document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener("click", function (event) {
          const id = anchor.getAttribute("href");
          if (!id || id === "#") return;
          const target = document.querySelector(id);
          if (!target) return;
          event.preventDefault();
          lenis.scrollTo(target, { offset: -80 });
        });
      });
    }

    /* ---- hero entrance -------------------------------------------------- */
    const heroTitle = document.querySelector("[data-hero-title]");
    if (heroTitle) {
      const lines = heroTitle.querySelectorAll(".split-line > span");
      const targets = lines.length ? lines : [heroTitle];
      gsap.from(targets, {
        yPercent: 110,
        opacity: 0,
        duration: 1.3,
        ease: "power4.out",
        stagger: 0.12,
        delay: 0.25,
      });
    }

    document.querySelectorAll("[data-hero-fade]").forEach(function (el, index) {
      gsap.from(el, {
        y: 26,
        opacity: 0,
        duration: 1.1,
        ease: "power3.out",
        delay: 0.6 + index * 0.12,
      });
    });

    /* ---- scroll reveals -------------------------------------------------- */
    document.querySelectorAll("[data-reveal]").forEach(function (el) {
      const delay = parseFloat(el.getAttribute("data-reveal-delay") || "0");
      gsap.fromTo(
        el,
        { y: 40, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 1.05,
          ease: "power3.out",
          delay: delay,
          scrollTrigger: { trigger: el, start: "top 88%", once: true },
        }
      );
      el.classList.add("is-visible");
    });

    /* ---- staggered grids -------------------------------------------------- */
    document.querySelectorAll("[data-stagger]").forEach(function (grid) {
      const children = grid.children;
      if (!children.length) return;
      gsap.fromTo(
        children,
        { y: 48, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 1,
          ease: "power3.out",
          stagger: 0.08,
          scrollTrigger: { trigger: grid, start: "top 85%", once: true },
        }
      );
    });

    /* ---- parallax media ---------------------------------------------------- */
    if (window.ScrollTrigger) {
      document.querySelectorAll("[data-parallax]").forEach(function (el) {
        const strength = parseFloat(el.getAttribute("data-parallax")) || 12;
        gsap.to(el, {
          yPercent: strength,
          ease: "none",
          scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: true },
        });
      });

      /* ---- counters ---------------------------------------------------- */
      document.querySelectorAll("[data-count]").forEach(function (el) {
        const target = parseFloat(el.getAttribute("data-count")) || 0;
        const state = { value: 0 };
        gsap.to(state, {
          value: target,
          duration: 1.8,
          ease: "power2.out",
          scrollTrigger: { trigger: el, start: "top 90%", once: true },
          onUpdate: function () {
            el.textContent = Math.round(state.value).toLocaleString();
          },
        });
      });
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      window.setTimeout(start, 60);
    });
  } else {
    window.setTimeout(start, 60);
  }
})();