from __future__ import annotations

from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def growth_chart(points) -> bytes:
    labels = [point.label for point in points]
    total = [point.users for point in points]
    organic = [point.organic for point in points]

    figure = plt.figure(figsize=(10, 5))
    axis = figure.add_subplot(111)
    width = 0.38
    x = list(range(len(labels)))

    axis.bar([value - width / 2 for value in x], total, width, label="Всего")
    axis.bar([value + width / 2 for value in x], organic, width, label="Органика")
    axis.set_title("Прирост пользователей")
    axis.set_xticks(x)
    axis.set_xticklabels(labels, rotation=45, ha="right")
    axis.legend()
    figure.tight_layout()

    output = BytesIO()
    figure.savefig(output, format="png", dpi=150)
    plt.close(figure)
    return output.getvalue()


def profit_chart(points) -> bytes:
    labels = [point.label for point in points]
    revenue = [point.revenue_kopecks / 100 for point in points]
    profit = [point.profit_kopecks / 100 for point in points]

    figure = plt.figure(figsize=(10, 5))
    axis = figure.add_subplot(111)
    width = 0.38
    x = list(range(len(labels)))

    axis.bar([value - width / 2 for value in x], revenue, width, label="Оборот")
    axis.bar([value + width / 2 for value in x], profit, width, label="Прибыль")
    axis.set_title("Оборот и прибыль, ₽")
    axis.set_xticks(x)
    axis.set_xticklabels(labels, rotation=45, ha="right")
    axis.legend()
    figure.tight_layout()

    output = BytesIO()
    figure.savefig(output, format="png", dpi=150)
    plt.close(figure)
    return output.getvalue()
