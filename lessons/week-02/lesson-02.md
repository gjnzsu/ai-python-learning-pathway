# 第 2 周 · 第 2 课：可迭代对象、迭代器与生成器

预计用时：90–120 分钟

## 本课目标

完成本课后，你能够：

- 区分可迭代对象（iterable）与迭代器（iterator）。
- 解释 `for`、`iter()`、`next()` 和 `StopIteration` 之间的关系。
- 使用包含 `yield` 的生成器函数按需产生数据。
- 说明 `return` 与 `yield` 的执行模型差异。
- 使用 `Iterable[T]` 和 `Iterator[T]` 标注数据处理函数。
- 识别迭代器“一次性消费”和惰性执行带来的常见陷阱。
- 将日志解析与过滤改造成可组合的惰性数据处理管道。
- 在保留现有 CLI 行为和旧接口的前提下完成增量重构。

## 1. 从一次性构建列表到按需处理数据

当前日志分析器先读取完整文件，再分别创建中间列表：

```text
日志文件
    ↓ read_log_lines()
list[str]
    ↓ parse_log_line()，循环调用
LogEvent
    ↓ filter_logs_by_level()
list[LogEvent]
    ↓ main()
终端输出
```

对于目前只有三行的 `sample.log`，这种实现完全可用。但如果日志文件包含数百万行，程序会先把所有文本行放进内存，再为匹配结果创建另一个列表。

很多数据处理任务并不需要同时持有所有结果。例如，CLI 可以在找到一条 `ERROR` 日志时立刻输出它，然后继续读取下一条。

本课把中间过程改造成惰性管道：

```text
Iterable[str]
    ↓ parse_log_lines()
Iterator[LogEvent]
    ↓ filter_events_by_level()
Iterator[LogEvent]
    ↓ for
逐条消费结果
```

“惰性”不是“更慢”，也不是“后台异步执行”。它表示：消费者请求下一个元素时，生产者才计算下一个元素。

## 2. `for` 循环背后的迭代协议

第一周已经使用过很多 `for` 循环：

```python
for line in lines:
    print(line)
```

只要对象是可迭代对象，`for` 就能遍历它。列表、元组、字符串、字典、集合和打开的文件对象都可迭代。

概念上，Python 会执行下面的过程：

```python
iterator = iter(lines)

while True:
    try:
        line = next(iterator)
    except StopIteration:
        break

    print(line)
```

实际代码应继续使用清晰的 `for`，这里展开只是为了观察协议。

### 可迭代对象与迭代器

- 可迭代对象能通过 `iter(obj)` 提供一个迭代器。
- 迭代器能通过 `next(iterator)` 逐个提供元素。
- 没有更多元素时，迭代器抛出 `StopIteration`。

列表是可迭代对象，但列表本身不是列表迭代器：

```python
lines = ["INFO|started", "ERROR|timeout"]
iterator = iter(lines)

print(iterator is lines)  # False
print(next(iterator))     # INFO|started
print(next(iterator))     # ERROR|timeout
next(iterator)            # 抛出 StopIteration
```

对同一个列表调用两次 `iter()`，通常会得到两个相互独立的迭代器：

```python
first_iterator = iter(lines)
second_iterator = iter(lines)

print(next(first_iterator))
print(next(second_iterator))
```

两次输出都是第一条数据。

### 迭代器通常只能消费一次

迭代器会保存当前遍历位置。一旦耗尽，再次遍历不会自动回到开头：

```python
iterator = iter(["INFO", "ERROR"])

print(list(iterator))  # ["INFO", "ERROR"]
print(list(iterator))  # []
```

这与列表不同：列表保存元素，可以反复创建新迭代器。调试生成器时，常见误判就是先用 `list()` 或调试器展开了结果，随后正式代码看到空数据。

## 3. 与 Java `Iterable`、`Iterator` 和 Stream 对照

| 关注点 | Java | Python |
| --- | --- | --- |
| 可遍历来源 | `Iterable<T>` | `Iterable[T]` / 支持迭代协议的对象 |
| 遍历状态 | `Iterator<T>` | `Iterator[T]` |
| 获取迭代器 | `value.iterator()` | `iter(value)` |
| 获取下一个元素 | `iterator.next()` | `next(iterator)` |
| 是否还有元素 | `hasNext()` | 没有对应调用；耗尽时抛出 `StopIteration` |
| 惰性变换 | `Stream<T>` | 生成器、生成器表达式和 `itertools` |
| 增强循环 | `for (T item : items)` | `for item in items` |

