# 第 5 周 · 第 4 课：真实数据 EDA 报告与建模准备

预计用时：180–210 分钟（正文约 155 分钟，练习与小测另计）

## 本课定位

第一课核验来源与契约，第二课建立可追踪转换，第三课学习分组比较。本课将它们组织成一份别人能够复查、能够复现、不会误读的报告，并为第六周的回归建模准备问题定义、特征边界和评估基线。

这是提前生成的讲义，不代表第三课或本课已经完成。完整报告需要第三课的图表与解释；下面的代码可以从第二课清洗 CSV 独立运行，不依赖第三课 Notebook 的内存状态。

本课不训练复杂模型，不追求最高分，也不把探索性关联包装成因果结论。

## 本课目标

- 将探索过程整理为“问题—证据—限制—行动”的报告。
- 区分面向读者的管理摘要与面向复现者的技术附录。
- 使用程序生成关键数字，避免手工复制造成口径漂移。
- 用敏感性检查判断结论是否依赖缺失小时或异常值处理。
- 根据预测时点识别目标泄漏和不可获得的特征。
- 按时间构造训练、验证和测试预留段，理解历史探索带来的限制。
- 以训练期统计量建立简单基线，在验证期计算 MAE。
- 记录文件校验和、运行环境、验证结果和待解决问题。

## 0. 先确定交付对象和文件结构（10 分钟）

假设报告面向一个希望理解共享单车需求模式的运营团队。读者首先想知道：发现了什么、证据有多强、可以做什么、不能做什么。

建议创建：

```text
projects/week-05-bike-sharing/
├── notebooks/
│   └── 04_eda_report.ipynb
└── reports/
    ├── lesson-03/              # 第三课导出的图表与汇总表
    └── lesson-04/
        ├── eda_report.md      # 自己撰写的面向读者的报告
        ├── evidence.csv
        ├── sensitivity.csv
        ├── split_manifest.csv
        ├── validation_baselines.csv
        └── provenance.json
```

本课示例都写在 `04_eda_report.ipynb` 中，从 `notebooks/` 目录运行。报告 Markdown 由你根据实际结果撰写；代码只生成支撑它的证据文件，不自动替你下结论。

报告建议按以下顺序组织：

1. 管理摘要：三条主要发现、两条重要限制、一项下一步建议。
2. 问题与数据范围：数据来源、时间、观察单位和适用范围。
3. 数据质量与转换：保留什么、修改什么、为什么。
4. 主要发现：精选第三课的图，而不是堆放全部输出。
5. 敏感性与限制：换口径后哪些结论仍成立。
6. 建模准备：预测时点、候选特征、时间切分和基线。
7. 技术附录：文件清单、环境、契约和复现步骤。

## 1. 独立读取，并建立报告输入契约（15 分钟）

```python
import hashlib
import json
import platform
from pathlib import Path

import pandas as pd

INPUT_PATH = Path("../data/processed/hourly_clean.csv")
RAW_DAY_PATH = Path("../data/raw/day.csv")
OUTPUT_DIR = Path("../reports/lesson-04")

assert INPUT_PATH.exists(), INPUT_PATH.resolve()
assert RAW_DAY_PATH.exists(), RAW_DAY_PATH.resolve()

df = pd.read_csv(INPUT_PATH, parse_dates=["dteday", "timestamp"])
day = pd.read_csv(RAW_DAY_PATH, parse_dates=["dteday"])
count_columns = ["casual", "registered", "cnt"]

assert df.shape == (17_379, 26)
assert df["timestamp"].notna().all()
assert df["timestamp"].is_unique
assert df["timestamp"].is_monotonic_increasing
assert df["cnt"].gt(0).all()
assert df["cnt"].eq(df["casual"] + df["registered"]).all()
assert int(df["cnt"].sum()) == 3_292_679
assert df[["dteday", "hr", "workingday"] + count_columns].notna().all().all()
assert len(day) == 731
assert day["dteday"].notna().all()
assert day["dteday"].is_unique
```

