"""Multi-panel figure → PDF, then read back as pandas DataFrames.

Shows the two things that only appear once you go beyond a single line:

* a multi-panel figure yields one ``PlotMeta`` per Axes, and ``to_pandas``
  returns one DataFrame per panel;
* the same data round-trips through a **PDF** identically to PNG/SVG — and the
  PDF additionally carries a ``pdftotext``-readable copy.
"""

import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import plotmeta


def main() -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2)
    fig.suptitle("Experiment 7")

    ax1.plot([1, 2, 3], [4, 5, 6], label="line")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Voltage (V)")
    ax1.set_title("Panel A")
    ax1.annotate("peak", xy=(3, 6))

    ax2.bar(["Control", "Treated"], [12.3, 18.7], label="yield")
    ax2.set_ylabel("Resistance (Ω)")
    ax2.set_title("Panel B")

    out = Path(tempfile.mkdtemp()) / "experiment.pdf"
    plotmeta.savefig(fig, out)
    print(f"saved: {out}")

    meta = plotmeta.load(out)
    print(f"suptitle: {meta.suptitle}")
    print(f"panels: {len(meta.plots)}")
    print(f"annotations on panel A: {[a.text for a in meta.plots[0].annotations]}")

    frames = plotmeta.to_pandas(out)  # list of DataFrames (one per panel)
    for i, df in enumerate(frames):
        print(f"\n--- panel {i} ({df.attrs.get('title')}) ---")
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
