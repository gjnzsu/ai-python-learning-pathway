# 第 5 周 · 第 3 课：分组比较与需求模式可视化

预计用时：180–210 分钟（含练习与小测；进阶挑战选做）

## 本课定位

上一课回答了“数据怎样转换才可信”，这一课回答“怎样比较才有意义”。

本课直接读取第二课导出的 `hourly_clean.csv`，不重复清洗，不修改原始文件，也不删除 505 条高需求候选。第二课复盘小测仍可稍后补答，生成本课讲义不代表上一课小测或本课学习已经完成。

你将创建 `projects/week-05-bike-sharing/notebooks/03_group_comparison.ipynb`。所有示例按顺序放在这个 Notebook 中；本课暂不拆分 Python 模块。

## 本课目标

- 使用 `groupby().agg()` 把分析问题转成有明确粒度的汇总表。
- 区分记录数、租赁总量、均值、中位数和占比各自回答的问题。
- 使用小时与工作日、星期、年份与季节编码等维度进行分组比较。
- 使用 `pivot()` 构造二维比较矩阵，并为颜色图提供样本量依据。
- 使用 `melt()` 将临时用户与注册用户计数转换成长表。
- 识别小样本、混杂因素、缺失时间窗口和统计分母带来的解释风险。
- 为每张图写“观察 + 证据 + 限制 + 下一步”，并导出图表和汇总表。

## 0. 先确定口径，而不是先选择图（10 分钟）

本课主要回答四个问题：

1. 工作日和非工作日的小时需求曲线有何不同？
2. 星期与小时组合中，哪些时段需求更高？
3. 季节编码和天气类别之间的差异，是否可能与年份和小时构成有关？
4. 临时用户与注册用户的租赁模式是否不同？

### 0.1 两个数据边界

第一，主表包含 17,379 个有租赁记录的小时，不包含完整时间轴中的 165 个零需求小时。因此主表上的均值是“有记录小时的平均需求”，不是“全部日历小时的平均需求”。本课第 8 节会比较这两种分母。

第二，存在数据字典版本冲突：本地压缩包 `Readme.txt` 的季节定义为 1–4 对应 spring、summer、fall、winter；UCI 当前页面则对应 winter、spring、summer、fall。第二课按本地文件生成的 `season_label` 因而不能直接用来下自然季节结论。本课不改动旧产物，新增 `season_group`，使用 `season_1` 至 `season_4` 的中性展示名，并保留该限制。

温度恢复公式也存在差异：本地 Readme 写为乘以 41/50，而 UCI 当前页面的小时数据说明使用 `temp * 47 - 8` 和 `atemp * 66 - 16`。因此本课不使用第二课的 `temp_c`、`feels_like_c` 作物理温度解释，也不静默覆盖它们。后续若分析温度，需要先确定采用的说明版本并重新记录转换依据。[UCI 官方字段说明，核验日期：2026-08-30](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset)

这不是说前面的范围断言失效，而是说明：程序验证可以证明转换符合所选公式，却不能证明公式来源没有问题。

### 0.2 指标词典

| 指标 | 计算方式 | 回答的问题 |
| --- | --- | --- |
| `sample_count` | 分组行数 | 比较依据有多少条小时记录？ |
| `total_rentals` | `cnt.sum()` | 该组累计发生多少次租赁？ |
| `mean_rentals` | `cnt.mean()` | 每个有记录小时平均多少次租赁？ |
| `median_rentals` | `cnt.median()` | 典型的有记录小时需求是多少？ |
| `p95_rentals` | `cnt.quantile(0.95)` | 大多数小时的需求上界大致在哪里？ |
| `casual_share` | `sum(casual) / sum(cnt)` | 该组全部租赁中，临时用户租赁占多少？ |

`casual` 和 `registered` 统计的是租赁次数，不是去重后的用户人数。

## 1. 独立读取与验证输入（10 分钟）

从 Notebook 所在的 `notebooks/` 目录运行下列代码。如果路径断言失败，先查看 `Path.cwd()`，确认工作目录；不要不断猜测 `../` 的数量。

