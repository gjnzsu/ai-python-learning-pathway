# 第 4 周 · 第 2 课：Pandas 表结构与数据清洗探索（Notebook 版）

预计用时：120–150 分钟

## 本课目标

完成本课后，你能够：

- 从 `numpy.ndarray` 过渡到 `pandas.DataFrame` 的表结构思维。
- 用 `Series`/`DataFrame` 处理缺失值与类型问题。
- 用 `loc`、`iloc`、布尔索引、`groupby` 完成基础分析。
- 用 `value_counts`、`sort_values`、`pivot_table` 输出可解释指标。
- 对比 `DataFrame.plot` 与 `seaborn` 两种可视化路径，并能写出结论。
- 为后续机器学习课程建立“表格化数据 => 特征工程预处理”流水线。

## 0. 第 4 周回顾（10 分钟）

上一课已经完成：

- `numpy` 的向量化与性能意识。
- `shape`、`axis`、`dtype` 的理解。
- 用至少三类图支撑假设验证（hist / scatter / boxplot）。

本课从“数组语义”切到“关系表语义”：

- 关键对象：**列 = 特征，行 = 样本**。
- 目标：把日志字段从“算术对象”变成“分析对象”。

## 1. 为什么要用 DataFrame

在 NumPy 里你擅长向量和矩阵运算；在业务分析里更常问：

- 哪类日志级别更多？
- 哪个时间段错误率最高？
- 不同来源的耗时是否有明显差异？

这些问题天然是“按列分组、按条件筛选、按字段聚合”的表操作。

```python
import numpy as np
import pandas as pd

print(type(np.array([1, 2, 3])))
print(type(pd.Series([1, 2, 3])))
print(type(pd.DataFrame([[1, 2], [3, 4]], columns=["a", "b"])))
```

## 2. 环境与 notebook 任务

先安装本课依赖（若未安装）：

```powershell
cd projects\log-analyzer
python -m pip install -e ".[dev]"
python -m pip install pandas
```

本课任务文件：

```powershell
New-Item -ItemType File -Path projects\week-04-data\eda.ipynb -Force
```

Notebook 需要完成三段：

1. 生成或读取 2000 条以上伪日志样本并转为 DataFrame。
2. 做 4 种基础清洗：列类型转换、缺失值处理、重复行检查、异常时延标记。
3. 输出至少 3 张图并写“业务结论”。

## 3. 从“原始列表”到 DataFrame

```python
import pandas as pd

data = [
    {"timestamp": "2026-08-01 10:01:00", "level": "INFO", "source": "api", "duration_ms": "120", "bytes": 1024, "msg": "start"},
    {"timestamp": "2026-08-01 10:01:05", "level": "ERROR", "source": "db", "duration_ms": "bad", "bytes": 2048, "msg": "timeout"},
    {"timestamp": "2026-08-01 10:01:09", "level": "INFO", "source": "api", "duration_ms": "95", "bytes": None, "msg": "ok"},
]

logs_df = pd.DataFrame(data)
print(logs_df)
```

`DataFrame` 是“带标签的二维表”，可在保持列语义清晰的同时，做大规模操作。

## 4. 类型转换与缺失值

```python
logs_df["timestamp"] = pd.to_datetime(logs_df["timestamp"])
logs_df["duration_ms"] = pd.to_numeric(logs_df["duration_ms"], errors="coerce")

print(logs_df.dtypes)
print(logs_df.isna().sum())

logs_df["bytes"] = logs_df["bytes"].fillna(0).astype(int)
logs_df["has_error"] = logs_df["level"].eq("ERROR")
```

常见原则：

- 先定“质量底线”：类型与缺失。
- 再做统计或画图，减少后续误导。

## 5. 行列选择：`loc`、`iloc`、布尔索引

```python
# 按列名与列范围选取
sub = logs_df.loc[:, ["timestamp", "level", "duration_ms", "bytes"]]

# 按位置选取
head3 = logs_df.iloc[:3, :]

# 条件筛选：ERROR 且耗时 > 100ms
err_slow = logs_df[(logs_df["level"] == "ERROR") & (logs_df["duration_ms"] > 100)]

print(sub.head(2))
print(head3)
print(err_slow)
```

### Java 对照

- `for`/`if` 依旧适合流程控制。
- `loc`/`iloc`/布尔索引更适合“集合化表达”筛选。

