"""Line plot with axis units — the canonical save → load round-trip.

Axis labels written as ``"Name (unit)"`` are split into a label and units on
extraction, so they survive as structured fields rather than a raw string.
"""

import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import plotmeta


def main() -> None:
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2, 3], [0.0, 1.2, 3.9, 8.7], label="signal")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Voltage (V)")
    ax.set_title("Decay")

    out = Path(tempfile.mkdtemp()) / "line.png"
    plotmeta.savefig(fig, out)

    meta = plotmeta.load(out)
    plot = meta.plots[0]
    print(f"saved: {out}")
    print(f"title: {plot.title}")
    print(f"x: {plot.x_axis.label} [{plot.x_axis.units}]")
    print(f"y: {plot.y_axis.label} [{plot.y_axis.units}]")
    print(f"series: {plot.series[0].label} ({plot.series[0].plot_type})")
    print(f"  x = {plot.series[0].x}")
    print(f"  y = {plot.series[0].y}")


if __name__ == "__main__":
    main()
