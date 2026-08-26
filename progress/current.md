# 当前学习进度

## 学习者背景

- 主要技术栈：Java、Spring Boot、微服务
- Python 起点：无语言经验
- 每周投入：10 小时以上
- 数学基础：学过线性代数、概率统计和微积分，目前需要复习
- 路线偏好：Python、机器学习和 AI 应用并重

## 当前状态

- 周次：第 4 周已完成
- 已完成：第 4 周，第 4 课，探索性数据分析报告与统计直觉（2026-08-26）
- 下一课：第 5 周，第 1 课
- 状态：第四周课程、EDA Notebook、复盘小测与最终验收均已完成
- 项目：`projects/week-04-data/eda_report.ipynb`（已从全新内核完整运行）
- 当前学习阶段：NumPy、Pandas、描述性统计、异常识别和可视化基础完成，准备进入真实公开数据分析

## 下一步

1. 进入第 5 周第 1 课，选择并理解一份真实公开数据集。
2. 将第四周的数据质量、样本量、分组基准和图表解释方法迁移到真实数据。
3. 继续巩固图表选择、Pearson 相关系数的线性含义，以及 Notebook 隐藏状态与执行顺序问题。

## 第 4 周 · 第 4 课成果

- 创建 `projects/week-04-data/eda_report.ipynb`，将第四周分析实践整理为 EDA 报告。
- 使用均值、中位数、标准差、P25、P75、P95 与 IQR 描述耗时分布，并理解极端值会显著影响均值。
- 理解 IQR 衡量中间 50% 数据的跨度，使用 `Q3 + 1.5 × IQR` 识别候选异常，同时明确统计异常不等于业务故障。
- 保留 `duration_was_missing` 与 `bytes_was_missing` 标记，避免缺失值填充抹去数据质量信息。
- 区分错误率、耗时分布与数据完整率应使用的样本范围，避免把填充值当成真实观测参与尾部分布分析。
- 使用固定随机种子生成 500 条可复现的合成日志，按来源设置不同的流量、错误概率和基础耗时。
- 使用分组 `transform()` 计算各来源 IQR 上界，并通过交叉表比较 ERROR 与耗时异常候选的覆盖和差异。
- 计算 `duration_ms` 与 `bytes` 的整体及来源内 Pearson 相关系数，理解相关性可以生成假设但不能证明因果。
- 完成关系图、错误率比较图、耗时箱线图和小时趋势图，并为图表补充结论、限制与下一步。
- 认识到比例必须同时展示样本量，不完整时间窗口不能与完整窗口直接比较。
- 完成管理摘要，明确合成数据只能验证分析流程，不能用于推断真实生产系统。
- 完成复盘小测，能够解释均值与中位数、P95、样本量、IQR、分组阈值、相关性边界和负责任的结论结构。
- 明确标准差衡量全部数据围绕均值的波动，IQR 衡量中间 50% 数据的跨度；前者更容易受极端值影响。
- 明确散点图用于观察两个数值变量的关系，折线图用于观察有序或时间变化，直方图与箱线图用于观察分布。
- 理解 Pearson 相关系数接近 0 只表示没有明显线性关系，不能排除非线性或分组关系。
- 理解 Notebook 从头运行失败通常暴露隐藏状态、执行顺序、变量覆盖、路径或依赖问题，而不只是环境设置问题。
- 掌握负责任的分析表达结构：`结论 + 证据 + 限制 + 下一步`。
- 已重启内核并完整运行 Notebook，57 个单元格无错误输出，第四课与第四周课程通过最终验收。

## 第 4 周 · 第 3 课成果

