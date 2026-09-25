// Interactive Hive Tower viewer. mountHiveTower(root) wires up one
// viewer.html block; the root's data-* elements are looked up inside it, so
// the viewer can be embedded in any page (see build-viewer.mjs).
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { buildHiveTower, PARTS } from './hive-model.js';

const SPECS = (d, p) => [
  ['Footprint', '810 × 666 mm'],
  ['Height', `${Math.round(d.crownTop + 110)} mm`],
  ['Stack', `${d.n} × Estonian body (${p.box.w}×${p.box.d}×${p.box.h})`],
  ['Stack open gap', `${p.gap} mm`],
  ['Frame lift', `${p.frameLift} mm, kept vertical`],
  ['Motors', '4 × NEMA23 · 2 × NEMA17 · 4 servos'],
  ['Box open time', '≈ 10 min for 10 frames (simulated)'],
  ['New parts', '≈ €1,660–1,790 (+€320 solar)'],
];

export function mountHiveTower(root) {
  const $ = (name) => root.querySelector(`[data-ht="${name}"]`);
  const canvas = $('canvas');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;

  const camera = new THREE.PerspectiveCamera(35, 1, 0.05, 50);
  camera.position.set(2.6, 1.9, 3.2);
  const controls = new OrbitControls(camera, canvas);
  controls.target.set(0, 0.95, 0);
  controls.enableDamping = true;
  controls.maxPolarAngle = Math.PI * 0.495;
  controls.minDistance = 0.6;
  controls.maxDistance = 8;

  const sun = new THREE.DirectionalLight(0xfff4e0, 2.2);
  sun.position.set(2.5, 4.5, 3);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -1.6, right: 1.6, top: 2.4, bottom: -0.4, near: 0.5, far: 12 });
  sun.shadow.bias = -0.0004;
  scene.add(sun, new THREE.HemisphereLight(0xdfe8ff, 0x3b4a2c, 0.5));
  const redLight = new THREE.PointLight(0xff2a10, 0, 2.2, 1.5);
  scene.add(redLight);

  const groundMat = new THREE.MeshStandardMaterial({ color: 0xb9c2b0, roughness: 1 });
  const ground = new THREE.Mesh(new THREE.CircleGeometry(6, 64), groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  const pad = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.02, 1.2), new THREE.MeshStandardMaterial({ color: 0x9d9a92, roughness: 1 }));
  pad.receiveShadow = true;
  scene.add(ground, pad);

  const applyThemeColors = () => {
    const cs = getComputedStyle(root);
    scene.background = new THREE.Color(cs.getPropertyValue('--ht-scene').trim() || '#dfe3dc');
    groundMat.color.set(cs.getPropertyValue('--ht-ground').trim() || '#b9c2b0');
  };
  applyThemeColors();
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyThemeColors);
  new MutationObserver(applyThemeColors).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  // ---- model ---------------------------------------------------------------
  let tower;
  let time = 0;
  let playing = !matchMedia('(prefers-reduced-motion: reduce)').matches;
  let speed = 1;
  let cladMode = 'ghost';
  const ghostCache = new WeakMap();
  const stepsEl = $('steps');

  function build(boxes, inspect) {
    const keep = tower ? time / tower.timeline.duration : 0;
    if (tower) {
      scene.remove(tower.root);
      tower.root.traverse((o) => o.geometry?.dispose());
    }
    tower = buildHiveTower({ boxes, inspectBox: inspect });
    // Cladding shares materials with the robot; clone so ghosting only hits the cabinet.
    const clones = new Map();
    tower.nodes.cladding.traverse((o) => {
      if (!o.isMesh) return;
      if (!clones.has(o.material)) {
        const c = o.material.clone();
        ghostCache.set(c, { opacity: c.opacity, transparent: c.transparent, depthWrite: c.depthWrite });
        clones.set(o.material, c);
      }
      o.material = clones.get(o.material);
    });
    scene.add(tower.root);
    time = keep * tower.timeline.duration;
    renderSteps();
    renderSpecs();
    setClad(cladMode);
    setXray($('xray').checked);
    controls.target.y = tower.derived.crownTop * tower.MM * 0.5;
  }

  function setClad(mode) {
    cladMode = mode;
    for (const b of $('clad').querySelectorAll('button')) b.setAttribute('aria-pressed', String(b.dataset.value === mode));
    const c = tower.nodes.cladding;
    c.visible = mode !== 'off';
    const seen = new Set();
    c.traverse((o) => {
      if (!o.isMesh || seen.has(o.material)) return;
      seen.add(o.material);
      const orig = ghostCache.get(o.material);
      if (mode === 'ghost') Object.assign(o.material, { transparent: true, opacity: Math.min(orig.opacity, 0.13), depthWrite: false });
      else Object.assign(o.material, orig);
      o.material.needsUpdate = true;
    });
    c.traverse((o) => { if (o.isMesh) o.castShadow = mode === 'solid'; });
  }

  function setXray(on) {
    for (const m of tower.nodes.boxMaterials) {
      Object.assign(m, { transparent: on, opacity: on ? 0.22 : 1, depthWrite: !on });
      m.needsUpdate = true;
    }
  }

  // ---- panel ---------------------------------------------------------------
  function renderSteps() {
    stepsEl.innerHTML = '';
    tower.timeline.steps.forEach((s, i) => {
      const li = document.createElement('li');
      li.tabIndex = 0;
      li.innerHTML = '<span class="n"></span><span class="t"></span><span class="r"></span><span class="d"></span>';
      li.querySelector('.n').textContent = String(i + 1).padStart(2, '0');
      li.querySelector('.t').textContent = s.label;
      li.querySelector('.r').textContent = s.real;
      li.querySelector('.d').textContent = s.detail;
      const go = () => { time = s.t0 + 0.001; };
      li.addEventListener('click', go);
      li.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
      stepsEl.appendChild(li);
    });
    const sel = $('inspect');
    const n = tower.derived.n;
    sel.innerHTML = '';
    for (let i = 0; i < n; i++) {
      const o = document.createElement('option');
      o.value = i;
      o.textContent = i === 0 ? '1 (bottom)' : i === n - 1 ? `${i + 1} (top)` : String(i + 1);
      o.selected = i === tower.derived.k;
      sel.appendChild(o);
    }
  }

  function renderSpecs() {
    $('specs').innerHTML = SPECS(tower.derived, tower.params).map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');
  }

  $('boxes').addEventListener('change', (e) => build(+e.target.value, Math.min(tower.derived.k, +e.target.value - 1)));
  $('inspect').addEventListener('change', (e) => build(tower.derived.n, +e.target.value));
  for (const b of $('clad').querySelectorAll('button')) b.addEventListener('click', () => setClad(b.dataset.value));
  $('xray').addEventListener('change', (e) => setXray(e.target.checked));
  for (const b of $('speed').querySelectorAll('button')) {
    b.addEventListener('click', () => {
      speed = +b.dataset.value;
      for (const o of $('speed').querySelectorAll('button')) o.setAttribute('aria-pressed', String(o === b));
    });
  }
  const playBtn = $('play');
  const syncPlay = () => { playBtn.textContent = playing ? 'Pause' : 'Play'; };
  playBtn.addEventListener('click', () => { playing = !playing; syncPlay(); });
  syncPlay();
  const scrub = $('scrub');
  scrub.addEventListener('input', () => { time = (scrub.value / 1000) * tower.timeline.duration; });

  // ---- hover info ----------------------------------------------------------
  const ray = new THREE.Raycaster();
  const ptr = new THREE.Vector2();
  let lastPart = null;
  const isUnder = (o, parent) => { for (; o; o = o.parent) if (o === parent) return true; return false; };
  canvas.addEventListener('pointermove', (e) => {
    const r = canvas.getBoundingClientRect();
    ptr.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ptr, camera);
    let part = null;
    for (const h of ray.intersectObject(tower.root, true)) {
      let o = h.object;
      if (!o.visible || o.scale.x < 0.01) continue;
      if (cladMode !== 'solid' && isUnder(o, tower.nodes.cladding)) continue;
      while (o && !o.userData.part) o = o.parent;
      if (o) { part = o.userData.part; break; }
    }
    if (part && part !== lastPart && PARTS[part]) {
      lastPart = part;
      $('info-title').textContent = PARTS[part][0];
      $('info-text').textContent = PARTS[part][1];
    }
  });

  // ---- loop ----------------------------------------------------------------
  const resize = () => {
    const r = canvas.parentElement.getBoundingClientRect();
    renderer.setSize(r.width, r.height, false);
    camera.aspect = r.width / Math.max(1, r.height);
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(canvas.parentElement);

  build(3, 1);
  const clock = new THREE.Clock();
  let activeStep = -1;
  const frame = () => {
    const dt = Math.min(clock.getDelta(), 0.1);
    const dur = tower.timeline.duration;
    if (playing) time = (time + dt * speed) % dur;
    tower.applyState(tower.timeline.stateAt(time));
    scrub.value = String(Math.round((time / dur) * 1000));
    $('clock').textContent = `${time.toFixed(1)} s`;

    const steps = tower.timeline.steps;
    const idx = steps.findIndex((s) => time >= s.t0 && time < s.t1);
    const cur = idx < 0 ? steps.length - 1 : idx;
    if (cur !== activeStep) {
      activeStep = cur;
      [...stepsEl.children].forEach((li, i) => li.classList.toggle('on', i === cur));
      const chip = $('chip');
      chip.replaceChildren('Step ', Object.assign(document.createElement('b'), { textContent: String(cur + 1) }), ` · ${steps[cur].label}`);
    }
    const busy = cur >= 1 && cur < steps.length - 1;
    redLight.intensity = busy ? 1.2 : 0;
    redLight.position.set(0, tower.derived.rim * tower.MM + 0.2, 0);

    const tt = performance.now() / 1000;
    tower.nodes.bees.children.forEach((b, i) => {
      if (!b.userData.flying) return;
      b.userData.y0 ??= b.position.y;
      b.position.y = b.userData.y0 + Math.sin(tt * 3 + i) * 0.012;
      b.rotation.y += 0.01;
    });
    tower.nodes.status.material.emissiveIntensity = busy ? 1.8 : 0.6 + 0.5 * Math.sin(tt * 2);

    controls.update();
    renderer.render(scene, camera);
  };
  // Only render while the viewer is on screen (it is embedded in long pages).
  new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting) { clock.getDelta(); renderer.setAnimationLoop(frame); }
    else renderer.setAnimationLoop(null);
  }).observe(root);
  frame();
}

export function mountAll() {
  for (const root of document.querySelectorAll('[data-hive-tower]')) {
    if (root.dataset.mounted) continue;
    root.dataset.mounted = '1';
    try {
      mountHiveTower(root);
    } catch (err) {
      const note = document.createElement('p');
      note.textContent = `3D preview failed to start: ${err instanceof Error ? err.message : err}`;
      root.replaceChildren(note);
    }
  }
}
