Greg CorridorKey Flame Tools

Compatibility:
- macOS on Apple Silicon (M1 or newer).
- Autodesk Flame 2023 or newer is the target.
- The installer copies the Python hook to /opt/Autodesk/shared/python.
- The installer copies GregCorridorKey.mx to every existing /opt/Autodesk/user/*_2023+ Matchbox folder.

What the installer includes:
- Flame right-click Python action:
  Greg CorridorKey / Roundtrip Selected Clip
- Flame Matchbox package:
  GregCorridorKey.mx
- EZ-CorridorKey setup helper:
  /Library/Application Support/Greg/CorridorKeyFlame/install_or_update_corridorkey.sh

What the installer does not bundle:
- The full EZ-CorridorKey repository, Python environment, or model weights.
  Those are large and the installer starts their setup automatically in Terminal.

First-time setup:
1. Install GregCorridorKeyFlame.pkg.
2. A Terminal window opens automatically and installs/updates EZ-CorridorKey.
3. Restart Flame or run Rescan Python Hooks after the Terminal setup completes.

Uninstall:
- Run GregCorridorKeyFlame-Uninstall.pkg.
- It removes the Flame hook, Matchbox package, and installer support files.
- It intentionally leaves /Users/Shared/GregCorridorKey in place because that may contain large downloaded models and rendered shot output.