## 6. 分组与聚合（`groupby`）

```python
level_summary = logs_df.groupby("level").agg(
    total=("bytes", "count"),
    avg_duration=("duration_ms", "mean"),
    p95_duration=("duration_ms", lambda s: s.quantile(0.95)),
)

source_summary = (
    logs_df.groupby("source")
    .agg(error_rate=("has_error", "mean"), avg_bytes=("bytes", "mean"))
    .sort_values("error_rate", ascending=False)
)

print(level_summary)
print(source_summary)
```

`groupby` 等价于“按键分桶后聚合”。只要你要“按 X 分组算 Y”，通常都应优先考虑它。

## 7. 排序、去重、透视

```python
print(logs_df.sort_values("duration_ms", ascending=False).head(5))
print(logs_df.duplicated(subset=["timestamp", "source", "msg"]).sum())

pivot = pd.pivot_table(
    logs_df,
    index="source",
    columns="level",
    values="duration_ms",
    aggfunc="mean",
)

print(pivot)
```

`pivot_table` 常用于把“长表”转成透视结构，便于横向对比。

## 8. 可视化（服务于决策）

```python
import matplotlib.pyplot as plt
import seaborn as sns

counts = logs_df["level"].value_counts()
counts.plot(kind="bar", title="Log level count")
plt.xlabel("level")
plt.ylabel("count")
plt.tight_layout()
plt.show()

logs_df["hour"] = logs_df["timestamp"].dt.hour
sns.violinplot(data=logs_df, x="level", y="duration_ms")
plt.title("Duration by level")
plt.tight_layout()
plt.show()

src_err = logs_df.groupby("source")["has_error"].mean().sort_values(ascending=False)
src_err.plot(kind="barh", title="Error rate by source")
plt.xlabel("error rate")
plt.tight_layout()
plt.show()
```

每张图都要写一句“我的判断”：

- 是否支持业务决策？
- 是否存在采样偏差？
- 下一步要补什么指标？

## 9. 第一轮练习（每题 10 分钟）

### 练习 1：清洗与结构化

给定至少 20 条 `list[dict]` 日志：

- 转为 `DataFrame`。
- 将 `duration_ms` 安全转数值。
- 构造 `timestamp` -> `hour`。
- 输出清洗后 `isna()` 汇总。

### 练习 2：布尔过滤与异常抽取

找出以下集合并比较规模：

- `level == ERROR`
- `duration_ms > 500`
- 同时满足以上条件

解释为什么要用位运算符 `&` 而不是 Python 的 `and`。

### 练习 3：groupby 与透视

在 `level` 维度上统计：

- 样本数
- 平均时延
- 最大时延

再做一个 `source` + `level` 的透视表，解释缺失格子的含义。

### 练习 4：图表结论写作

用同一份数据画至少 3 张图（条形图、折线图或箱线图/小提琴图之一），
每张图都配一句“支持业务决策”的结论语句。

## 10. 小测（10 题）

1. `read_csv` 默认把第一行当作什么？
2. `loc` 和 `iloc` 的最大区别是什么？
3. `pd.to_numeric(errors="coerce")` 的作用是什么？
4. `isna().sum()` 在清洗流程里回答什么问题？
5. `groupby("k").agg()` 与先 `sort` 再 `mean` 的区别是什么？
6. `df[col].eq(1)` 为什么比 `df[col] == 1` 更强调可读性？
7. `pivot_table` 的常见用途是什么？
8. 为什么要避免 `SettingWithCopyWarning`？
9. `fillna(0)` 与删行，在分布分析上会带来什么差异？
10. 为什么图表下必须写“局限性”？

## 11. 课后交付

- [ ] 已在 `projects/week-04-data/eda.ipynb` 完成清洗、筛选、分组和可视化流程。
- [ ] 已处理并展示至少 1 个缺失值与 1 个异常值案例。
- [ ] `groupby` 输出至少 3 个业务指标。
- [ ] 提交 1 张透视表结果图，1 张分组柱图，1 张分布/时序图。
- [ ] 提交小测第 1、2、5、6、8 题。
- [ ] 每张图都写有“结论 + 不确定性”。

## 12. 下课前回顾

下一课即将进入基础建模与特征矩阵构造。把本课 notebook 的关键输出整理为三段文字：

- 质量：你修了哪些字段
- 分析：你发现了哪些偏差
- 假设：你的下一步验证动作是什么