```python
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

DATA_PATH = Path("../data/processed/hourly_clean.csv")
REPORT_DIR = Path("../reports/lesson-03")

assert DATA_PATH.exists(), f"找不到输入文件: {DATA_PATH.resolve()}"
df = pd.read_csv(DATA_PATH, parse_dates=["dteday", "timestamp"])

required = {
    "timestamp", "dteday", "hr", "workingday", "weekday",
    "yr", "season", "weathersit", "casual", "registered", "cnt",
}
assert required.issubset(df.columns)
assert df.shape == (17_379, 26)
assert df[list(required)].notna().all().all()
assert df["timestamp"].is_unique
assert df["timestamp"].is_monotonic_increasing
assert df["cnt"].gt(0).all()
assert df["cnt"].eq(df["casual"] + df["registered"]).all()
assert int(df["cnt"].sum()) == 3_292_679
```

定义用于展示的维度：

```python
day_type_labels = {0: "non_workingday", 1: "workingday"}
season_groups = {i: f"season_{i}" for i in range(1, 5)}
weekday_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
weekday_labels = {
    0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed",
    4: "Thu", 5: "Fri", 6: "Sat",
}

df["day_type"] = df["workingday"].map(day_type_labels)
df["season_group"] = df["season"].map(season_groups)
df["weekday_display"] = df["weekday"].map(weekday_labels)
df["year"] = df["dteday"].dt.year

dimension_columns = ["day_type", "season_group", "weekday_display"]
assert df[dimension_columns].notna().all().all()
for column in dimension_columns:
    df[column] = df[column].astype("category")

assert df["year"].eq(df["yr"] + 2011).all()
assert ((df["dteday"].dt.dayofweek + 1) % 7).eq(df["weekday"]).all()
```

提醒：`workingday == 0` 同时包含周末和节假日，图例应该写“非工作日”，不能简称“周末”。

## 2. 从 `loc` 筛选过渡到分组汇总（15 分钟）

上一课你已经掌握：

```python
working_hours = df.loc[df["workingday"].eq(1), ["hr", "cnt"]]
working_hours.head()
```

`loc[行条件, 列选择]` 仍然返回逐行记录。如果要回答“每个小时的典型需求”，需要再分组。

```python
hourly_summary = df.groupby("hr", as_index=False).agg(
    sample_count=("cnt", "size"),
    total_rentals=("cnt", "sum"),
    mean_rentals=("cnt", "mean"),
    median_rentals=("cnt", "median"),
    p95_rentals=("cnt", lambda values: values.quantile(0.95)),
)

assert len(hourly_summary) == 24
assert hourly_summary["sample_count"].sum() == len(df)
assert hourly_summary["total_rentals"].sum() == df["cnt"].sum()
hourly_summary.head()
```

逐项理解 `median_rentals=("cnt", "median")`：

- 左侧：输出列名。
- 元组第一个元素：参与计算的原列。
- 元组第二个元素：聚合方式。

`as_index=False` 让 `hr` 保持为普通列，便于后续筛选、绘图和导出。`size` 统计组内行数，`count` 则忽略被统计列的缺失值。

Java / SQL 对照：`groupby("hr")` 类似 `GROUP BY hr`，`.agg()` 类似同时计算 `COUNT(*)`、`SUM(cnt)`、`AVG(cnt)`。但 SQL 中计算中位数的具体写法取决于数据库。

不要直接对所有数值列 `.mean()`：那会把标识符、星期编码等没有均值解释的字段也一起平均。

## 3. 工作日与非工作日的小时曲线（20 分钟）

### 3.1 两个分组键意味着新的观察单位

```python
hour_day = df.groupby(
    ["day_type", "hr"], as_index=False, observed=True,
).agg(
    sample_count=("cnt", "size"),
    mean_rentals=("cnt", "mean"),
    median_rentals=("cnt", "median"),
    total_rentals=("cnt", "sum"),
)

assert len(hour_day) == 48
assert hour_day["sample_count"].sum() == len(df)
assert hour_day["total_rentals"].sum() == df["cnt"].sum()
hour_day.head()
```

现在一行不再代表一个具体小时，而是“一个日类型 × 一个钟点”的汇总。

涉及 `category` 列时显式指定 `observed=True`，只返回数据中实际出现的分组组合，避免依赖 Pandas 版本默认值。它不代表缺失组合的需求为零。[Pandas groupby 官方文档](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html)

### 3.2 先汇总再画图，避免无意二次聚合

