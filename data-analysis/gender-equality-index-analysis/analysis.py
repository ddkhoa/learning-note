# %%
import pandas as pd

df = pd.read_excel("data/index-egalite-fh.xlsx")
print(df.shape)
print(df.columns)

# %%
df_establishments = pd.read_csv("etablissements.csv")
nb_big_companies = df_establishments[
    (df_establishments["trancheEffectifsEtablissement"] != 11)
    & (df_establishments["trancheEffectifsEtablissement"] != 12)
]["siren"].nunique()
print(nb_big_companies)
df_small_establishments = df_establishments[
    (df_establishments["trancheEffectifsEtablissement"] == 11)
    | (df_establishments["trancheEffectifsEtablissement"] == 12)
]
df_small_establishments["approxEmployees"] = df_small_establishments[
    "trancheEffectifsEtablissement"
].apply(lambda x: 10 if x == 11 else 20)
df_small_companies = (
    df_small_establishments.groupby("siren")
    .agg(approxEmployees=("approxEmployees", "sum"))
    .reset_index()
)
nb_companies_having_more_than_50_emp = (
    len(df_small_companies[df_small_companies["approxEmployees"] >= 50])
    + nb_big_companies
)
print(nb_companies_having_more_than_50_emp)

# %%
df_cleaned = df.drop(
    columns=["Raison Sociale", "SIREN", "Nom UES", "Entreprises UES (SIREN)"], axis=1
)
df_cleaned.rename(
    columns={
        "Année": "year",
        "Structure": "structure",
        "Tranche d'effectifs": "size",
        "Région": "region",
        "Département": "department",
        "Pays": "country",
        "Code NAF": "naf_code",
        "Note Ecart rémunération": "pay_gap_score",
        "Note Ecart taux d'augmentation (hors promotion)": "augmentation_excluding_promotion_gap_score",
        "Note Ecart taux de promotion": "promotion_gap_score",
        "Note Ecart taux d'augmentation": "augmentation_gap_score",
        "Note Retour congé maternité": "maternity_return_score",
        "Note Hautes rémunérations": "high_wages_score",
        "Note Index": "global_score",
    },
    inplace=True,
)
df_cleaned["naf_code"] = df_cleaned["naf_code"].apply(
    lambda x: x.split(" - ")[0] if x else None
)
print(df_cleaned.isnull().sum())

# %%
import dataframe_image as dfi

year_counts = df_cleaned["year"].value_counts().reset_index().sort_values("year")
year_counts.columns = ["Year", "Number of companies"]
year_counts = year_counts.set_index("Year").transpose()
dfi.export(year_counts, "output/year_counts.png", dpi=150)

# %%
from matplotlib import pyplot as plt
import matplotlib
import numpy as np

grey_colors = plt.cm.Greys(np.linspace(0.3, 1.0, 10))
grey_cmap = matplotlib.colors.LinearSegmentedColormap.from_list("mycmap", grey_colors)

# %%
fig = (
    df_cleaned.groupby(["year", "size"])
    .size()
    .unstack()
    .plot.bar(stacked=True, rot=0, figsize=(12, 6), colormap=grey_cmap)
)
fig.set_title("Number of companies published their result")
fig.set_xlabel(None)


# %%
df_cleaned["Group"] = df_cleaned["global_score"].apply(
    lambda x: (
        "Insufficient data"
        if x == "NC"
        else "To improve" if int(x) < 75 else "Equitable"
    )
)
df_cleaned["Group"] = pd.Categorical(
    df_cleaned["Group"],
    categories=[
        "To improve",
        "Equitable",
        "Insufficient data",
    ],
    ordered=True,
)
situation_evolution = (
    df_cleaned.groupby(["year", "Group"])
    .size()
    .unstack()
    .plot.bar(stacked=True, colormap=grey_cmap, rot=0, figsize=(12, 6))
)
situation_evolution.set_xlabel(None)
situation_evolution.set_title("The evolution of the Professional Equality Index")

