"""Fully decode experimental passes with the separate MLX environment's OpenCV.

Read-only: validates dimensions, frame coverage and straight-alpha pass contracts.
It does not establish visual quality, CUDA parity, or Flame compatibility.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

PASSES = ("FG", "Matte", "Comp", "Processed")


def validate(root):
    root = Path(root)
    receipt = json.loads((root / "experimental-run.json").read_text())
    if receipt["status"] != "complete":
        raise ValueError("Only complete runs can be validated")
    count = len(receipt["source_frames"])
    if not count:
        raise ValueError("Run has no source frames")
    names = ["%06d.png" % i for i in range(count)]
    for folder in PASSES:
        if sorted(p.name for p in (root / folder).iterdir()) != names:
            raise ValueError("Unexpected frame set in %s" % folder)
    alpha_means = []
    for name in names:
        passes = {key: cv2.imread(str(root / key / name), cv2.IMREAD_UNCHANGED) for key in PASSES}
        for key, image in passes.items():
            expected = (receipt["height"], receipt["width"], 4 if key == "Processed" else 3)
            if image is None or image.dtype != np.uint16 or image.shape != expected:
                raise ValueError("Cannot decode expected uint16 pass: %s/%s" % (key, name))
        matte = passes["Matte"]
        if not (np.array_equal(matte[:, :, 0], matte[:, :, 1])
                and np.array_equal(matte[:, :, 0], matte[:, :, 2])):
            raise ValueError("Matte channels disagree: %s" % name)
        if not np.array_equal(passes["Processed"][:, :, 3], matte[:, :, 0]):
            raise ValueError("Processed alpha disagrees with Matte: %s" % name)
        if not np.array_equal(passes["Processed"][:, :, :3], passes["FG"]):
            raise ValueError("Processed straight RGB disagrees with FG: %s" % name)
        alpha_means.append(float(matte[:, :, 0].mean() / 65535))
    return {"frames": count, "decoded_images": count * len(PASSES),
            "shape_hw": [receipt["height"], receipt["width"]], "dtype": "uint16",
            "processed_alpha_equals_matte": True, "processed_rgb_equals_fg": True,
            "alpha_mean_range": [min(alpha_means), max(alpha_means)],
            "visual_quality_validated": False}


def compare_alpha(first, second):
    first, second = Path(first), Path(second)
    receipts = [json.loads((root / "experimental-run.json").read_text()) for root in (first, second)]
    for key in ("source_frames", "width", "height"):
        if receipts[0][key] != receipts[1][key]:
            raise ValueError("Comparison requires matching source frames and dimensions")
    means, maxima = [], []
    for i in range(len(receipts[0]["source_frames"])):
        images = [cv2.imread(str(root / "Matte" / ("%06d.png" % i)), cv2.IMREAD_UNCHANGED)
                  for root in (first, second)]
        diff = np.abs(images[0][:, :, 0].astype(np.float64) - images[1][:, :, 0]) / 65535
        means.append(float(diff.mean()))
        maxima.append(float(diff.max()))
    return {"mean_alpha_absolute_difference": float(np.mean(means)),
            "maximum_alpha_absolute_difference": max(maxima),
            "interpretation": "Difference between outputs; neither output is ground truth."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--compare", type=Path, help="Also validate another run and compare its alpha")
    args = parser.parse_args()
    result = {"run": validate(args.root)}
    if args.compare:
        result["comparison_run"] = validate(args.compare)
        result["alpha_comparison"] = compare_alpha(args.root, args.compare)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