```python
fig_hour, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

for day_type, group in hour_day.groupby("day_type", observed=True):
    group = group.sort_values("hr")
    axes[0].plot(group["hr"], group["median_rentals"], marker="o", label=day_type)
    axes[1].plot(group["hr"], group["sample_count"], marker="o", label=day_type)

axes[0].set(title="Hourly demand by day type — recorded hours only",
            ylabel="Median rentals per recorded hour")
axes[0].legend()
axes[1].set(xlabel="Hour of day", ylabel="Recorded-hour count", xticks=range(24))
fig_hour.tight_layout()
plt.show()
```

上图比较典型需求，下图交代样本量；不要把两种单位画在同一个纵轴。

从表中定位各日类型的峰值：

```python
peak_rows = hour_day.groupby("day_type", observed=True)["median_rentals"].idxmax()
peak_hours = hour_day.loc[
    peak_rows, ["day_type", "hr", "median_rentals", "sample_count"]
]
peak_hours
```

`idxmax()` 返回最大值所在的行索引，不是最大值本身；并列时只返回首个位置，因此该表不是“所有并列峰值清单”。

观察提示：工作日是否存在早晚双峰，非工作日是否呈午后宽峰？“与通勤模式一致”是解释假设，不代表数据已经证明每个人的出行目的。

## 4. 星期 × 小时：从汇总表到热力图（20 分钟）

### 4.1 先聚合，再透视

```python
weekday_hour = df.groupby(
    ["weekday_display", "hr"], as_index=False, observed=True,
).agg(
    median_rentals=("cnt", "median"),
    sample_count=("cnt", "size"),
)

demand_matrix = weekday_hour.pivot(
    index="weekday_display", columns="hr", values="median_rentals",
).reindex(index=weekday_order, columns=range(24))

sample_matrix = weekday_hour.pivot(
    index="weekday_display", columns="hr", values="sample_count",
).reindex(index=weekday_order, columns=range(24))

assert demand_matrix.shape == (7, 24)
assert sample_matrix.sum().sum() == len(df)
sample_matrix
```

`pivot()` 只重排，不做聚合，所以每个“星期 × 小时”组合必须唯一。不能直接对原始小时表这样透视，因为同一星期与钟点会在不同日期重复出现。

`pivot_table()` 则可以边聚合边透视，但必须明确指定 `aggfunc`；本课分成两步，方便检查中间结果。

### 4.2 颜色展示需求，同时检查样本量矩阵

```python
fig_heat, ax = plt.subplots(figsize=(12, 4))
heat = ax.imshow(demand_matrix.to_numpy(), aspect="auto", cmap="YlGnBu")
ax.set_xticks(range(24), labels=range(24))
ax.set_yticks(range(7), labels=weekday_order)
ax.set(title="Weekday × hour — median rentals in recorded hours",
       xlabel="Hour of day", ylabel="Weekday")
fig_heat.colorbar(heat, ax=ax, label="Median rental count")
fig_heat.tight_layout()
plt.show()
```

星期顺序由 `weekday_order` 显式给出，不按英文单词排序。若某格没有观测，应保留缺失，不要 `.fillna(0)` 把“未知”涂成“零需求”。

回答：周一至周五的亮色区域与周末有什么区别？注意星期维度本身不区分法定节假日。

## 5. 季节编码比较：加入年份，减少粗糙混合（15 分钟）

先核对编码与月份的实际分布，理解为何不能直接相信旧标签：

```python
season_month_counts = pd.crosstab(df["season"], df["mnth"])
season_month_counts
```

不要只比较两年混合后的季节总量。总量同时受样本量和每小时需求影响；跨年需求规模也可能不同。

```python
season_year = df.groupby(
    ["year", "season_group"], as_index=False, observed=True,
).agg(
    sample_count=("cnt", "size"),
    mean_rentals=("cnt", "mean"),
    median_rentals=("cnt", "median"),
)

season_plot = season_year.pivot(
    index="season_group", columns="year", values="mean_rentals",
).reindex([f"season_{i}" for i in range(1, 5)])

fig_season, ax = plt.subplots(figsize=(9, 4))
season_plot.plot.bar(ax=ax, rot=0)
ax.set(title="Season codes by year — recorded hours only",
       xlabel="Original season code", ylabel="Mean rentals per recorded hour")
ax.legend(title="Year")
fig_season.tight_layout()
plt.show()
season_year
```

分年份比较可以避免把所有年份混成一个均值，但仍不能隔离“纯季节效应”：天气、工作日比例、节假日、系统规模和其他未观测因素仍然存在。本课不做因果推断，也不进行显著性检验。

## 6. 天气类别比较：样本量是结论的一部分（20 分钟）

