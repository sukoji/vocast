#!/usr/bin/env python3
"""Generate vocast README banner with accurate South Korea map."""

from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
MAP_URL = "https://cdn.jsdelivr.net/npm/@svg-maps/south-korea@1.0.1/south-korea.svg"

W, H = 1200, 160
MAP_BOX = (524, 631)

# Macro regions used by vocast (province ids from @svg-maps/south-korea)
REGIONS: dict[str, dict] = {
    "gangwon": {
        "label": "강원",
        "fill": "#22d3ee",
        "stroke": "#67e8f9",
        "provinces": {"gangwon"},
        "marker": (292, 128),
        "label_anchor": "middle",
        "label_dx": 0,
    },
    "gyeongsang": {
        "label": "경상",
        "fill": "#3b82f6",
        "stroke": "#93c5fd",
        "provinces": {
            "north-gyeongsang",
            "south-gyeongsang",
            "busan",
            "daegu",
            "ulsan",
        },
        "marker": (348, 318),
        "label_anchor": "middle",
        "label_dx": 0,
    },
    "jeolla": {
        "label": "전라",
        "fill": "#10b981",
        "stroke": "#6ee7b7",
        "provinces": {"north-jeolla", "south-jeolla", "gwangju"},
        "marker": (168, 368),
        "label_anchor": "middle",
        "label_dx": 0,
    },
    "chungcheong": {
        "label": "충청",
        "fill": "#a855f7",
        "stroke": "#c4b5fd",
        "provinces": {
            "north-chungcheong",
            "south-chungcheong",
            "daejeon",
            "sejong",
        },
        "marker": (228, 262),
        "label_anchor": "middle",
        "label_dx": 0,
    },
}

NEUTRAL = {"seoul", "gyeonggi", "incheon", "jeju"}


def fetch_map_svg() -> str:
    import urllib.request

    with urllib.request.urlopen(MAP_URL, timeout=30) as resp:
        return resp.read().decode("utf-8")


def province_paths(svg_text: str) -> dict[str, str]:
    paths: dict[str, str] = {}
    for match in re.finditer(
        r'<path[^>]*\bid="([^"]+)"[^>]*\bd="([^"]+)"', svg_text, re.DOTALL
    ):
        paths[match.group(1)] = match.group(2)
    if not paths:
        root = ET.fromstring(svg_text)
        for el in root.iter():
            if el.tag.endswith("path") and "id" in el.attrib:
                paths[el.attrib["id"]] = el.attrib["d"]
    return paths


def region_for_province(pid: str) -> str | None:
    for key, cfg in REGIONS.items():
        if pid in cfg["provinces"]:
            return key
    return None


def build_svg(provinces: dict[str, str]) -> str:
    map_w, map_h = MAP_BOX
    # Fit map in right panel; exclude Jeju vertical tail a bit for balance
    map_scale = 0.26
    map_tx = W - map_w * map_scale - 28
    map_ty = (H - map_h * map_scale) / 2 + 2

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="vocast banner">',
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1200" y2="160" gradientUnits="userSpaceOnUse">',
        '<stop offset="0%" stop-color="#0b1220"/>',
        '<stop offset="100%" stop-color="#111827"/>',
        "</linearGradient>",
        '<linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">',
        '<stop offset="0%" stop-color="#22d3ee"/>',
        '<stop offset="100%" stop-color="#38bdf8"/>',
        "</linearGradient>",
        '<filter id="mapGlow" x="-10%" y="-10%" width="120%" height="120%">',
        '<feDropShadow dx="0" dy="0" stdDeviation="2" flood-color="#22d3ee" flood-opacity="0.25"/>',
        "</filter>",
        "</defs>",
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>',
        f'<rect x="0" y="{H - 3}" width="{W}" height="3" fill="url(#accent)" opacity="0.7"/>',
        # left accent
        f'<rect x="40" y="34" width="4" height="92" rx="2" fill="url(#accent)"/>',
        # title
        '<text x="56" y="78" fill="#f8fafc" font-family="Inter,Segoe UI,Helvetica,Arial,sans-serif" '
        'font-size="46" font-weight="700">vocast</text>',
        '<text x="56" y="104" fill="#cbd5e1" font-family="Inter,Segoe UI,Helvetica,Arial,sans-serif" '
        'font-size="17">Dialect Voice Dataset Pipeline</text>',
        '<text x="56" y="126" fill="#64748b" font-family="Inter,Segoe UI,Helvetica,Arial,sans-serif" '
        'font-size="12">Typecast TTS · Optional RVC · 4-region export</text>',
        # subtle waveform
        '<path d="M0 145 C80 132,160 152,240 145 S400 132,480 145" fill="none" '
        'stroke="#22d3ee" stroke-width="1" opacity="0.25"/>',
        f'<g transform="translate({map_tx:.1f},{map_ty:.1f}) scale({map_scale})" filter="url(#mapGlow)">',
    ]

    # Neutral base (full SK silhouette readability)
    for pid, d in provinces.items():
        parts.append(
            f'<path d="{d}" fill="#1e293b" stroke="#334155" stroke-width="1.2" '
            f'stroke-linejoin="round"/>'
        )

    # Colored macro regions on top
    for region_key, cfg in REGIONS.items():
        parts.append(f'<g id="region-{region_key}">')
        for pid in cfg["provinces"]:
            if pid in provinces:
                parts.append(
                    f'<path d="{provinces[pid]}" fill="{cfg["fill"]}" fill-opacity="0.55" '
                    f'stroke="{cfg["stroke"]}" stroke-width="1.4" stroke-linejoin="round"/>'
                )
        parts.append("</g>")

    # Muted non-dialect provinces
    for pid in NEUTRAL:
        if pid in provinces:
            parts.append(
                f'<path d="{provinces[pid]}" fill="#334155" fill-opacity="0.45" '
                f'stroke="#475569" stroke-width="1" stroke-linejoin="round"/>'
            )

    parts.append("</g>")

    # Region labels (screen space, after map transform)
    for cfg in REGIONS.values():
        mx, my = cfg["marker"]
        sx = map_tx + mx * map_scale
        sy = map_ty + my * map_scale
        anchor = cfg.get("label_anchor", "start")
        dx = cfg.get("label_dx", 8)
        parts.extend(
            [
                f'<text x="{sx + dx:.1f}" y="{sy + 4:.1f}" fill="#f8fafc" '
                f'text-anchor="{anchor}" '
                f'font-family="Noto Sans KR,Apple SD Gothic Neo,Malgun Gothic,sans-serif" '
                f'font-size="10" font-weight="700" '
                f'stroke="#0b1220" stroke-width="2" paint-order="stroke">{cfg["label"]}</text>',
            ]
        )

    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    svg_path = ASSETS / "vocast-banner.svg"
    png_path = ASSETS / "vocast-banner.png"

    provinces = province_paths(fetch_map_svg())
    missing = [p for cfg in REGIONS.values() for p in cfg["provinces"] if p not in provinces]
    if missing:
        raise SystemExit(f"Missing province paths: {missing}")

    svg = build_svg(provinces)
    svg_path.write_text(svg, encoding="utf-8")

    # 2x PNG for sharp display when README scales to 960px width
    subprocess.run(
        [
            "rsvg-convert",
            "-w",
            str(W * 2),
            "-h",
            str(H * 2),
            str(svg_path),
            "-o",
            str(png_path),
        ],
        check=True,
    )
    print(f"Wrote {svg_path}")
    print(f"Wrote {png_path}")


if __name__ == "__main__":
    main()
