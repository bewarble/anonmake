from __future__ import annotations

from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def revenue_chart(points) -> bytes:
    labels = [point.label for point in points]
    revenue = [point.revenue_kopecks / 100 for point in points]

    figure = plt.figure(figsize=(10, 5))
    axis = figure.add_subplot(111)
    axis.bar(list(range(len(labels))), revenue)
    axis.set_title("Доход, ₽")
    axis.set_xticks(list(range(len(labels))))
    axis.set_xticklabels(labels, rotation=45, ha="right")
    figure.tight_layout()

    output = BytesIO()
    figure.savefig(output, format="png", dpi=150)
    plt.close(figure)
    return output.getvalue()
