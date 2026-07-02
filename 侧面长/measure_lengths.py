#!/usr/bin/env python3
import argparse
import csv
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np


IMAGE_SUFFIXES = {".bmp", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
CSV_FLOAT_FMT = ".6f"


@dataclass
class BaseDetection:
    threshold: float
    bbox_x: int
    bbox_y: int
    bbox_w: int
    bbox_h: int
    component_area: int
    component_fill: float
    slope: float
    confidence: float
    mask: np.ndarray

    @property
    def left_edge(self) -> float:
        return float(self.bbox_x)

    @property
    def right_edge(self) -> float:
        return float(self.bbox_x + self.bbox_w)


@dataclass
class EdgeDetection:
    left_x: float
    right_x: float
    left_strength: float
    right_strength: float
    left_contrast: float
    right_contrast: float
    profile_height: int
    confidence: float
    method: str


@dataclass
class Calibration:
    label_path: str
    label_image_path: str
    manual_points: Tuple[Tuple[float, float], Tuple[float, float]]
    manual_length_px: float
    manual_slope: float
    manual_angle_deg: float
    reference_base_slope: float
    x_left_offset: float
    x_right_offset: float
    edge_x_left_offset: float
    edge_x_right_offset: float
    reference_edge_left: float
    reference_edge_right: float
    y_mid_fraction: float
    expected_width_px: float


def fnum(value: Optional[float], digits: str = CSV_FLOAT_FMT) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return ""
    return format(float(value), digits)


def read_label_line(label_json: Path) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    data = json.loads(label_json.read_text(encoding="utf-8"))
    for shape in data.get("shapes", []):
        points = shape.get("points") or []
        if shape.get("shape_type") == "line" and len(points) >= 2:
            p1 = (float(points[0][0]), float(points[0][1]))
            p2 = (float(points[1][0]), float(points[1][1]))
            if p2[0] < p1[0]:
                p1, p2 = p2, p1
            return p1, p2
    raise ValueError(f"No line annotation found in {label_json}")


def load_gray(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Failed to read image: {path}")
    return image


def robust_line_fit(xs: np.ndarray, ys: np.ndarray) -> Tuple[float, float]:
    if len(xs) < 2:
        return 0.0, float(ys[0]) if len(ys) else 0.0

    work_x = xs.astype(np.float64)
    work_y = ys.astype(np.float64)
    for _ in range(4):
        if len(work_x) < 8:
            break
        slope, intercept = np.polyfit(work_x, work_y, 1)
        residuals = work_y - (slope * work_x + intercept)
        med = float(np.median(residuals))
        mad = float(np.median(np.abs(residuals - med)))
        if mad <= 1e-6:
            break
        keep = np.abs(residuals - med) <= 3.0 * 1.4826 * mad
        if int(keep.sum()) < max(8, int(0.45 * len(work_x))):
            break
        work_x = work_x[keep]
        work_y = work_y[keep]

    slope, intercept = np.polyfit(work_x, work_y, 1)
    return float(slope), float(intercept)


def estimate_component_slope(component_mask: np.ndarray, bbox: Tuple[int, int, int, int]) -> float:
    x, _y, w, _h = bbox
    xs: List[int] = []
    centers: List[float] = []
    for xx in range(x, x + w):
        yy = np.flatnonzero(component_mask[:, xx])
        if yy.size:
            xs.append(xx)
            centers.append((float(yy.min()) + float(yy.max())) / 2.0)

    if len(xs) < 16:
        return 0.0

    xs_arr = np.asarray(xs, dtype=np.float64)
    centers_arr = np.asarray(centers, dtype=np.float64)
    lo = x + 0.10 * w
    hi = x + 0.90 * w
    keep = (xs_arr >= lo) & (xs_arr <= hi)
    if int(keep.sum()) >= 16:
        xs_arr = xs_arr[keep]
        centers_arr = centers_arr[keep]

    slope, _intercept = robust_line_fit(xs_arr, centers_arr)
    return slope


def detect_bright_side_band(gray: np.ndarray) -> BaseDetection:
    height, width = gray.shape[:2]
    threshold, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = (binary > 0).astype(np.uint8)

    close_w = max(31, int(round(width * 0.010)))
    if close_w % 2 == 0:
        close_w += 1
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close_w, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel)

    num_labels, labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, 8)
    candidates = []
    image_area = float(height * width)
    for label_id in range(1, num_labels):
        x, y, w, h, area = [int(v) for v in stats[label_id]]
        if w <= 0 or h <= 0:
            continue
        aspect = w / max(h, 1)
        width_ratio = w / width
        height_ratio = h / height
        area_ratio = area / image_area
        if width_ratio < 0.35 or aspect < 4.0 or area_ratio < 0.015:
            continue
        if height_ratio > 0.45:
            continue

        center_y = y + h / 2.0
        centrality = 1.0 - min(1.0, abs(center_y - height / 2.0) / (height / 2.0))
        score = area * (1.0 + width_ratio) * (1.0 + min(aspect / 12.0, 1.0)) * (0.5 + centrality)
        candidates.append((score, label_id, x, y, w, h, area, aspect, width_ratio))

    if not candidates:
        raise ValueError("No long bright side band component was found")

    candidates.sort(reverse=True, key=lambda item: item[0])
    _score, label_id, x, y, w, h, area, aspect, width_ratio = candidates[0]
    component = labels == label_id
    component_fill = float(area) / float(max(w * h, 1))
    slope = estimate_component_slope(component, (x, y, w, h))

    width_score = min(1.0, width_ratio / 0.75)
    aspect_score = min(1.0, aspect / 8.0)
    area_score = min(1.0, (area / image_area) / 0.06)
    fill_score = min(1.0, component_fill / 0.45)
    confidence = max(0.0, min(1.0, 0.40 * width_score + 0.25 * aspect_score + 0.20 * area_score + 0.15 * fill_score))

    return BaseDetection(
        threshold=float(threshold),
        bbox_x=x,
        bbox_y=y,
        bbox_w=w,
        bbox_h=h,
        component_area=area,
        component_fill=component_fill,
        slope=slope,
        confidence=confidence,
        mask=component,
    )