Python 的迭代器协议与 Java `Iterator` 很接近，但 Python 不使用 `hasNext()`。`for` 会捕获 `StopIteration` 并正常结束循环。

生成器可以承担一部分 Java Stream 的角色，但两者不是一一对应：

- Python 生成器本身就是迭代器，通常只能消费一次。
- 生成器函数使用普通控制流和 `yield` 描述数据如何产生。
- Java Stream 提供 `map`、`filter`、`collect` 等集中式操作 API。
- Python 通常组合 `for`、生成器表达式、生成器函数和标准库工具。

本课不追求把 Java Stream 写法逐字翻译成 Python，而是建立 Python 自己的迭代心智模型。

## 4. 生成器函数与 `yield`

普通函数遇到 `return` 时结束，并返回一个最终结果：

```python
def collect_levels(events: list[LogEvent]) -> list[str]:
    levels: list[str] = []

    for event in events:
        levels.append(event.level)

    return levels
```

生成器函数使用 `yield` 逐个产生值：

```python
from collections.abc import Iterable, Iterator


def iter_levels(events: Iterable[LogEvent]) -> Iterator[str]:
    for event in events:
        yield event.level
```

调用生成器函数时，函数体不会立刻完整运行：

```python
levels = iter_levels(events)
```

此时得到的是生成器对象。消费它时才开始执行：

```python
first_level = next(levels)

for level in levels:
    print(level)
```

每次执行到 `yield`：

1. 把当前值交给调用者。
2. 暂停函数并保留局部变量与执行位置。
3. 下一次请求元素时，从暂停处继续。
4. 函数自然结束时，自动以 `StopIteration` 通知消费者。

### `return` 与 `yield` 的核心差异

```python
def with_return() -> int:
    return 1
    return 2
```

`with_return()` 只能得到 `1`，第一次 `return` 已经结束函数。

```python
def with_yield() -> Iterator[int]:
    yield 1
    yield 2
```

`list(with_yield())` 得到 `[1, 2]`，因为生成器会在两次请求之间暂停和恢复。

不要把 `yield` 理解成“返回一个列表元素”。它改变了整个函数的调用方式：只要函数体中包含 `yield`，调用该函数就会创建生成器对象。

## 5. 类型标注：接受 `Iterable`，返回 `Iterator`

本课从 `collections.abc` 导入类型：

```python
from collections.abc import Iterable, Iterator
```

如果函数只需要遍历输入，不需要索引、追加或读取长度，参数使用 `Iterable[T]` 比 `list[T]` 更准确：

```python
def parse_log_lines(lines: Iterable[str]) -> Iterator[LogEvent]:
    for line in lines:
        yield parse_log_line(line)
```

这个函数可以接收：

- `list[str]`
- `tuple[str, ...]`
- 文件对象产生的文本行
- 另一个产生字符串的生成器

返回类型是 `Iterator[LogEvent]`，明确告诉调用者结果按需产生并可能被消费完。

### 为什么不是 `Generator`

如果调用者只需要 `for` 和 `next()`，用 `Iterator[LogEvent]` 表达所需能力就足够。`Generator` 还暴露 `send()`、`throw()` 和 `close()` 等更具体的生成器能力，本课不需要这些接口。

这与面向接口编程的原则相同：参数和返回值优先表达真正需要的最小能力。

## 6. 开始前确认基线

进入项目目录：

```powershell
cd projects/log-analyzer
python -m unittest discover -s tests -v
```

开始本课前应有 13 个测试通过。如果数量不同或有失败，先保存文件并检查当前状态，不要在失败基线上继续重构。

本课采用增量方式新增两个惰性函数：

```python
parse_log_lines(lines)
filter_events_by_level(events, level)
```

现有 `parse_log_line()`、`filter_logs_by_level()`、`read_log_lines()` 和 CLI 外部输出暂时保持兼容。

