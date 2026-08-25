# 第 4 周 · 第 4 课：探索性数据分析报告与统计直觉

预计用时：120–150 分钟

## 本课定位

前三课已经完成了从 NumPy、DataFrame 到日志分析流程的过渡。本课不再以增加 Pandas API 为主，而是回答一个更重要的问题：

> 面对一张汇总表或一幅图，怎样判断结论是否可信，并把分析过程交付给别人复查？

本课将把现有日志分析整理成一份完整的探索性数据分析（Exploratory Data Analysis，EDA）报告，并为第 5 周的真实公开数据分析做好准备。

## 本课目标

完成本课后，你能够：

- 区分均值、中位数、分位数、标准差和四分位距各自回答的问题。
- 识别小样本、偏态分布、离群值和缺失数据对结论的影响。
- 使用 IQR 和分组基准识别候选异常，同时避免把统计异常直接等同于业务故障。
- 正确解释相关系数，并明确“相关不等于因果”。
- 根据比较、分布、趋势和关系四类问题选择图表。
- 用 Markdown、代码、表格和图形组织一份可复现的 Notebook 报告。
- 写出“结论 + 证据 + 限制 + 下一步”的分析摘要。

## 0. 热身：从“代码能跑”到“结论可信”（10 分钟）

上一课已经完成：

```text
原始日志 -> 清洗 -> 特征构造 -> 分组统计 -> 异常识别 -> 图表 -> 导出
```

但一条完整的数据链路不自动保证结论正确。请先思考：

1. 某来源只有 2 条日志，其中 1 条报错，50% 错误率说明它最危险吗？
2. 平均耗时为 200 ms，是否代表大部分请求都接近 200 ms？
3. `bytes` 与 `duration_ms` 高度相关，是否能断言“大响应一定导致慢请求”？
4. P95 很高，是否一定存在业务故障？

这些问题分别涉及样本量、分布、因果和指标语义。本课会逐一处理。

## 1. 本课工作文件与报告结构（5 分钟）

在现有 Notebook 的基础上新建最终报告：

```powershell
cd C:\Users\gjnzsu\Documents\ai-python-learning-pathway
Copy-Item projects\week-04-data\analysis_workflow.ipynb `
  projects\week-04-data\eda_report.ipynb
```

最终 Notebook 建议按以下顺序组织：

```text
1. 分析目标与问题
2. 数据来源与字段说明
3. 数据质量检查
4. 描述性统计
5. 核心问题分析
6. 异常候选与复核
7. 结论、限制与下一步
```

Notebook 不是代码草稿箱。阅读者应该能仅通过标题、文字、关键表格和图形理解你的分析逻辑。

## 2. 描述性统计：每个指标在回答什么（20 分钟）

假设已经有清洗后的 `df`：

```python
duration = df["duration_ms"].dropna()

summary = pd.Series(
    {
        "count": duration.count(),
        "mean": duration.mean(),
        "median": duration.median(),
        "std": duration.std(),
        "min": duration.min(),
        "p25": duration.quantile(0.25),
        "p75": duration.quantile(0.75),
        "p95": duration.quantile(0.95),
        "max": duration.max(),
    }
)
print(summary.round(2))
```

### 2.1 中心位置

- `mean`：所有值的算术平均，对极端值敏感。
- `median`：排序后的中间位置，对少量极端值更稳健。

如果均值明显高于中位数，常见原因是分布右偏：大部分值较低，少数超大值把均值拉高。

```python
print("mean - median:", duration.mean() - duration.median())
```

不要机械地规定二者相差多少才算偏态。差异需要结合业务尺度、直方图和样本量解释。

### 2.2 分散程度

- `std`：数据围绕均值的典型波动程度，对极端值敏感。
- `IQR = Q3 - Q1`：中间 50% 数据的跨度，对极端值更稳健。

```python
q1 = duration.quantile(0.25)
q3 = duration.quantile(0.75)
iqr = q3 - q1