- 创建并完成 `projects/week-04-data/analysis_workflow.ipynb`，建立从原始日志到分析结果导出的完整 Pandas 工作流。
- 使用 `pd.to_datetime(..., errors="coerce")` 与 `pd.to_numeric(..., errors="coerce")` 清洗时间和数值字段，并理解无效值会被转换为 `NaT` 或 `NaN`。
- 使用 `eq()`、`assign()` 和布尔列构造 `is_error`、`is_source_slow`、`is_global_slow`、`priority` 与 `has_data_issue` 等分析特征。
- 使用 `groupby().agg()`、`mean()`、`median()` 和 `quantile(0.95)` 计算来源与级别维度的数量、平均耗时、中位数和 P95。
- 区分 `size()` 与 `count()`：前者统计分组总行数，后者忽略指定列的缺失值。
- 使用 `merge()` 将各来源 P95 合并回日志明细，实现逐行比较所属来源基准。
- 使用 `loc` 配合 `&`、`|` 完成错误、慢日志、关键日志和数据质量问题的多条件筛选。
- 使用 `np.select()` 按条件优先级生成 `critical`、`error`、`slow` 和 `normal` 分类，并理解条件顺序会影响结果。
- 使用 `isna()`、`notna()` 和 `dropna(subset=...)` 检查与筛选缺失数据，区分业务优先级和数据质量维度。
- 绘制按来源错误率、按级别耗时分布和按小时错误率图表，并认识到小样本下分布图与分位数的解释限制。
- 汇总总日志数、错误数、慢日志数、严重日志数、数据问题数和错误率，并计算各来源耗时完整率。
- 将关注日志导出为 `projects/week-04-data/attention_logs.csv`，再通过 `read_csv(..., parse_dates=["timestamp"])` 恢复日期类型并使用 `info()` 检查结构。

## 第 4 周 · 第 2 课成果

- 从字典列表创建日志 `DataFrame`，并使用 `shape`、`columns`、`dtypes`、`info()` 和 `isna()` 检查表结构与数据质量。
- 使用 `pd.to_datetime(..., errors="coerce")` 转换时间戳，使用 `pd.to_numeric(..., errors="coerce")` 将异常数值转换为缺失值。
- 理解 Pandas `Series.median()` 默认忽略缺失值，以及 NumPy `median()` 与 `nanmedian()` 的差异。
- 保留原始 `logs_df`，通过副本 `clean_df` 使用中位数和 `0` 填充缺失值，并在清洗后再次验证缺失值数量。
- 使用布尔条件及 `&` 组合条件筛选日志，理解其与 NumPy 布尔索引的相似性。
- 使用 `loc` 按标签、条件和列名选择数据，使用 `iloc` 按整数位置选择数据，并理解筛选后索引不会自动重排。
- 使用 `groupby().agg()` 统计日志数量、平均耗时与总字节数，并区分包含缺失值的 `size()` 与忽略缺失值的 `count()`。
- 计算耗时字段的有效数量、有效率和百分比，识别填充值可能对分组统计结论造成的影响。
- 使用 `pivot_table()` 构建来源与日志级别的二维交叉汇总表。
- 使用 Pandas 绘图接口与 Matplotlib 绘制分组柱状图，并理解 `plt.xticks()` 可分别设置刻度位置和标签旋转角度。
- 完成并保存 `projects/week-04-data/eda.ipynb`，形成第 4 周数据探索练习成果。

## 第 4 周 · 第 1 课成果

- 创建并使用 `projects/week-04-data/exploration.ipynb`，建立第 4 周 Notebook 数据探索环境。
- 理解 Python `list` 与 NumPy `ndarray` 的语义差异：列表乘法会重复元素，数组乘法会逐元素计算。
- 使用数组标量运算、平方运算和比较运算完成批量计算，建立 NumPy 向量化思维。
- 使用单条件与 `&` 组合条件构造布尔数组，并通过布尔索引筛选分数区间。
- 使用 `size`、`mean()`、`max()`、`min()`、`sum()` 和 `std()` 计算描述性统计指标。
- 利用布尔数组的 `sum()` 和 `mean()` 统计及格人数与及格率，理解布尔值参与数值聚合的方式。
- 使用固定随机数生成器 `np.random.default_rng(42)` 建立可复现的数据实验习惯。
- 使用 Seaborn 与 Matplotlib 绘制成绩直方图、柱状图和箱线图，并添加平均线、及格线、数据标签和中文字体配置。
- 完成温度分析练习，计算平均值与中位数，筛选高于平均温度的数据并统计 30 度以上天数。
- 使用 `np.arange()` 生成横轴编号，使用 `np.where()` 根据温度条件设置柱形颜色，并理解 `plt.xticks()` 的刻度位置参数。

## 第 3 周 · 第 4 课成果

