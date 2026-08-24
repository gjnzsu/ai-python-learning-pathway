# 第 4 周 · 第 3 课：Pandas 数据分析流程（从清洗到洞察闭环）

预计用时：120–150 分钟

## 本课目标

完成本课后，你能够：

- 把“Pandas 清洗后的表”继续推进为一套可复现的数据分析流程。
- 使用 `query`、`assign`、`rank`、`sort_values`、`corr` 形成更高效的数据筛选与特征构造。
- 掌握 `merge`/`concat` 的基本用法，理解“联合主表”和“补齐空值”场景。
- 构建分析叙事：先提出问题，再给出指标定义、分组统计、可视化与结论。
- 形成一份可提交的“异常识别 + 复盘报告”草稿。
- 为下一阶段的特征工程与建模提前产出可直接迁移的列。

## 0. 先热身（10 分钟）：你今天在做什么

我们已经有了两个基础课的基础：

- 第 1 课：NumPy 向量化思维
- 第 2 课：DataFrame 的结构化清洗与分组

本课不再重复 API，而是把这些能力连成完整闭环：

```text
问题定义 -> 数据抽样 -> 清洗 -> 指标构造 -> 过滤与分组 -> 异常识别 -> 图形解释 -> 结论与下一步
```

这就是“工程化数据分析”的基本流程。

## 1. 复习与接口约束（20 分钟）

请确认你已经完成并理解上两课中的关键点：

- `duration_ms` 可安全转为数值，异常转为 `NaN`。
- `isna().sum()` 作为数据质量闸口。
- 布尔筛选要用 `&`/`|`，不要直接在 Series 上用 `and`/`or`。
- `groupby().agg()` 里 `count()` 与 `size()` 在缺失值处理上的差异。

### 小约束（本课统一）

本课后续 notebook 统一采用：

- 随机数种子固定为 `42`
- 每一步都保留 `before / after` 对比样本量
- 图表必须绑定“问题假设”

## 2. 课前准备（5 分钟）

先进入 notebook：

```powershell
cd C:\Users\gjnzsu\Documents\ai-python-learning-pathway
New-Item -ItemType File -Path projects\week-04-data\analysis_workflow.ipynb -Force
```

建议安装依赖：

```powershell
python -m pip install pandas numpy matplotlib seaborn
```

并加载：

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

pd.set_option("display.max_columns", 100)
np.random.seed(42)
```

## 3. 定义“分析问题”而非直接画图（15 分钟）

没有问题的图通常是“没结论的图”。先写问题：

1. 哪个 `source` 的错误率最高？
2. `ERROR` 日志的时延是不是显著更高？
3. 哪些时段出现异常高时延？

把问题转成可计算指标：

- `error_rate = error_count / total_count`
- `err_duration_gap = mean(duration_ms[ERROR]) - mean(duration_ms[ALL])`
- `hourly_count` 与 `hourly_error_rate`

每个分析问题都要求你先写：

- 假设：`H0`（原假设）与 `H1`（备择）
- 期望：比如“若无差异，某对比接近一致”
- 反证标准：比如“差异超过阈值”

## 4. 重构 DataFrame：从原始到分析态（20 分钟）

### 4.1 构造一份可复用的分析列

```python
df = logs_df.copy()

df["timestamp"] = pd.to_datetime(df["timestamp"])
df["hour"] = df["timestamp"].dt.hour
df["is_error"] = df["level"].eq("ERROR")
df["duration_ms"] = pd.to_numeric(df["duration_ms"], errors="coerce")
df["is_short_msg"] = df["msg"].str.len().le(6)
df["bytes_fill0"] = df["bytes"].fillna(0)