## 7. 第一轮 TDD：逐条解析日志

目标接口：

```python
def parse_log_lines(
    lines: Iterable[str],
) -> Iterator[LogEvent]:
    ...
```

### RED：先描述多个结果

在测试文件的导入列表中加入 `parse_log_lines`，然后新增：

```python
class ParseLogLinesTest(unittest.TestCase):
    def test_parses_multiple_lines(self) -> None:
        lines = [
            "2026-08-08T10:00:00|INFO|server started",
            "2026-08-08T10:01:00|ERROR|database timeout",
        ]

        events = list(parse_log_lines(lines))

        self.assertEqual(
            events,
            [
                LogEvent(
                    timestamp="2026-08-08T10:00:00",
                    level="INFO",
                    message="server started",
                ),
                LogEvent(
                    timestamp="2026-08-08T10:01:00",
                    level="ERROR",
                    message="database timeout",
                ),
            ],
        )
```

这里在测试边界使用 `list(...)`，把惰性结果具体化后比较内容。生产代码仍然可以逐条消费。

运行单个测试类：

```powershell
python -m unittest tests.test_log_analyzer.ParseLogLinesTest -v
```

因为函数尚不存在，预期先看到导入失败。这是本轮 RED。

### GREEN：使用 `yield` 复用单行解析

在 `log_analyzer.py` 顶部加入：

```python
from collections.abc import Iterable, Iterator
```

然后实现：

```python
def parse_log_lines(
    lines: Iterable[str],
) -> Iterator[LogEvent]:
    for line in lines:
        yield parse_log_line(line)
```

再次运行测试。这里不要复制 `split("|")` 和字段校验；生成器只负责“逐条协调”，单行规则仍由 `parse_log_line()` 负责。

## 8. 第二轮 TDD：证明解析是惰性的

第一个测试只证明结果正确，还不能区分“先创建完整列表”与“按需产生结果”。新增一个测试观察执行时机。

### RED：无效的第二行不应阻止取得第一行

```python
def test_parses_lines_lazily(self) -> None:
    lines = [
        "2026-08-08T10:00:00|INFO|server started",
        "invalid line",
    ]

    events = parse_log_lines(lines)
    first_event = next(events)

    self.assertEqual(first_event.level, "INFO")

    with self.assertRaisesRegex(
        ValueError,
        "expected exactly 3 fields",
    ):
        next(events)
```

这个测试表达两个重要行为：

- 创建 `events` 时还没有解析所有输入。
- 请求第二个事件时才暴露第二行的格式错误。

如果第一轮使用列表推导式并返回完整列表，这个测试会在 `parse_log_lines(lines)` 调用处提前失败。

### GREEN

第一轮的 `yield` 实现已经满足这个行为，所以新增测试可能直接通过。它仍然有价值：测试记录了惰性执行这一接口语义，防止未来重构偷偷恢复成预先构建列表。

## 9. 第三轮 TDD：惰性过滤事件

现有 `filter_logs_by_level()` 同时解析字符串和创建结果列表。新增更小的管道步骤：它只接收事件并按级别过滤。

目标接口：

```python
def filter_events_by_level(
    events: Iterable[LogEvent],
    level: str,
) -> Iterator[LogEvent]:
    ...
```

### RED：过滤已经解析的事件

在导入列表中加入 `filter_events_by_level`，然后新增：

```python
class FilterEventsByLevelTest(unittest.TestCase):
    def test_yields_matching_events(self) -> None:
        info_event = LogEvent(
            timestamp="2026-08-08T10:00:00",
            level="INFO",
            message="server started",
        )
        error_event = LogEvent(
            timestamp="2026-08-08T10:01:00",
            level="ERROR",
            message="database timeout",
        )

        events = filter_events_by_level(
            [info_event, error_event],
            "ERROR",
        )

        self.assertEqual(list(events), [error_event])
```

运行：

```powershell
python -m unittest tests.test_log_analyzer.FilterEventsByLevelTest -v
```

### GREEN：最直观的生成器实现

```python
def filter_events_by_level(
    events: Iterable[LogEvent],
    level: str,
) -> Iterator[LogEvent]:
    for event in events:
        if event.level == level:
            yield event
```