```python
weather_summary = df.groupby("weathersit", as_index=False).agg(
    sample_count=("cnt", "size"),
    mean_rentals=("cnt", "mean"),
    median_rentals=("cnt", "median"),
    p25_rentals=("cnt", lambda values: values.quantile(0.25)),
    p75_rentals=("cnt", lambda values: values.quantile(0.75)),
)
weather_summary = weather_summary.sort_values("weathersit")
assert weather_summary["sample_count"].tolist() == [11_413, 4_544, 1_419, 3]
weather_summary
```

使用点和 P25–P75 范围展示分布中心，不让均值独占视线：

```python
fig_weather, ax = plt.subplots(figsize=(8, 4))
for row in weather_summary.itertuples(index=False):
    color = "tab:red" if row.sample_count < 30 else "tab:blue"
    ax.vlines(row.weathersit, row.p25_rentals, row.p75_rentals, color=color, linewidth=5)
    ax.scatter(row.weathersit, row.median_rentals, color=color, s=55)

tick_labels = [
    f"Code {row.weathersit}\nn={row.sample_count}"
    for row in weather_summary.itertuples(index=False)
]
ax.set_xticks(weather_summary["weathersit"], labels=tick_labels)
ax.set(title="Weather: median and P25–P75 (not a confidence interval)",
       xlabel="Weather code; red = small sample warning",
       ylabel="Rentals per recorded hour")
fig_weather.tight_layout()
plt.show()
```

`itertuples()` 在这里逐行读取的是 4 行汇总表，用于画图，不是逐行处理 17,379 条原始记录。

务必区分：

- P25–P75 描述观测值中间 50% 的分布范围，不是均值或中位数的置信区间。
- `n < 30` 只是本课的人工提醒阈值，不是可靠性定理；31 条数据也不自动可信。
- 天气类别 4 只有 3 条记录，应展示但不能据此推广一般规律。
- 本表的天气类别样本量仅针对有记录小时，缺失小时天气未知，不能编造归属。

检查这 3 条记录具体发生在什么时候：

```python
rare_weather = df.loc[
    df["weathersit"].eq(4),
    ["timestamp", "hr", "workingday", "cnt"],
]
rare_weather
```

如果想更公平地比较，可进一步按工作日、小时、年份分层，但切得越细，每组样本越少。不要为了“控制变量”而产生大量没有观测或只有一条数据的格子。

## 7. 用户类型比较：宽表、长表和比例分母（20 分钟）

### 7.1 用 `melt()` 把列名转成维度值

原始宽表一行含两个计数：`casual`、`registered`。长表中，同一个小时对应两行，一行一种用户类型。

```python
user_long = df.melt(
    id_vars=["timestamp", "hr", "day_type"],
    value_vars=["casual", "registered"],
    var_name="user_type",
    value_name="rentals",
)

assert len(user_long) == 2 * len(df)
assert not user_long.duplicated(["timestamp", "user_type"]).any()
assert user_long["rentals"].sum() == df["cnt"].sum()
user_long.head()
```

`id_vars` 保留身份字段，`value_vars` 指定展开哪些列，后两个参数命名新列。转换后 `timestamp` 单独不再唯一，业务键变成 `timestamp + user_type`。行数翻倍不代表原始样本量翻倍，也不是新增了独立观测。[Pandas melt 官方文档](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.melt.html)

### 7.2 按日类型比较两类用户

```python
user_hour = user_long.groupby(
    ["day_type", "user_type", "hr"], as_index=False, observed=True,
).agg(
    sample_count=("rentals", "size"),
    mean_rentals=("rentals", "mean"),
)

fig_users, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
for ax, day_type in zip(axes, ["workingday", "non_workingday"]):
    subset = user_hour.loc[user_hour["day_type"].eq(day_type)]
    for user_type, group in subset.groupby("user_type", observed=True):
        group = group.sort_values("hr")
        ax.plot(group["hr"], group["mean_rentals"], label=user_type)
    ax.set(title=day_type, xlabel="Hour", xticks=range(0, 24, 3))
    ax.legend()
axes[0].set_ylabel("Mean rentals per recorded hour")
fig_users.suptitle("User types — recorded hours only")
fig_users.tight_layout()
plt.show()
```

两个面板共享纵轴，避免自动缩放把规模差异掩盖。该图描述用户类别对应的租赁计数，不识别个人，也不证明出行目的。