clean_before = len(df)
df = df[~df["duration_ms"].isna()].copy()
clean_after = len(df)
print("清洗掉异常duration：", clean_before - clean_after)
```

### 4.2 `assign` 与向量化表达

`assign` 适合一次性创建多个衍生列：

```python
df = df.assign(
    is_long_duration=lambda x: x["duration_ms"] > 200,
    msg_len=lambda x: x["msg"].str.len(),
    latency_bucket=lambda x: pd.cut(
        x["duration_ms"],
        bins=[0, 50, 100, 300, 1000, float("inf")],
        labels=["0-50", "50-100", "100-300", "300-1000", "1000+"],
        right=False,
    ),
)
```

### 4.3 `query`：筛选语句更像业务 SQL

```python
long_errors = df.query("is_error and duration_ms > 200 and source in ['api', 'db']")
print(len(long_errors))
```

`query` 可读，但在复杂变量、特殊列名或动态条件下，布尔索引更稳。

## 5. 深化筛选与排序（20 分钟）

### 5.1 Top-N 式问题

```python
top5_slowest = (
    df.sort_values("duration_ms", ascending=False)
      .head(5)
      [["timestamp", "source", "level", "duration_ms", "bytes", "msg"]]
)
```

### 5.2 分位与排名

```python
df["duration_rank"] = df["duration_ms"].rank(method="average", ascending=False)
df["duration_q"] = pd.qcut(df["duration_ms"], q=4, labels=["Q1", "Q2", "Q3", "Q4"])
```

注意：`rank` 对重复值会分配并列名次（`method` 可控）；`qcut` 会按样本分位切分，便于后续分组可视化。

### 5.3 条件比率

```python
grate = (
    df.assign(is_error_200=lambda x: x["is_error"] & (x["duration_ms"] > 200))
      .groupby("source")["is_error_200"]
      .mean()
      .sort_values(ascending=False)
)
```

## 6. 分组聚合进阶（20 分钟）

### 6.1 多指标透视 + 列重命名

```python
summary = (
    df.groupby(["source", "level"], as_index=False)
      .agg(
         count=("duration_ms", "count"),
         err_rate=("is_error", "mean"),
         avg_duration=("duration_ms", "mean"),
         p90_duration=("duration_ms", lambda s: s.quantile(0.9)),
         total_bytes=("bytes_fill0", "sum"),
      )
)

summary = summary.sort_values(["source", "err_rate"], ascending=[True, False])
```

### 6.2 `pivot_table` 回到矩阵视角

```python
pivot = df.pivot_table(
    index="source",
    columns="level",
    values="duration_ms",
    aggfunc="median",
    fill_value=np.nan,
)
print(pivot)
```

### 6.3 `corr` 与 `corrwith`（先有感知后再统计）

```python
corr_matrix = df[["duration_ms", "bytes_fill0", "msg_len"]].corr()
print(corr_matrix)
```

先把它当“假设生成器”，不是最终结论。相关性高并不等于因果。

## 7. 合并数据表（15 分钟）

假设你拿到了“运维服务属性表”：

```python
sla = pd.DataFrame(
    {
        "source": ["api", "db", "worker", "scheduler"],
        "sla_ms": [180, 220, 160, 200],
    }
)

df2 = df.merge(sla, on="source", how="left")
df2["sla_violation"] = df2["duration_ms"] > df2["sla_ms"]

violation_rate = df2.groupby("source")["sla_violation"].mean().sort_values(ascending=False)
```

`merge` 的重点：

- `on`：对齐键
- `how`：`left`/`inner`/`outer` 的行保留行为
- 重复键会导致行数膨胀，需核对。

## 8. 异常识别：规则法 vs 分位法（15 分钟）

### 8.1 简单规则

```python
rule_hits = df.query("duration_ms >= 300 or bytes_fill0 >= 50000 or is_error")
print(rule_hits.shape)
```

### 8.2 分位法

```python
p95 = df["duration_ms"].quantile(0.95)
p99 = df["duration_ms"].quantile(0.99)
outlier = df.query("duration_ms >= @p99")
print(p95, p99, len(outlier))
```

给每类异常打上 `tag`，以后可喂给告警/模型：

```python
df = df.assign(
    anomaly_tag=np.select(
        [df["duration_ms"] >= p99, df["duration_ms"] >= p95],
        ["critical", "high"],
        default="normal",
    )
)
```

## 9. 可视化（25 分钟）：让分析变成报告

### 9.1 需求映射到图

- 问题 1（哪个 source 错误率高）-> 分组条形图
- 问题 2（时延对比）-> 小提琴图 + 箱线图
- 问题 3（时间段异常）-> 按小时折线图

示例：

```python
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

