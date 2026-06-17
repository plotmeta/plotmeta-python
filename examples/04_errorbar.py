"""Error-bar plot — per-point lower/upper bounds are extracted alongside x/y."""

import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import plotmeta


def main() -> None:
    fig, ax = plt.subplots()
    ax.errorbar(
        [1, 2, 3, 4],
        [10.0, 19.5, 31.2, 38.9],
        yerr=[1.0, 1.5, 2.0, 1.8],
        label="measured",
        fmt="o-",
    )
    ax.set_xlabel("Trial")
    ax.set_ylabel("Count")

    out = Path(tempfile.mkdtemp()) / "errorbar.png"
    plotmeta.savefig(fig, out)

    s = plotmeta.load(out).plots[0].series[0]
    print(f"saved: {out}")
    print(f"series: {s.label} ({s.plot_type})")
    print(f"  x = {s.x}")
    print(f"  y = {s.y}")
    print(f"  y_err_lo = {s.y_err_lo}")
    print(f"  y_err_hi = {s.y_err_hi}")


if __name__ == "__main__":
    main()
