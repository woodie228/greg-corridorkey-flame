"""Opt-in SDR PNG adapter for the independent CorridorKey 2 MLX runtime.

No dependency installation, model downloads, Flame writes, or legacy backend changes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess
import uuid

OUTPUTS = {"fg": "FG", "alpha": "Matte", "checker": "Comp", "cutout": "Processed"}
SUPPORTED_PROFILES = {(768, 1280), (1024, 1536)}


def png_info(path):
    with Path(path).open("rb") as stream:
        header = stream.read(33)
    if (len(header) != 33 or header[:8] != b"\x89PNG\r\n\x1a\n"
            or header[8:16] != b"\x00\x00\x00\rIHDR"):
        raise ValueError("Not a PNG with an IHDR header: %s" % path)
    width, height, depth, color = struct.unpack(">IIBB", header[16:26])
    if not width or not height or depth not in (8, 16) or color not in (0, 2, 4, 6):
        raise ValueError("Only non-indexed 8/16-bit PNG is supported: %s" % path)
    return width, height, depth, color


def inspect_source(source):
    source = Path(source).resolve(strict=True)
    if source.is_dir():
        files = sorted(p for p in source.iterdir() if p.is_file() and not p.name.startswith("."))
        if not files or any(p.suffix.lower() != ".png" for p in files):
            raise ValueError("Input folder must contain only a zero-padded PNG sequence")
        stems = [p.stem for p in files]
        if not all(s.isdecimal() for s in stems) or len({len(s) for s in stems}) != 1:
            raise ValueError("Sequence names must be equally padded frame numbers")
        numbers = [int(s) for s in stems]
        if numbers != list(range(numbers[0], numbers[0] + len(numbers))):
            raise ValueError("Sequence contains missing frame numbers")
    elif source.suffix.lower() == ".png":
        files = [source]
    else:
        raise ValueError("Experimental backend accepts display-referred PNG only; EXR is unsupported")
    info = png_info(files[0])
    if any(png_info(p) != info for p in files[1:]):
        raise ValueError("All source frames must share dimensions, depth and channel layout")
    width, height, _, color = info
    if color not in (2, 6):
        raise ValueError("Source plates must be RGB or RGBA PNG")
    profile = ((height + 127) // 128 * 128, (width + 127) // 128 * 128)
    if profile not in SUPPORTED_PROFILES:
        raise ValueError("Unsupported padded shape %sx%s; never silently resizes" % profile)
    return source, files, info, profile


def plan(source, runtime_python, model_root, destination):
    source, files, info, profile = inspect_source(source)
    destination = Path(destination).resolve()
    if destination == source or source in destination.parents or destination in source.parents:
        raise ValueError("Input and destination must be separate without nesting")
    if destination.exists():
        raise ValueError("Destination must be new; existing results are never replaced")
    height, width = profile
    chunk, stride = (4, 2) if len(files) >= 4 else (1, 1)
    command = [str(Path(runtime_python).resolve(strict=True)), "-m", "corridorkey_mlx",
               "--input", str(source), "--model-root", str(Path(model_root).resolve(strict=True)),
               "--height", str(height), "--width", str(width),
               "--hann-chunk", str(chunk), "--hann-stride", str(stride),
               "--precision", "fp32", "--image-sequence", "--compile",
               "--outputs", *OUTPUTS]
    return {"command": command, "source_frames": [p.name for p in files],
            "width": info[0], "height": info[1], "profile_hw": list(profile),
            "destination": str(destination), "color": "display-referred sRGB",
            "experimental": True, "inference_validated": False}


def run(job, *, acknowledge_model_terms=False, runner=subprocess.run):
    if not acknowledge_model_terms:
        raise ValueError("Read model and foundation licenses and pass --acknowledge-model-terms before inference")
    destination = Path(job["destination"])
    # Recheck at execution time, then create exclusively to avoid overwriting user data.
    destination.mkdir(parents=True, exist_ok=False)
    work = destination / (".run-" + uuid.uuid4().hex)
    work.mkdir()
    raw = work / "raw"
    receipt = dict(job, status="running")
    report = destination / "experimental-run.json"
    report.write_text(json.dumps(receipt, indent=2) + "\n")
    try:
        runner(job["command"] + ["--check"], check=True)
        runner(job["command"] + ["--output-dir", str(raw)], check=True)
        expected_names = ["%06d.png" % i for i in range(len(job["source_frames"]))]
        for upstream_name in OUTPUTS:
            folder = raw / upstream_name
            found = sorted(p.name for p in folder.iterdir())
            if found != expected_names:
                raise ValueError("Unexpected frame set for %s" % upstream_name)
            for name in expected_names:
                w, h, depth, color = png_info(folder / name)
                if (w, h, depth) != (job["width"], job["height"], 16):
                    raise ValueError("Wrong output dimensions/depth: %s" % (folder / name))
                if upstream_name == "cutout" and color != 6:
                    raise ValueError("Processed output must contain RGBA")
        for upstream_name, flame_name in OUTPUTS.items():
            shutil.move(str(raw / upstream_name), str(destination / flame_name))
        receipt["status"] = "complete"
        receipt["note"] = "Adapter structure checks passed; this does not establish image quality or Flame validation."
    except Exception as error:
        receipt.update(status="failed", error=str(error))
        raise
    finally:
        report.write_text(json.dumps(receipt, indent=2) + "\n")
        # Delete only scratch owned by this adapter, preserving receipts and any mapped results.
        shutil.rmtree(work)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--runtime-python", required=True, help="Python in a separate community MLX runtime environment")
    parser.add_argument("--model-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--execute", action="store_true", help="Default prints a plan only")
    parser.add_argument("--acknowledge-model-terms", action="store_true")
    args = parser.parse_args()
    try:
        job = plan(args.input, args.runtime_python, args.model_root, args.output_dir)
        if args.execute:
            run(job, acknowledge_model_terms=args.acknowledge_model_terms)
        print(json.dumps(job, indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
