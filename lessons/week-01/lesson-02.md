# 第 1 周 · 第 2 课：控制流、循环与日志统计

预计用时：30–45 分钟

## 本课目标

完成本课后，你能够：

- 使用 `for` 遍历多行日志。
- 使用字典动态统计各日志级别的数量。
- 区分 `KeyError` 与 `ValueError`。
- 解释 `while`、`range`、`enumerate` 和 `zip` 的基本用途。
- 完成 `count_log_levels()` 的 RED → GREEN → REFACTOR 循环。

## 1. 使用 `for` 遍历日志

Java 增强 `for`：

```java
for (String line : lines) {
    System.out.println(line);
}
```

Python：

```python
for line in lines:
    print(line)
```

Python 的 `for` 直接遍历可迭代对象中的值，不需要声明元素类型，也不需要手动维护索引。代码块由缩进表示。

结合第一课的日志解析函数：

```python
for line in lines:
    event = parse_log_line(line)
    print(event["level"])
```

如果日志级别依次是 `INFO → ERROR → INFO`，输出为：

```text
INFO
ERROR
INFO
```

`print()` 默认会在每次输出后换行。

## 2. 使用字典计数

可以先初始化已知日志级别：

```python
counts = {
    "INFO": 0,
    "ERROR": 0,
}
```

然后更新计数：

```python
counts[level] += 1
```

它等价于：

```python
counts[level] = counts[level] + 1
```

但如果第一次遇到 `WARN`，读取 `counts["WARN"]` 时会抛出 `KeyError`。为了支持任意日志级别，可以使用：

```python
counts[level] = counts.get(level, 0) + 1
```

含义是：

- 键存在：取得当前计数并加 `1`。
- 键不存在：使用默认值 `0`，然后加 `1`。

需要区分：

- `KeyError`：访问字典中不存在的键。
- `ValueError`：值或格式不符合函数要求，例如日志字段数量不是 3。

## 3. 项目练习：统计日志级别

目标函数：

```python
def count_log_levels(lines: list[str]) -> dict[str, int]:
    ...
```

类型对应关系：

```text
list[str]      ≈ Java List<String>
dict[str, int] ≈ Java Map<String, Integer>
```

### RED：先运行失败测试

进入项目目录并运行：

```powershell
cd projects/log-analyzer
python -m unittest discover -s tests -v
```

如果函数还不存在，你会看到类似错误：

```text
ImportError: cannot import name 'count_log_levels'
```

测试尚未开始执行，因为测试模块无法导入目标函数。这仍然是有效的 RED。

### GREEN：实现最少代码

在 `log_analyzer.py` 中加入：

```python
def count_log_levels(lines: list[str]) -> dict[str, int]:
    """Count log entries grouped by level."""

    counts: dict[str, int] = {}

    for line in lines:
        event = parse_log_line(line)
        level = event["level"]
        counts[level] = counts.get(level, 0) + 1

    return counts
```

再次运行测试。目标是 3 个测试全部通过。

### REFACTOR：判断是否真的需要重构

检查以下问题：

- 函数名是否准确表达行为？
- `lines`、`event`、`level` 和 `counts` 是否容易理解？
- 是否存在重复逻辑？
- 是否加入了当前测试没有要求的功能？

目前函数很短、变量意图清楚，不需要为了“完成 REFACTOR”而强行改写。重构的目标是改善设计，不是制造变化。

## 4. 四个常用循环工具

### `while`：条件成立时持续执行

```python
attempts = 0

while attempts < 3:
    attempts += 1
```

适合不知道确切循环次数、但知道继续条件的场景，例如重试直到成功或达到上限。

### `range`：生成整数序列

```python
for number in range(3):
    print(number)
```

输出：

```text
0
1
2
```

`range(3)` 不包含终点 `3`。需要重复固定次数或生成整数序列时使用它。

### `enumerate`：同时取得位置和值

```python
for line_number, line in enumerate(lines, start=1):
    print(line_number, line)
```

适合显示符合人类习惯、从 `1` 开始的日志行号。通常比 `range(len(lines))` 更直接。

### `zip`：并行遍历多个序列

```python
levels = ["INFO", "ERROR"]
limits = [100, 10]

for level, limit in zip(levels, limits):
    print(level, limit)
```

输出：

```text
INFO 100
ERROR 10
```

默认情况下，`zip` 会在最短的序列结束时停止。

### 快速选择

| 需求 | 工具 |
|---|---|
| 直接遍历集合 | `for` |
| 条件成立时继续 | `while` |
| 生成整数序列 | `range` |
| 同时需要位置和值 | `enumerate` |
| 并行遍历多个序列 | `zip` |

## 5. 小测

先不要运行代码，尝试直接回答：

1. `list(range(3))` 的结果是什么？
2. 为什么 `counts["WARN"] += 1` 可能抛出 `KeyError`？
3. 需要同时取得日志行号和内容时，应该优先使用什么？
4. `zip(["INFO", "ERROR"], [100])` 会产生几组数据？
5. 日志级别依次为 `INFO → ERROR → INFO`，最终统计结果是什么？

## 6. 视频与阅读材料

建议只看与本课相关的短内容，不要一次看完整套课程：

1. [Microsoft：Loops | Python for Beginners（概念，约 6 分钟）](https://www.youtube.com/watch?v=LrOAl8vUFHY)
2. [Microsoft Learn：Demo: Loops（演示，约 4 分钟）](https://learn.microsoft.com/en-us/shows/intro-to-python-development/python-for-beginners-28-of-44-demo-loops)
3. [Bilibili：微软 Python 初学者教程（中文字幕）](https://www.bilibili.com/video/BV1aQ4y1d78L/)：只看第 27 集“循环”和第 28 集“实操 for 和 while 循环”。

按需查阅：

- [Python 3.12 官方教程：控制流](https://docs.python.org/3.12/tutorial/controlflow.html)
- [Python 3.12 官方教程：循环技巧](https://docs.python.org/3.12/tutorial/datastructures.html#looping-techniques)

推荐顺序：先读本课第 1–3 节并完成项目，再看两个短视频，最后学习第 4 节。

## 7. 完成检查

- [ ] 能解释 `for` 与 `while` 的区别。
- [ ] 能解释为什么未知字典键会产生 `KeyError`。
- [ ] 已实现 `count_log_levels()`。
- [ ] 已运行测试并确认 3 个测试通过。
- [ ] 能说出 `range`、`enumerate` 和 `zip` 的适用场景。
- [ ] 已回答小测的 5 个问题。

完成后，把测试结果和小测答案发给老师。