不要重新读取原始数据后偷偷绕过第二课的清洗产物，也不要依赖其他 Notebook 已经定义的变量。

### 1.1 报告中必须保留的来源限制

- 主清洗表仅含有记录的小时，少于完整的 17,544 个日历小时。
- 天气类别 4 只有 3 条记录，不能据此概括一般规律。
- 505 条 IQR 高值候选保留在主表中，统计高值不是删除依据。
- 季节标签和温度恢复公式存在数据字典版本差异。延续第三课的处理：季节比较展示原始编码，不用旧 `season_label` 下自然季节结论；不把旧 `temp_c`、`feels_like_c` 当作已经核验的物理温度。
- 数据只覆盖特定系统的 2011–2012 年，不能直接推广到其他城市或今天的需求。

来源差异详见 [第三课讲义](lesson-03.md) 和 [UCI 数据说明](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset)。本课不覆盖历史产物；若修正映射或恢复公式，应重新生成版本化产物并记录依据。

## 2. 用代码生成证据，而不是手工填写数字（20 分钟）

### 2.1 从原始粒度重新汇总关键发现

```python
hour_day = df.groupby(["workingday", "hr"], as_index=False).agg(
    sample_count=("cnt", "size"),
    median_rentals=("cnt", "median"),
    mean_rentals=("cnt", "mean"),
)
assert len(hour_day) == 48
assert hour_day["sample_count"].sum() == len(df)

group_max = hour_day.groupby("workingday")["median_rentals"].transform("max")
peaks = hour_day.loc[hour_day["median_rentals"].eq(group_max)].copy()
peaks
```

与 `idxmax()` 只返回首个峰值不同，这里通过 `transform("max")` 把每组最大值对齐回每一行，因此保留所有并列峰值。

注意：这是比较 24 个钟点的中位数后得到的峰值，不是找整张表最大的某个小时。

```python
high = df["cnt_iqr_high"]
assert high.dtype == bool
high_count = int(high.sum())
assert high_count == 505
commute_high_count = int((high & df["hr"].isin([8, 17, 18])).sum())
weather_counts = df.groupby("weathersit").size()

evidence = pd.DataFrame([
    {"metric": "recorded_hours", "value": len(df), "unit": "rows",
     "scope": "observed hourly table"},
    {"metric": "total_rentals", "value": int(df["cnt"].sum()), "unit": "rentals",
     "scope": "2011-2012 recorded hours"},
    {"metric": "weather_code_4_count", "value": int(weather_counts.loc[4]), "unit": "rows",
     "scope": "observed hourly table"},
    {"metric": "iqr_high_count", "value": high_count, "unit": "rows",
     "scope": "cnt > 642.5, EDA flag only"},
    {"metric": "commute_hour_share_of_high", "value": commute_high_count / high_count,
     "unit": "fraction", "scope": "share among high-demand candidates"},
])
evidence
```

`scope` 是指标口径，`unit` 是单位。比例的分母不能藏起来：这里约 81% 的分母是 505 条高值候选，不是全部 17,379 条记录，更不是全部租赁次数。

### 2.2 把图转换成可审查的结论

为第三课至少三张图补齐下面四项：

| 项目 | 写作要求 |
| --- | --- |
| 观察 | 图表直接显示了什么？ |
| 证据 | 指标、具体数值、样本量、分组口径分别是什么？ |
| 限制 | 还有哪些解释？遗漏了什么数据？ |
| 下一步 | 哪项进一步检查能缩小不确定性？ |

可以写：“工作日中位需求的峰值出现在某钟点，该组中位数为某值，样本量为某值。”数值从 `peaks` 读取。

不能写：“我们已经证明所有用户都是通勤者。”数据没有个人出行目的字段。

管理摘要中保留业务语言，`groupby`、类型转换和完整校验代码放到技术附录。

## 3. 敏感性检查：处理策略是否改变结论（20 分钟）

### 3.1 先重新验证缺失小时补零的依据

