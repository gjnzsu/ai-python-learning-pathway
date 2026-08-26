# 第 5 周 · 第 1 课：真实公开数据集、数据来源与数据契约

预计用时：120–150 分钟

## 本课目标

完成本课后，你能够：

- 从官方说明判断一份公开数据是否适合当前分析问题。
- 区分数据来源、采集对象、观察单位、时间范围和字段含义。
- 下载并以可复现方式保存原始数据，不在 Notebook 中依赖临时网络状态。
- 使用 Pandas 完成第一轮结构审计，而不是急于填补或删除数据。
- 为字段建立数据契约，检查唯一性、取值范围、字段关系和时间连续性。
- 识别编码类别、归一化字段、派生字段和潜在目标泄漏。
- 提出可以由数据回答的问题，并明确数据不能回答什么。

## 0. 从合成日志进入真实数据（10 分钟）

第四周已经建立了完整的 EDA 基础：

- 检查类型、缺失、重复和样本量。
- 使用均值、中位数、分位数和 IQR 描述分布。
- 使用比较图、分布图、趋势图和关系图回答问题。
- 用“结论 + 证据 + 限制 + 下一步”表达分析结果。

但上一周的数据由我们自己生成，字段含义、生成规则和异常来源都已知。真实数据多了一层更重要的工作：先理解数据是怎样产生的。

一个数值即使能被 Pandas 正确读取，也可能被错误解释。例如：

- `season == 1` 是冬季编码，不是可连续计算的“季节强度”。
- `temp == 0.5` 是归一化温度，不是 0.5 摄氏度。
- `cnt` 是总租赁量，而且按定义等于 `casual + registered`。
- 一行可能代表“一小时”，也可能代表“一天”；混淆粒度会改变所有结论。

本课原则：**先建立语义契约，再开始清洗。**

## 1. 本周项目：共享单车需求分析

本周使用 UCI Machine Learning Repository 的 Bike Sharing Dataset。

官方页面：

- [UCI Bike Sharing Dataset](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset)

数据记录了 2011–2012 年 Capital Bikeshare 的共享单车租赁数量，并附带天气和季节信息。压缩包中最重要的文件是：

| 文件 | 一行代表什么 | 是否有小时字段 | 适合的问题 |
| --- | --- | --- | --- |
| `hour.csv` | 某一天的某一个小时 | 有 `hr` | 小时模式、通勤高峰、后续预测 |
| `day.csv` | 一个自然日 | 无 `hr` | 日级趋势、长期变化、较粗粒度报告 |

本周默认以 `hour.csv` 为事实表。`day.csv` 暂时只用于验证跨粒度汇总，不把两个文件直接纵向拼接。

### 1.1 为什么选择它

它适合当前学习阶段，因为同时包含：

- 时间字段：日期、小时、月份、星期。
- 类别字段：季节、天气状况、是否工作日。
- 连续字段：温度、体感温度、湿度、风速。
- 计数字段：临时用户、注册用户和总租赁量。
- 真实世界中的周期性、极端天气、小样本分组和时间依赖。

它还能延续到第六周：将 `cnt` 作为预测目标，建立首个回归模型。

### 1.2 它不适合回答什么

这份数据不能直接回答：

- 某一位用户为什么租车。
- 某个站点是否缺车，因为没有站点级库存和位置。
- 天气是否因果性地导致租赁量变化。
- 2012 年之后或其他城市的需求是否相同。
- 调价、营销活动或交通事件的效果，因为缺少相应字段。

“数据里没有”与“分析者还没算”是两类完全不同的问题。

## 2. 先写分析任务，再下载数据（10 分钟）

本周报告围绕三个问题展开：

1. 租赁需求在小时、工作日和季节上呈现什么模式？
2. 不同天气状况下的需求分布有何差异，样本量是否足够？
3. 临时用户和注册用户的使用模式是否不同？

把问题转成可计算定义：

| 分析概念 | 本项目定义 |
| --- | --- |
| 需求 | 每小时租赁总数 `cnt` |
| 工作日 | `workingday == 1` |
| 小时模式 | 按 `hr` 分组后的样本量、中位数和均值 |
| 天气差异 | 按 `weathersit` 分组比较 `cnt` 分布，并展示样本量 |
| 用户结构 | `casual`、`registered` 及其占比 |