def sample_profile_along_line(
    gray: np.ndarray,
    slope: float,
    y_mid: float,
    x_mid: float,
    half_width: int,
) -> np.ndarray:
    width = gray.shape[1]
    xs = np.arange(width, dtype=np.float32)
    ys = y_mid + slope * (xs.astype(np.float64) - float(x_mid))
    image_f = gray.astype(np.float32)
    samples = []
    map_x = xs.reshape(1, -1)
    for offset in range(-half_width, half_width + 1):
        map_y = (ys + offset).astype(np.float32).reshape(1, -1)
        sampled = cv2.remap(
            image_f,
            map_x,
            map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        ).reshape(-1)
        samples.append(sampled)
    profile = np.median(np.vstack(samples), axis=0).astype(np.float32)
    smoothed = cv2.GaussianBlur(profile.reshape(1, -1), (0, 0), sigmaX=2.0).reshape(-1)
    return smoothed


def sample_percentile_projection_profile(
    gray: np.ndarray,
    base: BaseDetection,
    percentile: float = 98.0,
) -> np.ndarray:
    y0 = max(0, int(base.bbox_y))
    y1 = min(gray.shape[0], int(base.bbox_y + base.bbox_h))
    if y1 <= y0 + 4:
        raise ValueError("side band projection ROI is too small")
    roi = gray[y0:y1, :].astype(np.float32)
    profile = np.percentile(roi, percentile, axis=0).astype(np.float32)
    smoothed = cv2.GaussianBlur(profile.reshape(1, -1), (0, 0), sigmaX=2.0).reshape(-1)
    return smoothed


def subpixel_peak_position(values: np.ndarray, index: int) -> float:
    if index <= 0 or index >= len(values) - 1:
        return float(index)
    y0 = float(values[index - 1])
    y1 = float(values[index])
    y2 = float(values[index + 1])
    denom = y0 - 2.0 * y1 + y2
    if abs(denom) < 1e-9:
        return float(index)
    delta = 0.5 * (y0 - y2) / denom
    delta = max(-1.0, min(1.0, delta))
    return float(index) + delta