```python
hour_daily = df.groupby("dteday", as_index=False)[count_columns].sum()
daily_check = hour_daily.merge(
    day[["dteday"] + count_columns],
    on="dteday", how="outer", validate="one_to_one",
    suffixes=("_hour", "_day"), indicator=True,
)
assert daily_check["_merge"].eq("both").all()
for column in count_columns:
    assert daily_check[f"{column}_hour"].eq(daily_check[f"{column}_day"]).all()

full_hours = pd.date_range(df["timestamp"].min(), df["timestamp"].max(), freq="h")
timeline = df.set_index("timestamp")[["cnt"]].reindex(full_hours)
assert len(timeline) == 17_544
assert timeline["cnt"].isna().sum() == 165
timeline["cnt"] = timeline["cnt"].fillna(0).astype("int64")
assert timeline["cnt"].sum() == df["cnt"].sum()
```

`outer` 加连接指示列可以发现某侧缺少的日期；只做 `inner` 连接可能把不匹配日期悄悄丢掉。`validate="one_to_one"` 则检查连接键基数，防止重复键把行数放大。[Pandas merge 文档](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html)

补零结论依赖日表与小时表覆盖相同的租赁总量；它不能解释记录缺失的机制，也不提供缺失小时的天气。

### 3.2 比较三种口径

```python
sensitivity = pd.DataFrame([
    {"scenario": "recorded_hours", "rows": len(df),
     "total_rentals": df["cnt"].sum(), "mean_rentals": df["cnt"].mean()},
    {"scenario": "all_calendar_hours", "rows": len(timeline),
     "total_rentals": timeline["cnt"].sum(), "mean_rentals": timeline["cnt"].mean()},
    {"scenario": "drop_high_COUNTERFACTUAL", "rows": int((~high).sum()),
     "total_rentals": df.loc[~high, "cnt"].sum(),
     "mean_rentals": df.loc[~high, "cnt"].mean()},
])
sensitivity
```

第三行只是“假如删除高值”的对照实验，不修改主表、不生成删减版建模数据。

请说明：

- 补零为什么不改变总量，却改变均值？
- 删除高值为什么同时改变记录数和租赁总量？
- 全局均值变化不大，能否证明凌晨需求曲线也不受影响？不能，局部影响需要按小时检查。

敏感性分析不是为了挑一个更好看的结果，而是公开结论依赖哪些选择。

## 4. 为第六周写一份预测问题契约（15 分钟）

先用文字定义问题，不调用模型：

> 在目标小时开始前，利用已知的日历信息，估计该小时的租赁总数 `cnt`。本次课程先用已发布的有记录小时表做回顾性基准实验；它不代表可部署的全日历小时预测系统。

必须解释最后一句：真实预测时不知道未来哪个小时会有租赁。当前数据遗漏零需求小时，评估样本的选择依赖结果是否有记录。因此该基准的误差不等于完整时间轴上的误差；部署前应明确零需求小时处理、可用特征和完整日历评估方案。

| 项目 | 本课约定 |
| --- | --- |
| 预测单位 | 一个小时，不是单次骑行或单个用户 |
| 预测目标 | `cnt` 租赁次数 |
| 预测时点 | 目标小时开始前 |
| 首轮输入 | 小时、月份、星期、工作日、节假日、年份编码 |
| 学习用途 | 回顾性方法练习，不宣称独立上线评估 |
| 主要指标 | 验证期 MAE，单位为租赁次数/小时 |
| 禁止做法 | 用目标组成部分、目标派生标记或未来统计量当输入 |

## 5. 特征可用性审查：在预测时点是否拿得到（15 分钟）

