# 第 5 周 · 第 2 课：系统化数据清洗与可追踪转换

预计用时：120–150 分钟

## 本课目标

完成本课后，你能够：

- 把数据清洗理解为有依据的业务决策，而不是一组机械 API。
- 区分字段缺失、记录缺失、无效值、重复记录和真实极端值。
- 使用显式映射把整数编码转换成可读类别，同时保留原始字段。
- 从官方数据字典恢复温度、湿度和风速的业务单位。
- 使用 `assign()`、`map()`、`astype()` 和函数组织可复现的转换管道。
- 为每一步记录输入、输出、行数变化、修改范围、理由和验证结果。
- 导出处理后的数据，并重新读取验证 schema 与关键不变量。
- 解释为什么本数据集不需要“为了清洗而删除异常值”。

## 0. 从数据审计进入数据清洗（10 分钟）

上一课已经得到几项关键证据：

- `hour.csv` 有 17,379 行、17 个字段，字段内部没有 `NaN`。
- 没有完整重复行，也没有重复的 `dteday + hr` 业务键。
- 17,379 行全部满足 `cnt == casual + registered`。
- 理论时间轴有 17,544 个小时，实际缺少 165 个小时。
- 小时表聚合后的每日租赁总量与 `day.csv` 完全一致。
- 现有小时记录的最小 `cnt` 为 1，因此缺失小时可以解释为零租赁小时。

这意味着本课不能套用“发现缺失值 → 用均值填充”“发现高值 → 删除异常值”的模板。正确策略取决于数据产生过程和分析目的。

本课原则：**每一次转换都必须回答三个问题：为什么改、改了什么、如何证明没有改错。**

## 1. 本课交付物与清洗边界（10 分钟）

建议创建：

```text
projects/week-05-bike-sharing/
├── data/
│   ├── raw/
│   │   └── hour.csv
│   └── processed/
│       └── hourly_clean.csv
└── notebooks/
    └── 02_data_cleaning.ipynb
```

本课生成一个“观察记录版”清洗表：

- 一行仍代表原始数据中的一个有租赁记录的小时。
- 不补造 165 行完整天气记录。
- 不删除高需求记录。
- 不覆盖 `data/raw/hour.csv`。
- 保留原始编码列，并新增可读标签和业务单位列。

为什么不直接补齐 165 行？我们有充分证据认为这些小时的租赁数为 0，但并不知道这些小时准确的温度、湿度、风速和天气类别。把相邻值或日均值填入，会把“推测”伪装成“观测”。如后续只分析完整需求时间轴，可以另建专用表，并把天气字段保持缺失。

## 2. 先写清洗策略表（15 分钟）

在写代码前，把审计结果转成决策：

| 问题 | 审计证据 | 本课策略 | 是否改变行数 |
| --- | --- | --- | ---: |
| 日期是字符串 | `dteday` 为 `object` | 严格解析为日期 | 否 |
| 小时时间戳不存在 | 日期与小时分列 | 新增 `timestamp` | 否 |
| 整数编码不可读 | `season` 等字段语义是类别 | 保留编码并新增标签 | 否 |
| 数值为归一化单位 | 官方说明提供恢复系数 | 新增业务单位列 | 否 |
| 列内缺失 | 总缺失数为 0 | 不填充 | 否 |
| 完整重复和业务键重复 | 数量均为 0 | 不删除 | 否 |
| 时间轴缺 165 小时 | 日表守恒且现有 `cnt >= 1` | 主清洗表不补行，单独记录 | 否 |
| `cnt` 高值 | 最大值 977，但契约成立 | 保留，视为真实候选极端 | 否 |
| 目标组成字段 | `cnt = casual + registered` | EDA 保留，建模特征排除 | 否 |

这张表就是轻量级的“变更设计”。它让 Review 者知道未执行某项常见清洗动作是有意决策，而不是遗漏。

## 3. 建立不可变输入基线（10 分钟）

在 Notebook 开头固定路径并读取原始数据：

```python
from pathlib import Path

import pandas as pd

RAW_PATH = Path("../data/raw/hour.csv")
PROCESSED_PATH = Path("../data/processed/hourly_clean.csv")

assert RAW_PATH.exists(), f"找不到原始文件: {RAW_PATH.resolve()}"

raw = pd.read_csv(RAW_PATH)
df = raw.copy()

baseline = {
    "rows": len(raw),
    "columns": raw.columns.tolist(),
    "duplicate_rows": int(raw.duplicated().sum()),
    "missing_cells": int(raw.isna().sum().sum()),
    "cnt_total": int(raw["cnt"].sum()),
}

baseline
```

