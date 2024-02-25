import numpy as np
from matplotlib import pylab as plt


def page_fetched_worst_case(s, T, N, b):
    if T <= b:
        # print("1")
        a = 2 * T * N * s / (2 * T + N * s)
        return min(a, T)
    if s <= 2 * T * b / (N * (2 * T - b)):
        # print("2")
        return 2 * T * N * s / (2 * T + N * s)

    # print("3")
    return b + (N * s - 2 * T * b / (2 * T - b)) * (T - b) / T


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


xs = np.arange(0, 1, 0.01)
T = 179509
N = 10950049
b = 524288
t = 102924
n = 10950049
k1 = 2
k2 = 1
get_plot_seq_index(xs, T, N, b, t, n, k1, k2, "table_fit_cache_1")

T = 252687
N = 36233108
b = 524288
t = 30663
n = 36233108
k1 = 1
k2 = 1
get_plot_seq_index(xs, T, N, b, t, n, k1, k2, "table_fit_cache_2")

T = 179509
N = 10950049
b = 131072
t = 102924
n = 10950049
k1 = 2
k2 = 1
get_plot_seq_index(xs, T, N, b, t, n, k1, k2, "table_bigger_cache_1")

T = 252687
N = 36233108
b = 131072
t = 30663
n = 36233108
k1 = 1
k2 = 1
get_plot_seq_index(xs, T, N, b, t, n, k1, k2, "table_bigger_cache_2")

# get_plot_by_selectivity(page_fetched_worst_case, xs, T, N, b)

# T = 600000
# N = T * 60
# s = 0.1
# xb = [524288, 524288 * 2, 524288 * 4, 524288 * 8]
# get_plot_by_cache_size(page_fetched_worst_case, xb, T, N, s)


# s = 0.2
# b = 524288
# xT = np.arange(100_000, 600_000, 1000)
# xN = [T * 60 for T in xT]
# get_plot_by_table_size(page_fetched_worst_case, xT, xN, s, b)