- 使用 `argparse.ArgumentParser` 替代手写参数数量判断，自动生成 `--help`、usage 和位置参数说明。
- 通过第一轮 RED → GREEN 验证 `main(["--help"])` 返回 `0`，帮助文本写入 stdout，stderr 保持为空。
- 保持 `main(arguments) -> int` 与 `run() -> None` 的边界，并安全收窄 `SystemExit.code` 的联合类型，使 mypy 检查通过。
- 使用 `str | Path` 表达日志路径输入，在函数边界统一转换为 `Path`，同时保持字符串调用兼容。
- 将文件资源测试的 patch 目标从 `builtins.open` 调整为 `pathlib.Path.open`，继续验证正常退出和异常路径都会关闭文件。
- 使用 pytest `monkeypatch` 隔离 `sys.argv`，验证 console script 入口只负责参数转发与进程退出。
- 理解并修复 Ruff 的导入排序、顶层空行和嵌套 `with` 规则问题。
- 最终质量门禁：30 个 pytest 测试通过；mypy 检查 5 个源文件无错误；Ruff 检查通过；`git diff --check` 通过。
- 使用 `python -m build` 成功生成 wheel 与源码包，并将 `build/`、`dist/` 加入仓库忽略规则。
- 在全新临时虚拟环境中安装 wheel，并在项目目录外成功运行 `log-analyzer --help` 与日志过滤命令，退出码均为 `0`。
- 更新项目 README，使测试数量、质量检查命令和 CLI 参数格式与实际行为一致。
- 已提交并推送到 `origin/main`，提交为 `fc8017a`。

## 第 3 周 · 第 3 课成果

- 在 CLI 入口引入标准库 `logging`，为参数错误、非法日志级别和文件读取失败记录分级诊断信息。
- 定义合法日志级别集合，并将用户输入统一转换为大写，使日志级别校验不区分大小写。
- 明确 CLI 退出码约定：成功返回 `0`，文件 I/O 失败返回 `1`，参数或日志级别错误返回 `2`。
- 在 `main(arguments)` 中捕获 `OSError`，将不存在文件与权限错误转换为稳定、可测试的错误消息和退出码。
- 保持业务结果写入 stdout、诊断信息写入 stderr，并理解 logging 与直接 `print()` 的职责差异。
- 使用 pytest 的 `tmp_path` 和 `capsys` 验证缺失文件、权限异常、非法级别及标准输出边界。
- 使用 `caplog` 验证 warning 与 error 日志，避免依赖完整日志格式，只断言关键行为与消息。
- 保持 `run()` 只负责把 `main()` 返回值转换为 `SystemExit`，继续维持可测试入口与真实进程入口的边界。
- 完成本课后测试总数达到 24 个，覆盖正常路径、参数错误、日志级别校验与可靠 I/O 错误处理。

## 第 3 周 · 第 2 课成果

- 使用 pytest 9.1.1 直接收集并运行原有 21 个 `unittest.TestCase` 测试，建立渐进迁移基线。
- 使用 `--collect-only`、节点 ID 和 `-k` 区分测试发现、筛选与真正执行。
- 将全部 `TestCase` 迁移为普通测试函数，并使用原生 `assert` 观察数据类字段级失败差异。
- 使用 `pytest.raises(..., match=...)` 验证异常类型与消息，并理解第二个位置参数会进入旧式可调用对象模式。
- 将三个日志级别统计场景改为带领域化 ID 的参数化测试，同时保持总测试节点数为 21。
- 定义依赖内置 `tmp_path` 的 `log_file` fixture，理解 pytest 按参数名称递归解析 fixture 依赖。
- 使用 `tmp_path` 替代 `TemporaryDirectory`，为每个测试提供独立的 `pathlib.Path` 临时目录。
- 使用 `capsys` 分别验证 stdout 与 stderr，并移除手工的输出重定向。
- 保留 `unittest.mock.patch` 测试文件关闭行为，理解迁移 pytest 不等于替换所有标准库测试工具。
- 通过测试数从 21 变为 24 和 23 的两次现象识别重复保留的旧测试类，并恢复为 21 个独立场景。
- 使用 Ruff formatter 统一导入分组、顶层空行与文件结尾，并由 Ruff 发现残留的未使用 `unittest` 导入。
- 最终验证：21 个 pytest 测试通过；mypy 检查 5 个源文件无错误；Ruff 检查通过。

## 第 3 周 · 第 1 课成果