不要把 `raw` 当作工作变量反复覆盖。`raw` 是本次执行中读取到的输入证据，`df` 才是转换中的工作副本。

Java / Spring Boot 对照：这类似于保留原始请求 DTO，再映射到领域对象；不要一边验证一边原地改写输入，使问题来源无法追踪。

## 4. 严格处理类型，而不是静默吞掉错误（15 分钟）

上一周练习中使用过：

```python
pd.to_datetime(series, errors="coerce")
```

`coerce` 适合审计未知质量的数据，因为无效值会变成 `NaT`，便于统计。但当前数据契约已经明确日期必须有效，清洗阶段可以使用严格转换：

```python
df["dteday"] = pd.to_datetime(
    df["dteday"],
    format="%Y-%m-%d",
    errors="raise",
)

df["timestamp"] = df["dteday"] + pd.to_timedelta(df["hr"], unit="h")
```

两种模式的区别：

| 模式 | 无效输入 | 适用场景 |
| --- | --- | --- |
| `errors="coerce"` | 转为 `NaT` / `NaN` | 初次审计、统计坏数据规模 |
| `errors="raise"` | 立即抛出异常 | 已有明确契约、正式转换 |

随后验证：

```python
assert df["dteday"].notna().all()
assert df["timestamp"].notna().all()
assert df["timestamp"].is_unique
assert df["timestamp"].is_monotonic_increasing
```

失败得早、失败得清楚，比输出一份部分损坏的 CSV 更安全。

## 5. 类别编码：保留原值，新增可读标签（25 分钟）

### 5.1 显式映射

根据官方 `Readme.txt` 定义映射：

```python
SEASON_LABELS = {
    1: "spring",
    2: "summer",
    3: "fall",
    4: "winter",
}

WEATHER_LABELS = {
    1: "clear_or_partly_cloudy",
    2: "mist_or_cloudy",
    3: "light_rain_or_snow",
    4: "heavy_rain_snow_or_fog",
}

WEEKDAY_LABELS = {
    0: "sunday",
    1: "monday",
    2: "tuesday",
    3: "wednesday",
    4: "thursday",
    5: "friday",
    6: "saturday",
}

df["season_label"] = df["season"].map(SEASON_LABELS)
df["weather_label"] = df["weathersit"].map(WEATHER_LABELS)
df["weekday_label"] = df["weekday"].map(WEEKDAY_LABELS)
```

这里选择“保留编码 + 新增标签”，原因是：

- 可以回查原始数据和官方字典。
- 便于验证映射是否一对一覆盖。
- EDA 图表使用标签更容易理解。
- 第六周建模时可以重新决定编码方式，而不是继承一次不可逆修改。

### 5.2 映射必须验证覆盖率

`Series.map()` 遇到字典中不存在的值会返回缺失值。不要把这个行为当成自动清洗：

```python
label_columns = ["season_label", "weather_label", "weekday_label"]

assert df[label_columns].notna().all().all()
```

如果断言失败，先找未知编码：

```python
known_weather_codes = set(WEATHER_LABELS)
unknown_weather_codes = set(df["weathersit"].unique()) - known_weather_codes
print(unknown_weather_codes)
```

不要写 `.fillna("unknown")` 后立即继续。`unknown` 可以是明确的业务类别，但也可能掩盖 schema 漂移或输入错误。

### 5.3 转成 Pandas 类别类型

```python
for column in label_columns:
    df[column] = df[column].astype("category")
```

`category` 表达的是分析语义，并可能节省重复字符串的内存。它不意味着类别之间自动存在数值距离。

## 6. 恢复业务单位，但不删除归一化列（15 分钟）

官方说明给出：

- `temp` 乘以 41，得到摄氏温度。
- `atemp` 乘以 50，得到摄氏体感温度。
- `hum` 乘以 100，得到湿度百分比。
- `windspeed` 乘以 67，得到速度数值；官方说明未明确单位，因此列名避免擅自写成 `km/h`。

```python
df = df.assign(
    temp_c=df["temp"] * 41,
    feels_like_c=df["atemp"] * 50,
    humidity_pct=df["hum"] * 100,
    windspeed_scaled=df["windspeed"] * 67,
)
```

验证恢复后的范围：

