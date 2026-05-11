# Greg CorridorKey Flame Tools v0.3.3

Uninstaller clarity update for the Flame/EZ-CorridorKey integration package.

## Included Assets

- `GregCorridorKeyFlame-0.3.3.pkg`
  - Installs the Flame Python hook, Matchbox package, and setup helpers.
  - Automatically opens Terminal to install or update EZ-CorridorKey as the logged-in user.
- `GregCorridorKeyFlame-Uninstall-0.3.3.pkg`
  - Removes the Flame hook, Matchbox package, and installer support files.
  - Leaves `/Users/Shared/GregCorridorKey` intact so downloaded models and shot outputs are not accidentally deleted.
  - Opens Terminal with a clear uninstall summary because macOS Installer's final wording is generic and can sound like a normal install.
- `README_GregCorridorKeyFlame.txt`
  - Short install notes for end users.

## Compatibility

- Apple Silicon Mac only: M1 or newer
- Autodesk Flame 2023 or newer
- Tested primarily on Flame 2026.2

## Important Notes

- Packages are unsigned.
- First install can take a while because EZ-CorridorKey downloads Python packages and model weights.
- The installer now downloads the commonly needed optional model set by default: CorridorKey Blue, MLX weights, BiRefNet, MatAnyone2, SAM2 Base+, GVM, and VideoMaMa.
- GVM is about 6 GB and VideoMaMa is about 37 GB, so first install time and disk usage can be substantial.
- The uninstall package writes `/Users/Shared/GregCorridorKey/greg_corridorkey_uninstall.log` and opens Terminal with a clear removal message.
- Users should restart Flame or run `Rescan Python Hooks` after setup completes.
- After installation, `Greg CorridorKey` appears in Flame's right-click menu on supported timeline clips/segments.
- ML key processing time depends on Mac speed, Apple Silicon generation, available unified memory, shot length, and resolution.

## Flame Menu

![Flame right-click menu showing Greg CorridorKey](docs/images/flame-right-click-greg-corridorkey.png)

## Matchbox Hookup After Import

`Roundtrip Selected Clip` imports the EZ-CorridorKey outputs back into Flame, but this version does not automatically build a Batch FX setup or wire a Matchbox node.

After import, add `GregCorridorKey.mx` and connect:

- `CorridorKey_FG` -> Matchbox input 1, `Corridor FG`
- `CorridorKey_Matte` -> Matchbox input 2, `Corridor Matte`
- Optional comp background -> Matchbox input 3, `Background`
- Optional original source plate -> Matchbox input 4, `Original Plate`

`CorridorKey_Comp` is mainly a quick preview. `CorridorKey_Processed` is useful as a standalone result or comparison, but FG + Matte gives more control in the Matchbox.

## Credits

- **CorridorKey** was created by [Niko Pueringer](https://github.com/nikopueringer) / Corridor Digital, the team behind Corridor Crew. This Flame installer builds on their original AI chroma keyer.
- **EZ-CorridorKey** is maintained by [Ed Zisk](https://www.edzisk.com) / [EZSCAPE](https://www.ezscape.space), who created the GUI/workflow layer and Apple Silicon-friendly install path used here.
- **Greg CorridorKey Flame Tools** packages the Flame hook, Matchbox companion, and macOS installer workflow for Autodesk Flame users.

Please support the upstream projects:

- [CorridorKey](https://github.com/nikopueringer/CorridorKey)
- [EZ-CorridorKey](https://github.com/edenaion/EZ-CorridorKey)