| 字段 | 首轮处理 | 原因 |
| --- | --- | --- |
| `hr`、`mnth`、`weekday` | 候选 | 目标小时的日历信息可提前确定；不是都适合直接当线性连续值 |
| `holiday`、`workingday` | 候选 | 假设已有正确且提前发布的本地节假日日历 |
| `yr` | 候选 | 年份已知，但仅有两年数据，外推能力有限 |
| `instant` | 排除 | 数据集记录编号，不是稳定业务特征 |
| `dteday`、`timestamp` | 用于排序与派生日历 | 暂不作为原始字符串特征 |
| `casual`、`registered` | 排除 | 相加就是目标答案 |
| `cnt_iqr_high` | 排除 | 直接从当前小时的 `cnt` 派生；即使重算阈值也会泄漏 |
| `temp`、`atemp`、`hum`、`windspeed`、`weathersit` | 首轮排除 | 是实际天气，目标小时开始前未必可获得；不能假装成天气预报 |
| `temp_c`、`feels_like_c` | 排除 | 还存在恢复公式来源差异 |
| `season_label` | 不使用 | 季节标签来源冲突，日历月份已能提供部分季节信息 |

EDA 可以使用目标及其组成部分解释数据，建模输入则必须遵守预测时点边界。不是“数值型列都能喂给模型”。

```python
feature_columns = ["hr", "mnth", "weekday", "holiday", "workingday", "yr"]
forbidden = {"cnt", "casual", "registered", "cnt_iqr_high", "instant"}
assert forbidden.isdisjoint(feature_columns)
assert df[feature_columns].notna().all().all()
```

后续的缺失填充统计量、标准化参数、类别频次、目标编码等，必须只从训练数据学习，再用于验证和测试。固定的日历映射不同于从全量目标数据计算均值。[scikit-learn 数据泄漏说明](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage)

## 6. 时间切分与历史探索的限制（15 分钟）

本课采用固定日历边界，不根据哪个切分得分更好来选择日期：

- 训练：2011 年。
- 验证：2012 年 1–6 月，用于练习比较方案。
- 测试预留：2012 年 7–12 月，本课不计算测试指标。

```python
train_end = pd.Timestamp("2012-01-01")
validation_end = pd.Timestamp("2012-07-01")

train = df.loc[df["timestamp"] < train_end].copy()
validation = df.loc[
    (df["timestamp"] >= train_end) & (df["timestamp"] < validation_end)
].copy()
test = df.loc[df["timestamp"] >= validation_end].copy()

assert min(len(train), len(validation), len(test)) > 0
assert len(train) + len(validation) + len(test) == len(df)
assert train["timestamp"].max() < validation["timestamp"].min()
assert validation["timestamp"].max() < test["timestamp"].min()

split_manifest = pd.DataFrame([
    {"split": name, "rows": len(part),
     "start": part["timestamp"].min(), "end": part["timestamp"].max()}
    for name, part in [("train", train), ("validation", validation), ("test_reserved", test)]
])
split_manifest
```

关键限制：前几课已经探索过 2011–2012 年全部数据，所以最后一段不是“从未看过”的独立测试集。现在不再查看测试指标能约束接下来的选择，但不能抹去已有探索。正式研究应预先留出未探索数据，或增加新的未来数据做最终验证。

验证期与测试期覆盖不同季节，因此两期误差差异也可能来自季节构成；不能只归因为模型退化。后续可以学习滚动时间验证，但本课先掌握固定时间边界。

## 7. 用简单基线建立比较标准（20 分钟）

一个复杂模型只有超过合理基线，才值得讨论。先比较两个不用机器学习框架的规则：

- 常数基线：总是预测训练期 `cnt` 的中位数。
- 分组基线：预测训练期“工作日状态 × 小时”的中位数；没有该组则回退到训练期总体中位数。

中位数是绝对误差下合理的常数预测，不意味着任何任务都必须用它。