def median_slice(profile: np.ndarray, start: int, end: int) -> float:
    start = max(0, min(len(profile), int(start)))
    end = max(start + 1, min(len(profile), int(end)))
    return float(np.median(profile[start:end]))


def locate_edge_from_profile(
    profile: np.ndarray,
    gradient: np.ndarray,
    center: float,
    polarity: str,
    before: int,
    after: int,
) -> Tuple[float, float, float]:
    width = len(profile)
    start = max(1, int(round(center)) - before)
    end = min(width - 2, int(round(center)) + after)
    if end <= start + 2:
        raise ValueError("edge search window is too small")

    center_i = int(round(center))
    if polarity == "rising":
        dark = median_slice(profile, center_i - before, center_i - 8)
        bright = median_slice(profile, center_i + 18, center_i + after)
    else:
        bright = median_slice(profile, center_i - before, center_i - 18)
        dark = median_slice(profile, center_i + 8, center_i + after)
    contrast = max(0.0, bright - dark)
    if contrast < 20.0:
        raise ValueError("edge contrast is too weak")

    threshold = dark + 0.08 * contrast
    position: Optional[float] = None
    if polarity == "rising":
        for i in range(start, end):
            v0 = float(profile[i])
            v1 = float(profile[i + 1])
            if v0 <= threshold <= v1 and v1 > v0:
                frac = (threshold - v0) / max(v1 - v0, 1e-6)
                position = float(i) + max(0.0, min(1.0, frac))
                break
    else:
        for i in range(end - 1, start - 1, -1):
            v0 = float(profile[i])
            v1 = float(profile[i + 1])
            if v0 >= threshold >= v1 and v0 > v1:
                frac = (v0 - threshold) / max(v0 - v1, 1e-6)
                position = float(i) + max(0.0, min(1.0, frac))
                break

    if position is None:
        raise ValueError("edge threshold crossing was not found")

    ipos = int(round(position))
    signed = gradient if polarity == "rising" else -gradient
    strength = float(max(0.0, signed[ipos]))
    return position, strength, contrast


def detect_subpixel_side_edges(
    gray: np.ndarray,
    base: BaseDetection,
    measurement_slope: float,
    y_mid: float,
) -> EdgeDetection:
    del measurement_slope, y_mid
    profile = sample_percentile_projection_profile(gray, base, percentile=98.0)
    gradient = np.gradient(profile)

    left_x, left_strength, left_contrast = locate_edge_from_profile(
        profile,
        gradient,
        center=base.left_edge,
        polarity="rising",
        before=45,
        after=120,
    )
    right_x, right_strength, right_contrast = locate_edge_from_profile(
        profile,
        gradient,
        center=base.right_edge,
        polarity="falling",
        before=120,
        after=45,
    )

    if right_x <= left_x:
        raise ValueError("subpixel side edge order is invalid")

    strength_score = min(1.0, min(left_strength, right_strength) / 15.0)
    contrast_score = min(1.0, min(left_contrast, right_contrast) / 100.0)
    confidence = max(0.0, min(1.0, 0.55 * strength_score + 0.45 * contrast_score))
    return EdgeDetection(
        left_x=left_x,
        right_x=right_x,
        left_strength=left_strength,
        right_strength=right_strength,
        left_contrast=left_contrast,
        right_contrast=right_contrast,
        profile_height=base.bbox_h,
        confidence=confidence,
        method="subpixel_projection_edge",
    )


