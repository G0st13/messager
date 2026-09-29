#!/usr/bin/env python3
"""sprint23.py - real 3D Night City using Three.js."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PACKAGE_JSON = r'''{
  "name": "messenger-frontend",
  "private": true,
  "version": "0.3.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.51.0",
    "axios": "^1.7.0",
    "clsx": "^2.1.1",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0",
    "socket.io-client": "^4.7.5",
    "three": "^0.170.0",
    "zustand": "^4.5.4"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@types/three": "^0.170.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.40",
    "tailwindcss": "^3.4.7",
    "typescript": "^5.5.4",
    "vite": "^5.4.0"
  }
}
'''


PIXEL_CITY = r'''import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export type Weather = "auto" | "clear" | "rain" | "snow" | "smog" | "storm";

const SIZE = 400;
const HALF = SIZE / 2;

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

const SUBDISTRICTS: { name: string; x: number; z: number; color: number }[] = [
  { name: "KABUKI",           x: -110, z: -140, color: 0x00f0ff },
  { name: "LITTLE CHINA",     x: -50,  z: -90,  color: 0x00f0ff },
  { name: "NORTHSIDE",        x: -120, z: -60,  color: 0x00f0ff },
  { name: "JAPANTOWN",        x: 60,   z: -140, color: 0xb967ff },
  { name: "CHARTER HILL",     x: 140,  z: -90,  color: 0xb967ff },
  { name: "NORTH OAK",        x: 130,  z: -60,  color: 0xb967ff },
  { name: "DOWNTOWN",         x: -30,  z: 0,    color: 0xfcee0a },
  { name: "CORPO PLAZA",      x: 30,   z: 30,   color: 0xfcee0a },
  { name: "WELLSPRINGS",      x: 90,   z: 40,   color: 0xff00a0 },
  { name: "VISTA DEL REY",    x: 140,  z: 80,   color: 0xff00a0 },
  { name: "THE GLEN",         x: 100,  z: 110,  color: 0xff00a0 },
  { name: "ARROYO",           x: -100, z: 60,   color: 0xff6600 },
  { name: "RANCHO CORONADO",  x: -140, z: 120,  color: 0xff6600 },
  { name: "WEST WIND ESTATE", x: -40,  z: 150,  color: 0x7cff00 },
  { name: "COASTVIEW",        x: 60,   z: 165,  color: 0x7cff00 },
];

const LANDMARKS: { name: string; x: number; z: number; color: number }[] = [
  { name: "NCPD",        x: -110, z: -60,  color: 0x00f0ff },
  { name: "TRAUMA",      x: 80,   z: -90,  color: 0xff3355 },
  { name: "ARASAKA",     x: 20,   z: 30,   color: 0xfcee0a },
  { name: "DELAMAIN",    x: 120,  z: 70,   color: 0xb967ff },
  { name: "NCART",       x: 0,    z: -20,  color: 0x00f0ff },
  { name: "AVANTE",      x: 0,    z: 145,  color: 0x7cff00 },
  { name: "2ND AMEND.",  x: 130,  z: -110, color: 0xff00a0 },
  { name: "TOM'S DINER", x: -60,  z: -110, color: 0xfcee0a },
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

function makeLabelTexture(text: string, colorHex: string) {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 64;
  const ctx = c.getContext("2d")!;
  ctx.clearRect(0, 0, 256, 64);
  ctx.font = "bold 24px 'JetBrains Mono', monospace";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.shadowColor = colorHex;
  ctx.shadowBlur = 14;
  ctx.fillStyle = colorHex;
  ctx.fillText(text, 128, 32);
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

    // ---- scene ----
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x03060c);
    const fogFar = effective === "smog" ? 500 : 800;
    scene.fog = new THREE.Fog(0x03060c, 250, fogFar);

    // ---- camera ----
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 3000);
    camera.position.set(120, 210, 280);

    // ---- controls ----
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI / 2.15;
    controls.minDistance = 100;
    controls.maxDistance = 700;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.18;
    controls.target.set(0, 20, 0);

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

    // ---- buildings (instanced) ----
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

    // ---- NCART metro lines ----
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

    // ---- subdistrict dots ----
    for (const s of SUBDISTRICTS) {
      const m = new THREE.Mesh(
        new THREE.SphereGeometry(1.3, 10, 10),
        new THREE.MeshBasicMaterial({ color: s.color })
      );
      m.position.set(s.x, 0.6, s.z);
      scene.add(m);
    }

    // ---- landmark sprites + beams ----
    const sprites: THREE.Sprite[] = [];
    for (const lm of LANDMARKS) {
      const colorHex = "#" + lm.color.toString(16).padStart(6, "0");
      const tex = makeLabelTexture(lm.name, colorHex);
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
        map: tex, transparent: true, depthTest: false, depthWrite: false,
      }));
      sprite.position.set(lm.x, 32, lm.z);
      sprite.scale.set(32, 8, 1);
      scene.add(sprite);
      sprites.push(sprite);

      // beacon
      const beam = new THREE.Mesh(
        new THREE.CylinderGeometry(0.4, 0.4, 32, 6),
        new THREE.MeshBasicMaterial({ color: lm.color, transparent: true, opacity: 0.35 })
      );
      beam.position.set(lm.x, 16, lm.z);
      scene.add(beam);
    }

    // ---- traffic ----
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
      starPos.push((rng() - 0.5) * 2000, 200 + rng() * 400, (rng() - 0.5) * 2000);
    }
    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute("position", new THREE.Float32BufferAttribute(starPos, 3));
    const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({
      color: 0x88aaff, size: 1.6, transparent: true, opacity: 0.7,
    }));
    scene.add(stars);

    // ---- scan plane (holographic bar moving up) ----
    const scanMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff, transparent: true, opacity: 0.08,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false,
    });
    const scanPlane = new THREE.Mesh(new THREE.PlaneGeometry(SIZE, SIZE), scanMat);
    scanPlane.rotation.x = -Math.PI / 2;
    scanPlane.position.y = 0;
    scene.add(scanPlane);

    // vertical scan wall (the visible "slice")
    const wallMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff, transparent: true, opacity: 0.35,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false,
    });
    const wall = new THREE.Mesh(new THREE.PlaneGeometry(SIZE, 80), wallMat);
    wall.rotation.x = 0;
    wall.rotation.y = 0;
    wall.position.set(0, 40, 0);
    scene.add(wall);

    // ---- weather: rain ----
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

    // ---- animation ----
    let raf = 0;
    let last = performance.now();
    let scanY = 0;
    let scanDir = 1;

    const animate = (t: number) => {
      const dt = Math.min(0.05, (t - last) / 1000);
      last = t;

      // scan sweeps up and down
      scanY += scanDir * dt * 25;
      if (scanY > 90) { scanY = 90; scanDir = -1; }
      if (scanY < 0) { scanY = 0; scanDir = 1; }

      scanPlane.position.y = scanY;
      wall.position.y = scanY;
      scanMat.opacity = 0.06 + Math.sin(t / 300) * 0.03;
      wallMat.opacity = 0.25 + Math.sin(t / 300) * 0.1;

      // traffic
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

      // bob sprites
      for (let i = 0; i < sprites.length; i++) {
        sprites[i].position.y = 32 + Math.sin(t / 1000 + i) * 2;
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

    // ---- cleanup ----
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


CSS_PATCH = r'''
    /* ============ NIGHT CITY 3D ============ */
    .night-city-3d {
      position: fixed;
      inset: 0;
      z-index: 0;
      pointer-events: none;  /* не перехватывает клики UI */
    }
    .night-city-3d canvas {
      display: block;
      width: 100% !important;
      height: 100% !important;
    }
    /* даём городу вращаться мышью в пустых зонах, если хочется — раскомментируй: */
    /* .night-city-3d { pointer-events: auto; } */

    body.chat-open .night-city-3d {
      opacity: 0.42;
      filter: saturate(0.65) brightness(0.75);
      transition: opacity 0.3s, filter 0.3s;
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
    fe = root / "frontend"

    print("\nСпринт 23 — 3D Night City (Three.js)\n")

    # package.json — добавляем three
    (fe / "package.json").write_text(PACKAGE_JSON, encoding="utf-8")
    print(f"  ~ {fe / 'package.json'}")

    # PixelCity.tsx — переписываем на Three.js
    (src / "PixelCity.tsx").write_text(PIXEL_CITY, encoding="utf-8")
    print(f"  ~ {src / 'PixelCity.tsx'}")

    # CSS — патчим
    css_path = src / "index.css"
    css_text = css_path.read_text(encoding="utf-8")
    if "NIGHT CITY 3D" not in css_text:
        css_text = css_text.rstrip() + "\n" + CSS_PATCH + "\n"
        css_path.write_text(css_text, encoding="utf-8")
        print(f"  ~ {css_path}")

    print("\nГотово. ВАЖНО: нужен пересбор frontend с --no-cache из-за новой зависимости.")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml down")
    print("  docker compose -f infra/docker-compose.yml build --no-cache frontend")
    print("  docker compose -f infra/docker-compose.yml up")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())