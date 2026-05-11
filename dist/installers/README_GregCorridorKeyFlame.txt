# Greg CorridorKey Flame Tools

Flame integration for running an EZ-CorridorKey roundtrip from Autodesk Flame, plus a companion Matchbox for assembling the resulting passes.

## What This Is

- A Flame Python right-click action: `Greg CorridorKey / Roundtrip Selected Clip`
- A Flame Matchbox package: `GregCorridorKey.mx`
- A macOS installer package for Apple Silicon Macs
- An uninstall package
- A helper installer that downloads and installs [EZ-CorridorKey](https://github.com/edenaion/EZ-CorridorKey)

## Compatibility

- macOS on Apple Silicon: M1, M2, M3, M4, or newer
- Autodesk Flame 2023 or newer is the target
- Tested primarily on Flame 2026.2

Intel Macs, Windows, Linux, and Flame versions older than 2023 are not supported by this package.

## Downloads

Use the GitHub Release assets for normal installation:

- `GregCorridorKeyFlame-0.3.4.pkg`
- `GregCorridorKeyFlame-Uninstall-0.3.4.pkg`

The packages are currently unsigned. If macOS blocks a normal double-click, right-click the package and choose `Open`.

## Install Flow

1. Quit Flame.
2. Run `GregCorridorKeyFlame-0.3.4.pkg`.
3. The installer copies the Flame hook and Matchbox.
4. Terminal opens automatically and installs or updates EZ-CorridorKey as the logged-in user.
5. When Terminal finishes, open Flame and run `Rescan Python Hooks`, or restart Flame.

The first setup can take a while because EZ-CorridorKey downloads Python packages and model weights.

This package now installs the commonly needed EZ-CorridorKey model set automatically, including CorridorKey Blue, MLX weights for Apple Silicon, BiRefNet, MatAnyone2, SAM2 Base+, GVM, and VideoMaMa. Some of these are large: GVM is about 6 GB and VideoMaMa is about 37 GB. First install time depends heavily on internet speed, disk speed, and available space.

## Using It In Flame

After installation, right-click a timeline clip or segment in Flame. The menu should include `Greg CorridorKey`.

![Flame right-click menu showing Greg CorridorKey](docs/images/flame-right-click-greg-corridorkey.png)

Choose `Greg CorridorKey / Roundtrip Selected Clip` to export the selected shot, run the EZ-CorridorKey ML pass, and import the generated outputs back into Flame.

Processing speed depends heavily on the Mac. Faster Apple Silicon machines and more unified memory will finish the ML key sooner; slower or lower-memory Macs can take significantly longer, especially on high-resolution or long shots.

## Using The Matchbox After Roundtrip

`Roundtrip Selected Clip` imports the generated passes back into Flame. The current version does **not** automatically build a Batch FX setup or wire the passes into the Matchbox for you. After the outputs are back in Flame, add `GregCorridorKey.mx` as a Matchbox and connect the outputs manually.

Matchbox input order:

1. **Corridor FG**
   - Connect the imported `CorridorKey_FG` output.
   - This is the foreground RGB pass and gives the Matchbox the most control.
2. **Corridor Matte**
   - Connect the imported `CorridorKey_Matte` output.
   - The Matchbox defaults to reading the matte as luminance, which matches the generated image matte in most EZ-CorridorKey runs.
3. **Background**
   - Optional.
   - Connect your comp background if you want the Matchbox `Composite` output mode.
4. **Original Plate**
   - Optional but recommended.
   - Connect the original source plate if you want to use Matchbox despill/reference controls.

Imported output notes:

- `CorridorKey_FG`: best source for Matchbox input 1.
- `CorridorKey_Matte`: best source for Matchbox input 2.
- `CorridorKey_Comp`: quick preview from EZ-CorridorKey; normally not needed as a Matchbox input.
- `CorridorKey_Processed`: production-ready RGBA-style output from EZ-CorridorKey; useful as a standalone result or comparison, but FG + Matte gives more manual control in the Matchbox.

Suggested starting mode: set the Matchbox `Output Mode` to `RGBA Key` or `Composite`.

## Installed Files

- `/opt/Autodesk/shared/python/greg_corridor_key_roundtrip.py`
- `/opt/Autodesk/user/*_2023+/matchbox/shaders/MACHINE_LEARNING/GregCorridorKey.mx`
- `/Library/Application Support/Greg/CorridorKeyFlame`
- `/Users/Shared/GregCorridorKey`

Setup logs are written to:

`/Users/Shared/GregCorridorKey/greg_corridorkey_ez_setup.log`

## Uninstall

Run `GregCorridorKeyFlame-Uninstall-0.3.4.pkg`.

The uninstaller removes the Flame hook, Matchbox package, compiled hook cache, and installer support files. It intentionally leaves `/Users/Shared/GregCorridorKey` in place because that folder may contain large downloaded models and shot output.

macOS Installer may still show a generic success message that sounds like an install completed. The uninstall package also opens Terminal with a clear removal summary and writes:

`/Users/Shared/GregCorridorKey/greg_corridorkey_uninstall.log`

## Notes

This is a Flame integration wrapper around EZ-CorridorKey. EZ-CorridorKey and CorridorKey have their own licensing and model terms. Review the upstream project before redistribution or commercial use.

## Credits

- **CorridorKey**: Created by [Niko Pueringer](https://github.com/nikopueringer) / Corridor Digital, the team behind Corridor Crew. This installer exists because of their original AI chroma keyer work.
- **EZ-CorridorKey**: GUI, workflow, sound, QA, and maintenance by [Ed Zisk](https://www.edzisk.com) / [EZSCAPE](https://www.ezscape.space). The Flame installer downloads and drives EZ-CorridorKey for Apple Silicon Mac support.
- **Greg CorridorKey Flame Tools**: Flame hook, Matchbox companion, and installer packaging by Ryan Wood / Greg.

Please star and support the upstream projects:

- [CorridorKey](https://github.com/nikopueringer/CorridorKey)
- [EZ-CorridorKey](https://github.com/edenaion/EZ-CorridorKey)