### 7.3 总体占比不等于小时占比的简单平均

```python
user_share = df.groupby("day_type", as_index=False, observed=True).agg(
    sample_count=("cnt", "size"),
    casual_total=("casual", "sum"),
    registered_total=("registered", "sum"),
    total_rentals=("cnt", "sum"),
)
user_share["casual_share"] = user_share["casual_total"] / user_share["total_rentals"]
assert user_share["casual_share"].between(0, 1).all()
user_share
```

一个手算例子：小时 A 有 1 次租赁，全部是临时用户；小时 B 有 99 次租赁，全部是注册用户。

- 各小时占比简单平均：`(100% + 0%) / 2 = 50%`。
- 全部租赁中的临时占比：`1 / (1 + 99) = 1%`。

两者分母不同，回答的问题不同。报告“全部租赁的用户结构”时采用后者，不要把低流量小时与高流量小时等权后仍称为总体占比。

## 8. 敏感性检查：零需求小时如何改变均值（15 分钟）

沿用第二课已通过的日表守恒证据，仅补全租赁计数，不补天气：

```python
full_hours = pd.date_range(df["timestamp"].min(), df["timestamp"].max(), freq="h")
timeline = df.set_index("timestamp")[["cnt"]].reindex(full_hours)
timeline.index.name = "timestamp"
timeline["record_was_missing"] = timeline["cnt"].isna()
assert len(timeline) == 17_544
assert timeline["record_was_missing"].sum() == 165
timeline["cnt"] = timeline["cnt"].fillna(0).astype("int64")
timeline["hr"] = timeline.index.hour
assert timeline["cnt"].sum() == df["cnt"].sum()

all_hour_summary = timeline.groupby("hr", as_index=False).agg(
    calendar_hour_count=("cnt", "size"),
    mean_all_hours=("cnt", "mean"),
)
sensitivity = hourly_summary[["hr", "sample_count", "mean_rentals"]].merge(
    all_hour_summary, on="hr", validate="one_to_one",
)
sensitivity["mean_difference"] = (
    sensitivity["mean_rentals"] - sensitivity["mean_all_hours"]
)
assert sensitivity["calendar_hour_count"].eq(731).all()
assert sensitivity["mean_difference"].ge(-1e-10).all()
sensitivity.loc[sensitivity["hr"].between(2, 5)]
```

补零不改变租赁总量，却增加了均值分母，所以均值会降低或不变。这不是哪个表“算错了”，而是比较口径不同。

本课前面的图仍标注“recorded hours only”。如果要把工作日曲线也改为完整时间轴，需为补出的日期从可靠日历表或日表恢复 `workingday`，不能仅以星期几推断，因为还有节假日。

## 9. 写结论、导出资产和从头验收（15 分钟）

### 9.1 每张图都写四句话

推荐放在图下的 Markdown 单元格中：

```text
观察：工作日和非工作日的小时需求曲线形状不同。
证据：从 hour_day 表填入峰值小时、中位数和该组样本量。
限制：仅统计有记录小时；混合了年份、天气和季节，不能证明出行目的。
下一步：按年份复查曲线，并比较完整需求时间轴的结果。
```

必须用实际表格结果填入证据，不要直接照抄“工作日一定双峰”等未经检查的预设。

### 9.2 导出本课结果

以下代码只写入本课专用报告目录，重复执行会覆盖这些同名报告资产，不改动 `raw` 或第二课清洗文件。

```python
REPORT_DIR.mkdir(parents=True, exist_ok=True)

tables = {
    "hour_day": hour_day,
    "weekday_hour": weekday_hour,
    "season_year": season_year,
    "weather_summary": weather_summary,
    "user_hour": user_hour,
    "user_share": user_share,
    "zero_hour_sensitivity": sensitivity,
}
for name, table in tables.items():
    table.to_csv(REPORT_DIR / f"{name}.csv", index=False)

figures = {
    "hour_by_day_type": fig_hour,
    "weekday_hour_heatmap": fig_heat,
    "season_by_year": fig_season,
    "weather_distribution": fig_weather,
    "user_hour_patterns": fig_users,
}
for name, figure in figures.items():
    figure.savefig(REPORT_DIR / f"{name}.png", dpi=150, bbox_inches="tight")

reloaded_summary = pd.read_csv(REPORT_DIR / "hour_day.csv")
assert len(reloaded_summary) == 48
assert reloaded_summary["sample_count"].sum() == len(df)
assert reloaded_summary["total_rentals"].sum() == 3_292_679
assert all((REPORT_DIR / f"{name}.png").stat().st_size > 0 for name in figures)
print("本课汇总表和图表已导出，回读契约通过")
```

