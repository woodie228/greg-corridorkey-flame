"""
Flame custom action: export selected clips to CorridorKey, run inference,
and import the generated passes back into Flame.

Install location:
    /opt/Autodesk/user/ryan_2026/python/greg_corridor_key_roundtrip.py

Menu:
    Greg CorridorKey / Roundtrip Selected Clip
"""

from __future__ import annotations

import datetime
import os
import re
import shlex
import shutil
import traceback


GREG_INSTALL_ROOT = "/Users/Shared/GregCorridorKey"
GREG_CONFIG_ROOT_FILE = os.path.join(GREG_INSTALL_ROOT, "config", "corridorkey_root.txt")
DEFAULT_CORRIDORKEY_ROOT = os.path.join(GREG_INSTALL_ROOT, "EZ-CorridorKey")
LEGACY_CORRIDORKEY_ROOT = os.path.expanduser("~/Downloads/EZ-CorridorKey")


def _configured_corridorkey_root():
    env_root = os.environ.get("GREG_CORRIDORKEY_ROOT")
    if env_root:
        return os.path.abspath(os.path.expanduser(env_root))

    if os.path.exists(GREG_CONFIG_ROOT_FILE):
        try:
            with open(GREG_CONFIG_ROOT_FILE, "r") as handle:
                config_root = handle.read().strip()
            if config_root:
                return os.path.abspath(os.path.expanduser(config_root))
        except Exception:
            pass

    if os.path.exists(DEFAULT_CORRIDORKEY_ROOT):
        return DEFAULT_CORRIDORKEY_ROOT

    if os.path.exists(LEGACY_CORRIDORKEY_ROOT):
        return LEGACY_CORRIDORKEY_ROOT

    return DEFAULT_CORRIDORKEY_ROOT


CORRIDORKEY_ROOT = _configured_corridorkey_root()
CORRIDORKEY_CLIPS = os.path.join(CORRIDORKEY_ROOT, "ClipsForInference")
GREG_FLAME_ROOT = os.path.join(CORRIDORKEY_ROOT, ".greg_flame")
EXPORT_PRESET_DIR = "OpenEXR"
EXPORT_PRESET_NAME = "OpenEXR (16-bit fp Zip scanline).xml"
EXPORT_SAFE_NAME_PATTERN = "corridorkey."
DEVICE = "auto"
BACKEND = "torch"
SCREEN_COLOR = "auto"
INPUT_COLORSPACE = "srgb"
DESPILL = "0"
DESPECKLE = True
IMAGE_SIZE = "2048"
REFINER = "1.0"
GENERATE_ALPHA_HINTS = True
ALPHA_GENERATOR = "birefnet"
BIREFNET_USAGE = "Matting"
BIREFNET_DILATE_RADIUS = "0"
IMPORT_OUTPUTS = ("FG", "Matte", "Comp", "Processed")
MATCHBOX_PACKAGE_PATH = "GregCorridorKey.mx"
IMPORT_REEL_GROUP = "CorridorKey"
IMPORT_REEL = "Roundtrip Outputs"
DEBUG_REPORT = "/tmp/greg_corridorkey_selection_debug.txt"
SETUP_REPORT = "/tmp/greg_corridorkey_setup_debug.txt"


def _safe_name(value):
    value = str(value or "corridorkey_shot")
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return value or "corridorkey_shot"


def _get_value(value):
    if hasattr(value, "get_value"):
        return value.get_value()
    return value


def _clip_name(clip):
    return _safe_name(_get_value(getattr(clip, "name", "corridorkey_shot")))


def _show(message, level="info"):
    import flame

    try:
        flame.messages.show_in_console(message, level, 5)
    except Exception:
        print(message)


def _show_dialog(message, title="Greg CorridorKey"):
    import flame

    try:
        flame.messages.show_in_dialog(
            title=title,
            message=message,
            type="info",
            buttons=["OK"],
        )
    except Exception:
        print("%s: %s" % (title, message))


def _is_processable_clip(item):
    import flame

    return isinstance(item, (flame.PyClip, flame.PySequence, flame.PySegment))


def _is_exportable_media(item):
    import flame

    return isinstance(item, (flame.PyClip, flame.PySequence))


