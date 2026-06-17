"""Bar chart with categorical x — string categories round-trip as strings.

When the x tick labels are non-numeric, they are stored as categories rather
than bar-center coordinates.
"""

import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import plotmeta


def main() -> None:
    fig, ax = plt.subplots()
    ax.bar(["Control", "Treated", "Recovered"], [12.3, 18.7, 15.1], label="yield")
    ax.set_ylabel("Yield (%)")
    ax.set_title("Treatment groups")

    out = Path(tempfile.mkdtemp()) / "bar.png"
    plotmeta.savefig(fig, out)

    s = plotmeta.load(out).plots[0].series[0]
    print(f"saved: {out}")
    print(f"series: {s.label} ({s.plot_type})")
    print(f"  x (categories) = {s.x}")
    print(f"  y = {s.y}")


if __name__ == "__main__":
    main()
