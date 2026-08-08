# 第 1 周 · 第 3 课：条件判断、异常与日志过滤

预计用时：45–60 分钟

## 本课目标

完成本课后，你能够：

- 使用 `if` 按日志级别过滤数据。
- 使用列表和 `append()` 收集符合条件的事件。
- 使用 `ValueError` 表达参数值不合法。
- 解释 fail-fast 和异常传播。
- 区分 `continue`、`break`、`return` 和 `raise`。
- 为日志过滤和参数校验完成 RED → GREEN → REFACTOR 循环。

## 1. 使用 `if` 过滤日志

Java 条件判断：

```java
if (event.get("level").equals(targetLevel)) {
    filteredEvents.add(event);
}
```

Python：

```python
if event["level"] == level:
    result_list.append(event)
```

Python 使用冒号和缩进定义条件代码块，不需要圆括号和大括号。`==` 比较两个值是否相等。

如果条件为 `True`，执行缩进代码；如果条件为 `False`，直接继续执行后面的代码。

完整的分支结构是：

```python
if condition_a:
    ...
elif condition_b:
    ...
else:
    ...
```

`elif` 相当于 Java 的 `else if`。本课的过滤需求只需要一个 `if`，不必加入没有实际行为的 `else`。

## 2. 使用列表收集结果

Python 的 `list` 是可变容器，类似 Java 的 `ArrayList`：

```python
result_list: list[dict[str, str]] = []
```

向列表末尾添加一个元素：

```python
result_list.append(event)
```

对应 Java：

```java
List<Map<String, String>> resultList = new ArrayList<>();
resultList.add(event);
```

需要区分：

```python
result_list.append(event)       # 添加一个事件字典
result_list.append(line)        # 添加原始日志字符串
result_list.extend(more_events) # 添加另一个集合中的多个元素
```

`append()` 会直接修改原列表并返回 `None`，因此不要写成：

```python
result_list = result_list.append(event)
```

## 3. 第一轮项目练习：按级别过滤日志

目标函数：

```python
def filter_logs_by_level(
    line_array: list[str],
    level: str,
) -> list[dict[str, str]]:
    ...
```

输入：

```python
lines = [
    "2026-08-01T10:15:00|INFO|server started",
    "2026-08-01T10:16:00|ERROR|database timeout",
    "2026-08-01T10:17:00|INFO|request completed",
]
```

调用：

```python
filter_logs_by_level(lines, "ERROR")
```

期望返回：

```python
[
    {
        "timestamp": "2026-08-01T10:16:00",
        "level": "ERROR",
        "message": "database timeout",
    }
]
```

### RED：先定义行为

先在测试中导入尚未实现的函数，并断言返回值是一个包含事件字典的列表。此时会出现：

```text
ImportError: cannot import name 'filter_logs_by_level'
```

这仍然是有效的 RED，因为测试已经证明目标行为尚不存在。

### GREEN：实现最少代码

```python
def filter_logs_by_level(
    line_array: list[str],
    level: str,
) -> list[dict[str, str]]:
    result_list: list[dict[str, str]] = []

    for line in line_array:
        event = parse_log_line(line)

        if event["level"] == level:
            result_list.append(event)

    return result_list
```

每行只解析一次。判断使用解析后的事件字典，并把整个字典添加到结果列表。

### REFACTOR：检查数据流

检查以下问题：

- 是否重复调用 `parse_log_line()`？
- 添加的是事件字典，还是原始字符串？
- 变量名是否使用 `snake_case`？
- 返回类型是否与测试期望一致？

## 4. 使用 `ValueError` 表达非法参数

`ValueError` 是 Python 内置异常，表示对象类型正确，但值不符合函数要求。

例如：

```python
int("abc")
```

参数是字符串，但内容无法转换为整数，因此 Python 抛出 `ValueError`。

在日志过滤函数中，`level` 的类型是 `str`，但空字符串不是有效的目标级别：

```python
if level == "":
    raise ValueError("target level must not be empty")
```

与 Java 大致对应：

```java
if (level.isEmpty()) {
    throw new IllegalArgumentException("target level must not be empty");
}
```

`raise` 相当于 Java 的 `throw`。

## 5. 第二轮项目练习：fail-fast 参数校验

先写异常测试：

```python
def test_rejects_empty_target_level(self) -> None:
    lines = []

    with self.assertRaisesRegex(
        ValueError,
        "target level must not be empty",
    ):
        filter_logs_by_level(lines, "")
```

这里故意使用空日志列表。它可以证明参数校验独立于循环：即使没有任何日志，空级别仍然必须被拒绝。

校验应当放在循环之前：