def _try_get_attr(item, attr_name):
    try:
        value = getattr(item, attr_name)
    except Exception:
        return None

    if callable(value):
        try:
            value = value()
        except Exception:
            return None

    if hasattr(value, "get_value"):
        try:
            return value.get_value()
        except Exception:
            return value

    return value


def _first_exportable(value):
    if _is_exportable_media(value):
        return value

    if isinstance(value, (list, tuple)):
        for item in value:
            exportable = _first_exportable(item)
            if exportable is not None:
                return exportable

    return None


def _try_segment_method(item, method_name):
    method = getattr(item, method_name, None)
    if method is None or not callable(method):
        return None

    try:
        value = method()
    except Exception as error:
        _show("Greg CorridorKey segment.%s failed: %s" % (method_name, error), "warning")
        return None

    exportable = _first_exportable(value)
    if exportable is not None:
        _show("Greg CorridorKey using segment.%s() as export source." % method_name)
        return exportable

    _show(
        "Greg CorridorKey segment.%s() returned %s, not an exportable clip."
        % (method_name, type(value).__name__),
        "warning",
    )
    return None


def _walk_parent_chain(item):
    current = item
    seen = set()
    for _ in range(6):
        obj_id = id(current)
        if obj_id in seen:
            break
        seen.add(obj_id)

        parent = getattr(current, "parent", None)
        if parent is None:
            break
        if callable(parent):
            try:
                parent = parent()
            except Exception:
                break

        exportable = _first_exportable(parent)
        if exportable is not None:
            _show("Greg CorridorKey using parent chain as export source.")
            return exportable
        current = parent

    return None


def _resolve_export_source(item):
    import flame

    if _is_exportable_media(item):
        return item

    if not isinstance(item, flame.PySegment):
        return item

    for method_name in ("duplicate_source", "copy_to_media_panel"):
        exportable = _try_segment_method(item, method_name)
        if exportable is not None:
            return exportable

    for attr_name in (
        "source",
        "source_clip",
        "clip",
        "sequence",
        "parent_sequence",
        "timeline",
        "media",
        "record_clip",
        "container",
    ):
        value = _try_get_attr(item, attr_name)
        if _is_exportable_media(value):
            _show("Greg CorridorKey using segment.%s as export source." % attr_name)
            return value

    exportable_parent = _walk_parent_chain(item)
    if exportable_parent is not None:
        return exportable_parent

    return item


def _selection_debug_report(selection):
    lines = []
    lines.append("Greg CorridorKey selection debug")
    lines.append("Time: %s" % datetime.datetime.now().isoformat())
    lines.append("")

    for index, item in enumerate(selection):
        lines.append("Selection %d" % index)
        lines.append("  repr: %r" % item)
        lines.append("  type: %s.%s" % (type(item).__module__, type(item).__name__))

        try:
            public_attrs = [name for name in dir(item) if not name.startswith("_")]
        except Exception as error:
            public_attrs = []
            lines.append("  dir error: %s" % error)

        lines.append("  public attrs: %s" % ", ".join(public_attrs))
        for attr_name in public_attrs:
            if attr_name in ("frames", "versions", "tracks", "segments", "effects"):
                continue
            try:
                value = getattr(item, attr_name)
                value_type = "%s.%s" % (type(value).__module__, type(value).__name__)
                if hasattr(value, "get_value"):
                    try:
                        raw_value = value.get_value()
                        lines.append("  %s: %s get_value=%r" % (attr_name, value_type, raw_value))
                    except Exception as error:
                        lines.append("  %s: %s get_value_error=%s" % (attr_name, value_type, error))
                else:
                    lines.append("  %s: %s repr=%r" % (attr_name, value_type, value))
            except Exception as error:
                lines.append("  %s: error=%s" % (attr_name, error))
        lines.append("")

    with open(DEBUG_REPORT, "w") as handle:
        handle.write("\n".join(lines))

    _show_dialog(
        "Wrote selection debug report to:\n%s\n\nSend this path/output if the roundtrip still cannot find the segment source."
        % DEBUG_REPORT,
        title="Greg CorridorKey Debug",
    )