这些定义不是永久真理，而是本次分析的口径。报告必须让读者能复现同一口径。

## 3. 原始数据目录与可复现下载（15 分钟）

建议建立如下目录：

```text
projects/week-05-bike-sharing/
├── data/
│   ├── raw/          # 官方原始文件，只读保留
│   └── processed/    # 后续课程生成的清洗结果
├── notebooks/
│   └── 01_data_audit.ipynb
└── README.md
```

PowerShell：

```powershell
New-Item -ItemType Directory -Force projects\week-05-bike-sharing\data\raw
New-Item -ItemType Directory -Force projects\week-05-bike-sharing\data\processed
New-Item -ItemType Directory -Force projects\week-05-bike-sharing\notebooks
```

从 UCI 官方页面下载压缩包，解压后把以下文件复制到 `data/raw/`：

```text
hour.csv
day.csv
Readme.txt
```

记录下载日期和来源 URL。不要在原始 CSV 上手工改值；后续所有转换都从 `raw` 读取并写入 `processed`。

### 3.1 为什么本地保存，而不是每次读 URL

每次执行 Notebook 都访问远程 URL 会引入额外变量：

- 断网或服务暂时不可用。
- 远程文件被替换。
- 请求限速。
- URL 重定向或证书变化。

本地原始文件让同一分析可以重复执行。生产项目还会保存校验和；本课先记录文件大小与修改时间：

```python
from pathlib import Path

raw_dir = Path("../data/raw")

for path in sorted(raw_dir.iterdir()):
    if path.is_file():
        print(path.name, path.stat().st_size)
```

如果 Notebook 从项目根目录启动，路径会不同。先确认当前工作目录：

```python
from pathlib import Path

print(Path.cwd())
```

路径是输入契约的一部分，不要靠反复添加 `../` 猜测。

## 4. 阅读数据字典（15 分钟）

在写分析代码前，先阅读官方 `Readme.txt`。核心字段如下：

| 字段 | 含义 | 预期约束 | 分析角色 |
| --- | --- | --- | --- |
| `instant` | 记录编号 | 唯一、正整数 | 标识符 |
| `dteday` | 日期 | 2011–2012 年的有效日期 | 时间 |
| `season` | 季节编码 | 1–4 | 名义类别 |
| `yr` | 年份编码 | 0 或 1 | 类别/时间 |
| `mnth` | 月份 | 1–12 | 周期类别 |
| `hr` | 小时，仅小时表 | 0–23 | 周期类别 |
| `holiday` | 是否节假日 | 0 或 1 | 二元类别 |
| `weekday` | 星期编码 | 0–6 | 周期类别 |
| `workingday` | 非周末且非节假日 | 0 或 1 | 二元类别 |
| `weathersit` | 天气状况编码 | 1–4 | 有序类别 |
| `temp` | 归一化温度 | 通常在 0–1 | 连续特征 |
| `atemp` | 归一化体感温度 | 通常在 0–1 | 连续特征 |
| `hum` | 归一化湿度 | 0–1 | 连续特征 |
| `windspeed` | 归一化风速 | 0–1 | 连续特征 |
| `casual` | 临时用户租赁数 | 非负整数 | 目标组成部分 |
| `registered` | 注册用户租赁数 | 非负整数 | 目标组成部分 |
| `cnt` | 总租赁数 | `casual + registered` | 分析/预测目标 |

### 4.1 编码不是数值尺度

Pandas 会把 `season` 读取成整数，但这不意味着：

```text
season 4 > season 2
```

具有普通数值大小的业务含义。类似地，星期六的编码与星期日的编码相差 1，并不表示它们“更接近”。类别编码的底层类型可以是整数，分析语义仍然是类别。

### 4.2 归一化值不是原始单位

不要把 `temp` 直接标成“摄氏度”。在恢复原始量纲前，图表轴应写“normalized temperature”。恢复公式必须来自官方说明，并在代码和报告中保留依据。

### 4.3 `cnt` 暴露出的目标泄漏

数据定义保证：

```python
cnt == casual + registered
```

在 EDA 中可以同时分析三列；但第六周若预测 `cnt`，把 `casual` 和 `registered` 作为输入特征会直接泄漏答案。模型看似极其准确，实际上只是学会了加法。

## 5. 第一次读取：保留证据（15 分钟）

