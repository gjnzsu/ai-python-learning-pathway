# 第 4 周 · 第 1 课：NumPy 向量化与数据探索基础（Notebook 版）

预计用时：120–150 分钟

## 本课目标

完成本课后，你能够：

- 用 NumPy 取代显式 for 循环实现批量计算。
- 解释向量、矩阵与 `shape`、`dtype`、`axis` 的关系。
- 用点积与范数建立距离与相关性直觉。
- 在不引入数据库和复杂清洗流程的前提下，完成第一轮数据探索。
- 使用 Matplotlib 和 Seaborn 输出可复用的分布与关系图。
- 理解 `Python list` 与 `numpy.ndarray` 在可读性、性能和语义上的差异。
- 为第 4 周后续课程预留可复用的数据表示。

## 0. 第 3 周复盘（10 分钟）

先回顾一下本周结束时的工程能力：

- 包结构、`src` 布局、`pyproject.toml`、`editable install`。
- `pytest` 渐进迁移、`capsys` 与 `tmp_path` 测试策略。
- CLI 的可见行为、错误码、配置与日志边界。

现在切换到数据分析时，重点不是放弃这些工程习惯，而是把它们迁移到 notebook 工作流：

- 将可复现性从 CLI 改为固定随机种子与固定输出文件。
- 将人工排查从 `print()` 改为图表与统计摘要。
- 将行为回归从“终端输出”扩展到“数据处理结果可解释性”。

本课没有新项目工程规则，只是把“软件工程习惯”用于数据科学场景。

## 1. 为什么要先上 NumPy

上一阶段你更多操作的是单条日志。日志分析项目里多数计算是对象级别、字符串级别的。机器学习阶段，计算对象变成“列向量”和“矩阵”，例如：

```text
features = [x1, x2, x3, ...]
pred = w1*x1 + w2*x2 + w3*x3 + b
```

用纯 Python 表达成百上千条样本时，会遇到两个问题：

- 循环写法长，容易出错。
- `for` 嵌套性能差，不利于后续扩展到更大数据。

NumPy 让你把“批量计算”变成一次向量/矩阵运算，思路与 Java 中 `Stream` 更接近，但语义更明确、更接近数学公式。

## 2. 安装与环境

进入项目环境并安装本周依赖：

```powershell
cd projects/log-analyzer
python -m pip install -e ".[dev]"
python -m pip install numpy pandas matplotlib seaborn
```

建议把本周探索放在一个独立 notebook 文件，不要把实验性代码混进 `src/` 生产模块。

```powershell
python -c "import numpy as np; print(np.__version__)"
python -c "import matplotlib; print(matplotlib.__version__)"
python -c "import seaborn as sns; print(sns.__version__)"
```

如果你尚未安装 Jupyter，后续可用 `python -m ipykernel` 挂载虚拟环境；如果缺失，则先补：

```powershell
python -m pip install jupyter ipykernel
python -m ipykernel install --user --name log-analyzer --display-name "Python (log-analyzer)"
```

## 3. 本课任务：构建 `week-04-data` 探索 notebook

新建：

```powershell
cd C:\Users\gjnzsu\Documents\ai-python-learning-pathway
New-Item -ItemType Directory -Path projects\\week-04-data -Force
New-Item -ItemType File -Path projects\\week-04-data\\exploration.ipynb
```

Notebook 里完成以下三段：

1. 生成或读取 3000 行伪日志统计样本。
2. 使用纯 Python 与 NumPy 对比计算 `ERROR` 比例与数值指标。
3. 输出至少 3 张图并写“现象观察”。

这三段是一个完整闭环：数据 -> 计算 -> 可视化 -> 结论。

## 4. NumPy 基础：从 list 到 ndarray

先看对比例子：

```python
import numpy as np

python_list = [1, 2, 3, 4, 5]
numpy_array = np.array(python_list)

print(type(python_list))
print(type(numpy_array))
print(numpy_array + 10)
```