def _uv_command():
    uv = shutil.which("uv")
    if uv:
        return uv

    for common in (
        os.path.expanduser("~/.local/bin/uv"),
        "/opt/homebrew/bin/uv",
        "/usr/local/bin/uv",
    ):
        if os.path.exists(common):
            return common

    raise RuntimeError("Could not find uv. Install uv or add it to PATH before running CorridorKey.")


def _python_command():
    venv_python = os.path.join(CORRIDORKEY_ROOT, ".venv", "bin", "python")
    if os.path.exists(venv_python):
        return [venv_python]
    return [_uv_command(), "run", "python"]


def _factory_export_preset_path():
    import flame

    preset_dir = flame.PyExporter.get_presets_dir(
        flame.PyExporter.PresetVisibility.Autodesk,
        flame.PyExporter.PresetType.Image_Sequence,
    )
    return os.path.join(preset_dir, EXPORT_PRESET_DIR, EXPORT_PRESET_NAME)


def _export_preset_path():
    factory_preset = _factory_export_preset_path()
    if not os.path.exists(factory_preset):
        raise RuntimeError("Missing Flame export preset: %s" % factory_preset)

    custom_dir = os.path.join(GREG_FLAME_ROOT, "export_presets")
    custom_preset = os.path.join(custom_dir, "OpenEXR_CorridorKey_safe_names.xml")
    os.makedirs(custom_dir, exist_ok=True)

    with open(factory_preset, "r") as handle:
        preset_xml = handle.read()

    safe_xml = re.sub(
        r"<namePattern>.*?</namePattern>",
        "<namePattern>%s</namePattern>" % EXPORT_SAFE_NAME_PATTERN,
        preset_xml,
        count=1,
        flags=re.DOTALL,
    )
    if safe_xml == preset_xml:
        raise RuntimeError("Could not update namePattern in export preset: %s" % factory_preset)

    should_write = True
    if os.path.exists(custom_preset):
        with open(custom_preset, "r") as handle:
            should_write = handle.read() != safe_xml

    if should_write:
        with open(custom_preset, "w") as handle:
            handle.write(safe_xml)

    return custom_preset


def _prepare_shot_root(clip):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shot_root = os.path.join(CORRIDORKEY_CLIPS, "%s_%s" % (_clip_name(clip), timestamp))
    input_dir = os.path.join(shot_root, "Input")
    alpha_dir = os.path.join(shot_root, "AlphaHint")
    mask_dir = os.path.join(shot_root, "VideoMamaMaskHint")

    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(alpha_dir, exist_ok=True)
    os.makedirs(mask_dir, exist_ok=True)

    return shot_root, input_dir


def _export_clip_to_input(clip, input_dir):
    import flame

    preset_path = _export_preset_path()
    if not os.path.exists(preset_path):
        raise RuntimeError("Missing Flame export preset: %s" % preset_path)

    exporter = flame.PyExporter()
    exporter.foreground = True

    export_source = _resolve_export_source(clip)
    duplicate_source = None
    if isinstance(clip, flame.PySegment):
        if export_source is clip:
            try:
                duplicate_source = flame.duplicate(clip)
                export_source = duplicate_source
            except Exception as error:
                _selection_debug_report((clip,))
                raise RuntimeError(
                    "Timeline segment could not be prepared for export. "
                    "Try selecting the clip or sequence in the Media Panel instead. "
                    "Flame said: %s\n\nDebug report written to:\n%s" % (error, DEBUG_REPORT)
                )

    try:
        exporter.export(export_source, preset_path, input_dir)
    finally:
        if duplicate_source is not None:
            try:
                flame.delete(duplicate_source)
            except Exception:
                pass


def _run_command(command, cwd):
    import flame

    pretty = " ".join(shlex.quote(str(part)) for part in command)
    shell_command = "cd %s && %s" % (shlex.quote(cwd), pretty)
    _show("Greg CorridorKey running: %s" % pretty)
    status, stdout, stderr = flame.execute_command(
        command=shell_command,
        blocking=True,
        shell=True,
    )

    if stdout:
        print(stdout)
    if stderr:
        print(stderr)
    if status != 0:
        raise RuntimeError("Command failed with status %s: %s\n%s" % (status, pretty, stderr))


def _has_image_files(path):
    if not os.path.isdir(path):
        return False
    image_extensions = (".png", ".jpg", ".jpeg", ".exr", ".tif", ".tiff", ".bmp")
    return any(name.lower().endswith(image_extensions) for name in os.listdir(path))