```python
def filter_logs_by_level(
    line_array: list[str],
    level: str,
) -> list[dict[str, str]]:
    if level == "":
        raise ValueError("target level must not be empty")

    result_list: list[dict[str, str]] = []
    # 后续过滤逻辑
```

这种在函数入口尽早拒绝非法参数的方式称为 fail-fast。

如果把校验放在循环内部，当 `line_array` 是空列表时，循环不会执行，非法参数就会被漏掉。

## 6. 异常传播与处理

假设过滤过程中遇到非法日志：

```python
lines = [
    "2026-08-01T10:15:00|INFO|server started",
    "invalid log line",
    "2026-08-01T10:17:00|ERROR|database timeout",
]
```

`parse_log_line()` 会抛出：

```text
ValueError: expected exactly 3 fields
```

`filter_logs_by_level()` 没有捕获该异常，所以函数立即停止，异常继续传递给调用者。第三行不会被处理。

调用者可以选择处理异常：

```python
try:
    events = filter_logs_by_level(lines, "ERROR")
    print(events)
except ValueError as error:
    print(f"Cannot filter logs: {error}")
```

输出：

```text
Cannot filter logs: expected exactly 3 fields
```

当前项目不在过滤函数内部吞掉异常。底层函数负责准确报告问题，上层调用者决定显示错误、记录日志还是终止程序。

## 7. `continue`、`break`、`return` 和 `raise`

使用 `continue` 的过滤写法：

```python
for line in line_array:
    event = parse_log_line(line)

    if event["level"] != level:
        continue

    result_list.append(event)
```

快速对照：

| 语句 | 行为 |
|---|---|
| `continue` | 跳过当前循环，进入下一轮 |
| `break` | 结束整个循环，继续执行循环之后的代码 |
| `return` | 立即结束整个函数并返回结果 |
| `raise` | 抛出异常，当前函数停止执行 |

当前过滤函数使用正向条件更加简洁，不需要为了使用 `continue` 而改写。循环体很长、需要提前跳过多种情况时，`continue` 会更有价值。

## 8. 小测

先不要运行代码，尝试直接回答：

1. `append()` 与 `extend()` 有什么区别？
2. 为什么 `result_list.append(line)` 不符合过滤函数的返回类型？
3. `ValueError` 适合表达哪一类问题？
4. 为什么空级别校验必须放在循环之前？
5. `continue` 和 `break` 对循环的影响有什么不同？
6. 被调用函数抛出异常，而当前函数没有 `except` 时会发生什么？

## 9. 视频与阅读材料

建议按以下顺序学习：

1. [Microsoft Learn：Conditional Logic](https://learn.microsoft.com/en-us/shows/intro-to-python-development/python-for-beginners-19-of-44-conditional-logic)：建立 `if` 条件判断的直觉。
2. [Python 3.12 官方教程：if 语句](https://docs.python.org/3.12/tutorial/controlflow.html#if-statements)：查看 `if`、`elif` 和 `else`。
3. [Python 3.12 官方教程：break 与 continue](https://docs.python.org/3.12/tutorial/controlflow.html#break-and-continue-statements)：理解循环控制。
4. [Microsoft Learn：Error Handling](https://learn.microsoft.com/en-us/shows/intro-to-python-development/python-for-beginners-17-of-44-error-handling)：了解异常处理概念。
5. [Microsoft Learn：Demo: Error Handling](https://learn.microsoft.com/en-us/shows/intro-to-python-development/python-for-beginners-18-of-44-demo-error-handling)：查看 `try` 和 `except` 的演示。
6. [Python 3.12 官方教程：错误与异常](https://docs.python.org/3.12/tutorial/errors.html)：本课重点阅读 8.2、8.3 和 8.4。
7. [Bilibili：微软 Python 初学者教程（中文字幕）](https://www.bilibili.com/video/BV1aQ4y1d78L/)：可选，只看第 17、18、19 集。

推荐先完成日志过滤，再阅读异常章节。暂时不需要深入自定义异常、异常链和 `finally`。

## 10. 完成检查

- [ ] 能使用 `if` 过滤指定日志级别。
- [ ] 能使用 `append()` 收集事件字典。
- [ ] 能解释 `ValueError` 与 Java `IllegalArgumentException` 的相似之处。
- [ ] 能解释为什么参数校验要 fail-fast。
- [ ] 能说明异常如何在函数调用之间传播。
- [ ] 能区分 `continue`、`break`、`return` 和 `raise`。
- [ ] 已完成过滤和空级别校验的测试。
- [ ] 已运行测试并确认 7 个测试通过。

完成后，进入第 4 课：文件读取与命令行入口。