`list + list` 会拼接，而 `ndarray + 10` 会逐元素加。这个差异是本课关键。

你会反复用到的属性：

- `arr.shape`：数组的维度。
- `arr.ndim`：维度数量。
- `arr.dtype`：元素类型。
- `arr.size`：总元素个数。
- `arr.reshape()`：重排形状。

## 5. 向量化替代显式循环

下面用日志字段长度模拟一组“事件长度”作为列向量，比较旧方式和向量化方式。

```python
import numpy as np

lengths_py = []
for s in ["a|INFO|ok", "b|ERROR|timeout", "c|DEBUG|trace"]:
    parts = s.split("|")
    lengths_py.append(len(parts[2]))

lengths_np = np.array(lengths_py)
print(lengths_py)
print(lengths_np.mean())
```

向量化表达：

```python
messages = np.array(["ok", "timeout", "trace"], dtype=str)
message_lengths = np.char.str_len(messages)
print(message_lengths)
print(message_lengths.mean())
```

不要机械追求“全都向量化”。什么时候还是用 Python 更清晰？当算法本身是结构化流程控制（条件分支、状态机）时。

本课实践要求：

- 至少写 3 个你会把 `for` 循环改成 NumPy 运算的地方。
- 每次改写前后都对齐结果。
- 每个改写点都写一句“为何可替换，不可替换”的注释。

## 6. 轴（axis）与切片

创建一个二维数组表示两种指标（`duration`、`bytes`）：

```python
metrics = np.array(
    [
        [12.1, 1024],
        [8.5, 512],
        [7.2, 2048],
    ],
    dtype=float,
)
```

```python
duration_sum = metrics[:, 0].sum()
bytes_sum = metrics[:, 1].sum()
column_means = metrics.mean(axis=0)
row_means = metrics.mean(axis=1)
```

`axis=0` 表示沿列汇总，`axis=1` 表示沿行汇总。  
这个定义很像你在数据库里 `group by` 的“压缩方向”。

## 7. 线性代数直觉：点积与距离

先回忆日志里已经见过的“计数向量”。这里把它推广为一般向量运算。

```python
v = np.array([1.0, 2.0, 3.0])
w = np.array([2.0, 1.0, 0.0])

dot = np.dot(v, w)
norm_v = np.linalg.norm(v)
norm_w = np.linalg.norm(w)
cosine = dot / (norm_v * norm_w)

print(dot)
print(norm_v)
print(cosine)
```

点积越大，通常说明方向对齐越强；范数用于归一化。  
这和机器学习里相似度、线性模型中的权重评分是同一套数学语言。

你也可以先做一个二维示意验证：

```python
points = np.array([[1.0, 2.0], [3.0, 1.0], [4.0, 4.0]])
centroid = points.mean(axis=0)
dist2_to_centroid = np.sum((points - centroid) ** 2, axis=1)
euclid = np.sqrt(dist2_to_centroid)
```

从“对象中心距离”到“聚类近邻”的桥梁，在本周后续课程会继续用到。

## 8. 与 `list` 的对比：一个可复现的性能测试点

用同样任务比较速度前后差异（只做体验，不要求非常精确）：

```python
import time
import numpy as np

data = np.arange(1_000_000)

start = time.perf_counter()
_ = [x * 2 for x in data]
loop_ms = (time.perf_counter() - start) * 1000

start = time.perf_counter()
_ = data * 2
vector_ms = (time.perf_counter() - start) * 1000

print(loop_ms / vector_ms)
```

如果环境稳定，通常向量化写法更快。  
但更重要的是它和数学表达接近，错误率和维护成本更低。

## 9. 可视化第一课

你不是为了“把图画出来”，而是为了验证假设。至少画 3 类图：

1. 直方图：观察单变量分布。
2. 散点图：观察两个变量关系。
3. 箱线图：观察离群值与分位结构。

示例：

