# 当前学习进度

## 学习者背景

- 主要技术栈：Java、Spring Boot、微服务
- Python 起点：无语言经验
- 每周投入：10 小时以上
- 数学基础：学过线性代数、概率统计和微积分，目前需要复习
- 路线偏好：Python、机器学习和 AI 应用并重

## 当前状态

- 周次：第 1 周
- 已完成：第 3 课，条件判断、异常与日志过滤（2026-08-07）
- 下一课：第 4 课，文件读取与命令行入口
- 状态：第 3 课已完成
- 项目：日志分析 CLI
- 当前 TDD 阶段：日志过滤与空级别校验 GREEN

## 下一步

1. 从文件读取多行日志。
2. 为日志分析器设计命令行入口。
3. 继续使用测试驱动文件读取与参数行为。

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