- 创建项目专用 `.venv`，并通过 `sys.executable` 与 `python -m pip --version` 验证解释器和安装器属于同一环境。
- 区分发行名 `course-log-analyzer`、导入包名 `log_analyzer` 和终端命令名 `log-analyzer`。
- 使用 `pyproject.toml` 声明构建后端、Python 版本、开发依赖和 console script。
- 将单文件 `log_analyzer.py` 迁移为 `src/log_analyzer/` 包，并分离 `core.py`、`cli.py` 和 `__main__.py`。
- 使用 `__init__.py` 保持现有包级公开接口，使测试无需了解内部模块位置。
- 使用 editable install 连接虚拟环境与 `src/` 源码，并通过 `__file__` 定位真实导入来源。
- 识别并解决旧同名模块遮蔽新包的问题。
- 理解 `python -m log_analyzer` 经 `__main__.py` 启动，而 `log-analyzer` console script 直接调用 `cli.run()`。
- 将 `*.egg-info/` 加入忽略规则，不提交可重建的安装元数据。
- 手动验证模块入口、console script 和错误参数路径，退出码分别为 `0`、`0` 和 `2`。
- 当前测试：21 个测试通过；mypy 检查 5 个源文件无错误；Ruff 检查通过。

## 第 2 周 · 第 4 课成果

- 区分动态类型、鸭子类型、名义子类型与结构化子类型。
- 使用 mypy 检查现有代码，并为两个空字符串列表补充 `list[str]` 标注。
- 定义只包含 `open_lines()` 的最小 `LogSource` 协议，同时表达迭代器类型与资源生命周期。
- 实现无需显式继承协议的 `FileLogSource`，并复用已有 `open_log_lines()` 资源管理逻辑。
- 使用测试文件中的 `MemoryLogSource` 证明结构化替换，无需磁盘或全局 patch。
- 提取 `print_matching_events()`，让处理管道依赖协议，并让 `main()` 负责组装真实文件源。
- 通过 `BrokenLogSource` 实验观察 mypy 如何报告方法返回类型与协议不兼容。
- 理解单元测试验证运行时行为，mypy 验证静态类型契约，二者不能互相替代。
- 理解 `Any` 会掩盖类型问题并使错误延迟到运行时，不应作为默认修复方式。
- 手动验证正常 CLI 和参数错误路径，退出码分别为 `0` 和 `2`。
- 当前测试：21 个测试通过；mypy 检查 2 个源文件无错误。

## 第 2 周 · 第 3 课成果

- 理解迭代器控制数据如何按需产生，上下文管理器控制资源何时有效与清理。
- 理解 `with`、`__enter__()`、`__exit__()` 以及异常路径上的确定清理。
- 使用 `@contextmanager` 实现 `open_log_lines()`，在文件打开期间交出惰性行迭代器。
- 区分上下文管理器外层的一次 `yield` 与内层数据生成器的多次 `yield`。
- 通过真实临时文件验证逐行读取，通过 `StringIO` 和 `patch()` 验证资源关闭状态。
- 通过测试证明提前停止消费和解析异常都不会导致文件保持打开。
- 将 `read_log_lines()` 重构为保留 `list[str]` 契约的兼容适配层。
- 让 `main()` 在 `with` 块内完成读取、解析、过滤和输出，实现端到端流式处理。
- 手动验证 `ERROR` 和参数缺失两条 CLI 路径，退出码分别为 `0` 和 `2`。
- 当前测试：20 个测试通过。

## 第 2 周 · 第 2 课成果

- 区分可迭代对象与迭代器：前者能够创建迭代器，后者保存遍历位置并提供下一个元素。
- 理解调用生成器函数只创建生成器对象，`next()`、`for` 或 `list()` 才会驱动执行。
- 使用 `Iterable[str]` 接收任意可遍历的字符串来源，并返回 `Iterator[LogEvent]`。
- 实现 `parse_log_lines()`，逐条复用 `parse_log_line()` 惰性解析日志。
- 通过无效第二行测试证明解析错误发生在消费对应元素时，而不是创建生成器时。
- 实现 `filter_events_by_level()`，惰性过滤已经解析的日志事件。
- 使用普通外层函数和内部生成器兼顾立即参数校验与惰性过滤。
- 将 `filter_logs_by_level()` 重构为保留 `list → list` 契约的兼容适配层。
- 让 `main()` 直接组合解析与过滤生成器，并保持 CLI 输出格式和退出码不变。
- 手动验证 `ERROR`、`INFO` 和参数缺失三条 CLI 路径，退出码分别为 `0`、`0` 和 `2`。
- 当前测试：17 个测试通过。

## 第 2 周 · 第 1 课成果