def _image_files(path):
    if not os.path.isdir(path):
        return []
    image_extensions = (".png", ".jpg", ".jpeg", ".exr", ".tif", ".tiff", ".bmp")
    return sorted(
        os.path.join(path, name)
        for name in os.listdir(path)
        if name.lower().endswith(image_extensions)
    )


def _first_image_file(path):
    files = _image_files(path)
    if files:
        return files[0]
    return None


def _run_birefnet_alpha_hint(shot_root):
    script = (
        "import os, sys\n"
        "os.environ.setdefault('OPENCV_IO_ENABLE_OPENEXR', '1')\n"
        "from backend import ClipEntry, CorridorKeyService\n"
        "shot = sys.argv[1]\n"
        "device_arg = sys.argv[2]\n"
        "clip = ClipEntry(os.path.basename(shot), shot)\n"
        "clip.find_assets()\n"
        "service = CorridorKeyService()\n"
        "if device_arg == 'auto':\n"
        "    service.detect_device()\n"
        "else:\n"
        "    service._device = device_arg\n"
        "service.run_birefnet(clip, usage=sys.argv[3])\n"
    )
    _run_command(
        _python_command()
        + [
            "-c",
            script,
            shot_root,
            DEVICE,
            BIREFNET_USAGE,
        ],
        CORRIDORKEY_ROOT,
    )


def _ensure_alpha_hint(shot_root):
    alpha_dir = os.path.join(shot_root, "AlphaHint")
    if _has_image_files(alpha_dir):
        return

    if not GENERATE_ALPHA_HINTS:
        raise RuntimeError("No AlphaHint images found in %s" % alpha_dir)

    if ALPHA_GENERATOR == "birefnet":
        _run_birefnet_alpha_hint(shot_root)
    else:
        uv = _uv_command()
        _run_command(
            [
                uv,
                "run",
                "python",
                "corridorkey_cli.py",
                "--device",
                DEVICE,
                "generate-alphas",
            ],
            CORRIDORKEY_ROOT,
        )

    if not _has_image_files(alpha_dir):
        raise RuntimeError(
            "AlphaHint generation finished but no image files were created in %s. "
            "Check the Flame console for the generator error." % alpha_dir
        )


def _run_corridorkey_inference(shot_root):
    input_is_linear = "1" if INPUT_COLORSPACE == "linear" else "0"
    despeckle = "1" if DESPECKLE else "0"
    script = (
        "import os, sys\n"
        "os.environ.setdefault('OPENCV_IO_ENABLE_OPENEXR', '1')\n"
        "from backend import ClipEntry, CorridorKeyService, InferenceParams, OutputConfig\n"
        "shot = sys.argv[1]\n"
        "device_arg = sys.argv[2]\n"
        "clip = ClipEntry(os.path.basename(shot), shot)\n"
        "clip.find_assets()\n"
        "service = CorridorKeyService()\n"
        "if device_arg == 'auto':\n"
        "    service.detect_device()\n"
        "else:\n"
        "    service._device = device_arg\n"
        "service.set_inference_backend(sys.argv[3])\n"
        "service.set_model_resolution(int(sys.argv[7]))\n"
        "params = InferenceParams(\n"
        "    input_is_linear=bool(int(sys.argv[4])),\n"
        "    despill_strength=max(0, min(10, int(sys.argv[5]))) / 10.0,\n"
        "    auto_despeckle=bool(int(sys.argv[6])),\n"
        "    refiner_scale=float(sys.argv[8]),\n"
        "    screen_color=sys.argv[9],\n"
        ")\n"
        "output_config = OutputConfig(\n"
        "    fg_enabled=True,\n"
        "    matte_enabled=True,\n"
        "    comp_enabled=True,\n"
        "    processed_enabled=True,\n"
        "    fg_format='exr',\n"
        "    matte_format='exr',\n"
        "    comp_format='png',\n"
        "    processed_format='exr',\n"
        ")\n"
        "service.run_inference(clip, params, output_config=output_config)\n"
        "service.unload_engines()\n"
    )
    _run_command(
        _python_command()
        + [
            "-c",
            script,
            shot_root,
            DEVICE,
            BACKEND,
            input_is_linear,
            DESPILL,
            despeckle,
            IMAGE_SIZE,
            REFINER,
            SCREEN_COLOR,
        ],
        CORRIDORKEY_ROOT,
    )


