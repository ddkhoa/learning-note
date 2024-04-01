import numpy as np
from matplotlib import pylab as plt


def compute_pages_to_fetch_best_case(s, T):
    return s * T


def compute_pages_to_fetch_worst_case(s, T, N, b):
    if T <= b:
        # print("1")
        a = 2 * T * N * s / (2 * T + N * s)
        return min(a, T)
    if s <= 2 * T * b / (N * (2 * T - b)):
        # print("2")
        return 2 * T * N * s / (2 * T + N * s)

    # print("3")
    return b + (N * s - 2 * T * b / (2 * T - b)) * (T - b) / T


def draw_pages_fetched_chart(T, N, b, scenario):
    xs = np.arange(0, 1, 0.01)
    pages_to_fetch_best_case = [compute_pages_to_fetch_best_case(s, T) for s in xs]
    pages_to_fetch_worst_case = [
        compute_pages_to_fetch_worst_case(s, T, N, b) for s in xs
    ]
    plt.figure(figsize=(12, 6))
    plt.plot(xs, pages_to_fetch_best_case, label="high_correlation")
    plt.plot(xs, pages_to_fetch_worst_case, label="low_correlation")
    plt.xlabel("Selectivity")
    plt.ylabel("Number of pages to fetch")
    scenario_title = (" ".join(scenario.split("_"))).capitalize()
    plt.title(
        f"Number of pages to fetch in high and low correlation - {scenario_title} "
    )
    plt.legend(loc="center right")
    plt.savefig(f"./pages_to_fetch_{scenario}.png")


def get_plot_by_selectivity(func, xs, T, N, b):
    ys = []
    for x in xs:
        ys.append(func(x, T, N, b))
    ys = np.array(ys)
    plt.plot(xs, ys)
    plt.show()


def get_plot_by_cache_size(func, xb, T, N, s):
    yb = []
    for b in xb:
        yb.append(func(s, T, N, b))
    yb = np.array(yb)
    plt.plot(xb, yb)
    plt.show()


def get_plot_by_table_size(func, xT, xN, s, b):
    yT = []
    for i in range(0, len(xT)):
        yT.append(func(s, xT[i], xN[i], b))
    yT = np.array(yT)
    plt.plot(xT, yT)
    plt.show()


def get_plot_seq_index(xs, T, N, b, t, n, k1, k2, scenario):
    seqcosts = []
    for _ in xs:
        seqcosts.append((0.01 + 0.0025 * k1) * N + T)
    seqcosts = np.array(seqcosts)
    plt.figure(figsize=(12, 6))
    plt.plot(xs, seqcosts, label="seq_scan")

    indexcosts_best = []
    indexcosts_worst = []
    for s in xs:
        index_space_cost = (0.005 + k2 * 0.0025) * s * n + 4 * s * t

        table_space_cost_best = (0.01 + (k1 - k2) * 0.0025) * s * N + s * T
        indexcosts_best.append(index_space_cost + table_space_cost_best)

        if T <= b:
            a = 2 * T * N * s / (2 * T + N * s)
            table_space_cost_worst = 4 * min(a, T)

        elif s <= 2 * T * b / (N * (2 * T - b)):
            table_space_cost_worst = 8 * T * N * s / (2 * T + N * s)
        else:
            table_space_cost_worst = 4 * (
                b + (N * s - 2 * T * b / (2 * T - b)) * (T - b) / T
            )
        table_space_cost_worst += (0.01 + (k1 - k2) * 0.0025) * s * N
        indexcosts_worst.append(index_space_cost + table_space_cost_worst)

    plt.plot(xs, indexcosts_best, label="index_scan_best_case")
    plt.plot(xs, indexcosts_worst, label="index_scan_worst_case")
    plt.xlabel("Selectivity")
    plt.ylabel("Cost")
    plt.legend()
    plt.savefig(f"./cost_{scenario}.png")


def compute_cost(xs, T, N, b, t, n, k1, k2):
    index_cpu_cost = []
    index_IO_cost = []
    table_cpu_cost = []
    table_IO_cost_worst = []
    table_IO_cost_best = []

    for s in xs:
        index_cpu_cost.append((0.005 + k2 * 0.0025) * s * n)
        index_IO_cost.append(4 * s * t)
        table_cpu_cost.append((0.01 + (k1 - k2) * 0.0025) * s * N)
        table_IO_cost_best.append(s * T)

        if T <= b:
            a = 2 * T * N * s / (2 * T + N * s)
            IO_cost = 4 * min(a, T)
        elif s <= 2 * T * b / (N * (2 * T - b)):
            IO_cost = 8 * T * N * s / (2 * T + N * s)
        else:
            IO_cost = 4 * (b + (N * s - 2 * T * b / (2 * T - b)) * (T - b) / T)
        table_IO_cost_worst.append(IO_cost)
    return (
        index_cpu_cost,
        index_IO_cost,
        table_cpu_cost,
        table_IO_cost_worst,
        table_IO_cost_best,
    )


