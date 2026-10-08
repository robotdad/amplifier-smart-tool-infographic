Assemble local raster `IMAGES` into a new PNG at required `--output`.
`--layout` is vertical (default), horizontal or grid.

```bash
infographic stitch panel-1.png panel-2.png --output combined.png --layout horizontal
```

Requires 1 to 6 panels. Each input is normalized to maximum 1600 pixels per side; panels are centered on equal white cells without cropping or distortion.
Returns the output path and byte count. Existing output files are never overwritten. Invalid/oversized images or unwritable output paths fail. No model calls.