- 定义不可变的 `LogEvent` 数据类，以明确字段替代普通事件字典。
- 理解 `self`、实例属性、类属性以及共享可变类属性的风险。
- 使用 `@dataclass(frozen=True)` 获得字段初始化、对象表示和值相等比较。
- 将 `parse_log_line()` 的返回类型从字典迁移为 `LogEvent`。
- 将统计、过滤和 CLI 输出迁移为属性访问，同时保持外部行为不变。
- 当前测试：13 个测试通过。

## 第 1 周 · 第 4 课成果

- 使用 `with open(..., encoding="utf-8")` 安全读取文本文件。
- 使用 `rstrip("\r\n")` 删除行尾换行符，同时保留日志内容中的其他空白。
- 使用 `TemporaryDirectory` 和 `Path` 测试多行文件、空文件与不存在的文件。
- 区分空文件返回 `[]` 与不存在的文件抛出 `FileNotFoundError`。
- 理解直接执行与模块导入时 `__name__` 的不同取值。
- 使用 `sys.argv[1:]` 将命令行参数传给可独立测试的 `main(arguments)`。
- 区分标准输出、标准错误和进程退出码。
- 手动验证 `ERROR`、`INFO` 和参数缺失三种 CLI 路径。
- 当前测试：12 个测试通过。

## 第 1 周 · 第 3 课成果

- 使用 `if` 按目标级别过滤日志，并返回事件字典列表。
- 使用 `list.append()` 动态收集匹配结果。
- 使用 `ValueError` 和 fail-fast 校验空目标级别。
- 理解异常传播以及 `raise`、`continue`、`return` 和 `break` 的区别。
- 通过空日志列表验证参数校验位于循环之前。
- 完成两轮 RED → GREEN → REFACTOR。
- 当前测试：7 个测试通过。

## 第 1 周 · 第 1 课成果

- 使用 `split` 和序列解包将日志行转换为字典。
- 使用显式字段数量检查提供清晰的 `ValueError`。
- 使用 `unittest` 完成两轮 RED → GREEN → REFACTOR。
- 当前测试：2 个测试通过。

## 第 1 周 · 第 2 课成果

- 使用 `for` 遍历多行日志并复用 `parse_log_line()`。
- 使用 `dict.get(level, 0)` 动态统计任意日志级别。
- 区分 `KeyError` 与 `ValueError`。
- 了解 `while`、`range`、`enumerate` 和 `zip` 的适用场景。
- 为多级别、未知级别和空输入补充测试。
- 当前测试：5 个测试通过。

## 需要巩固的术语

- 序列解包时元素数量不匹配会抛出 `ValueError`，这不是字典越界。
- `event["source"]` 在键不存在时抛出 `KeyError`。
- `event.get("source")` 在键不存在且未提供默认值时返回 `None`；Python 使用 `None`，不是 `null`。
- `counts[level]` 使用变量 `level` 的值作为动态字典键；赋值时可以创建新键。
- `counts.get(level, 0)` 只读取当前值或返回默认值，真正写入发生在赋值语句左侧。
- 直接执行模块时 `__name__` 是 `"__main__"`；被导入时是模块名。
- `sys.argv[0]` 是脚本名称，`sys.argv[1:]` 才是传给程序的用户参数。
- `stdout` 用于正常结果，`stderr` 用于诊断信息；退出码独立表示成功或失败状态。
- 将参数显式传给 `main(arguments)` 比在函数内部直接读取全局 `sys.argv` 更容易测试。
- `Iterable[T]` 表示能提供迭代器的对象；`Iterator[T]` 保存当前位置，并能通过 `next()` 产生下一个元素。
- 列表可以反复创建新迭代器；生成器本身是通常只能消费一次的迭代器。
- 调用包含 `yield` 的函数只创建生成器，函数体会在首次消费时开始执行。
- `list(generator)` 会立即消费生成器直至耗尽或发生异常。
- `parse_log_lines()` 负责解析日志行；文件读取仍由 `read_log_lines()` 负责。
- `yield` 前是上下文进入阶段，`yield` 的值交给 `as` 变量，`yield` 后是退出与清理阶段。
- 已经读取出的字符串可在 `with` 外使用；仍需访问文件的惰性迭代器必须在 `with` 内消费。
- `read_log_lines()` 保留列表契约用于兼容，`open_log_lines()` 为新调用者提供显式的流式资源边界。