print("Q1:", q1)
print("Q3:", q3)
print("IQR:", iqr)
```

### 2.3 尾部指标

P95 表示约 95% 的有效样本不高于该值，约 5% 的样本高于它。它不是“最慢 5% 的平均值”，也不是“95% 的请求都等于该值”。

```python
p95 = duration.quantile(0.95)
actual_ratio = duration.le(p95).mean()
print("P95:", p95)
print("不高于 P95 的实际比例:", actual_ratio)
```

有限样本、重复值和分位数插值会使实际比例不恰好等于 95%。

### Java 对照

在 Java 中，你可能会把这些统计量封装为聚合器或使用 Stream 收集；Pandas 的价值在于让“列级统计”成为主要表达方式。但 API 简洁不意味着解释可以省略。

## 3. 样本量：比例必须带分母（15 分钟）

只比较错误率可能产生误导：

```python
source_quality = (
    df.groupby("source")
    .agg(
        sample_count=("source", "size"),
        error_count=("is_error", "sum"),
        error_rate=("is_error", "mean"),
        median_duration=("duration_ms", "median"),
        p95_duration=("duration_ms", lambda s: s.quantile(0.95)),
    )
    .sort_values(["error_rate", "sample_count"], ascending=[False, False])
)
print(source_quality)
```

报告比例时至少同时展示：

- 分子：事件数，例如 `error_count`。
- 分母：总样本数，例如 `sample_count`。
- 比例：例如 `error_rate`。

错误率同为 50% 时，`1 / 2` 与 `500 / 1000` 的证据强度完全不同。

为了避免小组样本误导，可以先设一个“展示门槛”：

```python
min_samples = 5
comparable_sources = source_quality.query("sample_count >= @min_samples")
```

这里的 `5` 只是本课演示规则，不是通用统计标准。真实项目应根据采样周期、业务流量与决策风险确定门槛，并在报告中说明。

## 4. 缺失值不是一个单独的技术问题（15 分钟）

先按来源检查耗时字段完整率：

```python
duration_completeness = (
    df.groupby("source")["duration_ms"]
    .agg(valid_count="count", total_count="size")
    .assign(
        completeness=lambda x: x["valid_count"] / x["total_count"]
    )
    .sort_values("completeness")
)
print(duration_completeness)
```

需要区分三种情况：

1. 随机缺失：缺失与业务状态无明显关系。
2. 条件性缺失：例如某来源、某级别更容易缺失。
3. 结构性缺失：该字段对某类记录本来就不适用。

如果慢请求更容易丢失 `duration_ms`，那么直接 `dropna()` 会系统性低估耗时。仅报告“删除了几行”不够，还应比较删除前后不同分组的构成。

```python
missing_by_level = (
    df.assign(duration_missing=df["duration_ms"].isna())
    .groupby("level")["duration_missing"]
    .agg(missing_count="sum", missing_rate="mean")
)
print(missing_by_level)
```

## 5. 用 IQR 找候选异常（20 分钟）

### 5.1 全局 IQR 规则

箱线图常使用如下边界：

```text
下界 = Q1 - 1.5 × IQR
上界 = Q3 + 1.5 × IQR
```

```python
q1 = df["duration_ms"].quantile(0.25)
q3 = df["duration_ms"].quantile(0.75)
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr

df = df.assign(
    is_iqr_outlier=lambda x: (x["duration_ms"] < lower)
    | (x["duration_ms"] > upper)
)

print(df["is_iqr_outlier"].value_counts())
```

耗时不可能为负时，下界通常没有业务意义，可以只关注上界。

### 5.2 分组 IQR 规则

不同服务有不同延迟基线。全局阈值可能把正常的慢服务全部标为异常，也可能漏掉快服务内部的异常。

```python
source_duration = df.groupby("source")["duration_ms"]
source_q1 = source_duration.transform(lambda s: s.quantile(0.25))
source_q3 = source_duration.transform(lambda s: s.quantile(0.75))
source_iqr_upper = source_q3 + 1.5 * (source_q3 - source_q1)

df_with_iqr = df.assign(
    source_iqr_upper=source_iqr_upper,
    is_source_iqr_outlier=df["duration_ms"] > source_iqr_upper,
)
```

`transform()` 会把每个分组计算出的结果对齐回原始行，因此特别适合“先计算组内基准，再逐行比较”的场景。

### 5.3 异常值不等于错误数据

IQR 只能产生“候选异常”：

- 真实高延迟请求：业务异常。
- 批处理任务：合理但极端的业务行为。
- 单位录错：数据质量问题。
- 新服务样本过少：统计基准不稳定。

因此，最终报告应使用“异常候选”“需复核记录”等表述，而不是直接宣布“故障”。

## 6. 相关性：生成假设，不证明因果（20 分钟）

```python
numeric_cols = ["duration_ms", "bytes", "hour"]
corr = df[numeric_cols].corr(method="pearson")
print(corr.round(2))
```

Pearson 相关系数大致解释为：

- 接近 `1`：强正线性关系。
- 接近 `-1`：强负线性关系。
- 接近 `0`：没有明显线性关系，但仍可能有非线性关系。

画散点图检查矩阵背后的形状：

```python
import matplotlib.pyplot as plt
import seaborn as sns