这个函数不关心事件来自列表、文件还是另一个生成器。它只依赖 `Iterable[LogEvent]` 协议。

## 10. 生成器陷阱：参数校验也会被延迟

我们希望继续保持空目标级别 fail-fast：

```python
with self.assertRaisesRegex(
    ValueError,
    "target level must not be empty",
):
    filter_events_by_level([], "")
```

如果直接把校验写进包含 `yield` 的函数：

```python
def filter_events_by_level(events, level):
    if level == "":
        raise ValueError("target level must not be empty")

    for event in events:
        if event.level == level:
            yield event
```

上面的测试不会看到异常。原因不是校验条件错误，而是调用生成器函数只创建生成器对象，函数体尚未开始执行。

异常会延迟到第一次消费：

```python
events = filter_events_by_level([], "")
next(events)  # 此时才执行参数校验
```

### 保持立即校验的实现

让外层函数正常执行校验，再返回一个内部生成器：

```python
def filter_events_by_level(
    events: Iterable[LogEvent],
    level: str,
) -> Iterator[LogEvent]:
    if level == "":
        raise ValueError("target level must not be empty")

    def matching_events() -> Iterator[LogEvent]:
        for event in events:
            if event.level == level:
                yield event

    return matching_events()
```

外层函数没有 `yield`，因此调用时立即运行校验；内部生成器仍然惰性遍历事件。

把空级别测试加入 `FilterEventsByLevelTest`，确认调用函数时就抛出异常：

```python
def test_rejects_empty_target_level_immediately(self) -> None:
    with self.assertRaisesRegex(
        ValueError,
        "target level must not be empty",
    ):
        filter_events_by_level([], "")
```

这说明惰性执行会影响的不只是性能，还包括异常发生的时间。

## 11. 第四轮 TDD：组合管道并保持旧接口

现在可以组合两个步骤：

```python
lines = [
    "2026-08-08T10:00:00|INFO|server started",
    "2026-08-08T10:01:00|ERROR|database timeout",
]

events = parse_log_lines(lines)
matching_events = filter_events_by_level(events, "ERROR")

for event in matching_events:
    print(event.message)
```

数据流是：

```text
list[str]
    → parse_log_lines
    → Iterator[LogEvent]
    → filter_events_by_level
    → Iterator[LogEvent]
    → for
```

为了保持现有调用者兼容，让旧函数成为适配层：

```python
def filter_logs_by_level(
    line_array: list[str],
    level: str,
) -> list[LogEvent]:
    events = parse_log_lines(line_array)
    matching_events = filter_events_by_level(events, level)
    return list(matching_events)
```

旧接口仍返回 `list[LogEvent]`，所以第一周和第二周第一课的测试不需要修改。新管道负责解析与过滤，旧函数只负责兼容旧调用方式。

运行全部测试：

```powershell
python -m unittest discover -s tests -v
```

预期原有 13 个测试和本课新增测试全部通过。

## 12. 让 CLI 直接消费惰性管道

当前 `main()` 可以继续调用兼容函数，也可以直接组合新函数：

```python
def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        print(
            "usage: python log_analyzer.py <log-file> <level>",
            file=sys.stderr,
        )
        return 2

    file_path, level = arguments
    lines = read_log_lines(file_path)
    events = parse_log_lines(lines)
    matching_events = filter_events_by_level(events, level)

    for event in matching_events:
        print(f"{event.timestamp}|{event.level}|{event.message}")

    return 0
```

这里的解析和过滤已经惰性执行，但 `read_log_lines()` 仍会把文件读入列表。这是有意保留的边界：

- 本课专注迭代器和生成器。
- 下一课学习上下文管理器时，再安全处理“文件打开期间惰性读取”的资源生命周期。
- 不在一次重构中同时改变文件资源管理、解析、过滤和 CLI。

运行 CLI 测试，确认外部行为没有变化：

```powershell
python -m unittest tests.test_log_analyzer.MainTest -v
```

## 13. 生成器表达式

简单的惰性变换可以使用生成器表达式：

```python
levels = (event.level for event in events)
```

它与列表推导式只有括号不同，但执行方式不同：

```python
level_list = [event.level for event in events]
level_iterator = (event.level for event in events)
```