```python
assert df["temp_c"].between(0, 41).all()
assert df["feels_like_c"].between(0, 50).all()
assert df["humidity_pct"].between(0, 100).all()
assert df["windspeed_scaled"].between(0, 67).all()
```

这里没有覆盖原列，因为归一化列是官方发布的数据，后续复现和建模仍可能使用它们。新增列名应携带单位；无法确认单位时，应明确表达“已缩放”，不要自行猜测。

## 7. 缺失、重复和异常：三类问题，三种决策（20 分钟）

### 7.1 字段缺失：本数据不需要填充

```python
missing_by_column = df.isna().sum().sort_values(ascending=False)
assert missing_by_column.sum() == 0
```

因此不应为了展示 `fillna()` 而制造清洗步骤。API 不是课程目标，正确决策才是。

### 7.2 记录缺失：零需求已知，天气未知

构造完整小时索引只用于诊断：

```python
full_hours = pd.date_range(
    start=df["timestamp"].min(),
    end=df["timestamp"].max(),
    freq="h",
)

missing_hours = full_hours.difference(df["timestamp"])

assert len(full_hours) == 17_544
assert len(missing_hours) == 165
```

如果后续需要完整需求序列，可以建立一个独立视图：

```python
demand_timeline = (
    df.set_index("timestamp")[["casual", "registered", "cnt"]]
    .reindex(full_hours)
    .rename_axis("timestamp")
)

missing_record = demand_timeline["cnt"].isna()
demand_timeline["record_was_missing"] = missing_record
demand_timeline.loc[
    missing_record, ["casual", "registered", "cnt"]
] = 0
```

这个零填充只适用于已由日表守恒验证的三个计数字段。不能把同样逻辑扩展到天气字段。

### 7.3 重复：先定义重复，再决定删除

```python
assert df.duplicated().sum() == 0
assert df.duplicated(subset=["dteday", "hr"]).sum() == 0
```

如果未来真的出现重复，不要先执行 `drop_duplicates()`。先回答：

- 是文件重复导入，还是两条真实事件？
- 哪些列定义业务唯一性？
- 保留第一条、最后一条或聚合，依据是什么？
- 删除前后总租赁量变化多少？

### 7.4 高值：统计异常不等于脏数据

用 IQR 标记候选高值，但不删除：

```python
q1 = df["cnt"].quantile(0.25)
q3 = df["cnt"].quantile(0.75)
iqr = q3 - q1
upper_bound = q3 + 1.5 * iqr

df["cnt_iqr_high"] = df["cnt"] > upper_bound

df.loc[
    df["cnt_iqr_high"],
    ["timestamp", "workingday", "hr", "cnt"],
].head()
```

共享单车需求具有早晚高峰、季节变化和年份增长。全局 IQR 会把许多真实高峰标为候选异常。标记适合后续分析；删除需要额外的业务错误证据。

## 8. 把转换封装成纯函数（20 分钟）

把散落的 Notebook 操作收拢成一个输入明确、返回新表的函数：

```python
def clean_hourly_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    cleaned = raw_df.copy()

    cleaned["dteday"] = pd.to_datetime(
        cleaned["dteday"],
        format="%Y-%m-%d",
        errors="raise",
    )
    cleaned["timestamp"] = cleaned["dteday"] + pd.to_timedelta(
        cleaned["hr"], unit="h"
    )

    cleaned["season_label"] = cleaned["season"].map(SEASON_LABELS)
    cleaned["weather_label"] = cleaned["weathersit"].map(WEATHER_LABELS)
    cleaned["weekday_label"] = cleaned["weekday"].map(WEEKDAY_LABELS)

    label_columns = ["season_label", "weather_label", "weekday_label"]
    if cleaned[label_columns].isna().any().any():
        raise ValueError("发现无法映射的类别编码")

    for column in label_columns:
        cleaned[column] = cleaned[column].astype("category")

    cleaned = cleaned.assign(
        temp_c=cleaned["temp"] * 41,
        feels_like_c=cleaned["atemp"] * 50,
        humidity_pct=cleaned["hum"] * 100,
        windspeed_scaled=cleaned["windspeed"] * 67,
    )

    return cleaned
```

验证函数不会修改调用者的输入：

```python
raw_again = pd.read_csv(RAW_PATH)
cleaned = clean_hourly_data(raw_again)

assert "timestamp" not in raw_again.columns
assert "timestamp" in cleaned.columns
assert len(cleaned) == len(raw_again)
```

