Greg Corridor Key - Flame Matchbox companion for CorridorKey

What this is:
- A Flame Matchbox shader for assembling and tuning CorridorKey outputs in Flame.
- It does not run the CorridorKey neural network inside Matchbox. Flame Matchbox shaders cannot execute Python or load the CorridorKey model.
- Use CorridorKey first to generate FG and Matte passes, then use this Matchbox in Flame to combine, despill, shape, and QC the result.

Inputs:
1. Corridor FG
   - CorridorKey /FG output is preferred.
   - /Processed can also be used for quick previews, but FG gives more control.
2. Corridor Matte
   - CorridorKey /Matte output.
   - Use Matte Channel if Flame reads the matte into red/luma instead of alpha.
3. Background
   - Optional. Used by Composite output mode.
4. Original Plate
   - Optional but recommended when using Despill.

Useful output modes:
- Composite: foreground over the Background input.
- RGBA Key: keyed foreground with alpha for downstream compositing.
- FG Only: despilled/recovered foreground preview.
- Matte: shaped matte preview.
- Edge QC: quick edge-gradient view.
- Spill QC: shows where despill is changing the image.

Suggested Flame flow:
1. Run CorridorKey on the shot outside Flame.
2. Import the CorridorKey FG and Matte EXR sequences into Flame.
3. Add Greg Corridor Key Matchbox.
4. Connect FG to input 1 and Matte to input 2.
5. Optional: connect your comp background to input 3 and original plate to input 4.
6. Start with Output Mode = RGBA Key or Composite.
7. Use Matte Black/White/Gamma, Matte Blur, Matte Choke, and Despill for final polish.

Installed package name:
- GregCorridorKey.mx

Optional roundtrip automation:
- `greg_corridor_key_roundtrip.py` installs as a Flame Python custom action.
- In Flame, select a clip or sequence and choose:
  Greg Tools / CorridorKey / Roundtrip Selected Clip
- The action exports an OpenEXR sequence into CorridorKey's `ClipsForInference`,
  runs CorridorKey, and imports `FG`, `Matte`, and `Processed` outputs back
  into Flame.
- Matchbox cannot trigger this by itself when applied; the Python action is
  the automation layer around the Matchbox.