- 方括号立即创建完整列表。
- 圆括号创建惰性生成器。

过滤函数也可以写成：

```python
return (event for event in events if event.level == level)
```

本课项目优先使用命名清晰的生成器函数，因为它更容易加入分支、校验和调试。生成器表达式适合逻辑很短、立即交给 `sum()`、`any()`、`all()` 或其他消费者的场景。

示例：

```python
error_count = sum(
    1
    for event in events
    if event.level == "ERROR"
)
```

## 14. 常见错误与定位方法

### 把生成器当作列表比较

```python
self.assertEqual(parse_log_lines(lines), expected_events)
```

这比较的是生成器对象与列表，不是里面的元素。测试有限结果时使用：

```python
self.assertEqual(list(parse_log_lines(lines)), expected_events)
```

### 同一个生成器遍历两次

```python
events = parse_log_lines(lines)

print(list(events))
print(list(events))  # []
```

如果确实需要反复读取，应保存为列表，或者重新调用生成器函数创建新的迭代器。

### 忘记消费生成器

```python
events = parse_log_lines(lines)
```

这行只创建管道，不会解析日志。需要通过 `for`、`next()`、`list()`、`sum()` 等消费者驱动执行。

### 以为生成器自动并行或异步

普通生成器仍在当前线程同步执行。它节省中间结果占用的内存，并允许按需计算，但不会自动使用多核、线程或异步 I/O。

### 捕获 `StopIteration` 作为日常业务逻辑

手动调用 `next()` 时可能需要处理 `StopIteration`，普通遍历应使用 `for`。不要在生成器内部随意抛出或吞掉它来表达一般业务错误。

## 15. REFACTOR：检查管道边界

完成后检查：

- `parse_log_line()` 只负责一行文本到一个 `LogEvent`。
- `parse_log_lines()` 只负责逐条复用单行解析。
- `filter_events_by_level()` 只负责过滤已经解析的事件。
- `filter_logs_by_level()` 是保留旧接口的适配层。
- `main()` 只负责连接读取、解析、过滤与输出。
- 没有在多个函数中重复字段拆分和错误消息。
- 惰性函数返回 `Iterator[...]`，只需要遍历的输入接收 `Iterable[...]`。

不要为了使用类而手写 `__iter__()` 和 `__next__()`。本项目的转换逻辑用生成器函数更短、更清晰，也能自动维护迭代状态。

## 16. 手动验证完整 CLI

在 `projects/log-analyzer` 目录运行：

```powershell
python log_analyzer.py sample.log ERROR
$LASTEXITCODE
```

预期输出：

```text
2026-08-08T10:01:00|ERROR|database timeout
0
```

再验证 INFO：

```powershell
python log_analyzer.py sample.log INFO
$LASTEXITCODE
```

最后验证参数缺失：

```powershell
python log_analyzer.py
$LASTEXITCODE
```

预期向标准错误输出用法提示，退出码为 `2`。内部改成惰性管道后，CLI 文本格式与退出码都不能改变。

## 17. 小测

先不要运行代码，尝试直接回答：

1. 可迭代对象与迭代器的职责分别是什么？
2. `for item in values` 在幕后如何使用 `iter()` 和 `next()`？
3. Python 为什么不需要 Java `Iterator.hasNext()`？
4. 为什么同一个列表可以遍历多次，而同一个生成器通常只能遍历一次？
5. 调用包含 `yield` 的函数时，函数体会立刻完整执行吗？
6. `return` 和 `yield` 对函数执行状态有什么不同影响？
7. 为什么 `parse_log_lines()` 的参数使用 `Iterable[str]`，而不是限定为 `list[str]`？
8. 为什么测试生成器内容时经常使用 `list(generator)`？这样做有什么副作用？
9. 为什么把参数校验直接写在生成器函数体中会延迟异常？
10. 本课为什么暂时不把 `read_log_lines()` 也改成文件生成器？

## 18. 完成检查