# %%
global_score_2023 = df_cleaned[df_cleaned["global_score"] != "NC"]["global_score"]
colors_grey = plt.cm.Greys(np.linspace(1, 0, 10))
cm1 = matplotlib.colors.LinearSegmentedColormap.from_list("grey", colors_grey)
colors_blue = plt.cm.Blues(np.linspace(-1, 0.7, 5))
cm2 = matplotlib.colors.LinearSegmentedColormap.from_list("blue", colors_blue)
plt.figure(figsize=(10, 6))
n, bins, patches = plt.hist(global_score_2023, bins=20, width=3.5)
plt.axvline(x=75, color="red", linestyle="--")
plt.text(45, 23500, "Low equitable threshold = 75", color="red")
plt.xlabel("Total Score")
plt.ylabel("Number of companies")
plt.title("Distribution of Professional Equality Index in 2023")

# scale values to interval [0,1]
bin_centers = 0.5 * (bins[:-1] + bins[1:])
col = bin_centers - min(bin_centers)
col /= max(col)

for c, p in zip(col, patches):
    # plt.setp(p, 'facecolor', cmap(c))
    if c < 0.75:
        plt.setp(p, "facecolor", cm1(c))
    else:
        plt.setp(p, "facecolor", cm2(c))

plt.show()

# %%
companies_with_nc_pay_gap = df_cleaned[df_cleaned["pay_gap_score"] == "NC"]
nc_pay_gap_count_by_size = (
    companies_with_nc_pay_gap.groupby(["size", "year"]).size().unstack()
)
count_by_size = df_cleaned.groupby(["size", "year"]).size().unstack()
df_ratio_nc_pay_gap = nc_pay_gap_count_by_size / count_by_size

df_ratio_nc_pay_gap = (
    df_ratio_nc_pay_gap.round(4).style.format(precision=4).background_gradient()
)
dfi.export(df_ratio_nc_pay_gap, "output/nc_pay_gap_ratio_by_size.png", dpi=300)

# %%
companies_with_pay_gap = df_cleaned[df_cleaned["pay_gap_score"] != "NC"]
average_pay_gap_by_size = (
    companies_with_pay_gap.groupby(["size", "year"])["pay_gap_score"]
    .mean()
    .unstack()
    .apply(pd.to_numeric)
)
average_pay_gap_by_size = (
    average_pay_gap_by_size.round(2).style.format(precision=2).background_gradient()
)
dfi.export(average_pay_gap_by_size, "output/average_pay_gap_by_size.png", dpi=300)

# %%
filtered_data = df_cleaned[
    (df_cleaned["high_wages_score"] != "NC") & (df_cleaned["pay_gap_score"] != "NC")
]
correlation = filtered_data["pay_gap_score"].corr(filtered_data["high_wages_score"])
print(correlation)

# %%
df_naf = pd.read_excel("data/naf2008_5_niveaux.xls")
df_naf_lv1 = pd.read_excel("data/naf2008_liste_n1.xls", skiprows=2)
df_naf_with_name = pd.merge(
    df_naf, df_naf_lv1, left_on="NIV1", right_on="Code", how="inner"
)

df_filtered = df_cleaned[
    (df_cleaned["pay_gap_score"] != "NC") & (df_cleaned["year"] == 2023)
]
df_merged = pd.merge(
    df_filtered, df_naf_with_name, left_on="naf_code", right_on="NIV5", how="inner"
)

average_pay_gap_score_by_naf = (
    df_merged.groupby("Libellé")
    .agg(
        mean=("pay_gap_score", "mean"),
        count=("pay_gap_score", "count"),
    )
    .reset_index()
    .sort_values(by="mean", ascending=True)
)
average_pay_gap_score_by_naf = average_pay_gap_score_by_naf[
    average_pay_gap_score_by_naf["count"] >= 100
]
average_pay_gap_score_by_naf["mean"] = (
    average_pay_gap_score_by_naf["mean"].apply(pd.to_numeric).round(2)
)

