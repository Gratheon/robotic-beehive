// Builds the Robotic Beehive scene in Node and writes hive-tower.glb with the
// inspection sequence baked in as an animation clip ("inspection").
//   node export-glb.mjs [--boxes 3] [--inspect 1] [--out hive-tower.glb]
import { writeFileSync } from 'node:fs';
import * as THREE from 'three';
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';
import { buildHiveTower, PARTS } from './hive-model.js';

// GLTFExporter uses FileReader for binary output; Node only has Blob.
globalThis.FileReader = class {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then((buf) => { this.result = buf; this.onloadend?.(); this.onload?.({ target: this }); });
  }
  readAsDataURL(blob) {
    blob.arrayBuffer().then((buf) => {
      this.result = `data:${blob.type || 'application/octet-stream'};base64,${Buffer.from(buf).toString('base64')}`;
      this.onloadend?.(); this.onload?.({ target: this });
    });
  }
};

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > 0 ? process.argv[i + 1] : fallback;
};

const tower = buildHiveTower({ boxes: Number(arg('boxes', 3)), inspectBox: Number(arg('inspect', 1)) });
const { root, timeline, applyState, animated } = tower;

// Attach human-readable part info as glTF extras.
root.traverse((o) => {
  const key = o.userData.part;
  if (key && PARTS[key]) o.userData = { part: key, title: PARTS[key][0], info: PARTS[key][1] };
});

// Bake the procedural timeline into keyframe tracks.
const FPS = 15;
const times = [];
for (let t = 0; t <= timeline.duration + 1e-6; t += 1 / FPS) times.push(+t.toFixed(4));
const samples = new Map(animated.map((o) => [o, { p: [], q: [], s: [] }]));
for (const t of times) {
  applyState(timeline.stateAt(t));
  for (const o of animated) {
    const rec = samples.get(o);
    rec.p.push(...o.position.toArray());
    rec.q.push(...o.quaternion.toArray());
    rec.s.push(...o.scale.toArray());
  }
}
const tracks = [];
const constant = (arr, stride) => arr.every((v, i) => Math.abs(v - arr[i % stride]) < 1e-7);
for (const o of animated) {
  const { p, q, s } = samples.get(o);
  if (!constant(p, 3)) tracks.push(new THREE.VectorKeyframeTrack(`${o.name}.position`, times, p));
  if (!constant(q, 4)) tracks.push(new THREE.QuaternionKeyframeTrack(`${o.name}.quaternion`, times, q));
  if (!constant(s, 3)) tracks.push(new THREE.VectorKeyframeTrack(`${o.name}.scale`, times, s));
}
const clip = new THREE.AnimationClip('inspection', timeline.duration, tracks);
clip.optimize();
applyState(timeline.stateAt(0));

const scene = new THREE.Scene();
scene.add(root);
const out = arg('out', new URL('./hive-tower.glb', import.meta.url).pathname);
new GLTFExporter().parse(
  scene,
  (glb) => {
    writeFileSync(out, Buffer.from(glb));
    console.log(`wrote ${out} (${(glb.byteLength / 1024).toFixed(0)} KB, ${tracks.length} tracks, ${timeline.duration.toFixed(1)} s clip)`);
  },
  (err) => { console.error(err); process.exit(1); },
  { binary: true, animations: [clip] },
);