文件非空只能证明导出有内容，不能证明布局正确。打开 5 张 PNG，检查标题、图例、单位、坐标顺序和文字是否被裁切。

最后重启 Notebook 内核并运行全部单元格，确认不依赖第二课的内存变量。文件中的示例代码按正文顺序执行；Markdown 解读需要自己补充。

## 10. 课堂练习

### 练习 1：解释分组后的粒度

分别用一句话描述 `df`、`hour_day`、`weekday_hour`、`user_long` 中的一行代表什么。解释为什么只有 `user_long` 不能单独用 `timestamp` 作为唯一键。

### 练习 2：替换中心指标

把工作日小时曲线的中位数换成均值，比较峰值和形状是否改变。保留原图，说明两个指标对极端值的敏感性差异。

### 练习 3：小样本天气

展示天气类别 4 的全部 3 行记录。判断“极端天气不影响租赁需求”这一结论是否得到支持，至少写两个限制。

### 练习 4：年份分层

按 `year + day_type + hr` 重新汇总，分别画 2011、2012 年曲线。比较形状和规模，写明新增分组后每格样本量变少的代价。

### 练习 5：两种占比

分别计算所有有记录小时的临时用户占比平均值，以及全部租赁中的临时用户占比。给两个指标起不会混淆的名称，并解释为何数值可能不同。

## 11. 小测（10 题）

1. 分组 `size()` 与 `cnt.sum()` 的统计单位分别是什么？
2. 为什么比较工作日和非工作日时，不应只比较租赁总量？
3. `as_index=False` 和 `observed=True` 分别控制什么？
4. `pivot()` 与 `pivot_table()` 在聚合行为上有什么不同？
5. 热力图某格没有观测，为什么不应直接填 0？
6. P25–P75 为什么不是置信区间？天气类别 4 有哪些限制？
7. `melt()` 后行数翻倍，是否意味着有两倍独立样本？
8. 总体临时用户租赁占比为什么不一定等于每小时占比的平均值？
9. 补齐零需求小时后，总量和均值分别如何变化？
10. 为什么按年份分层后仍不能把季节或天气差异解释成因果效应？

## 12. 进阶挑战（选做）

- 在热力图旁增加样本量热力图；为空或低样本格子增加明确注释，不用 0 表示未知。
- 把 `day.csv` 的日期与工作日字段一对一验证后连接到完整小时需求表，检查连接前后行数和总量，再重画工作日曲线。
- 生成每个 `day_type` 的全部并列峰值，而不是只使用 `idxmax()` 返回的第一行。
- 整理一张“数据字典版本差异表”，记录季节标签和温度公式的两个来源、对分析的影响与后续处理建议，不覆盖旧产物。

## 13. 完成检查与交付

- [ ] 创建 `03_group_comparison.ipynb`，从清洗 CSV 独立读取并通过输入契约。
- [ ] 明确主分析只覆盖有记录小时，不把零需求缺行忽略为无关因素。
- [ ] 说明季节标签和温度公式的来源冲突，使用中性季节编码名。
- [ ] 完成 48 行工作日 × 小时汇总，验证行数计数与租赁总量守恒。
- [ ] 完成星期 × 小时需求矩阵及样本量矩阵。
- [ ] 完成年份 × 季节编码比较和天气样本量检查。
- [ ] 完成长表转换，验证组合键唯一、行数和总量关系。
- [ ] 正确计算用户租赁占比，并解释与小时占比平均值的差别。
- [ ] 完成补零前后的均值敏感性比较。
- [ ] 保存 5 张图、7 张汇总表，并完成 CSV 回读与图像目视检查。
- [ ] 每张图下都有观察、实际证据、限制和下一步。
- [ ] Notebook 重启内核后能够全部运行，无错误输出。
- [ ] 回答小测 10 题。

请提交 Notebook、`reports/lesson-03/` 中的图表与汇总表，以及小测第 2、4、6、7、8、9、10 题答案。

Review 重点：不是图是否漂亮，而是每个结论的观察单位、分母、样本量、来源和推断边界是否一致。第五周第四课将把这些分析整理成一份可复查的真实数据 EDA 报告，并为第六周建模准备问题定义和特征边界。
