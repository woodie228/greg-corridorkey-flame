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


def rough_hint(image, *, remove_black_columns=False, reference_matte=None):
    if image is None or image.ndim != 3 or image.shape[2] != 3 or image.dtype not in (np.uint8, np.uint16):
        raise ValueError("Expected an 8/16-bit three-channel SDR PNG plate")
    rgb = image.astype(np.float32) / np.iinfo(image.dtype).max
    blue, green, red = cv2.split(rgb)
    alpha = 1 - np.clip((green - np.maximum(red, blue) - .04) / .16, 0, 1)
    if reference_matte is not None:
        if reference_matte.dtype not in (np.uint8,np.uint16):
            raise ValueError("Reference must be an integer PNG matte")
        reference=reference_matte
        if reference.ndim==3:
            reference=reference[:,:,3] if reference.shape[2]==4 else reference[:,:,0]
        if reference.shape!=alpha.shape:
            raise ValueError("Reference dimensions must match source")
        reference=reference.astype(np.float32)/np.iinfo(reference_matte.dtype).max
        # Keep reviewed/semantic decisions for screen-like and dark neutral pixels.
        # Boost only non-screen foreground holdouts; do not classify black props
        # by connectivity or erase green wardrobe by its colour alone.
        screen_like=green-np.maximum(red,blue)>.04
        neutral_dark=(np.max(rgb,axis=2)<.25)&(np.max(rgb,axis=2)-np.min(rgb,axis=2)<.06)
        alpha=np.where(screen_like|neutral_dark,reference,alpha)
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


def generate(source, destination, *, remove_black_columns=False, reference_mattes=None):
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
    reference_root=Path(reference_mattes).resolve(strict=True) if reference_mattes is not None else None
    if reference_root is not None:
        reference_names=sorted(p.name for p in reference_root.iterdir() if p.is_file() and not p.name.startswith('.'))
        if reference_names!=[p.name for p in files]:
            raise ValueError("Reference frame names must exactly match source")
    destination.mkdir(parents=True, exist_ok=False)
    shape = None
    # Keep partial work on failure for diagnosis; never delete or overwrite user data.
    for file in files:
        image = cv2.imread(str(file), cv2.IMREAD_UNCHANGED)
        reference=cv2.imread(str(reference_root/file.name),cv2.IMREAD_UNCHANGED) if reference_root is not None else None
        if reference_root is not None and reference is None:raise ValueError("Cannot decode dark reference")
        hint = rough_hint(image, remove_black_columns=remove_black_columns,reference_matte=reference)
        if shape is not None and hint.shape != shape:
            raise ValueError("Changing source dimensions")
        shape = hint.shape
        if not cv2.imwrite(str(destination / file.name), hint):
            raise OSError("Cannot write hint %s" % file.name)
    return {'frames': len(files), 'shape_hw': list(shape), 'remove_black_columns': remove_black_columns, 'reference_used':reference_root is not None,
            'warning': 'Rough conditioning hints only; artist review required; not final output masks.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--remove-black-columns', action='store_true',
                        help='Explicitly discard uniform full-height dark pillarbox columns only')
    parser.add_argument('--reference-mattes',type=Path,help='Optional matching reviewed matte directory for screen-like/dark-neutral decisions')
    args = parser.parse_args()
    print(json.dumps(generate(args.source, args.destination, remove_black_columns=args.remove_black_columns,reference_mattes=args.reference_mattes), indent=2))


if __name__ == '__main__':
    main()