sns.scatterplot(
    data=df,
    x="bytes",
    y="duration_ms",
    hue="source",
    alpha=0.7,
)
plt.title("Bytes and duration by source")
plt.tight_layout()
plt.show()
```

即使相关系数很高，也不能直接推出因果。可能存在：

- 混杂变量：某个服务既返回更多字节，也天然更慢。
- 反向关系：慢请求累积了更多输出，而不是更多输出导致慢。
- 极端值驱动：少数点同时很大，拉高了相关系数。
- 分组效应：各组内部无明显关系，合并后却呈现关系。

更稳妥的报告语言是：

> 在当前样本中，`bytes` 与 `duration_ms` 呈正相关；该结果仅用于生成“响应体大小可能影响延迟”的假设，尚不能证明因果，需要在同一来源、相近请求类型下继续验证。

## 7. 根据问题选择图，而不是根据 API 选图（15 分钟）

| 分析问题 | 推荐图形 | 日志示例 |
| --- | --- | --- |
| 比较类别 | 条形图 | 各来源错误率 |
| 查看分布 | 直方图、箱线图、小提琴图 | 各级别耗时分布 |
| 查看趋势 | 折线图 | 每小时错误率 |
| 查看关系 | 散点图 | 字节数与耗时 |

常见误区：

- 类别很多时仍使用饼图，难以比较角度。
- 时间点顺序混乱时直接画折线，制造不存在的跳变。
- 用截断的纵轴夸大微小差异，却不在图中说明。
- 在样本量很小时使用小提琴图，让平滑形状显得比数据更确定。
- 图中只显示错误率，不显示样本数。

为错误率条形图增加样本数标签：

```python
plot_df = source_quality.reset_index()

ax = sns.barplot(data=plot_df, x="source", y="error_rate")
for index, row in plot_df.iterrows():
    ax.text(
        index,
        row["error_rate"],
        f'n={int(row["sample_count"])}',
        ha="center",
        va="bottom",
    )

ax.set_title("Error rate by source")
ax.set_ylabel("error rate")
plt.tight_layout()
plt.show()
```

## 8. 把 Notebook 写成可复查的报告（15 分钟）

每个核心问题使用同一个模板：

```markdown
### 问题：哪个来源需要优先排查？

**指标定义**：错误率 = ERROR 数 / 该来源总日志数；同时展示样本数和 P95。

**证据**：运行下方代码生成汇总表与图。

**结论**：db 的错误率在当前样本中最高，但样本数只有……

**限制**：采样窗口短，且部分 duration_ms 缺失。

**下一步**：扩大到 7 天数据，并按请求类型分层比较。
```

### 8.1 保证执行顺序可复现

提交前执行：

1. 重启 Notebook 内核。
2. 从第一格开始运行全部单元格。
3. 确认没有依赖旧变量或跳跃执行。
4. 确认输入数据使用相对项目路径。
5. 检查所有表格、图形和结论仍一致。

### 8.2 保留数据质量闸口

可以加入轻量断言，让关键假设在数据变化时立即失败：

```python
required_columns = {
    "timestamp",
    "level",
    "source",
    "duration_ms",
    "bytes",
}