```python
global_median = train["cnt"].median()
lookup = train.groupby(["workingday", "hr"], as_index=False).agg(
    predicted_rentals=("cnt", "median"),
)
assert not lookup.duplicated(["workingday", "hr"]).any()

validation_predictions = validation[["timestamp", "workingday", "hr", "cnt"]].merge(
    lookup, on=["workingday", "hr"], how="left", validate="many_to_one",
)
assert len(validation_predictions) == len(validation)
assert validation_predictions["timestamp"].is_unique

fallback_count = int(validation_predictions["predicted_rentals"].isna().sum())
validation_predictions["predicted_rentals"] = (
    validation_predictions["predicted_rentals"].fillna(global_median)
)

constant_mae = (validation_predictions["cnt"] - global_median).abs().mean()
grouped_mae = (
    validation_predictions["cnt"] - validation_predictions["predicted_rentals"]
).abs().mean()

validation_baselines = pd.DataFrame([
    {"baseline": "training_global_median", "validation_mae": constant_mae,
     "evaluated_rows": len(validation_predictions)},
    {"baseline": "training_workday_hour_median", "validation_mae": grouped_mae,
     "evaluated_rows": len(validation_predictions)},
])
assert validation_baselines["validation_mae"].notna().all()
assert validation_baselines["validation_mae"].ge(0).all()
print("分组缺失回退行数:", fallback_count)
validation_baselines
```

MAE 的计算是“每行预测与实际值相减 → 取绝对值 → 求平均”。例如实际 `[10, 20]`、预测 `[8, 25]`，MAE 为 `(2 + 5) / 2 = 3.5`。它不是百分比，也不是准确率。[MAE 官方定义](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html)

不要提前写“分组基线一定更好”，以实际输出为准。也不要把第三课用全量数据计算的分组中位数当作预测表：那样验证期的答案已经参与了规则生成。

即使指标改善，也只说明该验证段上规则表现不同，不说明对所有未来年份都有效。MAE 也不能直接表达缺车成本与空置成本的不对称；业务指标需要另行定义。

## 8. 记录来源并导出报告资产（15 分钟）

```python
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

provenance = {
    "dataset": "UCI Bike Sharing Dataset",
    "source_url": "https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset",
    "input_file": INPUT_PATH.name,
    "input_sha256": sha256_file(INPUT_PATH),
    "daily_reference_file": RAW_DAY_PATH.name,
    "daily_reference_sha256": sha256_file(RAW_DAY_PATH),
    "input_rows": len(df),
    "python_version": platform.python_version(),
    "pandas_version": pd.__version__,
    "scope": "recorded hourly rows; retrospective educational analysis",
    "validation_start": str(train_end.date()),
    "test_reserved_start": str(validation_end.date()),
    "test_previously_explored": True,
    "weather_at_prediction_time": "excluded in first baseline",
    "dictionary_conflict": "season labels and temperature formulas; see lesson-03",
}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
tables = {
    "evidence": evidence,
    "sensitivity": sensitivity,
    "split_manifest": split_manifest,
    "validation_baselines": validation_baselines,
}
for name, table in tables.items():
    table.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)

with (OUTPUT_DIR / "provenance.json").open("w", encoding="utf-8") as stream:
    json.dump(provenance, stream, ensure_ascii=False, indent=2)

with (OUTPUT_DIR / "provenance.json").open(encoding="utf-8") as stream:
    saved_provenance = json.load(stream)
assert saved_provenance["input_sha256"] == sha256_file(INPUT_PATH)
saved_splits = pd.read_csv(OUTPUT_DIR / "split_manifest.csv")
assert saved_splits["rows"].sum() == len(df)
saved_baselines = pd.read_csv(OUTPUT_DIR / "validation_baselines.csv")
assert saved_baselines["evaluated_rows"].eq(len(validation)).all()
print("报告资产已导出并通过回读检查")
```

此代码只覆盖本课专用目录中的同名资产，不改动输入 CSV。校验和可以识别内容是否改变，但不能证明业务定义正确。

### 8.1 撰写 `eda_report.md`

使用第 0 节的报告结构，用实际输出填入数字。插入第三课图片时，报告中的相对路径示例为：

```markdown
![工作日与非工作日小时需求](../lesson-03/hour_by_day_type.png)
```

确保第三课已经生成该文件；不要插入不存在的图片。最终报告至少包含：

