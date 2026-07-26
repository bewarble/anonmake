from __future__ import annotations

from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def statistics_chart(points) -> bytes:
    labels = [point.label for point in points]
    joined = [point.joined for point in points]
    blocked = [point.blocked for point in points]

    figure = plt.figure(figsize=(10, 5))
    axis = figure.add_subplot(111)

    width = 0.38
    positions = list(range(len(labels)))

    axis.bar(
        [position - width / 2 for position in positions],
        joined,
        width,
        label="Пришли",
    )
    axis.bar(
        [position + width / 2 for position in positions],
        blocked,
        width,
        label="Заблокировали",
    )

    axis.set_title("Пользователи по дням")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels, rotation=45, ha="right")
    axis.legend()
    figure.tight_layout()

    output = BytesIO()
    figure.savefig(output, format="png", dpi=150)
    plt.close(figure)
    return output.getvalue()


def revenue_chart(points) -> bytes:
    labels = [point.label for point in points]
    revenue = [point.revenue_kopecks / 100 for point in points]

    figure = plt.figure(figsize=(10, 5))
    axis = figure.add_subplot(111)
    positions = list(range(len(labels)))

    axis.bar(positions, revenue)
    axis.set_title("Доход, ₽")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels, rotation=45, ha="right")
    figure.tight_layout()

    output = BytesIO()
    figure.savefig(output, format="png", dpi=150)
    plt.close(figure)
    return output.getvalue()
