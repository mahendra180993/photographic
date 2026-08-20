/* =========================================================================
   Lumina Atelier - optional Three.js particle veil behind the hero.
   Degrades silently when WebGL or the CDN is unavailable.
   ========================================================================= */
(function () {
  "use strict";

  const canvas = document.getElementById("hero-canvas");
  if (!canvas) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  if (typeof window.THREE === "undefined") return;

  const THREE = window.THREE;
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
  } catch (err) {
    return;
  }

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 100);
  camera.position.z = 14;

  const COUNT = 620;
  const positions = new Float32Array(COUNT * 3);
  for (let i = 0; i < COUNT; i += 1) {
    positions[i * 3] = (Math.random() - 0.5) * 34;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 20;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 18;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));

  const material = new THREE.PointsMaterial({
    color: new THREE.Color("#D4AF37"),
    size: 0.055,
    transparent: true,
    opacity: 0.55,
    depthWrite: false,
  });

  const points = new THREE.Points(geometry, material);
  scene.add(points);

  const pointer = { x: 0, y: 0 };
  window.addEventListener("pointermove", function (event) {
    pointer.x = (event.clientX / window.innerWidth - 0.5) * 2;
    pointer.y = (event.clientY / window.innerHeight - 0.5) * 2;
  });

  const resize = function () {
    const parent = canvas.parentElement;
    if (!parent) return;
    const width = parent.clientWidth;
    const height = parent.clientHeight;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height, false);
    camera.aspect = width / Math.max(height, 1);
    camera.updateProjectionMatrix();
  };

  let frame = 0;
  const render = function () {
    frame = window.requestAnimationFrame(render);
    points.rotation.y += 0.0009;
    points.rotation.x += 0.0004;
    camera.position.x += (pointer.x * 1.6 - camera.position.x) * 0.03;
    camera.position.y += (-pointer.y * 1.1 - camera.position.y) * 0.03;
    camera.lookAt(scene.position);
    renderer.render(scene, camera);
  };

  window.addEventListener("resize", resize);
  resize();
  render();

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      window.cancelAnimationFrame(frame);
    } else {
      render();
    }
  });
})();