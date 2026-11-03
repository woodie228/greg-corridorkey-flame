"""Opt-in rough green-screen conditioning hints, not final mattes.

Review before inference. Green wardrobe/reflections/transparency can be mislabeled.
The source is never modified and hints are never applied directly to output alpha.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import cv2
import numpy as np


def rough_hint(image, *, remove_black_columns=False):
    if image is None or image.ndim != 3 or image.shape[2] != 3 or image.dtype not in (np.uint8, np.uint16):
        raise ValueError("Expected an 8/16-bit three-channel SDR PNG plate")
    rgb = image.astype(np.float32) / np.iinfo(image.dtype).max
    blue, green, red = cv2.split(rgb)
    alpha = 1 - np.clip((green - np.maximum(red, blue) - .04) / .16, 0, 1)
    if remove_black_columns:
        # Only complete uniform edge columns; never flood-fill dark foreground props.
        dark = np.max(rgb, axis=(0, 2)) < .025
        left, right = 0, len(dark)
        while left < right and dark[left]:
            left += 1
        while right > left and dark[right - 1]:
            right -= 1
        alpha[:, :left] = 0
        alpha[:, right:] = 0
    return np.round(alpha * 65535).astype(np.uint16)


def generate(source, destination, *, remove_black_columns=False):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve()
    if destination == source or source in destination.parents or destination in source.parents:
        raise ValueError("Hint destination must be separate from source without nesting")
    files = sorted(p for p in source.iterdir() if p.is_file() and not p.name.startswith('.'))
    if not files or any(p.suffix.lower() != '.png' for p in files):
        raise ValueError("Source must be a numbered PNG sequence directory")
    names = [p.stem for p in files]
    if not all(s.isdecimal() for s in names) or len({len(s) for s in names}) != 1:
        raise ValueError("Source names must be equally padded frame numbers")
    numbers = [int(s) for s in names]
    if numbers != list(range(numbers[0], numbers[0] + len(numbers))):
        raise ValueError("Source sequence has missing frames")
    destination.mkdir(parents=True, exist_ok=False)
    shape = None
    # Keep partial work on failure for diagnosis; never delete or overwrite user data.
    for file in files:
        image = cv2.imread(str(file), cv2.IMREAD_UNCHANGED)
        hint = rough_hint(image, remove_black_columns=remove_black_columns)
        if shape is not None and hint.shape != shape:
            raise ValueError("Changing source dimensions")
        shape = hint.shape
        if not cv2.imwrite(str(destination / file.name), hint):
            raise OSError("Cannot write hint %s" % file.name)
    return {'frames': len(files), 'shape_hw': list(shape), 'remove_black_columns': remove_black_columns,
            'warning': 'Rough conditioning hints only; artist review required; not final output masks.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--remove-black-columns', action='store_true',
                        help='Explicitly discard uniform full-height dark pillarbox columns only')
    args = parser.parse_args()
    print(json.dumps(generate(args.source, args.destination, remove_black_columns=args.remove_black_columns), indent=2))


if __name__ == '__main__':
    main()