这里的“纯”是工程上的近似表达：相同 DataFrame 输入得到相同结果，函数内部不读写文件，也不修改传入对象。文件 I/O 放在函数外，测试会更容易。

## 9. 建立转换日志和质量闸口（20 分钟）

### 9.1 转换摘要

```python
transformation_log = pd.DataFrame(
    [
        {
            "step": "parse_date_and_build_timestamp",
            "reason": "建立严格的小时级时间键",
            "rows_before": len(raw),
            "rows_after": len(cleaned),
            "affected_rows": len(cleaned),
        },
        {
            "step": "add_category_labels",
            "reason": "让整数编码具备可读业务语义",
            "rows_before": len(cleaned),
            "rows_after": len(cleaned),
            "affected_rows": len(cleaned),
        },
        {
            "step": "restore_business_scales",
            "reason": "依据官方公式恢复解释尺度",
            "rows_before": len(cleaned),
            "rows_after": len(cleaned),
            "affected_rows": len(cleaned),
        },
    ]
)

transformation_log
```

`affected_rows` 不总等于“被纠正的错误行”。新增派生列时，全部行都参与转换。字段命名要让读者知道指标含义。

### 9.2 清洗后不变量

```python
EXPECTED_ROW_COUNT = 17_379

assert len(cleaned) == EXPECTED_ROW_COUNT
assert cleaned["instant"].is_unique
assert cleaned["timestamp"].is_unique
assert cleaned["cnt"].eq(
    cleaned["casual"] + cleaned["registered"]
).all()
assert int(cleaned["cnt"].sum()) == baseline["cnt_total"]
assert cleaned[label_columns].notna().all().all()
assert cleaned["cnt"].ge(0).all()
```

这些检查分别保护：

- 行数没有意外变化。
- 标识符和业务时间键仍唯一。
- 跨字段关系没有被破坏。
- 总租赁量守恒。
- 类别映射完整。
- 计数保持非负。

数据清洗的质量不能只用“代码执行无异常”来证明。

## 10. 导出、重新读取与验证（15 分钟）

CSV 不保存 Pandas 的类别 dtype，日期也可能在重新读取后恢复为字符串。因此导出成功不等于产物可用：

```python
PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
cleaned.to_csv(PROCESSED_PATH, index=False)

reloaded = pd.read_csv(
    PROCESSED_PATH,
    parse_dates=["dteday", "timestamp"],
)

assert len(reloaded) == len(cleaned)
assert reloaded["timestamp"].is_unique
assert reloaded["cnt"].eq(
    reloaded["casual"] + reloaded["registered"]
).all()
assert int(reloaded["cnt"].sum()) == baseline["cnt_total"]
```

再检查：

```python
print(PROCESSED_PATH.resolve())
print(PROCESSED_PATH.stat().st_size)
reloaded.info()
reloaded.head(3).T
```

如果需要保留更丰富的类型信息，后续可以学习 Parquet；本课继续使用 CSV，重点是理解序列化边界。

## 11. Java / Spring Boot 对照

| Java / Spring Boot | Pandas 清洗流程 |
| --- | --- |
| 原始请求 DTO | `raw` DataFrame |
| DTO → 领域对象 mapper | `clean_hourly_data()` |
| enum code → enum label | `Series.map()` + `category` |
| Bean Validation | 范围、唯一性、关系断言 |
| service 不修改输入对象 | `raw_df.copy()` |
| 审计日志 | `transformation_log` |
| repository 写入后回读测试 | CSV 导出后重新读取验证 |
| 数据库 migration | schema 变化需要显式记录 |

重要差异：应用接口经常拒绝非法输入；离线数据管道通常还要统计问题规模、保留原始证据，并允许对异常做隔离分析。

## 12. 课堂练习

### 练习 1：选择处理策略

为以下情况选择“修正、填充、删除、标记、保留或阻断流程”，并说明证据：

1. `season` 出现编码 5。
2. 某行 `cnt` 为 900，但字段关系成立。
3. 两行具有相同 `dteday + hr`，其他值不同。
4. 时间轴少一小时，日表总量证明该小时租赁数为 0。
5. 某行 `temp` 缺失，且没有其他来源可以恢复。

### 练习 2：故意破坏映射

```python
broken = raw.head(3).copy()
broken.loc[broken.index[0], "season"] = 5
```

运行 `clean_hourly_data(broken)`，让函数以明确错误终止。改进错误消息，使其输出未知字段名和未知编码。

### 练习 3：验证输入未被修改