def get_plot_index_breakdown(cost, scenario):
    (
        index_cpu_cost,
        index_IO_cost,
        table_cpu_cost,
        table_IO_cost_worst,
        table_IO_cost_best,
    ) = cost
    # Specify colors for each series
    colors = ["blue", "orange", "green", "red"]
    plt.figure(figsize=(12, 6))

    # Plotting the first area chart
    plt.subplot(1, 2, 1)
    series = [
        (index_cpu_cost, "Index CPU Cost"),
        (index_IO_cost, "Index IO Cost"),
        (table_cpu_cost, "Table CPU Cost"),
        (table_IO_cost_worst, "Table IO Cost Worst"),
    ]

    cumulated = []
    last_cumulated = []
    for i in range(0, len(series)):
        data, label = series[i]
        color = colors[i]

        if i == 0:
            last_cumulated = [0 for _ in range(len(data))]
            cumulated = [0 for _ in range(len(data))]
        else:
            last_cumulated = [elem for elem in cumulated]

        cumulated = [cumulated[i] + data[i] for i in range(len(data))]
        plt.plot(
            cumulated,
            label=label,
            color=color,
            alpha=0.7,
        )

        plt.fill_between(
            range(len(data)),
            last_cumulated,
            cumulated,
            color=color,
            alpha=0.3,
            edgecolor=color,
        )

    plt.xlabel("s")
    plt.ylabel("Cost")
    plt.title("Area Chart - Worst Case")
    plt.legend()

    # Plotting the second area chart
    plt.subplot(1, 2, 2)
    series = [
        (index_cpu_cost, "Index CPU Cost"),
        (index_IO_cost, "Index IO Cost"),
        (table_cpu_cost, "Table CPU Cost"),
        (table_IO_cost_best, "Table IO Cost Best"),
    ]
    cumulated = []
    last_cumulated = []
    for i in range(0, len(series)):
        data, label = series[i]
        color = colors[i]

        if i == 0:
            last_cumulated = [0 for _ in range(len(data))]
            cumulated = [0 for _ in range(len(data))]
        else:
            last_cumulated = [elem for elem in cumulated]

        cumulated = [cumulated[i] + data[i] for i in range(len(data))]
        plt.plot(
            cumulated,
            label=label,
            color=color,
            alpha=0.7,
        )

        plt.fill_between(
            range(len(data)),
            last_cumulated,
            cumulated,
            color=color,
            alpha=0.3,
            edgecolor=color,
        )

    plt.xlabel("s")
    plt.ylabel("Cost")
    plt.title("Area Chart - Best Case")
    plt.legend()

    # Adjust layout for better visualization
    plt.tight_layout()

    # Show the plot
    plt.savefig(f"./index_cost_breakdown_{scenario}.png")


# xs = np.arange(0, 1, 0.01)
# T = 161984
# N = 14838350
# b = 524288
# t = 18663
# n = 14838350
# k1 = 2
# k2 = 1
# get_plot_seq_index(xs, T, N, b, t, n, k1, k2, "table_fit_cache_1")
# get_plot_index_breakdown(
#     compute_cost(
#         xs,
#         T,
#         N,
#         b,
#         t,
#         n,
#         k1,
#         k2,
#     ),
#     "table_fit_cache_1",
# )

# T = 252687
# N = 36233108
# b = 524288
# t = 30663
# n = 36233108
# k1 = 1
# k2 = 1
# get_plot_seq_index(xs, T, N, b, t, n, k1, k2, "table_fit_cache_2")
# get_plot_index_breakdown(
#     compute_cost(
#         xs,
#         T,
#         N,
#         b,
#         t,
#         n,
#         k1,
#         k2,
#     ),
#     "table_fit_cache_2",
# )

# T = 161984
# N = 14838350
# b = 131072
# t = 18663
# n = 14838350
# k1 = 2
# k2 = 1
# get_plot_seq_index(xs, T, N, b, t, n, k1, k2, "table_bigger_cache_1")
# get_plot_index_breakdown(
#     compute_cost(
#         xs,
#         T,
#         N,
#         b,
#         t,
#         n,
#         k1,
#         k2,
#     ),
#     "table_bigger_cache_1",
# )

# T = 252687
# N = 36233108
# b = 131072
# t = 30663
# n = 36233108
# k1 = 1
# k2 = 1
# get_plot_seq_index(xs, T, N, b, t, n, k1, k2, "table_bigger_cache_2")
# get_plot_index_breakdown(
#     compute_cost(
#         xs,
#         T,
#         N,
#         b,
#         t,
#         n,
#         k1,
#         k2,
#     ),
#     "table_bigger_cache_2",
# )


# get_plot_by_selectivity(compute_pages_to_fetch_worst_case, xs, T, N, b)

# T = 600000
# N = T * 60
# s = 0.1
# xb = [524288, 524288 * 2, 524288 * 4, 524288 * 8]
# get_plot_by_cache_size(compute_pages_to_fetch_worst_case, xb, T, N, s)


# s = 0.2
# b = 524288
# xT = np.arange(100_000, 600_000, 1000)
# xN = [T * 60 for T in xT]
# get_plot_by_table_size(compute_pages_to_fetch_worst_case, xT, xN, s, b)

T = 161984
N = 14838350
b = 524288
draw_pages_fetched_chart(T, N, b, "table_fit_in_cache")
T1 = 161984
N1 = 14838350
b1 = 131072
draw_pages_fetched_chart(T1, N1, b1, "table_bigger_than_cache")