assert required_columns.issubset(df.columns)
assert df["source"].notna().all()
assert df["level"].isin(["DEBUG", "INFO", "WARNING", "ERROR"]).all()
assert df["duration_ms"].dropna().ge(0).all()
```

这些断言表达的是当前分析的输入契约，不是为了让所有脏数据都崩溃。若脏数据本身是分析对象，应先保留原始数据，再生成质量报告和清洗副本。

## 9. 综合实战：完成第四周 EDA 报告（30–45 分钟）

在 `projects/week-04-data/eda_report.ipynb` 中完成以下任务。

### 任务 1：报告入口

用 Markdown 写清：

- 分析目的。
- 数据来源与时间范围。
- 每行代表什么。
- 关键字段含义。
- 本报告要回答的 3 个问题。

### 任务 2：数据质量概览

至少输出：

- 总行数、总列数与重复行数。
- 每列类型与缺失数量。
- `duration_ms` 的有效率。
- 各来源样本量。
- 发现的数据质量问题及处理策略。

### 任务 3：描述性统计

分别对全局和各来源输出：

- `count`
- `mean`
- `median`
- `std`
- `p25`
- `p75`
- `p95`
- `max`

至少解释一处均值与中位数的差异。

### 任务 4：异常候选

同时使用：

- 业务规则：`ERROR`、严重级别或 SLA 超限。
- 统计规则：全局 P95 或来源内 IQR。

比较两种规则的交集和差集，并抽取 5–10 条记录人工检查。

### 任务 5：四类图

各完成一张：

1. 比较图：来源错误率，标注样本量。
2. 分布图：来源或级别的耗时分布。
3. 趋势图：按小时的日志数或错误率。
4. 关系图：`bytes` 与 `duration_ms` 散点图。

每张图下写：结论、限制、下一步。

### 任务 6：管理摘要

用 150–250 字写出：

- 最值得关注的 1–2 个现象。
- 支撑结论的指标。
- 结论目前不能说明什么。
- 下一轮需要补充的数据或实验。

## 10. 课堂练习

### 练习 1：均值会骗人吗

```python
sample = pd.Series([80, 90, 95, 100, 110, 1200])
```

计算 `mean`、`median`、`std`、P95 和 IQR 上界，回答哪个指标最能描述“典型请求”。

### 练习 2：比例与样本量

```python
rates = pd.DataFrame(
    {
        "source": ["api", "db", "worker"],
        "errors": [1, 40, 12],
        "total": [2, 1000, 100],
    }
)
```

计算错误率并按错误率排序。然后写一句不夸大 `api` 风险的结论。

### 练习 3：全局异常与分组异常

对每个 `source` 分别计算 P95，将其合并回明细，比较：

- 超过全局 P95 的记录。
- 超过所属来源 P95 的记录。

解释两组结果为什么不同。

### 练习 4：相关性措辞

若 `bytes` 与 `duration_ms` 的 Pearson 相关系数为 `0.72`，分别写出：

- 一句错误的因果结论。
- 一句合格的分析结论。
- 两个下一步验证动作。

## 11. 小测（10 题）

1. 均值和中位数中，哪个更容易受极端值影响？
2. P95 的准确含义是什么？
3. 为什么报告错误率时必须同时展示样本量？
4. 标准差与 IQR 的主要差异是什么？
5. IQR 上界之外的数据为什么不能直接删除？
6. 为什么分组异常阈值有时比全局阈值合理？
7. 相关系数接近 0 是否能证明两个变量完全无关？
8. 什么时候应使用散点图而不是折线图？
9. Notebook 从头运行失败通常暴露了什么问题？
10. 一条负责任的分析结论应包含哪四部分？

## 12. 进阶挑战（选做）

### 挑战 1：异常规则比较表

构造下表：

| 规则 | 命中数 | 命中率 | ERROR 占比 | 数据问题占比 |
| --- | ---: | ---: | ---: | ---: |
| 全局 P95 |  |  |  |  |
| 来源 P95 |  |  |  |  |
| 来源 IQR |  |  |  |  |
| SLA 规则 |  |  |  |  |

说明哪条规则适合“告警”，哪条更适合“离线分析”。

### 挑战 2：时间窗口敏感性

分别按小时和按天统计错误率。观察聚合粒度改变后，结论是否变化，并解释可能原因。

### 挑战 3：导出报告资产

将关键汇总表导出为 CSV，将图形保存为 PNG：

```python
from pathlib import Path

output_dir = Path("projects/week-04-data/report_assets")
output_dir.mkdir(parents=True, exist_ok=True)

source_quality.to_csv(
    output_dir / "source_quality.csv",
    encoding="utf-8-sig",
)
plt.savefig(
    output_dir / "error_rate_by_source.png",
    dpi=150,
    bbox_inches="tight",
)
```

`utf-8-sig` 主要用于改善某些 Windows Excel 环境打开中文 CSV 时的兼容性；Python 内部处理仍优先使用标准 UTF-8。

## 13. 完成检查

- [ ] 已创建 `projects/week-04-data/eda_report.ipynb`。
- [ ] Notebook 可重启内核后从头运行成功。
- [ ] 已写明数据来源、字段含义和 3 个分析问题。
- [ ] 已报告缺失、重复、类型和样本量。
- [ ] 已解释均值、中位数、P95 与 IQR 中至少三项。
- [ ] 已比较全局规则与分组异常规则。
- [ ] 已区分统计异常、业务异常和数据质量问题。
- [ ] 已输出比较、分布、趋势、关系四类图。
- [ ] 每张图都有“结论 + 限制 + 下一步”。
- [ ] 已完成 150–250 字管理摘要。
- [ ] 已回答小测 10 题。

## 14. 下课前交付

请提交：

1. `projects/week-04-data/eda_report.ipynb`。
2. 一张全局与分组异常规则的对比表。
3. 四张核心图及对应解释。
4. 管理摘要。
5. 小测第 2、3、5、6、7、9、10 题答案。

我会重点 Review：

- 结论是否有明确指标支撑。
- 比例是否同时报告样本量。
- 是否把相关性或异常标记说成了因果或故障事实。
- Notebook 是否能从头复现。
- 图表是否真正回答问题。
- 限制和下一步是否具体可执行。

完成本课后，第 4 周的数据探索阶段结束。下一周将把同一套方法迁移到更完整的真实公开数据，进一步学习系统化清洗、连接、缺失值策略与分析报告交付。
