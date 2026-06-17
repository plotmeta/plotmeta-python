"""Scatter plot — point coordinates are recovered from the collection offsets."""

import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import plotmeta


def main() -> None:
    fig, ax = plt.subplots()
    ax.scatter([1.0, 2.0, 3.0, 4.0], [2.1, 3.9, 6.2, 7.8], label="measurements")
    ax.set_xlabel("Dose (mg)")
    ax.set_ylabel("Response")

    out = Path(tempfile.mkdtemp()) / "scatter.png"
    plotmeta.savefig(fig, out)

    s = plotmeta.load(out).plots[0].series[0]
    print(f"saved: {out}")
    print(f"series: {s.label} ({s.plot_type})")
    print(f"  x = {s.x}")
    print(f"  y = {s.y}")


if __name__ == "__main__":
    main()
