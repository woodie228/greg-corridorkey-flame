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
   - The Matchbox defaults to Luminance for EZ-CorridorKey image mattes. Change Matte Channel to Alpha only if your matte file has a real alpha channel.
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
1. Run Greg CorridorKey / Roundtrip Selected Clip from Flame's right-click menu.
2. Wait for the generated passes to import back into Flame.
3. Add Greg Corridor Key Matchbox.
4. Connect the imported outputs:
   - CorridorKey_FG -> Matchbox input 1: Corridor FG
   - CorridorKey_Matte -> Matchbox input 2: Corridor Matte
   - Optional comp background -> Matchbox input 3: Background
   - Optional original source plate -> Matchbox input 4: Original Plate
5. Start with Output Mode = RGBA Key or Composite.
6. Use Matte Black/White/Gamma, Matte Blur, Matte Choke, and Despill for final polish.

Imported output notes:
- CorridorKey_FG is the best Matchbox foreground input.
- CorridorKey_Matte is the best Matchbox matte input.
- CorridorKey_Comp is a quick preview from EZ-CorridorKey and normally does not need to be connected to the Matchbox.
- CorridorKey_Processed is useful as a standalone RGBA-style result or comparison, but FG + Matte gives more manual control.

Installed package name:
- GregCorridorKey.mx

Optional roundtrip automation:
- `greg_corridor_key_roundtrip.py` installs as a Flame Python custom action.
- In Flame, select a clip or sequence and choose:
  Greg CorridorKey / Roundtrip Selected Clip
- The action exports an OpenEXR sequence, runs EZ-CorridorKey, and imports
  `FG`, `Matte`, `Comp`, and `Processed` outputs back into Flame as image
  sequences when the generated frames use numbered filenames.
- Current limitation: the action does not automatically create a Batch FX setup
  or wire those imported outputs into this Matchbox. Connect the imported
  outputs manually using the input notes above.
- Matchbox cannot trigger this by itself when applied; the Python action is
  the automation layer around the Matchbox.
