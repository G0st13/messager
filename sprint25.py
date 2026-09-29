#!/usr/bin/env python3
"""sprint25.py - holograms + flying AVs over Night City."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PIXEL_CITY = r'''import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export type Weather = "auto" | "clear" | "rain" | "snow" | "smog" | "storm";

const SIZE = 400;

interface District {
  name: string;
  x: number; z: number;
  w: number; d: number;
  color: number;
  count: number;
  maxH: number;
}

const DISTRICTS: District[] = [
  { name: "WATSON",        x: -85,  z: -100, w: 130, d: 100, color: 0x00f0ff, count: 120, maxH: 30 },
  { name: "WESTBROOK",     x: 95,   z: -100, w: 150, d: 105, color: 0xb967ff, count: 140, maxH: 36 },
  { name: "CITY CENTER",   x: 0,    z: 5,    w: 100, d: 90,  color: 0xfcee0a, count: 180, maxH: 60 },
  { name: "HEYWOOD",       x: 115,  z: 70,   w: 100, d: 90,  color: 0xff00a0, count: 130, maxH: 40 },
  { name: "SANTO DOMINGO", x: -110, z: 95,   w: 120, d: 85,  color: 0xff6600, count: 100, maxH: 28 },
  { name: "PACIFICA",      x: 0,    z: 145,  w: 140, d: 70,  color: 0x7cff00, count: 60,  maxH: 22 },
];

const LANDMARKS: { name: string; x: number; z: number; color: number }[] = [
  { name: "NCPD",        x: -110, z: -60,  color: 0x00f0ff },
  { name: "TRAUMA",      x: 80,   z: -90,  color: 0xff3355 },
  { name: "ARASAKA",     x: 20,   z: 30,   color: 0xfcee0a },
  { name: "DELAMAIN",    x: 120,  z: 70,   color: 0xb967ff },
  { name: "NCART",       x: 0,    z: -20,  color: 0x00f0ff },
  { name: "AVANTE",      x: 0,    z: 145,  color: 0x7cff00 },
];

// ---- holographic ads shown over districts ----
const HOLOGRAMS: { text: string; x: number; z: number; y: number; color: number; w: number }[] = [
  { text: "ARASAKA",       x: 20,    z: 5,    y: 90, color: 0xfcee0a, w: 70 },
  { text: "NIGHT CITY",    x: 0,     z: 5,    y: 110, color: 0x00f0ff, w: 90 },
  { text: "MILITECH",      x: 60,    z: -100, y: 70, color: 0xff3355, w: 60 },
  { text: "KIROSHI",       x: -80,   z: -90,  y: 62, color: 0xb967ff, w: 55 },
  { text: "TRAUMA TEAM",   x: 80,    z: -90,  y: 78, color: 0xff3355, w: 65 },
  { text: "DELAMAIN",      x: 120,   z: 70,   y: 65, color: 0xb967ff, w: 60 },
  { text: "NCPD",          x: -110,  z: -60,  y: 70, color: 0x00f0ff, w: 40 },
  { text: "AFTERLIFE",     x: -60,   z: 80,   y: 55, color: 0xff00a0, w: 60 },
  { text: "NO-TELL HOTEL", x: 130,   z: -60,  y: 55, color: 0xfcee0a, w: 70 },
  { text: "2ND AMEND.",    x: 130,   z: -110, y: 50, color: 0xff00a0, w: 55 },
];

function rngFactory(seed: number) {
  let s = (seed >>> 0) || 1;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---- holographic text texture ----
function makeHoloTextTexture(text: string, colorHex: string) {
  const c = document.createElement("canvas");
  c.width = 1024;
  c.height = 256;
  const ctx = c.getContext("2d")!;

  ctx.clearRect(0, 0, c.width, c.height);
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = "bold 140px 'Rajdhani', 'JetBrains Mono', monospace";

  // outer glow layers
  ctx.shadowColor = colorHex;
  ctx.shadowBlur = 40;
  ctx.fillStyle = colorHex;
  ctx.fillText(text, c.width / 2, c.height / 2);

  ctx.shadowBlur = 20;
  ctx.fillText(text, c.width / 2, c.height / 2);

  // bright core
  ctx.shadowBlur = 0;
  ctx.fillStyle = "#ffffff";
  ctx.globalAlpha = 0.9;
  ctx.font = "bold 138px 'Rajdhani', 'JetBrains Mono', monospace";
  ctx.fillText(text, c.width / 2, c.height / 2);

  // subtle horizontal lines
  ctx.globalAlpha = 0.35;
  ctx.fillStyle = colorHex;
  for (let y = 0; y < c.height; y += 5) {
    ctx.fillRect(0, y, c.width, 1);
  }

  const tex = new THREE.CanvasTexture(c);
  tex.minFilter = THREE.LinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.needsUpdate = true;
  return tex;
}

// ---- small ad texture ----
function makeAdTexture(text: string, colorHex: string) {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 512;
  const ctx = c.getContext("2d")!;

  ctx.fillStyle = "rgba(3, 10, 20, 0.9)";
  ctx.fillRect(0, 0, c.width, c.height);

  // border
  ctx.strokeStyle = colorHex;
  ctx.lineWidth = 4;
  ctx.strokeRect(8, 8, c.width - 16, c.height - 16);

  // glow border
  ctx.shadowColor = colorHex;
  ctx.shadowBlur = 20;
  ctx.strokeRect(8, 8, c.width - 16, c.height - 16);

  // inner text
  ctx.fillStyle = colorHex;
  ctx.shadowBlur = 16;
  ctx.font = "bold 60px 'Rajdhani', monospace";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, c.width / 2, c.height / 2);

  // scanlines
  ctx.shadowBlur = 0;
  ctx.fillStyle = colorHex;
  ctx.globalAlpha = 0.15;
  for (let y = 0; y < c.height; y += 6) {
    ctx.fillRect(0, y, c.width, 1);
  }

  const tex = new THREE.CanvasTexture(c);
  tex.minFilter = THREE.LinearFilter;
  tex.magFilter = THREE.LinearFilter;
  return tex;
}

export default function PixelCity({ weather = "auto", seed = 1 }: { weather?: Weather; seed?: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = ref.current;
    if (!container) return;

    let width = container.clientWidth;
    let height = container.clientHeight;

    const effective: Weather = weather === "auto"
      ? (["clear", "rain", "rain", "snow", "smog"] as const)[new Date().getDate() % 5]
      : weather;

    // ---- renderer ----
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(1.5, window.devicePixelRatio));
    renderer.setSize(width, height);
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x03060c);
    const fogFar = effective === "smog" ? 600 : 900;
    scene.fog = new THREE.Fog(0x03060c, 300, fogFar);

    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 3000);
    camera.position.set(140, 220, 300);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI / 2.15;
    controls.minDistance = 100;
    controls.maxDistance = 800;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.18;
    controls.target.set(0, 30, 0);

    // ---- lights ----
    scene.add(new THREE.AmbientLight(0x30415a, 1.1));
    const dl1 = new THREE.DirectionalLight(0x00f0ff, 0.9);
    dl1.position.set(120, 260, 100);
    scene.add(dl1);
    const dl2 = new THREE.DirectionalLight(0xff00a0, 0.5);
    dl2.position.set(-150, 200, -120);
    scene.add(dl2);
    const dl3 = new THREE.DirectionalLight(0xfcee0a, 0.35);
    dl3.position.set(0, 300, -200);
    scene.add(dl3);

    // ---- ground ----
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(SIZE, SIZE),
      new THREE.MeshBasicMaterial({ color: 0x050910 })
    );
    ground.rotation.x = -Math.PI / 2;
    scene.add(ground);

    // ---- grid ----
    const grid = new THREE.GridHelper(SIZE, 40, 0x00f0ff, 0x0a2233);
    const gm = grid.material as THREE.LineBasicMaterial;
    gm.opacity = 0.32;
    gm.transparent = true;
    grid.position.y = 0.03;
    scene.add(grid);

    // ---- districts ----
    for (const d of DISTRICTS) {
      const geo = new THREE.PlaneGeometry(d.w, d.d);
      const mesh = new THREE.Mesh(
        geo,
        new THREE.MeshBasicMaterial({ color: d.color, transparent: true, opacity: 0.08, side: THREE.DoubleSide })
      );
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.set(d.x, 0.06, d.z);
      scene.add(mesh);

      const edge = new THREE.LineSegments(
        new THREE.EdgesGeometry(geo),
        new THREE.LineBasicMaterial({ color: d.color, transparent: true, opacity: 0.85 })
      );
      edge.rotation.x = -Math.PI / 2;
      edge.position.set(d.x, 0.08, d.z);
      scene.add(edge);
    }

    // ---- roads ----
    const roadMat = new THREE.MeshBasicMaterial({ color: 0xffaa3c, transparent: true, opacity: 0.55 });
    for (let z = -180; z <= 180; z += 60) {
      const r = new THREE.Mesh(new THREE.PlaneGeometry(SIZE - 20, 2), roadMat);
      r.rotation.x = -Math.PI / 2;
      r.position.set(0, 0.12, z);
      scene.add(r);
    }
    for (let x = -180; x <= 180; x += 60) {
      const r = new THREE.Mesh(new THREE.PlaneGeometry(2, SIZE - 20), roadMat);
      r.rotation.x = -Math.PI / 2;
      r.position.set(x, 0.12, 0);
      scene.add(r);
    }

    // ---- buildings ----
    const rng = rngFactory(seed);
    const totalB = DISTRICTS.reduce((s, d) => s + d.count, 0);
    const boxGeo = new THREE.BoxGeometry(1, 1, 1);
    const bMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      roughness: 0.5,
      metalness: 0.4,
      emissiveIntensity: 0.4,
      emissive: 0x0a1420,
    });
    const inst = new THREE.InstancedMesh(boxGeo, bMat, totalB);

    const dummy = new THREE.Object3D();
    const col = new THREE.Color();
    const white = new THREE.Color(0xffffff);
    let idx = 0;

    for (const d of DISTRICTS) {
      for (let i = 0; i < d.count; i++) {
        const x = d.x + (rng() - 0.5) * d.w * 0.85;
        const z = d.z + (rng() - 0.5) * d.d * 0.85;
        const w = 3 + rng() * 6;
        const dep = 3 + rng() * 6;
        const h = 4 + rng() * d.maxH;

        dummy.position.set(x, h / 2, z);
        dummy.scale.set(w, h, dep);
        dummy.rotation.y = rng() * Math.PI;
        dummy.updateMatrix();
        inst.setMatrixAt(idx, dummy.matrix);

        col.setHex(0x0a1420);
        col.lerp(new THREE.Color(d.color), 0.2 + rng() * 0.35);
        if (rng() < 0.35) col.lerp(white, 0.2);
        inst.setColorAt(idx, col);
        idx++;
      }
    }
    inst.instanceMatrix.needsUpdate = true;
    if (inst.instanceColor) inst.instanceColor.needsUpdate = true;
    scene.add(inst);

    // ============================================================
    // HOLOGRAMS — big text floating above city
    // ============================================================
    const holoGroup = new THREE.Group();
    scene.add(holoGroup);

    interface HoloObj {
      mesh: THREE.Mesh;
      baseY: number;
      phase: number;
      kind: "text" | "ad" | "ring";
      speed: number;
      baseOpacity: number;
      material: THREE.MeshBasicMaterial;
    }
    const holoObjs: HoloObj[] = [];

    for (const h of HOLOGRAMS) {
      const colorHex = "#" + h.color.toString(16).padStart(6, "0");

      // большие текст-голограммы — плоские фейс-к-центру plane
      const w = h.w;
      const hh = w / 4;
      const tex = makeHoloTextTexture(h.text, colorHex);
      const mat = new THREE.MeshBasicMaterial({
        map: tex,
        transparent: true,
        opacity: 0.85,
        side: THREE.DoubleSide,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      });
      const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, hh), mat);
      mesh.position.set(h.x, h.y, h.z);
      // смотрит в центр сцены
      mesh.lookAt(0, h.y, 0);
      holoGroup.add(mesh);

      holoObjs.push({
        mesh,
        baseY: h.y,
        phase: rng() * 6,
        kind: "text",
        speed: 0.3 + rng() * 0.4,
        baseOpacity: 0.75 + rng() * 0.2,
        material: mat,
      });

      // световая колонна под голограммой
      const beamMat = new THREE.MeshBasicMaterial({
        color: h.color,
        transparent: true,
        opacity: 0.18,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        side: THREE.DoubleSide,
      });
      const beam = new THREE.Mesh(
        new THREE.CylinderGeometry(0.6, 2.5, h.y, 8, 1, true),
        beamMat,
      );
      beam.position.set(h.x, h.y / 2, h.z);
      holoGroup.add(beam);
    }

    // ---- floating ad panels above districts ----
    const adTexts = ["RAMEN", "CLUB", "2077", "COLA", "SUSHI", "STRIP", "CYBER", "DATA", "PACHINKO", "HOTEL"];
    for (const d of DISTRICTS) {
      const count = 2 + Math.floor(rng() * 3);
      for (let i = 0; i < count; i++) {
        const t = adTexts[Math.floor(rng() * adTexts.length)];
        const colorHex = "#" + d.color.toString(16).padStart(6, "0");
        const tex = makeAdTexture(t, colorHex);
        const mat = new THREE.MeshBasicMaterial({
          map: tex,
          transparent: true,
          opacity: 0.7,
          side: THREE.DoubleSide,
          depthWrite: false,
          blending: THREE.AdditiveBlending,
        });
        const size = 8 + rng() * 8;
        const mesh = new THREE.Mesh(new THREE.PlaneGeometry(size, size), mat);
        mesh.position.set(
          d.x + (rng() - 0.5) * d.w * 0.7,
          25 + rng() * 30,
          d.z + (rng() - 0.5) * d.d * 0.7,
        );
        holoGroup.add(mesh);

        holoObjs.push({
          mesh,
          baseY: mesh.position.y,
          phase: rng() * 6,
          kind: "ad",
          speed: 0.5 + rng() * 0.5,
          baseOpacity: 0.55 + rng() * 0.25,
          material: mat,
        });
      }
    }

    // ---- giant rotating ring above CITY CENTER ----
    {
      const ringGeo = new THREE.TorusGeometry(30, 0.4, 8, 48);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0x00f0ff,
        transparent: true,
        opacity: 0.7,
        blending: THREE.AdditiveBlending,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.set(0, 140, 5);
      ring.rotation.x = Math.PI / 2;
      holoGroup.add(ring);

      holoObjs.push({
        mesh: ring,
        baseY: 140,
        phase: 0,
        kind: "ring",
        speed: 0.15,
        baseOpacity: 0.7,
        material: ringMat,
      });

      const ring2Geo = new THREE.TorusGeometry(38, 0.3, 8, 60);
      const ring2Mat = new THREE.MeshBasicMaterial({
        color: 0xff00a0,
        transparent: true,
        opacity: 0.5,
        blending: THREE.AdditiveBlending,
      });
      const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
      ring2.position.set(0, 140, 5);
      ring2.rotation.x = Math.PI / 2;
      holoGroup.add(ring2);

      holoObjs.push({
        mesh: ring2,
        baseY: 140,
        phase: 1.5,
        kind: "ring",
        speed: -0.2,
        baseOpacity: 0.5,
        material: ring2Mat,
      });
    }

    // ---- floating sprite particles (dust/motes near holograms) ----
    const moteCount = 300;
    const motePos = new Float32Array(moteCount * 3);
    for (let i = 0; i < moteCount; i++) {
      motePos[i * 3] = (rng() - 0.5) * SIZE * 0.9;
      motePos[i * 3 + 1] = 5 + rng() * 130;
      motePos[i * 3 + 2] = (rng() - 0.5) * SIZE * 0.9;
    }
    const moteGeo = new THREE.BufferGeometry();
    moteGeo.setAttribute("position", new THREE.BufferAttribute(motePos, 3));
    const motes = new THREE.Points(moteGeo, new THREE.PointsMaterial({
      color: 0x88c8ff, size: 0.6, transparent: true, opacity: 0.5,
      blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    scene.add(motes);

    // ============================================================
    // FLYING AVs (aerial vehicles) — fly above the city with trails
    // ============================================================
    interface AV {
      x: number; y: number; z: number;
      vx: number; vy: number; vz: number;
      color: number;
      trail: THREE.Line;
      trailPts: THREE.Vector3[];
      blinkPhase: number;
    }

    const avs: AV[] = [];
    const AV_COUNT = 18;
    const avGroup = new THREE.Group();
    scene.add(avGroup);

    const avColors = [0x00f0ff, 0xff00a0, 0xfcee0a, 0xff6600, 0xb967ff, 0xff3355];

    for (let i = 0; i < AV_COUNT; i++) {
      // каждый AV — маленькая светящаяся "капсула" из 2 частей + трейл
      const avMesh = new THREE.Mesh(
        new THREE.BoxGeometry(2.2, 0.5, 0.8),
        new THREE.MeshBasicMaterial({ color: 0xffffff })
      );
      const color = avColors[Math.floor(rng() * avColors.length)];
      const glow = new THREE.Mesh(
        new THREE.SphereGeometry(1.6, 8, 8),
        new THREE.MeshBasicMaterial({
          color, transparent: true, opacity: 0.55,
          blending: THREE.AdditiveBlending, depthWrite: false,
        })
      );
      avMesh.add(glow);

      // trail: buffer of 40 points
      const TRAIL_LEN = 40;
      const trailPts: THREE.Vector3[] = [];
      const posArr = new Float32Array(TRAIL_LEN * 3);
      for (let j = 0; j < TRAIL_LEN; j++) {
        trailPts.push(new THREE.Vector3(0, 0, 0));
        posArr[j * 3] = 0;
        posArr[j * 3 + 1] = 0;
        posArr[j * 3 + 2] = 0;
      }
      const trailGeo = new THREE.BufferGeometry();
      trailGeo.setAttribute("position", new THREE.BufferAttribute(posArr, 3));
      const trail = new THREE.Line(trailGeo, new THREE.LineBasicMaterial({
        color, transparent: true, opacity: 0.7,
        blending: THREE.AdditiveBlending,
      }));

      // start position at random corner, heading roughly across city
      const startX = (rng() - 0.5) * SIZE * 0.7;
      const startZ = (rng() - 0.5) * SIZE * 0.7;
      const startY = 30 + rng() * 60;
      const speed = 25 + rng() * 30;
      const angle = rng() * Math.PI * 2;
      avMesh.position.set(startX, startY, startZ);

      avGroup.add(avMesh);
      scene.add(trail);

      avs.push({
        x: startX, y: startY, z: startZ,
        vx: Math.cos(angle) * speed,
        vy: (rng() - 0.5) * 6,
        vz: Math.sin(angle) * speed,
        color,
        trail,
        trailPts,
        blinkPhase: rng() * 10,
      });
    }

    // ---- NCART metro ----
    const metroMat = new THREE.LineDashedMaterial({
      color: 0x00f0ff, dashSize: 3, gapSize: 5, transparent: true, opacity: 0.8,
    });
    const metroRoutes: [number, number][][] = [
      [[-180, -50], [-60, -50], [60, -50], [180, -50]],
      [[-180, 60], [-60, 60], [60, 60], [180, 60]],
      [[-50, -180], [-50, -60], [-50, 60], [-50, 180]],
      [[80, -180], [80, -60], [80, 60], [80, 180]],
    ];
    for (const route of metroRoutes) {
      const pts = route.map((p) => new THREE.Vector3(p[0], 0.35, p[1]));
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const line = new THREE.Line(geo, metroMat);
      line.computeLineDistances();
      scene.add(line);
    }

    // ---- traffic (ground) ----
    interface Traffic { x: number; z: number; vx: number; vz: number }
    const traffic: Traffic[] = [];
    const trafficMesh = new THREE.InstancedMesh(
      new THREE.SphereGeometry(1, 8, 8),
      new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.95 }),
      40
    );
    for (let i = 0; i < 40; i++) {
      const horiz = rng() < 0.5;
      if (horiz) {
        const z = (Math.floor(rng() * 7) - 3) * 60;
        traffic.push({ x: (rng() - 0.5) * 360, z, vx: (rng() < 0.5 ? -1 : 1) * (30 + rng() * 40), vz: 0 });
      } else {
        const x = (Math.floor(rng() * 7) - 3) * 60;
        traffic.push({ x, z: (rng() - 0.5) * 360, vx: 0, vz: (rng() < 0.5 ? -1 : 1) * (30 + rng() * 40) });
      }
    }
    const tCol = new THREE.Color();
    for (let i = 0; i < traffic.length; i++) {
      tCol.setHSL(rng(), 0.9, 0.7);
      trafficMesh.setColorAt(i, tCol);
    }
    if (trafficMesh.instanceColor) trafficMesh.instanceColor.needsUpdate = true;
    scene.add(trafficMesh);

    // ---- stars ----
    const starPos: number[] = [];
    for (let i = 0; i < 400; i++) {
      starPos.push((rng() - 0.5) * 2000, 260 + rng() * 400, (rng() - 0.5) * 2000);
    }
    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute("position", new THREE.Float32BufferAttribute(starPos, 3));
    const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({
      color: 0x88aaff, size: 1.6, transparent: true, opacity: 0.7,
    }));
    scene.add(stars);

    // ---- scan wall ----
    const scanMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff, transparent: true, opacity: 0.08,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false,
    });
    const scanPlane = new THREE.Mesh(new THREE.PlaneGeometry(SIZE, SIZE), scanMat);
    scanPlane.rotation.x = -Math.PI / 2;
    scene.add(scanPlane);
    const wallMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff, transparent: true, opacity: 0.35,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false,
    });
    const wall = new THREE.Mesh(new THREE.PlaneGeometry(SIZE, 80), wallMat);
    scene.add(wall);

    // ---- rain ----
    let rainPoints: THREE.Points | null = null;
    if (effective === "rain" || effective === "storm") {
      const N = 1800;
      const pos: number[] = [];
      for (let i = 0; i < N; i++) {
        pos.push((rng() - 0.5) * SIZE, rng() * 180, (rng() - 0.5) * SIZE);
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
      rainPoints = new THREE.Points(geo, new THREE.PointsMaterial({
        color: 0x9ecfff, size: 1.4, transparent: true, opacity: 0.55,
      }));
      scene.add(rainPoints);
    }

    // ---- lightning ----
    const lightning = new THREE.PointLight(0xc8dcff, 0, 900);
    lightning.position.set(0, 220, 0);
    scene.add(lightning);
    let nextLightning = 2 + rng() * 4;

    // ============================================================
    // ANIMATION
    // ============================================================
    let raf = 0;
    let last = performance.now();
    let scanY = 0;
    let scanDir = 1;
    const tmpVec = new THREE.Vector3();

    const animate = (t: number) => {
      const dt = Math.min(0.05, (t - last) / 1000);
      last = t;
      const timeSec = t / 1000;

      // scan
      scanY += scanDir * dt * 25;
      if (scanY > 90) { scanY = 90; scanDir = -1; }
      if (scanY < 0) { scanY = 0; scanDir = 1; }
      scanPlane.position.y = scanY;
      wall.position.y = scanY;
      scanMat.opacity = 0.06 + Math.sin(t / 300) * 0.03;
      wallMat.opacity = 0.25 + Math.sin(t / 300) * 0.1;

      // holograms
      for (const h of holoObjs) {
        const bobY = Math.sin(timeSec * h.speed + h.phase) * 3;
        h.mesh.position.y = h.baseY + bobY;

        if (h.kind === "ring") {
          h.mesh.rotation.z += dt * 0.35;
        } else if (h.kind === "text") {
          // текст-голограмма слегка поворачивается к камере
          const angleToCam = Math.atan2(
            camera.position.x - h.mesh.position.x,
            camera.position.z - h.mesh.position.z,
          );
          h.mesh.rotation.y = angleToCam;
          // мерцание
          const flick = 0.85 + Math.sin(timeSec * 5 + h.phase) * 0.15;
          h.material.opacity = h.baseOpacity * flick;
        } else if (h.kind === "ad") {
          const angleToCam = Math.atan2(
            camera.position.x - h.mesh.position.x,
            camera.position.z - h.mesh.position.z,
          );
          h.mesh.rotation.y = angleToCam + Math.sin(timeSec * 0.6 + h.phase) * 0.15;
          const flick = 0.7 + Math.sin(timeSec * 7 + h.phase) * 0.3;
          h.material.opacity = h.baseOpacity * flick;
        }
      }

      // motes drift
      {
        const attr = motes.geometry.attributes.position as THREE.BufferAttribute;
        const arr = attr.array as Float32Array;
        for (let i = 0; i < arr.length; i += 3) {
          arr[i + 1] += dt * 2.5;
          if (arr[i + 1] > 140) arr[i + 1] = 5;
        }
        attr.needsUpdate = true;
      }

      // flying AVs
      for (const av of avs) {
        av.x += av.vx * dt;
        av.y += av.vy * dt;
        av.z += av.vz * dt;

        // wrap and turn if far
        if (Math.abs(av.x) > 220) { av.vx *= -1; av.x = Math.sign(av.x) * 219; }
        if (Math.abs(av.z) > 220) { av.vz *= -1; av.z = Math.sign(av.z) * 219; }
        if (av.y > 110) { av.vy = -Math.abs(av.vy); }
        if (av.y < 20) { av.vy = Math.abs(av.vy); }

        // slight turning noise
        av.vx += (rng() - 0.5) * 6 * dt;
        av.vz += (rng() - 0.5) * 6 * dt;
        // clamp speed
        const sp = Math.hypot(av.vx, av.vz);
        if (sp > 70) {
          av.vx = (av.vx / sp) * 70;
          av.vz = (av.vz / sp) * 70;
        }

        // update visuals
        av.trailPts.unshift(new THREE.Vector3(av.x, av.y, av.z));
        if (av.trailPts.length > 40) av.trailPts.pop();

        const posAttr = av.trail.geometry.attributes.position as THREE.BufferAttribute;
        const arr = posAttr.array as Float32Array;
        for (let j = 0; j < 40; j++) {
          const p = av.trailPts[j] || av.trailPts[av.trailPts.length - 1];
          arr[j * 3] = p.x;
          arr[j * 3 + 1] = p.y;
          arr[j * 3 + 2] = p.z;
        }
        posAttr.needsUpdate = true;
      }

      // update AV mesh positions
      let ai = 0;
      avGroup.children.forEach((child, i) => {
        if (i < avs.length) {
          const av = avs[i];
          child.position.set(av.x, av.y, av.z);
          // rotate to look in flight direction
          const ang = Math.atan2(av.vx, av.vz);
          child.rotation.y = ang;
          // blink glow
          const blink = 0.6 + Math.sin(timeSec * 6 + av.blinkPhase) * 0.4;
          const glow = child.children[0] as THREE.Mesh;
          if (glow) {
            (glow.material as THREE.MeshBasicMaterial).opacity = 0.35 + blink * 0.4;
          }
        }
        ai++;
      });

      // ground traffic
      for (let i = 0; i < traffic.length; i++) {
        const tr = traffic[i];
        tr.x += tr.vx * dt;
        tr.z += tr.vz * dt;
        if (tr.x > 200) tr.x = -200;
        if (tr.x < -200) tr.x = 200;
        if (tr.z > 200) tr.z = -200;
        if (tr.z < -200) tr.z = 200;
        dummy.position.set(tr.x, 1.5, tr.z);
        dummy.scale.set(1, 1, 1);
        dummy.rotation.set(0, 0, 0);
        dummy.updateMatrix();
        trafficMesh.setMatrixAt(i, dummy.matrix);
      }
      trafficMesh.instanceMatrix.needsUpdate = true;

      // rain
      if (rainPoints) {
        const attr = rainPoints.geometry.attributes.position as THREE.BufferAttribute;
        const arr = attr.array as Float32Array;
        for (let i = 0; i < arr.length; i += 3) {
          arr[i + 1] -= 180 * dt;
          if (arr[i + 1] < 0) {
            arr[i + 1] = 180;
            arr[i] = (rng() - 0.5) * SIZE;
            arr[i + 2] = (rng() - 0.5) * SIZE;
          }
        }
        attr.needsUpdate = true;
      }

      // lightning
      if (effective === "storm") {
        nextLightning -= dt;
        if (nextLightning <= 0) {
          lightning.intensity = 3;
          nextLightning = 3 + rng() * 5;
        }
        lightning.intensity *= 0.85;
      }

      stars.rotation.y += dt * 0.005;

      controls.update();
      renderer.render(scene, camera);
      raf = requestAnimationFrame(animate);
    };

    raf = requestAnimationFrame(animate);

    // ---- resize ----
    const onResize = () => {
      width = container.clientWidth;
      height = container.clientHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      controls.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
    };
  }, [seed, weather]);

  return <div ref={ref} className="night-city-3d" />;
}
'''


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    src = root / "frontend" / "src"

    print("\nСпринт 25 — Голограммы и летающие AV над городом\n")

    # перезаписываем PixelCity.tsx — полностью
    target = src / "PixelCity.tsx"
    existed = target.exists()
    target.write_text(PIXEL_CITY, encoding="utf-8")
    print(f"  {'~' if existed else '+'} {target}")

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    print("Что добавилось:")
    print("  🛸 18 летающих AV с trails над городом")
    print("  📺 10 больших текстовых голограмм (ARASAKA, NIGHT CITY, TRAUMA TEAM...)")
    print("  📢 ~20 маленьких ad-панелей над районами (RAMEN, CLUB, 2077...)")
    print("  💡 Световые колонны под каждой голограммой")
    print("  ⭕ Вращающиеся кольца над CITY CENTER")
    print("  ✨ 300 частиц пыли, летающих вверх")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())