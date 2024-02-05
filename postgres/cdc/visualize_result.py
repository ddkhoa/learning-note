from typing import Literal
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


# Function to format y-axis ticks without scientific notation
def format_y_ticks(value, pos):
    return "{:.2f}".format(value)


def draw_chart(
    scenario: Literal["low_diff_ratio", "medium_diff_ratio", "high_diff_ratio"],
):
    df_replace = pd.read_csv(f"result/{scenario}/result_update_data_replace.csv")
    df_incremental = pd.read_csv(
        f"result/{scenario}/result_update_data_incremental.csv"
    )

    df_replace["index_size_changed"] = (
        df_replace["index_size"] - df_replace.at[0, "index_size"]
    )
    df_replace["heap_size_changed"] = (
        df_replace["heap_size"] - df_replace.at[0, "heap_size"]
    )
    df_incremental["index_size_changed"] = (
        df_incremental["index_size"] - df_incremental.at[0, "index_size"]
    )
    df_incremental["heap_size_changed"] = (
        df_incremental["heap_size"] - df_incremental.at[0, "heap_size"]
    )
    df_replace["index_size_changed"] = df_replace["index_size_changed"] / (1024 * 1024)
    df_replace["heap_size_changed"] = df_replace["heap_size_changed"] / (1024 * 1024)
    df_incremental["index_size_changed"] = df_incremental["index_size_changed"] / (
        1024 * 1024
    )
    df_incremental["heap_size_changed"] = df_incremental["heap_size_changed"] / (
        1024 * 1024
    )

    df_replace["group"] = "replace update"
    df_incremental["group"] = "incremental update"
    combined_df = pd.concat([df_replace, df_incremental])

    combined_df.rename(columns={"Unnamed: 0": "nth_update"}, inplace=True)
    print(combined_df)
    plt.figure(figsize=(12, 6))

    exec_df = combined_df.dropna(subset=["exec_time"])
    exec_chart = sns.lineplot(
        data=exec_df,
        x="nth_update",
        y="exec_time",
        hue="group",
        marker="o",
    )

    plt.xlabel("nth update")
    plt.ylabel("Execution Time (s)")
    plt.title("Execution Time")
    plt.ylim(0, None)
    sns.move_legend(exec_chart, "upper center")
    plt.savefig(f"result/{scenario}/exec_time.png")
    plt.clf()

    heap_size_chart = sns.lineplot(
        data=combined_df, x="nth_update", y="heap_size_changed", hue="group", marker="o"
    )
    plt.xlabel("nth update")
    plt.ylabel("Heap size changed (MB)")
    plt.gca().get_yaxis().set_major_formatter(FuncFormatter(format_y_ticks))
    plt.title("Heap size evolution")
    sns.move_legend(heap_size_chart, "upper center")
    plt.savefig(f"result/{scenario}/heap_size.png")
    plt.clf()

    index_size_chart = sns.lineplot(
        data=combined_df,
        x="nth_update",
        y="index_size_changed",
        hue="group",
        marker="o",
    )
    plt.xlabel("nth update")
    plt.ylabel("Index size changed (MB)")
    plt.gca().get_yaxis().set_major_formatter(FuncFormatter(format_y_ticks))
    plt.title("Index size evolution")
    sns.move_legend(index_size_chart, "upper center")
    plt.savefig(f"result/{scenario}/index_size.png")
    plt.clf()

    dead_rows_chart = sns.lineplot(
        data=combined_df,
        x="nth_update",
        y="n_dead_tuples",
        hue="group",
        marker="o",
    )
    plt.xlabel("nth update")
    plt.ylabel("Number of dead tuples")
    plt.gca().get_yaxis().set_major_formatter(FuncFormatter(format_y_ticks))
    plt.title("Number of dead tuples")
    sns.move_legend(dead_rows_chart, "upper center")
    plt.savefig(f"result/{scenario}/dead_tuples.png")
    plt.clf()


draw_chart("low_diff_ratio")
draw_chart("medium_diff_ratio")
draw_chart("high_diff_ratio")