def _run_corridorkey(shot_root):
    _ensure_alpha_hint(shot_root)
    _run_corridorkey_inference(shot_root)

    return os.path.join(shot_root, "Output")


def _rename_imported(imported, output_name):
    items = imported if isinstance(imported, list) else [imported]
    renamed = []
    for item in items:
        if item is None:
            continue
        name = getattr(item, "name", None)
        desired = "CorridorKey_%s" % output_name
        try:
            if hasattr(name, "set_value"):
                name.set_value(desired)
            else:
                item.name = desired
        except Exception as error:
            _show("Greg CorridorKey could not rename imported %s: %s" % (output_name, error), "warning")
        renamed.append(item)
    return renamed


def _find_named(items, name):
    for item in items:
        item_name = getattr(item, "name", None)
        try:
            item_name = item_name.get_value() if hasattr(item_name, "get_value") else item_name
        except Exception:
            item_name = None
        if item_name == name:
            return item
    return None


def _corridorkey_import_destination():
    import flame

    desktop = flame.projects.current_project.current_workspace.desktop
    reel_group = _find_named(getattr(desktop, "reel_groups", []), IMPORT_REEL_GROUP)
    if reel_group is None:
        reel_group = desktop.create_reel_group(IMPORT_REEL_GROUP)

    reel = _find_named(getattr(reel_group, "reels", []), IMPORT_REEL)
    if reel is None:
        reel = reel_group.create_reel(IMPORT_REEL)

    return reel


def _import_output_dir(path, output_name):
    import flame

    if not os.path.isdir(path):
        return None

    import_path = _first_image_file(path) or path
    destination = None
    try:
        destination = _corridorkey_import_destination()
    except Exception as error:
        _show("Could not prepare CorridorKey import reel, importing to the active reel instead: %s" % error, "warning")

    if hasattr(flame, "batch") and flame.get_current_tab() == "Batch":
        try:
            imported = flame.batch.import_clip(import_path, flame.batch.reels[0].name.get_value())
            _rename_imported(imported, output_name)
            return imported
        except Exception as error:
            _show("Batch import failed for %s: %s" % (import_path, error), "warning")

    if destination is not None:
        try:
            imported = flame.import_clips(import_path, destination)
            _rename_imported(imported, output_name)
            return imported
        except Exception as error:
            _show("Import to CorridorKey reel failed for %s, importing to the active reel instead: %s" % (import_path, error), "warning")

    imported = flame.import_clips(import_path)
    _rename_imported(imported, output_name)
    return imported


def _import_corridorkey_outputs(output_root):
    imported = {}
    for output_name in IMPORT_OUTPUTS:
        output_dir = os.path.join(output_root, output_name)
        imported_clip = _import_output_dir(output_dir, output_name)
        if imported_clip:
            imported[output_name] = imported_clip
    return imported


def _object_report(label, value):
    lines = ["%s: %r" % (label, value), "  type: %s.%s" % (type(value).__module__, type(value).__name__)]
    try:
        public_attrs = [name for name in dir(value) if not name.startswith("_")]
    except Exception as error:
        lines.append("  dir error: %s" % error)
        return lines

    lines.append("  public attrs: %s" % ", ".join(public_attrs))
    for attr_name in public_attrs:
        if attr_name in ("frames", "segments", "tracks", "versions", "effects", "nodes"):
            continue
        try:
            attr_value = getattr(value, attr_name)
            if hasattr(attr_value, "get_value"):
                try:
                    attr_value = attr_value.get_value()
                except Exception:
                    pass
            lines.append("  %s: %s repr=%r" % (attr_name, type(attr_value).__name__, attr_value))
        except Exception as error:
            lines.append("  %s: error=%s" % (attr_name, error))
    return lines


def _write_setup_report(lines):
    with open(SETUP_REPORT, "w") as handle:
        handle.write("\n".join(lines))
    _show("Greg CorridorKey setup report written to %s" % SETUP_REPORT)


