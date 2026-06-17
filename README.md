# plotmeta-python

Embed and extract the **exact data** behind a scientific figure, inside the
image file itself. Save a matplotlib figure as PNG, SVG, or PDF and read the
underlying series, axes, and annotations straight back out — no sidecar file,
no re-running the analysis.

```python
import matplotlib.pyplot as plt
import plotmeta

fig, ax = plt.subplots()
ax.plot([0, 1, 2, 3], [0.0, 1.2, 3.9, 8.7], label="signal")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Voltage (V)")

plotmeta.savefig(fig, "decay.png")          # or .svg / .pdf

meta = plotmeta.load("decay.png")           # structured data back out
df = plotmeta.to_pandas("decay.png")        # ...or straight to pandas
```

The same payload is embedded byte-for-byte across PNG/SVG/PDF, so `load()`
returns identical data from any of them. PDFs additionally carry a
`pdftotext`-readable copy of the data table, which survives being dropped into a
LaTeX document with `\includegraphics`.

## Install

```bash
pip install plotmeta            # PNG + SVG + PDF
pip install "plotmeta[pdf]"     # high-fidelity PDF invisible text (reportlab + pypdf)
```

## Docs & examples

- [Quickstart](docs/quickstart.md)
- [Matplotlib support](docs/matplotlib.md) — supported plot types and what gets captured
- [`examples/`](examples/) — a runnable script per plot type
