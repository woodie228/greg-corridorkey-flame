Greg CorridorKey Flame Tools 0.3.0

Files:
- GregCorridorKeyFlame-0.3.0.pkg
- GregCorridorKeyFlame-Uninstall-0.3.0.pkg

Target:
- macOS Apple Silicon, M1 or newer.
- Autodesk Flame 2023 or newer is the intended compatibility range.

Install:
1. Quit Flame.
2. Run GregCorridorKeyFlame-0.3.0.pkg.
3. The installer opens Terminal automatically and installs/updates EZ-CorridorKey.
4. When the Terminal setup finishes, open Flame and run Rescan Python Hooks, or restart Flame.

Installed Flame pieces:
- /opt/Autodesk/shared/python/greg_corridor_key_roundtrip.py
- /opt/Autodesk/user/*_2023+/matchbox/shaders/MACHINE_LEARNING/GregCorridorKey.mx

Configuration:
- /Users/Shared/GregCorridorKey/config/corridorkey_root.txt
- The hook also respects the GREG_CORRIDORKEY_ROOT environment variable.

Uninstall:
- Run GregCorridorKeyFlame-Uninstall-0.3.0.pkg.
- It removes the Flame hook, Matchbox package, and support files.
- It intentionally leaves /Users/Shared/GregCorridorKey in place because that folder can contain large model downloads and shot output.

Notes:
- The packages are currently unsigned. On another Mac, right-click the pkg and choose Open if Gatekeeper blocks a normal double-click.
- The helper script downloads EZ-CorridorKey from:
  https://github.com/edenaion/EZ-CorridorKey
- First install can take a while because EZ-CorridorKey downloads Python packages and model weights.
- Setup logs are written to:
  /Users/Shared/GregCorridorKey/greg_corridorkey_ez_setup.log