def _try_call_method(obj, method_names, *args):
    for method_name in method_names:
        method = getattr(obj, method_name, None)
        if not callable(method):
            continue
        try:
            method(*args)
            return method_name
        except Exception as error:
            _show("Greg CorridorKey %s failed: %s" % (method_name, error), "warning")
    return None


def _try_set_attr(obj, attr_names, value):
    for attr_name in attr_names:
        if not hasattr(obj, attr_name):
            continue
        try:
            setattr(obj, attr_name, value)
            return attr_name
        except Exception as error:
            _show("Greg CorridorKey setting %s failed: %s" % (attr_name, error), "warning")
    return None


def _write_bfx_status_report(clip, output_root, imported):
    import flame

    report = []
    report.append("No timeline effect was created on this run.")
    report.append("Reason: PySegment.create_effect() creates Timeline FX only; it does not expose Batch FX creation.")
    report.append("Desired end state remains: create a Batch FX on the selected segment and add a Matchbox node inside it.")
    report.append("Desired Matchbox package: %s" % MATCHBOX_PACKAGE_PATH)
    report.append("Imported media destination: %s / %s" % (IMPORT_REEL_GROUP, IMPORT_REEL))
    report.append("Output root: %s" % output_root)

    for output_name in IMPORT_OUTPUTS:
        output_dir = os.path.join(output_root, output_name)
        report.append("%s first frame: %s" % (output_name, _first_image_file(output_dir) or "missing"))
        report.append("%s imported object: %r" % (output_name, imported.get(output_name)))

    if isinstance(clip, flame.PySegment):
        report.extend(_object_report("segment_for_bfx_api", clip))
        report.append("Segment effect_types: %r" % getattr(clip, "effect_types", []))
    report.extend(_object_report("flame.timeline", getattr(flame, "timeline", None)))
    report.extend(_object_report("flame.batch", getattr(flame, "batch", None)))
    _write_setup_report(report)
    return False


def roundtrip_clip(clip):
    shot_root, input_dir = _prepare_shot_root(clip)
    _show("Greg CorridorKey exporting %s to %s" % (_clip_name(clip), input_dir))

    _export_clip_to_input(clip, input_dir)
    output_root = _run_corridorkey(shot_root)
    imported = _import_corridorkey_outputs(output_root)

    if not imported:
        raise RuntimeError("CorridorKey finished but no output folders were imported from %s" % output_root)

    setup_created = _write_bfx_status_report(clip, output_root, imported)

    _show_dialog(
        "Imported CorridorKey outputs: %s\n\nImported to Media Panel: %s / %s\n\nTimeline BFX setup: %s\n\nShot folder:\n%s\n\nSetup report:\n%s"
        % (
            ", ".join(imported.keys()),
            IMPORT_REEL_GROUP,
            IMPORT_REEL,
            "created" if setup_created else "not created by Python API",
            shot_root,
            SETUP_REPORT,
        )
    )


def roundtrip_selection(selection):
    selected = [item for item in selection if _is_processable_clip(item)]
    if not selected:
        _show_dialog("Select one or more clips or sequences first.", title="Greg CorridorKey")
        return

    for clip in selected:
        try:
            roundtrip_clip(clip)
        except Exception as error:
            print(traceback.format_exc())
            _show_dialog(str(error), title="Greg CorridorKey Error")
            raise


def inspect_selection(selection):
    _selection_debug_report(selection)


def _selection_has_clip(selection):
    return any(_is_processable_clip(item) for item in selection)


def get_media_panel_custom_ui_actions():
    return [
        {
            "name": "Greg CorridorKey",
            "actions": [
                {
                    "name": "Roundtrip Selected Clip",
                    "caption": "Roundtrip Selected Clip",
                    "isVisible": _selection_has_clip,
                    "isEnabled": _selection_has_clip,
                    "execute": roundtrip_selection,
                },
                {
                    "name": "Inspect Selected Object",
                    "caption": "Inspect Selected Object",
                    "isVisible": _selection_has_clip,
                    "isEnabled": _selection_has_clip,
                    "execute": inspect_selection,
                },
            ],
        }
    ]

def get_timeline_custom_ui_actions():
    return get_media_panel_custom_ui_actions()


get_media_panel_custom_ui_actions.minimum_version = "2022"
get_timeline_custom_ui_actions.minimum_version = "2022"