average_pay_gap_score_by_naf.rename(
    columns={
        "Libellé": "Sector",
        "mean": "Average score",
        "count": "Number of companies",
    },
    inplace=True,
)
average_pay_gap_score_by_naf = (
    average_pay_gap_score_by_naf.style.hide()
    .format(precision=2)
    .background_gradient(axis=0, subset=["Average score"])
)
dfi.export(
    average_pay_gap_score_by_naf, "output/average_pay_gap_score_by_naf.png", dpi=300
)


# %%
def no_augmentation_data_filter(row):
    if row["size"] == "50 à 250":
        return row["augmentation_gap_score"] == "NC"

    if row["size"] == "251 à 999" or row["size"] == "1000 et plus":
        return (
            row["augmentation_excluding_promotion_gap_score"] == "NC"
            and row["promotion_gap_score"] == "NC"
        )


no_augmentation_data = df_cleaned.copy()
no_augmentation_data["filter"] = no_augmentation_data.apply(
    no_augmentation_data_filter, axis=1
)
no_augmentation_data = no_augmentation_data[no_augmentation_data["filter"] == True]

no_augmentation_data_count_by_size = (
    no_augmentation_data.groupby(["size", "year"]).size().unstack()
)
count_by_size = df_cleaned.groupby(["size", "year"]).size().unstack()
df_ratio_no_aug_data = no_augmentation_data_count_by_size / count_by_size

df_ratio_no_aug_data = (
    df_ratio_no_aug_data.round(4).style.format(precision=4).background_gradient()
)
dfi.export(
    df_ratio_no_aug_data, "output/nc_augmentation_gap_ratio_by_size.png", dpi=300
)

# %%
aug_gap_score_50_250 = df_cleaned[
    (df_cleaned["year"] == 2023)
    & (df_cleaned["size"] == "50 à 250")
    & (df_cleaned["augmentation_gap_score"] != "NC")
]
aug_gap_score_50_250 = pd.merge(
    aug_gap_score_50_250,
    df_naf_with_name,
    left_on="naf_code",
    right_on="NIV5",
    how="inner",
)
average_aug_gap_score_50_250_by_naf = (
    aug_gap_score_50_250.groupby("Libellé")
    .agg(
        mean=("augmentation_gap_score", "mean"),
        count=("augmentation_gap_score", "count"),
    )
    .reset_index()
    .sort_values(by="mean", ascending=True)
)
average_aug_gap_score_50_250_by_naf = average_aug_gap_score_50_250_by_naf[
    average_aug_gap_score_50_250_by_naf["count"] >= 100
]
average_aug_gap_score_50_250_by_naf["mean"] = (
    average_aug_gap_score_50_250_by_naf["mean"].apply(pd.to_numeric).round(2)
)

average_aug_gap_score_50_250_by_naf.rename(
    columns={
        "Libellé": "Sector",
        "mean": "Average score",
        "count": "Number of companies",
    },
    inplace=True,
)
average_aug_gap_score_50_250_by_naf = (
    average_aug_gap_score_50_250_by_naf.style.hide()
    .format(precision=2)
    .background_gradient(axis=0, subset=["Average score"])
)
dfi.export(
    average_aug_gap_score_50_250_by_naf,
    "output/average_aug_gap_score_50_250_by_naf.png",
    dpi=300,
)


