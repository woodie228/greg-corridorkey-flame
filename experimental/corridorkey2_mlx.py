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


def inspect_hint(path, source_count, size, *, first_frame=False):
    path = Path(path).resolve(strict=True)
    if first_frame:
        files = [path] if path.is_file() else []
    else:
        files = sorted(p for p in path.iterdir() if p.is_file() and not p.name.startswith(".")) if path.is_dir() else []
        stems = [p.stem for p in files]
        if files and (not all(s.isdecimal() for s in stems) or len({len(s) for s in stems}) != 1):
            raise ValueError("Hint sequence requires equally padded numeric PNG names")
        numbers = [int(s) for s in stems] if files else []
        if numbers and numbers != list(range(numbers[0], numbers[0] + len(numbers))):
            raise ValueError("Hint sequence contains missing frames")
    expected_count = 1 if first_frame else source_count
    if len(files) != expected_count:
        raise ValueError("Hint frame count does not match the source")
    for file in files:
        if file.suffix.lower() != ".png":
            raise ValueError("Hints must be PNG")
        width, height, depth, color = png_info(file)
        if (width, height) != size or color not in (0, 6):
            raise ValueError("Hints must match source dimensions and be grayscale or RGBA PNG")
    return path, [p.name for p in files]


def plan(source, runtime_python, model_root, destination, *, framewise=False, temporal=False,
         hint_first_frame=None, hint_sequence=None, active_area=None):
    if framewise and temporal:
        raise ValueError("Choose framewise or temporal, not both")
    source, files, info, profile = inspect_source(source)
    destination = Path(destination).resolve()
    if destination == source or source in destination.parents or destination in source.parents:
        raise ValueError("Input and destination must be separate without nesting")
    if destination.exists():
        raise ValueError("Destination must be new; existing results are never replaced")
    if active_area is not None:
        x, y, active_width, active_height = active_area
        if min(x, y) < 0 or min(active_width, active_height) < 1 or x + active_width > info[0] or y + active_height > info[1]:
            raise ValueError("Active area must be inside the source canvas")
    height, width = profile
    chunk, stride = (4, 2) if len(files) >= 4 and temporal else (1, 1)
    runtime_python = Path(runtime_python).absolute()
    if not runtime_python.is_file():
        raise ValueError("Runtime Python does not exist: %s" % runtime_python)
    # Resolving a venv Python symlink bypasses pyvenv.cfg and loses its packages.
    command = [str(runtime_python), "-m", "corridorkey_mlx",
               "--input", str(source), "--model-root", str(Path(model_root).resolve(strict=True)),
               "--height", str(height), "--width", str(width),
               "--hann-chunk", str(chunk), "--hann-stride", str(stride),
               "--precision", "fp32", "--image-sequence", "--compile",
               "--outputs", *OUTPUTS]
    if active_area is not None:
        command.extend(["--active-area", *map(str, active_area)])
    hints = {}
    for value, key, flag, first in [(hint_first_frame, "first_frame", "--hint-first-frame", True),
                                    (hint_sequence, "sequence", "--hint-video", False)]:
        if value is not None:
            path, names = inspect_hint(value, len(files), info[:2], first_frame=first)
            command.extend([flag, str(path)])
            hints[key] = {"path": str(path), "ordered_files": names}
    if chunk > 1:
        # Requires the local runtime patch; argparse fails safely if it is missing.
        command.append("--no-carry-hint")
    return {"command": command, "source_frames": [p.name for p in files],
            "width": info[0], "height": info[1], "profile_hw": list(profile),
            "destination": str(destination), "color": "display-referred sRGB",
            "experimental": True, "production_validated": False,
            "temporal_window": chunk, "temporal_stride": stride,
            "framewise_requested": framewise, "temporal_requested": temporal,
            "carry_hint": False if chunk > 1 else None, "explicit_hints": hints,
            "active_area_xywh": list(active_area) if active_area is not None else None}


def run(job, *, acknowledge_model_terms=False, runner=subprocess.run):
    if not acknowledge_model_terms:
        raise ValueError("Read model and foundation licenses and pass --acknowledge-model-terms before inference")
    restore_canvas = None
    if job.get("active_area_xywh") is not None:
        try:
            import importlib.util
            helper = Path(__file__).with_name("restore_active_canvas.py")
            spec = importlib.util.spec_from_file_location("greg_restore_active_canvas", helper)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            restore_canvas = module.restore
        except ImportError as error:
            raise ValueError("Active-area restoration requires running the adapter with the isolated runtime Python") from error
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
        if restore_canvas is not None:
            restore_canvas(raw, (job["height"], job["width"]), job["active_area_xywh"])
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
        if (raw / "settings.json").is_file():
            shutil.copyfile(raw / "settings.json", destination / "runtime-settings.json")
        receipt["status"] = "complete"
        receipt["inference_completed"] = True
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--temporal", action="store_true",
                      help="Opt into t4 Hann 4/2 with self-generated carry disabled (requires patched runtime)")
    mode.add_argument("--framewise", action="store_true",
                        help="Explicitly use only t1 profiles; keeps RVM recurrence but loses Hann window context")
    parser.add_argument("--active-area", type=int, nargs=4, metavar=("X", "Y", "WIDTH", "HEIGHT"),
                        help="Explicit image area excluding empty source margins; requires patched runtime")
    parser.add_argument("--hint-first-frame", help="Artist grayscale/RGBA PNG for the first frame")
    parser.add_argument("--hint-sequence", help="Matching ordered grayscale/RGBA PNG matte sequence")
    parser.add_argument("--execute", action="store_true", help="Default prints a plan only")
    parser.add_argument("--acknowledge-model-terms", action="store_true")
    args = parser.parse_args()
    try:
        job = plan(args.input, args.runtime_python, args.model_root, args.output_dir, framewise=args.framewise, temporal=args.temporal,
                   hint_first_frame=args.hint_first_frame, hint_sequence=args.hint_sequence, active_area=args.active_area)
        if args.execute:
            run(job, acknowledge_model_terms=args.acknowledge_model_terms)
        print(json.dumps(job, indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
