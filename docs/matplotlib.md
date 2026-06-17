# Matplotlib support

`plotmeta` reads a live matplotlib figure and extracts the data and structure
that define it. Extraction lives in `plotmeta.writers.matplotlib` and is
deliberately self-contained (no plotmeta IO imports) so it could be contributed
upstream; saving is layered on top in `plotmeta.save`.

You normally never call the writer directly — `plotmeta.savefig`,
`plotmeta.extract`, and `plotmeta.to_pandas` all route through it. The pieces
below are exposed for inspection and testing:

```python
from plotmeta.writers.matplotlib import extract_figure, extract_axes

meta = extract_figure(fig)     # -> FigureMeta (all axes)
plot = extract_axes(ax)        # -> PlotMeta  (one axes)
```

## Supported plot types

| matplotlib call | `plot_type` | Notes |
|---|---|---|
| `ax.plot(...)` | `line` | captures color, marker, linestyle |
| `ax.scatter(...)` | `scatter` | coordinates from collection offsets; first facecolor |
| `ax.bar(...)` | `bar` | categorical x kept as strings, else bar-center x |
| `ax.errorbar(...)` | `errorbar` | per-point `y_err_lo` / `y_err_hi` from the bar segments |

Error-bar artists are detected first and their child lines are excluded from
line extraction, so an `errorbar` is never double-counted as a `line`.

## What else is captured

- **Axis label and units** — `set_xlabel("Pressure (kPa)")` splits into
  `label="Pressure"`, `units="kPa"`. A label with no trailing `(...)` keeps
  `units=None`.
- **Axis scale** — `linear`, `log`, etc., from `get_xscale()`.
- **Axis range** — the current view limits.
- **Ticks** — non-numeric tick labels are stored as categories; otherwise the
  numeric tick positions.
- **Titles** — per-axes `title`, plus the figure `suptitle`.
- **Annotations** — non-empty `ax.text` / `ax.annotate` content with position.
- **Multi-panel layout** — one `PlotMeta` per axes, with an inferred
  `subplot_grid` of `[nrows, ncols]`. Colorbar axes are detected by aspect ratio
  and skipped.

## Numeric precision

Floating-point values are rounded to 6 significant figures
(`SIGNIFICANT_FIGURES` in the writer) before storage. This keeps the payload
compact and avoids serializing float noise; it is not full IEEE-754 round-trip
precision.

## Not yet supported

These plot types are on the roadmap but currently extract nothing (the figure
still saves; the data just isn't captured):

- histogram (`ax.hist`)
- step plots (`ax.step`)
- `ax.fill_between`
- heatmap / `imshow`
- contour
- violin / boxplot
- twin axes
- colorbar value extraction (colorbar axes are skipped)

## Known limitations

- **Categorical values with tabs/newlines** are not yet escaped in the
  canonical table format and would corrupt a row.
- **Numeric-looking categories** (e.g. an x category `"300"`) round-trip as
  floats, not strings.
- `metadata(fig)` produces PNG-only metadata; feeding it to an SVG/PDF
  `savefig` raises, because those backends reject unknown metadata keys. Use
  `plotmeta.savefig` for SVG/PDF.