def build_calibration(label_json: Path, label_image: Path) -> Calibration:
    p1, p2 = read_label_line(label_json)
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    if abs(dx) < 1e-6:
        raise ValueError("Reference line is vertical or too short for length calibration")

    manual_length = math.hypot(dx, dy)
    manual_slope = dy / dx
    manual_angle = math.degrees(math.atan2(dy, dx))

    gray = load_gray(label_image)
    base = detect_bright_side_band(gray)
    y_mid = (p1[1] + p2[1]) / 2.0
    y_mid_fraction = (y_mid - base.bbox_y) / max(base.bbox_h, 1)
    y_mid_fraction = max(-0.25, min(1.25, y_mid_fraction))
    edge = detect_subpixel_side_edges(gray, base, manual_slope, y_mid)

    return Calibration(
        label_path=str(label_json),
        label_image_path=str(label_image),
        manual_points=(p1, p2),
        manual_length_px=manual_length,
        manual_slope=manual_slope,
        manual_angle_deg=manual_angle,
        reference_base_slope=base.slope,
        x_left_offset=p1[0] - base.left_edge,
        x_right_offset=p2[0] - base.right_edge,
        edge_x_left_offset=p1[0] - edge.left_x,
        edge_x_right_offset=p2[0] - edge.right_x,
        reference_edge_left=edge.left_x,
        reference_edge_right=edge.right_x,
        y_mid_fraction=y_mid_fraction,
        expected_width_px=dx,
    )


def parse_metadata(path: Path) -> Dict[str, str]:
    text = path.with_suffix("").as_posix().lower()
    sample_patterns = [
        r"(?:^|[/_\-\s])(?:sample|s)[_\-\s]*0*(\d+)(?=$|[/_\-\s])",
        r"(?:^|[/_\-\s])yangpin[_\-\s]*0*(\d+)(?=$|[/_\-\s])",
        r"(?:^|[/_\-\s])样品[_\-\s]*0*(\d+)(?=$|[/_\-\s])",
    ]
    position_patterns = [
        r"(?:^|[/_\-\s])(?:position|pos)[_\-\s]*0*(\d+)(?=$|[/_\-\s])",
        r"(?:^|[/_\-\s])位置[_\-\s]*0*(\d+)(?=$|[/_\-\s])",
    ]
    repeat_patterns = [
        r"(?:^|[/_\-\s])(?:repeat|rep|shot|run|idx|r)[_\-\s]*0*(\d+)(?=$|[/_\-\s])",
        r"(?:^|[/_\-\s])(?:第)?0*(\d+)(?:次)(?=$|[/_\-\s])",
    ]

    def first_match(patterns: Sequence[str]) -> Optional[str]:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return str(int(match.group(1)))
        return None

    sample = first_match(sample_patterns)
    position = first_match(position_patterns)
    repeat = first_match(repeat_patterns)
    return {
        "sample_id": f"s{sample}" if sample is not None else "unknown_sample",
        "position": f"pos{position}" if position is not None else "unknown_position",
        "repeat_index": repeat or "",
    }


def path_is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def collect_images(
    input_path: Path,
    recursive: bool,
    excluded_paths: Iterable[Path],
    excluded_dirs: Iterable[Path],
) -> List[Path]:
    excluded = {p.resolve() for p in excluded_paths if p.exists()}
    excluded_roots = [p for p in excluded_dirs if p.exists()]
    if input_path.is_file():
        candidates = [input_path]
    else:
        iterator = input_path.rglob("*") if recursive else input_path.glob("*")
        candidates = [p for p in iterator if p.is_file()]

    images = []
    for path in candidates:
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if path.resolve() in excluded:
            continue
        if any(path_is_under(path, root) for root in excluded_roots):
            continue
        images.append(path)
    return sorted(images, key=lambda p: p.as_posix())


def draw_overlay(
    gray: np.ndarray,
    detection: BaseDetection,
    result: Dict[str, object],
    overlay_path: Path,
) -> None:
    overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    x, y, w, h = detection.bbox_x, detection.bbox_y, detection.bbox_w, detection.bbox_h
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 180, 255), 3)

    x1 = int(round(float(result["x1_px"])))
    y1 = int(round(float(result["y1_px"])))
    x2 = int(round(float(result["x2_px"])))
    y2 = int(round(float(result["y2_px"])))
    cv2.line(overlay, (x1, y1), (x2, y2), (0, 0, 255), 5, cv2.LINE_AA)
    cv2.circle(overlay, (x1, y1), 16, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.circle(overlay, (x2, y2), 16, (0, 255, 0), 4, cv2.LINE_AA)

    label = f"length={float(result['length_px']):.2f}px  conf={float(result['confidence']):.2f}"
    text_origin = (max(20, x), max(45, y - 20))
    cv2.putText(overlay, label, text_origin, cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 7, cv2.LINE_AA)
    cv2.putText(overlay, label, text_origin, cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 0), 3, cv2.LINE_AA)

    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(overlay_path), overlay)