err_by_source = df.groupby("source")["is_error"].mean().sort_values(ascending=False)
err_by_source.plot(kind="bar", ax=axes[0], color="#2d6a9f")
axes[0].set_title("Error rate by source")

sns.violinplot(data=df, x="level", y="duration_ms", ax=axes[1])
axes[1].set_title("Duration distribution by level")

hourly = df.groupby("hour")["is_error"].mean()
hourly.plot(kind="line", marker="o", ax=axes[2], color="#8c2d96")
axes[2].set_title("Hourly error rate")

plt.tight_layout()
plt.show()
```

### 9.2 结论模板（每图都写）

- “该图支持什么结论？”
- “支持强度高吗？”
- “可能的反例或偏差？”

## 10. 课堂练习（每题 12 分钟）

### 练习 1：问题驱动分析

给一份 3000 条日志 DataFrame，完成：

1. 识别 `source` 维度错误率前 3 的来源。
2. 计算每个来源的 `95%` 时延。
3. 用 `bar` 图输出对照。

### 练习 2：复用 `query + assign`

构造字段 `is_slow`、`is_large`、`is_risky`

- `is_slow`：时延大于全局 90 分位
- `is_large`：字节大于 8000
- `is_risky`：`is_slow & is_large & is_error`

输出每列比例并解释。

### 练习 3：构造对照指标

分别按 `level` 和 `source` 算：

- `count`
- `mean(duration_ms)`
- `median(duration_ms)`
- `p95(duration_ms)`

再转成 `pivot_table` 并回答：

- 哪个 source 在 `ERROR` 下最不稳定？

### 练习 4：合并外部维表

新增一个维表：

- `service_type`（如 `api`、`db`、`worker` 的类型）
- `critical_flag`（是否关键链路）

`merge` 到主表后，比较关键链路与普通链路的错误率与时延。

### 练习 5：异常归因小结

用 `duration_q` 分位段和 `source` 做一个交叉分析：

1. 找到异常最集中的 2 个 source。
2. 给出一次可能的“根因假设”。
3. 写 3 条下一步验证建议（可采集字段、可增加的指标）。

## 11. 小测（10 题）

1. 为什么先写问题再选图比“先画再想结论”更稳？
2. `rank` 和 `nlargest` 的适用场景有什么区别？
3. `query("duration_ms > 100 and level == 'ERROR'")` 和布尔索引相比，有何优劣？
4. `merge(..., how="left")` 的行为是什么？
5. `how="inner"` 和 `how="outer"` 的行数差异来自哪里？
6. `fill_value` 在 `pivot_table` 里为什么很重要？
7. `corr` 的值接近 1、0、-1 分别代表什么？
8. `qcut` 与固定区间切分（`bins=[0,50,100,...]`）的关键差异是什么？
9. `assign` 的优势是什么？
10. 为什么异常检测输出不能直接代替人工复核？

## 12. 课后交付

- [ ] 已完成 `projects/week-04-data/analysis_workflow.ipynb`
- [ ] `df` 至少保留 4 个衍生字段（`hour`、`is_error`、`duration_bucket`、`latency_bucket` 等）
- [ ] 完成 5 个练习题中的至少 4 个
- [ ] 输出 4 类以上图表（条形图、线图、箱线图/小提琴图、分位段图任意）
- [ ] 每张图都写 `问题 -> 指标 -> 结论 -> 限制`
- [ ] 提交一个 180–250 字的课程复盘：
  - 我今天最值得复用的分析模式是什么？
  - 哪一步最容易把相关性当因果？
  - 下次我会优先验证什么“反例”

## 13. 下课前复盘（3 分钟）

把下方补成“口头答辩脚本”：

1. “我的数据分析问题是 ___”
2. “我采用的核心指标是 ___”
3. “我看见的结论是 ___”
4. “我的结论不确定在于 ___”
5. “下一步我会补一个 ___ 实验”

你下一步只要把 `analysis_workflow.ipynb` 发来，我就按“可复现性 + 统计合理性 + 可解释性”三个维度给你 Review。 