- [ ] 能用自己的话区分 iterable 和 iterator。
- [ ] 能解释 `for`、`iter()`、`next()` 与 `StopIteration` 的关系。
- [ ] 能说明列表与生成器在重复遍历上的差异。
- [ ] 已实现 `parse_log_lines()` 并通过多行解析测试。
- [ ] 已通过测试证明无效的第二行会延迟到第二次消费时才报错。
- [ ] 已实现 `filter_events_by_level()`。
- [ ] 空目标级别仍然在调用时立即抛出 `ValueError`。
- [ ] 已让旧 `filter_logs_by_level()` 复用新管道并保持返回列表。
- [ ] 已理解 `Iterable[T]` 与 `Iterator[T]` 类型标注。
- [ ] 已运行全部自动化测试并确认通过。
- [ ] 已手动验证 CLI 输出和退出码未变化。
- [ ] 已回答小测的 10 个问题。

## 19. 视频与阅读材料

建议按“短视频建立直觉 → 阅读讲义 → 完成 TDD → 官方文档查漏”的顺序学习。

### 推荐视频

1. [Real Python：Understanding Generators（11:33）](https://realpython.com/videos/understanding-generators/)：用代码讲解生成器函数、`yield`、惰性迭代和生成器表达式。本课先看这一段即可；英文视频带完整文字稿。
2. [PyCon US 2013：Iteration & Generators—the Python Way](https://pyvideo.org/pycon-us-2013/iteration-generators-the-python-way.html)：Luciano Ramalho 从 `for`、推导式到迭代器协议和生成器，适合有 Java 经验的开发者建立完整的 Python 迭代心智模型。内容较长，可以重点观看前半部分及生成器示例。

推荐先看第一段，再完成第 7–12 节；第二段用于课后巩固，不影响本课验收。

### 进阶选看

- [PyCon US 2014：Generators—The Final Frontier](https://pyvideo.org/pycon-us-2014/generators-the-final-frontier.html)：David Beazley 展示生成器在控制流、上下文管理器等方向的高级用法。当前只需知道它存在，不要提前模仿 `send()`、协程和 actor 示例。
- [Real Python：Python Generators 101](https://realpython.com/courses/python-generators/)：完整的 8 节视频课程，包含生成器数据管道和练习。可按需选看，其中部分内容可能需要账户或订阅。

### 必读

- [Python 3.12 官方教程：迭代器、生成器与生成器表达式](https://docs.python.org/zh-cn/3.12/tutorial/classes.html#iterators)：重点阅读 9.8–9.10 节，观察 `for` 如何使用 `iter()`、`next()` 和 `StopIteration`。
- [Python 3.12 官方 HOWTO：函数式编程指引](https://docs.python.org/zh-cn/3.12/howto/functional.html#iterators)：重点阅读“迭代器”和“生成器”，理解数据流、惰性计算和文件对象的可迭代性。
- [Python 3.12 官方文档：`collections.abc`](https://docs.python.org/zh-cn/3.12/library/collections.abc.html)：按需查阅 `Iterable`、`Iterator` 和 `Generator` 的抽象接口关系。

### 按需查阅

- [Python 3.12 官方文档：迭代器类型](https://docs.python.org/zh-cn/3.12/library/stdtypes.html#iterator-types)：查看容器迭代器与生成器迭代器的通用行为。
- [Python 3.12 官方文档：`itertools`](https://docs.python.org/zh-cn/3.12/library/itertools.html)：了解标准库如何组合惰性迭代步骤；本课不要求使用。
- [Typing 官方规范：Protocols](https://typing.python.org/en/latest/spec/protocol.html)：用于理解 `Iterable` 和 `Iterator` 为什么属于结构化协议。本课不要求自定义 `Protocol`，后续课程会单独实践。

本课暂时不学习异步生成器、生成器的 `send()` / `throw()`、`yield from`、无限迭代器和自定义迭代器类。先把单向、同步、有限的数据管道掌握扎实。

## 20. 提交给老师的内容

完成后发送：

1. 全部测试的运行结果和测试总数。
2. `parse_log_lines()` 与 `filter_events_by_level()` 的实现。
3. 证明惰性解析的测试。
4. CLI 手动运行输出和 `$LASTEXITCODE`。
5. 小测第 1、4、6、9、10 题的答案。

我会从以下方面进行代码评审：迭代协议理解、惰性执行语义、类型标注、错误发生时机、管道职责、测试完整性和旧接口兼容性。