def detect_length(image_path: Path, output_overlay_dir: Path, calibration: Calibration) -> Tuple[Dict[str, object], List[Dict[str, str]]]:
    gray = load_gray(image_path)
    height, width = gray.shape[:2]
    metadata = parse_metadata(image_path)
    anomalies: List[Dict[str, str]] = []

    base = detect_bright_side_band(gray)
    measurement_slope = calibration.manual_slope + (base.slope - calibration.reference_base_slope)
    measurement_slope = max(-0.08, min(0.08, measurement_slope))

    y_mid = base.bbox_y + calibration.y_mid_fraction * base.bbox_h
    measurement_method = "subpixel_projection_edge"
    edge_left_x = float("nan")
    edge_right_x = float("nan")
    edge_left_strength = float("nan")
    edge_right_strength = float("nan")
    edge_left_contrast = float("nan")
    edge_right_contrast = float("nan")
    edge_profile_height = 0
    edge_confidence = 0.0

    try:
        edge = detect_subpixel_side_edges(gray, base, measurement_slope, y_mid)
        edge_left_x = edge.left_x
        edge_right_x = edge.right_x
        edge_left_strength = edge.left_strength
        edge_right_strength = edge.right_strength
        edge_left_contrast = edge.left_contrast
        edge_right_contrast = edge.right_contrast
        edge_profile_height = edge.profile_height
        edge_confidence = edge.confidence
        x1 = edge.left_x + calibration.edge_x_left_offset
        x2 = edge.right_x + calibration.edge_x_right_offset
    except Exception as exc:
        measurement_method = "bbox_fallback"
        x1 = base.left_edge + calibration.x_left_offset
        x2 = base.right_edge + calibration.x_right_offset
        anomalies.append(
            anomaly_row(
                image_path,
                metadata,
                "warning",
                "subpixel_edge_failed",
                f"Falling back to connected-component box endpoints: {exc}",
                "",
                "",
            )
        )

    x_mid = (x1 + x2) / 2.0
    y1 = y_mid + measurement_slope * (x1 - x_mid)
    y2 = y_mid + measurement_slope * (x2 - x_mid)
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    angle_deg = math.degrees(math.atan2(dy, dx))
    delta = length - calibration.manual_length_px
    ratio = length / calibration.manual_length_px if calibration.manual_length_px > 0 else float("nan")
    confidence = min(base.confidence, edge_confidence) if measurement_method == "subpixel_projection_edge" else base.confidence * 0.60

    if metadata["sample_id"] == "unknown_sample" or metadata["position"] == "unknown_position":
        anomalies.append(
            anomaly_row(
                image_path,
                metadata,
                "warning",
                "metadata_parse_failed",
                "Could not parse sample_id and/or position from path; repeatability grouping may be incomplete.",
                "",
                "",
            )
        )

    if measurement_method == "subpixel_projection_edge" and edge_confidence < 0.40:
        anomalies.append(
            anomaly_row(
                image_path,
                metadata,
                "warning",
                "low_edge_confidence",
                "Subpixel edge confidence is lower than expected.",
                fnum(edge_confidence),
                ">=0.40",
            )
        )

    if base.confidence < 0.55:
        anomalies.append(
            anomaly_row(
                image_path,
                metadata,
                "warning",
                "low_confidence",
                "Detected side band confidence is lower than expected.",
                fnum(base.confidence),
                ">=0.55",
            )
        )

    if not (0.75 <= ratio <= 1.25):
        anomalies.append(
            anomaly_row(
                image_path,
                metadata,
                "error",
                "length_out_of_reference_range",
                "Measured length differs strongly from the single labeled reference.",
                fnum(ratio),
                "0.75..1.25",
            )
        )

    if x1 < -5 or x2 > width + 5 or y1 < -5 or y2 > height + 5:
        anomalies.append(
            anomaly_row(
                image_path,
                metadata,
                "warning",
                "endpoint_outside_image",
                "Calibrated endpoint falls outside the image bounds.",
                f"({fnum(x1)},{fnum(y1)})-({fnum(x2)},{fnum(y2)})",
                f"0..{width},0..{height}",
            )
        )

    overlay_path = output_overlay_dir / f"{safe_stem(image_path)}_overlay.png"
    result: Dict[str, object] = {
        "image_path": image_path.as_posix(),
        "image_name": image_path.name,
        "sample_id": metadata["sample_id"],
        "position": metadata["position"],
        "repeat_index": metadata["repeat_index"],
        "status": "OK" if not any(a["severity"] == "error" for a in anomalies) else "CHECK",
        "length_px": length,
        "dx_px": dx,
        "dy_px": dy,
        "angle_deg": angle_deg,
        "measurement_method": measurement_method,
        "x1_px": x1,
        "y1_px": y1,
        "x2_px": x2,
        "y2_px": y2,
        "band_bbox_x": base.bbox_x,
        "band_bbox_y": base.bbox_y,
        "band_bbox_w": base.bbox_w,
        "band_bbox_h": base.bbox_h,
        "component_area_px": base.component_area,
        "component_fill": base.component_fill,
        "threshold": base.threshold,
        "band_slope": base.slope,
        "confidence": confidence,
        "band_confidence": base.confidence,
        "edge_confidence": edge_confidence,
        "edge_left_x_px": edge_left_x,
        "edge_right_x_px": edge_right_x,
        "edge_left_strength": edge_left_strength,
        "edge_right_strength": edge_right_strength,
        "edge_left_contrast": edge_left_contrast,
        "edge_right_contrast": edge_right_contrast,
        "edge_profile_height_px": edge_profile_height,
        "reference_length_px": calibration.manual_length_px,
        "length_delta_from_reference_px": delta,
        "length_ratio_to_reference": ratio,
        "overlay_path": overlay_path.as_posix(),
        "message": "" if not anomalies else "; ".join(a["code"] for a in anomalies),
    }
    draw_overlay(gray, base, result, overlay_path)
    return result, anomalies