```python
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

rng = np.random.default_rng(42)
x = rng.normal(loc=10, scale=2, size=400)
y = 0.8 * x + rng.normal(loc=0, scale=2, size=400)

plt.figure(figsize=(6, 4))
plt.hist(x, bins=25)
plt.title("Feature Distribution")
plt.xlabel("value")
plt.ylabel("count")
plt.tight_layout()
plt.show()

plt.figure(figsize=(6, 4))
sns.scatterplot(x=x, y=y, alpha=0.6)
plt.title("Two-variable relationship")
plt.tight_layout()
plt.show()

sns.boxplot(x=y)
plt.title("y box plot")
plt.show()
```

在 notebook 中保留每张图下方一句“结论”（例如“存在右偏”“离群值明显”“关系近似线性”）。

## 10. 第一轮练习（每题 8 分钟）

### 练习 1：用向量化修复循环

把以下任务改为 NumPy：

- 先把字符串日志级别转为长度 30 的 one-hot 权重（模拟）。
- 统计每种长度奇偶性在 ERROR 里的比例。
- 输出比例矩阵。

### 练习 2：用 axis 改写 `groupby` 思路

用一个 `5 x 4` 的矩阵，分别计算：

- 按列平均
- 按行最大值
- 全局方差

并用一句话解释 axis 选择的语义。

### 练习 3：点积与相似度

构造两组长度都为 4 的向量：

- 计算点积
- 计算 cosine 相似度
- 解释相似度为负值时的含义

### 练习 4：绘图解释

同一个数据，画出 histogram、scatter、boxplot。  
给每张图写一句“我相信/不相信”的判断。

## 11. 本课小测

1. `np.array([1,2,3]) + 1` 与 `[1,2,3] + [1,2,3]` 的结果差异是什么？
2. `axis=0` 与 `axis=1` 的含义各是什么？
3. 为什么 `for` 循环并不总是最合适的批量数据处理方式？
4. `dot(a, b)` 在几何上可理解为什么？
5. 在向量化语句里，`dtype=float` 的意义是什么？
6. `np.random.default_rng(42)` 的用途是什么？
7. 直方图适合回答什么问题，散点图适合回答什么问题，箱线图适合回答什么问题？
8. 为什么可视化结论不能完全替代统计检验？
9. 什么场景下应该保留 Python list 而非立刻转成 ndarray？
10. 本课的图像观察里，如果看到明显离群值，你会先做什么？

## 12. 完成检查

- [ ] 已在 `projects/week-04-data/exploration.ipynb` 新建探索 notebook。
- [ ] 已演示 `list` 与 `numpy.ndarray` 的语义差异。
- [ ] 已完成至少 3 处 `for` 循环到向量化改写。
- [ ] 已用 `shape`、`dtype`、`axis` 解读至少一个二维数组。
- [ ] 已完成点积、范数与一个简单相似度计算。
- [ ] 已输出至少 3 张图（hist、scatter、boxplot）。
- [ ] 每张图都配有简短解释。
- [ ] 练习 1~4 已提交，并标注每题假设与结论。
- [ ] 回答完小测 10 题。

## 13. 下课前交付

给我提交以下内容：

1. `exploration.ipynb` 路径与关键输出截图。
2. 3 个向量化替换片段（含旧写法与新写法对比）。
3. 图像 3 张文件（可以是 notebook 导出的 png）。
4. 小测第 1、2、3、6、7 题答案。
5. 一句本周复盘：哪一步最容易把“数学公式”理解错误成“代码写法”。

我会重点 review：

- 向量化是否正确而非仅仅“能跑”。
- `axis` 选择是否与业务问题一致。
- 图形是否服务于结论而不是堆积视觉。
- 是否把可复用分析习惯（固定随机种子、明确假设、可复现输出）建立起来。
- 下一课将从 DataFrame 语义接力，是否已具备从 ndarray 到表结构迁移能力。