aug_gap_score_above_250 = df_cleaned[
    (df_cleaned["year"] == 2023)
    & ((df_cleaned["size"] == "251 à 999") | (df_cleaned["size"] == "1000 et plus"))
    & (
        (df_cleaned["augmentation_excluding_promotion_gap_score"] != "NC")
        & (df_cleaned["promotion_gap_score"] != "NC")
    )
].copy()
aug_gap_score_above_250 = pd.merge(
    aug_gap_score_above_250,
    df_naf_with_name,
    left_on="naf_code",
    right_on="NIV5",
    how="inner",
)
aug_gap_score_above_250["sum_augmentation_promotion_score"] = (
    aug_gap_score_above_250["augmentation_excluding_promotion_gap_score"]
    + aug_gap_score_above_250["promotion_gap_score"]
)
aug_gap_score_above_250_by_naf = (
    aug_gap_score_above_250.groupby("Libellé")
    .agg(
        mean=("sum_augmentation_promotion_score", "mean"),
        count=("sum_augmentation_promotion_score", "count"),
    )
    .reset_index()
    .sort_values(by="mean", ascending=True)
)
aug_gap_score_above_250_by_naf = aug_gap_score_above_250_by_naf[
    aug_gap_score_above_250_by_naf["count"] >= 100
]
aug_gap_score_above_250_by_naf["mean"] = (
    aug_gap_score_above_250_by_naf["mean"].apply(pd.to_numeric).round(2)
)

aug_gap_score_above_250_by_naf.rename(
    columns={
        "Libellé": "Sector",
        "mean": "Average score",
        "count": "Number of companies",
    },
    inplace=True,
)
aug_gap_score_above_250_by_naf = (
    aug_gap_score_above_250_by_naf.style.hide()
    .format(precision=2)
    .background_gradient(axis=0, subset=["Average score"])
)
dfi.export(
    aug_gap_score_above_250_by_naf,
    "output/average_aug_gap_score_above_250_by_naf.png",
    dpi=300,
)

# %%
augmentation_gap_score_50_250 = df_cleaned[
    (df_cleaned["size"] == "50 à 250") & (df_cleaned["augmentation_gap_score"] != "NC")
].copy()
augmentation_gap_score_above_250 = df_cleaned[
    ((df_cleaned["size"] == "251 à 999") | (df_cleaned["size"] == "1000 et plus"))
    & (
        (df_cleaned["augmentation_excluding_promotion_gap_score"] != "NC")
        & (df_cleaned["promotion_gap_score"] != "NC")
    )
].copy()
augmentation_gap_score_above_250["sum_augmentation_promotion_score"] = (
    augmentation_gap_score_above_250["augmentation_excluding_promotion_gap_score"]
    + augmentation_gap_score_above_250["promotion_gap_score"]
)

mean_augmentation_gap_score_50_250 = (
    augmentation_gap_score_50_250.groupby("year")
    .agg(mean=("augmentation_gap_score", "mean"))
    .reset_index()
)
augmentation_gap_score_above_250 = (
    augmentation_gap_score_above_250.groupby("year")
    .agg(mean=("sum_augmentation_promotion_score", "mean"))
    .reset_index()
)
mean_augmentation_gap_score_50_250.columns = ["Year", "Average score"]
mean_augmentation_gap_score_50_250["Average score"] = (
    mean_augmentation_gap_score_50_250["Average score"].apply(pd.to_numeric).round(2)
)
mean_augmentation_gap_score_50_250 = mean_augmentation_gap_score_50_250.set_index(
    "Year"
).transpose()
mean_augmentation_gap_score_50_250 = mean_augmentation_gap_score_50_250.style.format(
    precision=2
).background_gradient(axis=1)
mean_augmentation_gap_score_50_250

dfi.export(
    mean_augmentation_gap_score_50_250,
    "output/average_aug_gap_score_50_250.png",
    dpi=300,
)

augmentation_gap_score_above_250.columns = ["Year", "Average score"]
augmentation_gap_score_above_250["Average score"] = (
    augmentation_gap_score_above_250["Average score"].apply(pd.to_numeric).round(2)
)
augmentation_gap_score_above_250 = augmentation_gap_score_above_250.set_index(
    "Year"
).transpose()
augmentation_gap_score_above_250 = augmentation_gap_score_above_250.style.format(
    precision=2
).background_gradient(axis=1)
augmentation_gap_score_above_250


dfi.export(
    augmentation_gap_score_above_250,
    "output/average_aug_gap_score_above_250.png",
    dpi=300,
)

# %%