def safe_stem(path: Path) -> str:
    base = path.with_suffix("").as_posix().strip("/").replace("/", "__")
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", base)


def anomaly_row(
    image_path: Path,
    metadata: Dict[str, str],
    severity: str,
    code: str,
    message: str,
    value: str,
    limit: str,
) -> Dict[str, str]:
    return {
        "image_path": image_path.as_posix(),
        "image_name": image_path.name,
        "sample_id": metadata.get("sample_id", ""),
        "position": metadata.get("position", ""),
        "repeat_index": metadata.get("repeat_index", ""),
        "severity": severity,
        "code": code,
        "message": message,
        "value": value,
        "limit": limit,
    }


def write_measurements(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    fieldnames = [
        "image_path",
        "image_name",
        "sample_id",
        "position",
        "repeat_index",
        "status",
        "length_px",
        "dx_px",
        "dy_px",
        "angle_deg",
        "measurement_method",
        "x1_px",
        "y1_px",
        "x2_px",
        "y2_px",
        "band_bbox_x",
        "band_bbox_y",
        "band_bbox_w",
        "band_bbox_h",
        "component_area_px",
        "component_fill",
        "threshold",
        "band_slope",
        "confidence",
        "band_confidence",
        "edge_confidence",
        "edge_left_x_px",
        "edge_right_x_px",
        "edge_left_strength",
        "edge_right_strength",
        "edge_left_contrast",
        "edge_right_contrast",
        "edge_profile_height_px",
        "reference_length_px",
        "length_delta_from_reference_px",
        "length_ratio_to_reference",
        "overlay_path",
        "message",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(format_row(row, fieldnames))


def format_row(row: Dict[str, object], fieldnames: Sequence[str]) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for key in fieldnames:
        value = row.get(key, "")
        if isinstance(value, float):
            out[key] = fnum(value)
        else:
            out[key] = value
    return out


def write_anomalies(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    fieldnames = [
        "image_path",
        "image_name",
        "sample_id",
        "position",
        "repeat_index",
        "severity",
        "code",
        "message",
        "value",
        "limit",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def group_repeatability(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    groups: Dict[Tuple[str, str], List[Dict[str, object]]] = {}
    for row in rows:
        if row.get("status") != "OK":
            continue
        key = (str(row.get("sample_id", "")), str(row.get("position", "")))
        groups.setdefault(key, []).append(row)

    summary = []
    for (sample_id, position), group in sorted(groups.items()):
        lengths = np.asarray([float(r["length_px"]) for r in group], dtype=np.float64)
        angles = np.asarray([float(r["angle_deg"]) for r in group], dtype=np.float64)
        x1s = np.asarray([float(r["x1_px"]) for r in group], dtype=np.float64)
        x2s = np.asarray([float(r["x2_px"]) for r in group], dtype=np.float64)
        mean_length = float(np.mean(lengths))
        std_length = float(np.std(lengths, ddof=1)) if len(lengths) > 1 else 0.0
        summary.append(
            {
                "sample_id": sample_id,
                "position": position,
                "image_count": len(group),
                "ok_count": len(group),
                "length_min_px": float(np.min(lengths)),
                "length_max_px": float(np.max(lengths)),
                "length_range_px": float(np.max(lengths) - np.min(lengths)),
                "length_mean_px": mean_length,
                "length_std_px": std_length,
                "length_cv_percent": (std_length / mean_length * 100.0) if mean_length else 0.0,
                "angle_min_deg": float(np.min(angles)),
                "angle_max_deg": float(np.max(angles)),
                "angle_range_deg": float(np.max(angles) - np.min(angles)),
                "x1_range_px": float(np.max(x1s) - np.min(x1s)),
                "x2_range_px": float(np.max(x2s) - np.min(x2s)),
            }
        )
    return summary


def write_repeatability(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    fieldnames = [
        "sample_id",
        "position",
        "image_count",
        "ok_count",
        "length_min_px",
        "length_max_px",
        "length_range_px",
        "length_mean_px",
        "length_std_px",
        "length_cv_percent",
        "angle_min_deg",
        "angle_max_deg",
        "angle_range_deg",
        "x1_range_px",
        "x2_range_px",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(format_row(row, fieldnames))


def write_report(
    path: Path,
    input_path: Path,
    rows: Sequence[Dict[str, object]],
    repeatability_rows: Sequence[Dict[str, object]],
    anomalies: Sequence[Dict[str, str]],
    calibration: Calibration,
) -> None:
    ok_count = sum(1 for row in rows if row.get("status") == "OK")
    priority = [r for r in repeatability_rows if str(r.get("position")) == "pos1"]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": input_path.as_posix(),
        "algorithm": {
            "name": "calibrated_bright_side_band_length",
            "version": "1.1",
            "description": "Detects the long bright side band, then refines both endpoints with a high-percentile projection profile and subpixel threshold crossings calibrated from the single manual line.",
            "uses_synthetic_data": False,
            "uses_fake_implementation": False,
        },
        "reference": {
            "label_json": calibration.label_path,
            "label_image": calibration.label_image_path,
            "manual_points": calibration.manual_points,
            "manual_length_px": calibration.manual_length_px,
            "manual_angle_deg": calibration.manual_angle_deg,
            "x_left_offset_px": calibration.x_left_offset,
            "x_right_offset_px": calibration.x_right_offset,
            "edge_x_left_offset_px": calibration.edge_x_left_offset,
            "edge_x_right_offset_px": calibration.edge_x_right_offset,
            "reference_edge_left_px": calibration.reference_edge_left,
            "reference_edge_right_px": calibration.reference_edge_right,
            "y_mid_fraction": calibration.y_mid_fraction,
        },
        "summary": {
            "image_count": len(rows),
            "ok_count": ok_count,
            "check_count": len(rows) - ok_count,
            "anomaly_count": len(anomalies),
            "repeatability_group_count": len(repeatability_rows),
        },
        "priority_pos1_repeatability": priority,
        "repeatability": list(repeatability_rows),
        "anomalies": list(anomalies),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure side-mark length from BMP images.")
    parser.add_argument("--input", default="sample", help="Image file or directory to process. Defaults to sample/.")
    parser.add_argument("--label-json", default="s1_label.json", help="LabelMe JSON containing the single manual line.")
    parser.add_argument("--label-image", default="s1_label.bmp", help="Image corresponding to the manual line.")
    parser.add_argument("--output", default="output", help="Output directory. Defaults to output/.")
    parser.add_argument("--recursive", action="store_true", help="Recursively scan input directory.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input)
    label_json = Path(args.label_json)
    label_image = Path(args.label_image)
    output_dir = Path(args.output)
    overlay_dir = output_dir / "detection_overlays"

    if not input_path.exists():
        print(f"ERROR: input path does not exist: {input_path}", file=sys.stderr)
        return 2
    if not label_json.exists():
        print(f"ERROR: label JSON does not exist: {label_json}", file=sys.stderr)
        return 2
    if not label_image.exists():
        print(f"ERROR: label image does not exist: {label_image}", file=sys.stderr)
        return 2

    print(f"Loading label: {label_json}")
    calibration = build_calibration(label_json, label_image)
    print(
        "Reference length: "
        f"{calibration.manual_length_px:.3f}px, "
        f"angle={calibration.manual_angle_deg:.3f}deg"
    )

    images = collect_images(input_path, args.recursive, excluded_paths=[label_image], excluded_dirs=[output_dir])
    if not images:
        print(f"ERROR: no images found under {input_path}", file=sys.stderr)
        return 2

    measurements: List[Dict[str, object]] = []
    anomalies: List[Dict[str, str]] = []

    for image_path in images:
        print(f"Processing {image_path.as_posix()} ...")
        try:
            result, image_anomalies = detect_length(image_path, overlay_dir, calibration)
            measurements.append(result)
            anomalies.extend(image_anomalies)
            print(
                "Detected "
                f"{image_path.name}: sample={result['sample_id']} position={result['position']} "
                f"length={float(result['length_px']):.3f}px "
                f"confidence={float(result['confidence']):.3f} "
                f"status={result['status']}"
            )
        except Exception as exc:
            metadata = parse_metadata(image_path)
            anomaly = anomaly_row(
                image_path,
                metadata,
                "error",
                "detection_failed",
                str(exc),
                "",
                "",
            )
            anomalies.append(anomaly)
            measurements.append(
                {
                    "image_path": image_path.as_posix(),
                    "image_name": image_path.name,
                    "sample_id": metadata["sample_id"],
                    "position": metadata["position"],
                    "repeat_index": metadata["repeat_index"],
                    "status": "ERROR",
                    "message": str(exc),
                }
            )
            print(f"ERROR detecting {image_path.name}: {exc}", file=sys.stderr)

    repeatability = group_repeatability(measurements)
    write_measurements(output_dir / "measurements.csv", measurements)
    write_repeatability(output_dir / "static_repeatability.csv", repeatability)
    write_anomalies(output_dir / "detection_anomalies.csv", anomalies)
    write_report(output_dir / "repeatability_report.json", input_path, measurements, repeatability, anomalies, calibration)

    print(f"Wrote {output_dir / 'measurements.csv'}")
    print(f"Wrote {output_dir / 'static_repeatability.csv'}")
    print(f"Wrote {output_dir / 'detection_anomalies.csv'}")
    print(f"Wrote {output_dir / 'repeatability_report.json'}")
    print(f"Wrote overlays to {overlay_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