调用清洗函数前保存：

```python
before_columns = raw.columns.tolist()
```

调用后验证原表列、行数和 `cnt` 总量均未变化。

### 练习 4：建立完整需求时间轴

创建 `demand_timeline`，验证：

- 行数为 17,544。
- `record_was_missing` 为真的行数为 165。
- 三个计数字段补零后没有缺失。
- 补零后的日汇总仍与 `day.csv` 一致。

解释为什么不能同时给天气字段补零。

### 练习 5：导出回读

导出 `hourly_clean.csv` 后重新读取，比较：

- 行数与列数。
- 日期列 dtype。
- 标签列 dtype。
- 总租赁量。
- 业务键唯一性。

说明为什么内存中的 dtype 与 CSV 回读结果不一定相同。

## 13. 小测（10 题）

1. 数据审计与数据清洗分别解决什么问题？
2. 为什么本数据集字段内部没有 `NaN`，仍然存在时间记录缺失？
3. 为什么不能把缺失小时的天气字段全部填 0？
4. 为什么类别映射后必须检查新标签是否缺失？
5. `errors="coerce"` 与 `errors="raise"` 各适合什么阶段？
6. 为什么本课保留原始类别编码列？
7. IQR 判定为高值是否足以支持删除记录？为什么？
8. 为什么清洗函数内部先调用 `copy()`？
9. 为什么 CSV 导出后必须重新读取验证？
10. 哪些不变量可以证明清洗没有改变租赁事实？至少列出三项。

## 14. 进阶挑战（选做）

### 挑战 1：生成机器可读质量报告

生成一行汇总表并导出为 `data/processed/cleaning_report.csv`：

| input_rows | output_rows | missing_cells | duplicate_keys | unmapped_labels | cnt_total_before | cnt_total_after |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |

确保其中所有值由代码计算，而不是手工填写。

### 挑战 2：改进未知编码错误

编写辅助函数：

```python
def map_required(
    series: pd.Series,
    mapping: dict[int, str],
    field_name: str,
) -> pd.Series:
    ...
```

当出现未知编码时，抛出类似消息：

```text
season 存在未知编码: [5]
```

### 挑战 3：记录文件校验和

使用标准库 `hashlib` 计算原始 CSV 和处理后 CSV 的 SHA-256。解释为什么校验和可以识别文件内容变化，但不能证明数据业务含义正确。

## 15. 完成检查

- [ ] 已创建 `02_data_cleaning.ipynb`。
- [ ] 已保留独立的 `raw` 输入基线和工作副本。
- [ ] 已用严格格式解析 `dteday` 并创建唯一 `timestamp`。
- [ ] 已保留类别编码并新增季节、天气和星期标签。
- [ ] 已验证所有类别编码都成功映射。
- [ ] 已依据官方公式新增温度、体感温度、湿度和风速缩放列。
- [ ] 已说明主清洗表为什么不补齐 165 个小时。
- [ ] 已说明高需求记录为什么只标记、不删除。
- [ ] 已把核心转换封装为不修改输入的函数。
- [ ] 已记录转换步骤、理由、前后行数和影响范围。
- [ ] 已验证行数、键唯一性、关系契约和总租赁量守恒。
- [ ] 已导出 `hourly_clean.csv` 并完成回读验证。
- [ ] 已回答小测 10 题。

## 16. 下课前交付

请提交：

1. `projects/week-05-bike-sharing/notebooks/02_data_cleaning.ipynb`。
2. `projects/week-05-bike-sharing/data/processed/hourly_clean.csv`。
3. 一张清洗策略表和一张转换日志表。
4. 清洗函数 `clean_hourly_data()`。
5. 导出前与回读后的质量闸口结果。
6. 小测第 2、3、4、5、7、9、10 题答案。

我会重点 Review：

- 每项处理是否有审计证据，而不是套用通用模板。
- 是否区分字段缺失、记录缺失和真实的零需求。
- 是否保留原始数据与原始编码，避免不可逆修改。
- 是否对类别映射和单位恢复使用官方定义。
- 是否把统计异常误判为错误数据。
- 转换函数是否输入明确、不修改调用者对象。
- 是否使用行数、总量和跨字段关系验证转换守恒。
- 导出的产物能否从头读取并通过相同契约。

下一课将在这份可追踪的清洗数据上进行分组比较和可视化，重点分析小时、工作日、季节、天气和用户类型之间的需求模式，同时始终展示样本量并控制结论边界。