- 工作日与非工作日曲线及样本量说明。
- 天气类别比较，明确类别 4 只有 3 条记录。
- 用户类型模式或星期 × 小时图，配实际证据。
- 补零和删除高值对指标的影响。
- 建模输入排除清单、时间切分和验证基线结果。

重启 Notebook 内核并运行全部单元格，再打开 Markdown 检查图片、表格和相对链接。不要将“代码无报错”当成“报告结论一定正确”。

## 9. 课堂练习

1. 把“天气越差租车越少，所以坏天气导致人们不骑车”改成不越过证据边界的表述。
2. 从 `peaks` 中报告所有并列峰值，解释为什么它与 `idxmax()` 的结果可能不同。
3. 比较完整时间轴和有记录小时在凌晨 3 点的均值，说明全局差异为什么不能代表局部差异。
4. 给分组查找表构造一个训练期未出现的组合，验证预测回退到训练期总体中位数，而不是使用验证期统计量。
5. 给管理摘要写一段不超过 200 字的草稿：至少一项实际数字、一条限制和一个可执行的下一步。

## 10. 小测（10 题）

1. 管理摘要与技术附录分别面向谁，应该保留哪些内容？
2. 为什么报告中的比例必须说明分母？
3. 为什么删除 IQR 高值可能损害共享单车需求分析？
4. 缺失小时计数补零的证据是什么，它不能证明什么？
5. 为什么 `cnt_iqr_high` 不适合作为预测 `cnt` 的输入？
6. 实际天气和提前可获得的天气预报有何区别？
7. 为什么分组预测基线的中位数只能从训练期计算？
8. 验证集与测试预留段各有什么用途？此前已探索的测试段有什么限制？
9. MAE 的单位是什么，为什么不是准确率或百分比？
10. SHA-256 相同能够证明什么，又不能证明什么？

## 11. 进阶挑战（选做）

- 将验证期误差按小时与工作日分组，附上每组样本量，检查平均误差是否掩盖高峰期问题；仍不查看测试指标。
- 为输入文件和第三课图表生成一个完整资产清单，识别旧图配新数据的风险。
- 设计未来“完整日历小时预测”需要的数据契约：补全日历、未知天气、零需求、发布时间、训练与评估范围。
- 给报告每条结论分配证据编号，建立“结论 → 汇总表 → 输入文件校验和”的追踪关系。

## 12. 第五周交付与验收

- [ ] `04_eda_report.ipynb` 从头运行成功，不依赖其他 Notebook 的变量。
- [ ] 原始文件与第二课清洗产物未被覆盖。
- [ ] 关键数字由代码生成，并有单位、分母与范围说明。
- [ ] 报告含至少三张有效图及观察、证据、限制、下一步。
- [ ] 已公开记录数据字典冲突、零需求缺行和小样本问题。
- [ ] 完成日表守恒和敏感性检查，没有把对照删减作为正式数据清洗。
- [ ] 预测问题明确了目标、时点、输入和评估样本范围。
- [ ] 特征清单排除了目标组成部分、目标派生标记与不可提前获得的实际天气。
- [ ] 时间段无重叠，训练期早于验证期，验证期早于测试预留段。
- [ ] 基线仅从训练期学习，只报告验证期 MAE。
- [ ] 明确此前全量探索对测试独立性的影响。
- [ ] 4 张证据 CSV 与来源 JSON 导出、回读检查通过。
- [ ] `eda_report.md` 的管理摘要、图表和技术附录相互一致。
- [ ] 小测完成；尚未完成的前课学习与小测单独列为待办。

请提交本课 Notebook、报告目录以及小测第 3、4、5、6、7、8、9 题答案。

第五周的目标不是“做出很多图”，而是能够对一份真实数据说明：它是什么、有哪些问题、做了哪些转换、支持哪些结论、不能回答什么，以及下一步怎样建立可信的预测实验。

第六周将在这些约定上学习监督学习、回归模型和评估流程；先让简单基线和输入边界可信，再讨论模型复杂度。
