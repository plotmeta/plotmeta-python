# Quickstart

`plotmeta` embeds the exact data behind a matplotlib figure into the image file
itself, so a saved PNG, SVG, or PDF can be read back into structured data — no
sidecar file, no re-running the analysis.

## Install

```bash
pip install plotmeta            # PNG + SVG + PDF (invisible-text via matplotlib)
pip install "plotmeta[pdf]"     # adds reportlab + pypdf for high-fidelity PDF text
pip install "plotmeta[dev]"     # test + lint tooling
```

## Save with embedded metadata

```python
import matplotlib.pyplot as plt
import plotmeta

fig, ax = plt.subplots()
ax.plot([0, 1, 2, 3], [0.0, 1.2, 3.9, 8.7], label="signal")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Voltage (V)")

plotmeta.savefig(fig, "decay.png")   # also "decay.svg" or "decay.pdf"
```

The same payload is embedded byte-for-byte in each format, so `load()` returns
identical data regardless of which you pick.

PDFs are a little special. The lossless data lives in the page content stream
(as invisible text), so it **survives `\includegraphics`** — a figure embedded
in a compiled paper is still losslessly reloadable. Two consequences:

- Reading a PDF back needs a text extractor — install the `[pdf]` extra (pypdf)
  or have `pdftotext` on your `PATH`. (PNG/SVG read with the stdlib alone.)
- For a dependency-free `load()` on a PDF *file* you wrote, add the after-EOF
  marker: `plotmeta.savefig(fig, "f.pdf", stdlib_marker=True)`. The marker does
  not survive `\includegraphics`; the content-stream copy is the durable one.

PDFs also carry a `pdftotext`-readable copy of the table for humans and LLMs.

If you prefer matplotlib's own `savefig`, `metadata()` builds the dict it wants
(**PNG only** — SVG/PDF reject unknown metadata keys):

```python
fig.savefig("decay.png", metadata=plotmeta.metadata(fig))
```

## Load it back

```python
meta = plotmeta.load("decay.png")     # dispatches on extension; .svg / .pdf too
meta.to_text()                        # human-readable
meta.to_json()                        # structured JSON
meta.to_csv()                         # CSV

# or skip the file entirely and read the live figure
meta = plotmeta.extract(fig)
```

`load()` returns `None` for a plain image with no plotmeta payload.

## Straight to pandas

```python
df = plotmeta.to_pandas("decay.png")   # one DataFrame, or a list per panel
df = plotmeta.to_pandas(fig)           # from a live figure
```

For a multi-panel figure, `to_pandas` returns one DataFrame per panel; panel
title and axis units are attached on `df.attrs`.

## Runnable examples

The [`examples/`](https://github.com/plotmeta/plotmeta-python/tree/main/examples)
directory has a short script per plot type (line, scatter, bar, errorbar,
multi-panel → PDF → pandas). Each is self-contained:

```bash
python examples/01_line_and_units.py
```

See [Matplotlib support](matplotlib.md) for exactly which artists and
attributes are captured.
