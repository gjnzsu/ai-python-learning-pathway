# 当前学习进度

## 学习者背景

- 主要技术栈：Java、Spring Boot、微服务
- Python 起点：无语言经验
- 每周投入：10 小时以上
- 数学基础：学过线性代数、概率统计和微积分，目前需要复习
- 路线偏好：Python、机器学习和 AI 应用并重

## 当前状态

- 周次：第 1 周已完成
- 已完成：第 4 课，文件读取与命令行入口（2026-08-09）
- 下一课：第 2 周，第 1 课，类与数据类
- 状态：第 4 课已完成
- 项目：日志分析 CLI
- 当前 TDD 阶段：文件读取、CLI 正常参数与用法错误 GREEN

## 下一步

1. 复盘第 1 周的 Python 与 Java 心智模型差异。
2. 学习 Python 类、实例属性和数据类。
3. 将日志事件从普通字典逐步演进为类型更明确的数据对象。

## 第 4 课成果

- 使用 `with open(..., encoding="utf-8")` 安全读取文本文件。
- 使用 `rstrip("\r\n")` 删除行尾换行符，同时保留日志内容中的其他空白。
- 使用 `TemporaryDirectory` 和 `Path` 测试多行文件、空文件与不存在的文件。
- 区分空文件返回 `[]` 与不存在的文件抛出 `FileNotFoundError`。
- 理解直接执行与模块导入时 `__name__` 的不同取值。
- 使用 `sys.argv[1:]` 将命令行参数传给可独立测试的 `main(arguments)`。
- 区分标准输出、标准错误和进程退出码。
- 手动验证 `ERROR`、`INFO` 和参数缺失三种 CLI 路径。
- 当前测试：12 个测试通过。

## 第 3 课成果

- 使用 `if` 按目标级别过滤日志，并返回事件字典列表。
- 使用 `list.append()` 动态收集匹配结果。
- 使用 `ValueError` 和 fail-fast 校验空目标级别。
- 理解异常传播以及 `raise`、`continue`、`return` 和 `break` 的区别。
- 通过空日志列表验证参数校验位于循环之前。
- 完成两轮 RED → GREEN → REFACTOR。
- 当前测试：7 个测试通过。

## 第 1 课成果

- 使用 `split` 和序列解包将日志行转换为字典。
- 使用显式字段数量检查提供清晰的 `ValueError`。
- 使用 `unittest` 完成两轮 RED → GREEN → REFACTOR。
- 当前测试：2 个测试通过。

## 第 2 课成果

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