先少做自动转换，观察原始解析结果：

```python
from pathlib import Path

import pandas as pd

DATA_PATH = Path("../data/raw/hour.csv")

assert DATA_PATH.exists(), f"找不到数据文件: {DATA_PATH.resolve()}"

raw = pd.read_csv(DATA_PATH)
raw.head()
```

依次检查：

```python
print(raw.shape)
print(raw.columns.tolist())
raw.info()
raw.head(3).T
raw.tail(3).T
```

为什么同时看 `head()` 和 `tail()`？时间数据可能在末尾出现不同年份、不同编码或不完整周期，只看开头容易误判覆盖范围。

Pandas 的 `read_csv()` 可以用 `dtype` 显式指定类型、用 `na_values` 声明额外缺失标记，并用 `parse_dates` 与 `date_format` 解析日期。官方参考：

- [pandas.read_csv](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html)
- [Pandas IO tools](https://pandas.pydata.org/docs/user_guide/io.html)

本课先读取原始版本，再创建审计副本：

```python
df = raw.copy()
df["dteday"] = pd.to_datetime(df["dteday"], errors="coerce")
```

不要立即覆盖或导出 `raw`。它是解析后的基线证据，便于比较转换前后的变化。

## 6. 建立第一版数据契约（25 分钟）

数据契约描述“我们期望收到什么”。它不是说数据一定干净，而是让偏离预期的情况可见。

### 6.1 表级契约

```python
EXPECTED_COLUMNS = {
    "instant",
    "dteday",
    "season",
    "yr",
    "mnth",
    "hr",
    "holiday",
    "weekday",
    "workingday",
    "weathersit",
    "temp",
    "atemp",
    "hum",
    "windspeed",
    "casual",
    "registered",
    "cnt",
}

assert set(df.columns) == EXPECTED_COLUMNS
assert len(df) > 0
assert df["instant"].is_unique
```

这里使用集合比较，字段顺序改变不会失败。如果下游导出依赖固定列顺序，则应另外检查 `df.columns.tolist()`。

### 6.2 缺失、重复与类型审计

```python
audit = pd.DataFrame(
    {
        "dtype": df.dtypes.astype(str),
        "missing_count": df.isna().sum(),
        "missing_rate": df.isna().mean(),
        "unique_count": df.nunique(dropna=False),
    }
)

audit.sort_values(["missing_rate", "unique_count"], ascending=[False, True])
```

检查重复：

```python
print("完整重复行:", df.duplicated().sum())
print("日期小时重复:", df.duplicated(subset=["dteday", "hr"]).sum())
```

`instant` 唯一不代表业务键一定唯一。对小时表而言，`dteday + hr` 更接近观察单位的自然键。

### 6.3 取值范围契约

```python
assert df["season"].isin([1, 2, 3, 4]).all()
assert df["yr"].isin([0, 1]).all()
assert df["mnth"].between(1, 12).all()
assert df["hr"].between(0, 23).all()
assert df["holiday"].isin([0, 1]).all()
assert df["weekday"].between(0, 6).all()
assert df["workingday"].isin([0, 1]).all()
assert df["weathersit"].isin([1, 2, 3, 4]).all()

for column in ["temp", "atemp", "hum", "windspeed"]:
    assert df[column].between(0, 1).all(), column

for column in ["casual", "registered", "cnt"]:
    assert df[column].ge(0).all(), column
```

断言适合验证明确的不变量。如果异常值本身是研究对象，不应使用断言把它悄悄排除，而应输出质量报告。

### 6.4 字段关系契约

```python
count_matches = df["cnt"].eq(df["casual"] + df["registered"])

print(count_matches.value_counts(dropna=False))
assert count_matches.all()
```

字段各自都在合理范围内，并不代表字段之间一定一致。关系契约能发现单列检查看不到的问题。

## 7. 时间粒度与连续性（15 分钟）

创建真正的小时级时间戳：

```python
df["timestamp"] = df["dteday"] + pd.to_timedelta(df["hr"], unit="h")

print(df["timestamp"].min())
print(df["timestamp"].max())
print(df["timestamp"].is_monotonic_increasing)
print(df["timestamp"].duplicated().sum())
```

检查相邻记录间隔：

```python
time_gaps = df["timestamp"].sort_values().diff().value_counts().head(10)
time_gaps
```

不要先假设“每小时都有记录”。如果某些小时不存在，至少有三种解释：

- 该小时没有租赁，因此未记录。
- 数据采集缺失。
- 官方预处理删除了部分记录。

只有结合数据说明或额外证据，才能区分它们。缺行和某列为 `NaN` 也不是同一种缺失。

### 7.1 为什么机器学习不能随机忽略时间

数据跨越 2011–2012 年，2012 年的使用规模可能与 2011 年不同。如果随机切分训练集和测试集，未来记录会进入训练集，评估场景与“用过去预测未来”不一致。

本课只记录规则：第六周优先使用按时间排序后的切分，而不是默认随机切分。

## 8. 第一轮画像：只描述，不急于解释（15 分钟）

### 8.1 类别覆盖与样本量

```python
categorical_columns = [
    "season",
    "yr",
    "mnth",
    "hr",
    "holiday",
    "weekday",
    "workingday",
    "weathersit",
]

for column in categorical_columns:
    print(f"\n--- {column} ---")
    print(df[column].value_counts(dropna=False).sort_index())
```

注意天气类别 4 是否有足够样本。若样本极少或没有出现，不能只比较均值后就下强结论。

### 8.2 数值概览

```python
numeric_columns = [
    "temp",
    "atemp",
    "hum",
    "windspeed",
    "casual",
    "registered",
    "cnt",
]

df[numeric_columns].describe(
    percentiles=[0.25, 0.5, 0.75, 0.95, 0.99]
).T
```

这一步先记录现象：

- `cnt` 是否右偏。
- 均值与中位数差距多大。
- 最大值距离 P99 多远。
- 归一化字段是否覆盖完整的 0–1。

不要在本课删除高租赁量记录。高值可能是真实的通勤高峰，而不是错误。

### 8.3 最小基线图

```python
import matplotlib.pyplot as plt
import seaborn as sns

hourly = df.groupby("hr", as_index=False).agg(
    sample_count=("cnt", "size"),
    median_rentals=("cnt", "median"),
    mean_rentals=("cnt", "mean"),
)

fig, ax = plt.subplots(figsize=(10, 4))
sns.lineplot(data=hourly, x="hr", y="median_rentals", marker="o", ax=ax)
ax.set(
    title="Median hourly rentals by hour of day",
    xlabel="hour",
    ylabel="median rental count",
)
ax.set_xticks(range(24))
plt.tight_layout()
plt.show()
```

图下只写一条观察和一条限制。例如：

> 观察：小时中位租赁量在早晚部分时段出现峰值。限制：该图混合了工作日、周末、季节与两个年份，不能把峰值单独归因于通勤。

## 9. Java / Spring Boot 对照

可以把本课的数据契约理解为进入分析管道前的 DTO 校验，但两者不完全相同：

| 应用服务概念 | 数据分析对应物 |
| --- | --- |
| 请求 DTO 字段 | CSV 列 |
| Bean Validation | 范围、非空、集合约束 |
| 业务主键 | `dteday + hr` 自然键 |
| 跨字段校验 | `cnt == casual + registered` |
| API 版本变化 | 数据集 schema 漂移 |
| 原始请求日志 | `data/raw` 不可变原始数据 |
| 转换后的领域对象 | `data/processed` 清洗数据 |

差异在于：在线 API 常拒绝非法请求，而离线分析通常需要保留坏数据、统计问题规模，并解释处理策略。

## 10. 课堂练习

### 练习 1：写观察单位

分别用一句话描述：

- `hour.csv` 中一行代表什么。
- `day.csv` 中一行代表什么。
- 为什么不能直接 `pd.concat([hour, day])` 后一起算平均值。

### 练习 2：字段角色分类

把全部字段分成：

- 标识符
- 时间
- 类别
- 连续数值
- 计数
- 目标或目标组成部分

说明 `hr` 为什么虽然是整数，却不适合简单当作线性连续变量。

### 练习 3：让契约失败

复制前三行并故意制造三个错误：

```python
broken = df.head(3).copy()
broken.loc[broken.index[0], "hr"] = 24
broken.loc[broken.index[1], "cnt"] = -1
broken.loc[broken.index[2], "cnt"] += 1
```

为每个错误编写一个会失败的断言。观察错误消息是否足以定位问题。

### 练习 4：数据能否回答

判断以下问题属于“可以直接回答”“只能描述关联”还是“数据不足”，并说明理由：

1. 哪个小时的典型租赁量最高？
2. 下雨会不会导致某个人放弃骑车？
3. 工作日和非工作日的小时模式是否不同？
4. 哪个站点最容易缺车？

### 练习 5：泄漏检查

假设预测目标是 `cnt`，把字段分成：

- 当前可考虑的输入特征。
- 明确排除的泄漏特征。
- 是否可用取决于预测时点的字段。

至少解释 `casual`、`registered`、`instant` 和天气字段。

## 11. 小测（10 题）

1. 什么是观察单位？为什么它必须在分析前明确？
2. 数据类型为整数，是否代表字段一定是连续数值？
3. `instant` 唯一为什么不能替代 `dteday + hr` 的重复检查？
4. 缺失行与某列的 `NaN` 有什么区别？
5. 为什么原始数据不应被 Notebook 手工覆盖？
6. 数据契约中的范围检查与关系检查各能发现什么？
7. 为什么 `temp == 0.5` 不能直接解释成 0.5 摄氏度？
8. 预测 `cnt` 时，为什么不能使用 `casual` 和 `registered`？
9. 为什么极端的 `cnt` 不应在第一轮审计中直接删除？
10. 为什么时间数据通常要考虑按时间切分训练集和测试集？

## 12. 进阶挑战（选做）

### 挑战 1：生成结构化审计表

为每列输出：

| column | dtype | missing | missing_rate | unique | min | max |
| --- | --- | ---: | ---: | ---: | ---: | ---: |

类别字段的 `min`、`max` 可能没有业务解释，说明为什么通用审计表仍需配合数据字典。

### 挑战 2：跨粒度守恒检查

将 `hour.csv` 按日期汇总 `casual`、`registered` 和 `cnt`，再与 `day.csv` 对应字段连接，检查每日总量是否一致。

提示：

```python
hour_daily = (
    df.groupby("dteday", as_index=False)[["casual", "registered", "cnt"]]
    .sum()
)
```

这一挑战为后续 `merge()` 课程预热。连接前先检查两侧连接键是否唯一。

### 挑战 3：数据来源清单

创建 `projects/week-05-bike-sharing/README.md`，记录：

- 数据集名称与官方 URL。
- 下载日期。
- 原始文件名和文件大小。
- 许可证或使用说明。
- 观察单位与时间范围。
- 本地目录约定。
- 已知限制。

## 13. 完成检查

- [ ] 已从 UCI 官方来源获取并保留 `Readme.txt`。
- [ ] 已建立 `data/raw`、`data/processed` 和 `notebooks` 目录。
- [ ] 已创建 `01_data_audit.ipynb`。
- [ ] 已用一句话准确描述 `hour.csv` 的观察单位。
- [ ] 已记录数据来源、下载日期与原始文件信息。
- [ ] 已检查列集合、行数、类型、缺失、重复和唯一值数量。
- [ ] 已检查所有核心字段的取值范围。
- [ ] 已验证 `cnt == casual + registered`。
- [ ] 已创建小时级 `timestamp` 并检查重复与间隔。
- [ ] 已解释至少一个编码类别和一个归一化字段。
- [ ] 已识别 `casual` 与 `registered` 的目标泄漏风险。
- [ ] 已输出一张小时需求基线图，并写观察与限制。
- [ ] 已回答小测 10 题。

## 14. 下课前交付

请提交：

1. `projects/week-05-bike-sharing/notebooks/01_data_audit.ipynb`。
2. 数据来源说明与字段数据字典。
3. 一张列级审计表。
4. 表级、范围和字段关系三类契约检查结果。
5. 一张小时需求基线图及“观察 + 限制”。
6. 小测第 1、3、4、6、8、10 题答案。

我会重点 Review：

- 观察单位和字段含义是否准确。
- 原始数据是否保持不变，路径是否可复现。
- 是否把类别编码误当成连续尺度。
- 是否区分字段缺失与时间记录缺失。
- 断言是否表达明确的数据不变量。
- 是否提前识别目标泄漏和时间切分风险。
- 结论是否严格停留在数据能够支持的范围内。

下一课将基于这份审计结果制定系统化清洗策略，处理类型、缺失、重复、异常和类别标签，并保留每一步转换的理由与影响。
