from __future__ import annotations

from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _date_range_title(labels: list[str], prefix: str) -> str:
    if not labels:
        return prefix
    if len(labels) == 1:
        return f"{prefix} за {labels[0]}"
    return f"{prefix} с {labels[0]} по {labels[-1]}"


def _save(figure) -> bytes:
    output = BytesIO()
    figure.savefig(output, format="png", dpi=160, bbox_inches="tight")
    plt.close(figure)
    return output.getvalue()


def _label_bars(axis, bars, *, formatter=str) -> None:
    for bar in bars:
        value = bar.get_height()
        if value <= 0:
            continue
        axis.annotate(
            formatter(value),
            xy=(bar.get_x() + bar.get_width() / 2, value),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def statistics_chart(points) -> bytes:
    labels = [point.label for point in points]
    joined = [point.joined for point in points]
    blocked = [point.blocked for point in points]
    positions = list(range(len(labels)))

    figure = plt.figure(figsize=(11.5, 5.8))
    axis = figure.add_subplot(111)

    width = 0.34
    joined_bars = axis.bar(
        [position - width / 2 for position in positions],
        joined,
        width,
        label="Пользователи",
        color="#5369d8",
    )
    blocked_bars = axis.bar(
        [position + width / 2 for position in positions],
        blocked,
        width,
        label="Заблокированные",
        color="#a4382d",
    )

    axis.set_title(_date_range_title(labels, "Статистика"), fontsize=15)
    axis.set_ylabel("Количество")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels, rotation=55, ha="right")
    axis.legend(loc="upper right")
    axis.grid(axis="y", alpha=0.16)
    axis.set_axisbelow(True)
    axis.margins(x=0.015)

    _label_bars(axis, joined_bars, formatter=lambda value: f"{int(value)}")
    _label_bars(axis, blocked_bars, formatter=lambda value: f"{int(value)}")

    figure.tight_layout()
    return _save(figure)


def revenue_chart(points) -> bytes:
    labels = [point.label for point in points]
    revenue = [point.revenue_kopecks / 100 for point in points]
    positions = list(range(len(labels)))

    figure = plt.figure(figsize=(11.5, 5.8))
    axis = figure.add_subplot(111)

    bars = axis.bar(
        positions,
        revenue,
        width=0.62,
        label="Оборот",
        color="#e9b447",
    )

    axis.set_title(_date_range_title(labels, "Оборот"), fontsize=15)
    axis.set_ylabel("Оборот, ₽")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels, rotation=55, ha="right")
    axis.legend(loc="upper right")
    axis.grid(axis="y", alpha=0.16)
    axis.set_axisbelow(True)
    axis.margins(x=0.015)

    def money_label(value: float) -> str:
        if float(value).is_integer():
            return f"{int(value):,}".replace(",", " ")
        return f"{value:,.2f}".replace(",", " ").replace(".", ",")

    _label_bars(axis, bars, formatter=money_label)

    figure.tight_layout()
    return _save(figure)
