# 第 2 周 · 第 3 课：上下文管理器与流式文件读取

预计用时：90–120 分钟

## 本课目标

完成本课后，你能够：

- 解释文件为什么需要确定的打开与关闭边界。
- 说明 `with`、`__enter__()` 与 `__exit__()` 的协作关系。
- 对照 Python 上下文管理器与 Java `try-with-resources`。
- 使用 `contextlib.contextmanager` 编写生成器式上下文管理器。
- 区分“惰性计算”与“资源生命周期”，避免返回依赖已关闭文件的迭代器。
- 使用 `Iterator[str]` 在文件打开期间逐行读取，而不是先构建完整列表。
- 让文件在正常结束、提前结束和异常路径上都能确定关闭。
- 在保持旧 `read_log_lines()` 契约和 CLI 外部行为不变的前提下演进日志分析管道。

## 1. 上一课留下的边界

上一课已经把解析和过滤改成了惰性管道：

```text
list[str]
    → parse_log_lines
    → Iterator[LogEvent]
    → filter_events_by_level
    → Iterator[LogEvent]
    → for
```

但文件读取仍然先创建完整列表：

```python
def read_log_lines(file_path: str) -> list[str]:
    lines: list[str] = []

    with open(file_path, "r", encoding="utf-8") as log_file:
        for line in log_file:
            lines.append(line.rstrip("\r\n"))

    return lines
```

这段代码的资源管理是正确的：离开 `with` 时文件会关闭。问题是所有行都先保存在内存中，后面的生成器只能减少解析结果和过滤结果的中间列表，无法减少原始文本列表。

本课把数据流演进为：

```text
打开文件
    → Iterator[str]
    → parse_log_lines
    → Iterator[LogEvent]
    → filter_events_by_level
    → Iterator[LogEvent]
    → 输出一条结果
关闭文件
```

任意时刻只需要保留当前行和当前事件。对当前很小的 `sample.log`，性能差异几乎看不出来；这次改造的价值是建立可扩展的数据处理边界。

## 2. 文件不只是一个可迭代对象

文本文件对象可以直接被遍历：

```python
for line in log_file:
    print(line)
```

它同时也是外部资源的句柄。操作系统需要维护文件描述符或文件句柄、当前位置和缓冲区。程序如果只关注“能不能迭代”，却没有明确“谁负责关闭”，就可能出现：

- 文件句柄长期不释放。
- Windows 上文件仍被占用，其他操作无法删除或替换它。
- 异常路径忘记执行 `close()`。
- 返回的生成器在消费时才发现底层文件已经关闭。

因此这里有两个不同的问题：

1. **数据何时产生**：由迭代器和生成器解决。
2. **资源何时有效**：由上下文管理器解决。

惰性执行不会自动替你管理资源生命周期。

## 3. `with` 语句的核心语义

最常见的文件使用方式是：

```python
with open("sample.log", "r", encoding="utf-8") as log_file:
    first_line = log_file.readline()
```

可以把它近似理解为：

```python
manager = open("sample.log", "r", encoding="utf-8")
log_file = manager.__enter__()

try:
    first_line = log_file.readline()
finally:
    manager.__exit__(...)
```

真实展开规则还会把异常类型、异常对象和 traceback 传给 `__exit__()`，但当前最重要的是：

- `__enter__()` 在进入代码块时取得要使用的资源。
- `as log_file` 接收 `__enter__()` 的返回值。
- `__exit__()` 在离开代码块时执行清理。
- 正常结束、`return`、`break` 或异常离开，都不会跳过上下文管理器的退出逻辑。

如果 `__exit__()` 返回真值，它可以抑制代码块中的异常。资源管理代码通常不应无意吞掉业务异常；本课实现让异常继续向上传播。

### `with` 不是文件专用语法

只要对象实现上下文管理协议，就可以用于 `with`。常见场景包括：

- 文件和网络连接。
- 数据库事务。
- 锁。
- 临时目录。
- 测试中的输出重定向。

项目测试里已经使用过这些上下文管理器：

```python
with TemporaryDirectory() as temp_dir:
    ...

with redirect_stdout(output):
    ...

with self.assertRaises(ValueError):
    ...
```

你之前已经在使用协议，本课只是把协议背后的生命周期模型说清楚。

## 4. 与 Java `try-with-resources` 对照

Java 常见写法：

```java
try (BufferedReader reader = Files.newBufferedReader(path, UTF_8)) {
    return reader.readLine();
}
```

Python 对应写法：

```python
with open(path, "r", encoding="utf-8") as reader:
    return reader.readline()
```

| 关注点 | Java | Python |
| --- | --- | --- |
| 语法 | `try (...) { ... }` | `with ... as ...:` |
| 协议 | `AutoCloseable.close()` | `__enter__()` / `__exit__()` |
| 清理时机 | 离开 `try` 块 | 离开 `with` 块 |
| 异常信息 | `close()` 本身不接收块内异常 | `__exit__()` 接收异常信息 |
| 多资源 | 分号分隔声明 | 一个 `with` 中用逗号分隔 |
| 常用抽象 | 资源关闭 | 进入/退出一段动态上下文 |

Python 上下文管理器比 `AutoCloseable` 表达的范围更广。它不一定对应一个有 `close()` 的对象，也可以临时改变状态并在退出时恢复。

## 5. 自定义上下文管理器协议

先用一个最小类观察协议，不把它加入项目：

```python
class ManagedValue:
    def __enter__(self) -> str:
        print("enter")
        return "ready"

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> bool:
        print("exit")
        return False
```

使用：

```python
with ManagedValue() as value:
    print(value)
```

输出顺序：

```text
enter
ready
exit
```

`return False` 表示若代码块中有异常，就继续传播。这个例子只用于理解协议；生产代码中的精确异常类型标注稍后再学习，不需要现在记忆三个参数的类型。

## 6. `@contextmanager`：用生成器表达进入与退出

很多上下文只需要“一段进入逻辑、一次交出资源、一段清理逻辑”。标准库提供 `contextlib.contextmanager`，可以用生成器函数表达这个结构：

```python
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def managed_value() -> Iterator[str]:
    print("enter")
    try:
        yield "ready"
    finally:
        print("exit")
```

这里的 `yield` 只执行一次：

- `yield` 之前相当于 `__enter__()` 阶段。
- `yield` 的值交给 `as value`。
- `yield` 之后相当于 `__exit__()` 阶段。
- `finally` 保证清理逻辑执行。

注意它和上一课“不断产生业务数据”的生成器用途不同。`@contextmanager` 包装的生成器必须只交出一次上下文值，不是用来连续 `yield` 多行日志的。

## 7. 本课要实现的接口

新增接口：

```python
@contextmanager
def open_log_lines(file_path: str) -> Iterator[Iterator[str]]:
    ...
```

调用方式：

```python
with open_log_lines("sample.log") as lines:
    for line in lines:
        print(line)
```

两个 `Iterator` 分别表示不同层次：

- 外层 `Iterator[...]` 描述 `@contextmanager` 装饰前的生成器函数：它向上下文交出一次值。
- 内层 `Iterator[str]` 是 `with` 块内使用的逐行数据源。

从调用者视角，`open_log_lines(...)` 返回的是一个上下文管理器，而不是要求调用者对外层迭代器调用 `next()`。

本课保持以下行为不变：

- 每行只删除结尾的 `\r` 和 `\n`，不删除消息中的其他空白。
- 文件按 UTF-8 文本读取。
- 空文件产生零行。
- 文件不存在时抛出 `FileNotFoundError`。
- 旧 `read_log_lines(file_path)` 仍返回 `list[str]`。
- CLI 输出格式和退出码不变。

## 8. 开始前确认基线

进入项目目录：

```powershell
cd projects/log-analyzer
python -m unittest discover -s tests -v
```

开始本课前应有 17 个测试通过。若数量不同或出现失败，先保存输出并检查当前状态，不要在未知基线上继续重构。

本课预计新增 3 个测试，完成后共 20 个测试。

## 9. 第一轮 TDD：取得流式行迭代器

先在测试文件加入导入：

```python
from log_analyzer import open_log_lines
```

新增测试类：

```python
class OpenLogLinesTest(unittest.TestCase):
    def test_yields_stripped_lines_as_an_iterator(self) -> None:
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "app.log"
            file_path.write_text(
                "2026-08-08T10:00:00|INFO|server started\n"
                "2026-08-08T10:01:00|ERROR|database timeout\n",
                encoding="utf-8",
            )

            with open_log_lines(str(file_path)) as lines:
                self.assertIs(iter(lines), lines)
                first_line = next(lines)

            self.assertEqual(
                first_line,
                "2026-08-08T10:00:00|INFO|server started",
            )
```

### RED

运行：

```powershell
python -m unittest tests.test_log_analyzer.OpenLogLinesTest -v
```

因为 `open_log_lines` 尚不存在，预期先看到导入失败。

`self.assertIs(iter(lines), lines)` 验证 `lines` 本身是迭代器，而不是列表。随后只调用一次 `next()`，没有把整个来源转成列表。

### GREEN

在 `log_analyzer.py` 顶部加入：

```python
from contextlib import contextmanager
```

实现：

```python
@contextmanager
def open_log_lines(file_path: str) -> Iterator[Iterator[str]]:
    with open(file_path, "r", encoding="utf-8") as log_file:
        def stripped_lines() -> Iterator[str]:
            for line in log_file:
                yield line.rstrip("\r\n")

        yield stripped_lines()
```

运行测试，确认第一轮变绿。

### 为什么需要内层生成器

外层生成器的 `yield` 表示“把一个上下文值交给 `with`”，只能交出一次。内层生成器才负责逐行产生数据：

```text
open_log_lines 的 yield：1 次上下文值
stripped_lines 的 yield：0 到多行文本
```

如果直接在带 `@contextmanager` 的函数中对每一行执行 `yield line`，第二行就会违反上下文管理器只交出一次值的契约。

## 10. 第二轮 TDD：正常退出时关闭文件

功能测试证明了能读取一行，但资源管理还需要可观察的证据。使用内存文本流代替真实文件，并检查它的 `closed` 状态。

在测试顶部加入：

```python
from unittest.mock import patch
```

在 `OpenLogLinesTest` 中新增：

```python
def test_closes_file_when_context_exits(self) -> None:
    log_file = StringIO(
        "2026-08-08T10:00:00|INFO|server started\n"
        "2026-08-08T10:01:00|ERROR|database timeout\n"
    )

    with patch("builtins.open", return_value=log_file):
        with open_log_lines("app.log") as lines:
            next(lines)
            self.assertFalse(log_file.closed)

    self.assertTrue(log_file.closed)
```

这里故意只消费第一行就离开 `with`。即使迭代器尚未耗尽，文件仍然必须关闭。

运行：

```powershell
python -m unittest tests.test_log_analyzer.OpenLogLinesTest -v
```

现有实现中的内层 `with open(...)` 会在外层上下文退出时关闭 `log_file`，第二轮应直接变绿。TDD 不要求每轮都新增生产代码；测试也可以把已经依赖但尚未证明的行为固定下来。

## 11. 第三轮 TDD：异常退出时仍然关闭

流式管道的错误可能发生在消费中途。例如第一行有效，第二行格式错误：

```python
def test_closes_file_when_consumer_raises(self) -> None:
    log_file = StringIO(
        "2026-08-08T10:00:00|INFO|server started\n"
        "invalid line\n"
    )

    with self.assertRaisesRegex(
        ValueError,
        "expected exactly 3 fields",
    ):
        with patch("builtins.open", return_value=log_file):
            with open_log_lines("app.log") as lines:
                events = parse_log_lines(lines)
                list(events)

    self.assertTrue(log_file.closed)
```

这个测试同时确认两件事：

- `ValueError` 没有被上下文管理器吞掉。
- 异常离开 `with` 后，文件依然关闭。

运行 `OpenLogLinesTest`，预期 3 个测试全部通过。

## 12. 保留旧接口作为兼容适配层

第一周已经建立了这个接口：

```python
def read_log_lines(file_path: str) -> list[str]:
    ...
```

不要突然改成返回迭代器，否则旧测试和现有调用者的契约都会改变。让它复用新上下文：

```python
def read_log_lines(file_path: str) -> list[str]:
    with open_log_lines(file_path) as lines:
        return list(lines)
```

这和上一课的兼容策略一致：

- 新接口提供更通用的流式能力。
- 旧接口保留原返回类型。
- 旧接口内部复用新实现，避免两处重复文件读取规则。

运行旧文件读取测试：

```powershell
python -m unittest tests.test_log_analyzer.ReadLogLineTest -v
```

多行、空文件和不存在文件三个行为都应保持不变。

## 13. 让 CLI 在资源上下文内消费完整管道

把 `main()` 中的：

```python
lines = read_log_lines(str(file_path))
events = parse_log_lines(lines)
matching_events = filter_events_by_level(events, level)

for event in matching_events:
    print(f"{event.timestamp}|{event.level}|{event.message}")
```

改成：

```python
with open_log_lines(file_path) as lines:
    events = parse_log_lines(lines)
    matching_events = filter_events_by_level(events, level)

    for event in matching_events:
        print(f"{event.timestamp}|{event.level}|{event.message}")
```

关键不是缩进风格，而是消费范围：

```text
with 进入 ───────────────────────────── with 退出
          文件迭代 → 解析 → 过滤 → 输出
          底层文件在整条管道消费期间保持打开
```

运行 CLI 测试：

```powershell
python -m unittest tests.test_log_analyzer.MainTest -v
```

用户仍然看到相同文本和退出码，内部则不再先创建完整行列表。

## 14. 一个危险写法：返回依赖已关闭文件的生成器

下面的函数看起来很合理，但有生命周期错误：

```python
def broken_log_lines(file_path: str) -> Iterator[str]:
    with open(file_path, "r", encoding="utf-8") as log_file:
        return (
            line.rstrip("\r\n")
            for line in log_file
        )
```

执行 `return` 时就会离开 `with`，文件随即关闭。调用者之后才消费生成器：

```python
lines = broken_log_lines("sample.log")
next(lines)  # 底层文件已经关闭
```

这说明“返回了迭代器”不等于“正确实现了流式读取”。迭代器依赖的资源必须在消费期间保持有效。

## 15. 另一种写法：生成器自己持有文件

也可以写成：

```python
def iter_log_lines(file_path: str) -> Iterator[str]:
    with open(file_path, "r", encoding="utf-8") as log_file:
        for line in log_file:
            yield line.rstrip("\r\n")
```

完整消费时它能正常关闭文件，而且代码很短。但如果调用者只取一行后仍然保存着生成器对象，文件会继续保持打开，直到生成器耗尽、显式 `close()` 或被回收。

```python
lines = iter_log_lines("sample.log")
print(next(lines))
# lines 仍然存活，文件也可能仍然打开
```

这不是所有场景下都错误。它适合“生成器拥有资源，调用方保证完整消费或显式关闭”的接口。本课选择 `with open_log_lines(...)`，是为了让资源边界在调用点可见，并让提前离开也能确定关闭。

## 16. 谁拥有资源，谁定义边界

设计流式 API 时先回答：谁负责关闭？

| 设计 | 资源所有者 | 调用者责任 |
| --- | --- | --- |
| 返回完整 `list` | 函数内部 | 无需管理文件，但占用完整列表内存 |
| 返回持有文件的生成器 | 生成器 | 完整消费或显式关闭 |
| 返回上下文管理器 | `with` 块 | 在 `with` 内消费，边界明确 |

本项目采用第三种。调用者不能把 `lines` 保存到 `with` 外继续消费：

```python
with open_log_lines("sample.log") as lines:
    saved_lines = lines

next(saved_lines)  # 生命周期已经结束
```

如果确实需要在块外使用，就在块内物化：

```python
with open_log_lines("sample.log") as lines:
    saved_lines = list(lines)
```

这会主动接受完整列表的内存成本。

## 17. 类型标注读法

项目会出现：

```python
@contextmanager
def open_log_lines(file_path: str) -> Iterator[Iterator[str]]:
    ...
```

不要把它误读成调用者要处理“迭代器的迭代器”。这个标注描述的是装饰器接收的生成器函数。装饰后，调用方式是：

```python
with open_log_lines(path) as lines:
    # lines: Iterator[str]
    ...
```

也可以为返回的上下文管理器写更直接、更显式的类型，但会引入 `AbstractContextManager` 等当前不需要的细节。本课优先遵循 `@contextmanager` 官方示例常用的生成器返回标注。

`str` 路径类型也暂时保持不变。以后学习 `pathlib.Path` 和 `os.PathLike` 时，再扩展路径接口，不在本次资源重构中顺带改变多个契约。

## 18. 异常发生时间

`@contextmanager` 装饰的函数在创建管理器对象时通常不会执行函数体：

```python
manager = open_log_lines("missing.log")
```

真正进入上下文时才打开文件：

```python
with manager as lines:  # 此处抛出 FileNotFoundError
    ...
```

解析错误则在消费到对应行时发生：

```python
with open_log_lines("app.log") as lines:
    events = parse_log_lines(lines)
    first = next(events)   # 第一行有效
    second = next(events)  # 第二行非法，此处 ValueError
```

因此管道里存在不同的错误时机：

- `with` 进入：打开文件，可能发生 `FileNotFoundError` 或 `PermissionError`。
- 迭代文件：可能发生 I/O 或解码错误。
- 解析当前行：可能发生格式 `ValueError`。
- 输出事件：可能发生输出流错误。
- `with` 退出：无论上面哪一步失败，都尝试清理资源。

本课不捕获并转换这些异常；目标是保证清理，同时保留原始错误语义。

## 19. REFACTOR：检查职责与重复

完成后检查：

- `open_log_lines()` 拥有文件资源，并把其有效期绑定到 `with`。
- 内层 `stripped_lines()` 只负责逐行删除行尾换行符。
- `read_log_lines()` 是保留 `list[str]` 契约的适配层。
- `parse_log_lines()` 不知道输入来自列表还是文件。
- `filter_events_by_level()` 不知道事件来自哪个数据源。
- `main()` 在资源上下文内连接并消费整条管道。
- UTF-8 和 `rstrip("\r\n")` 规则没有重复实现。
- 没有依赖垃圾回收器“以后大概会关闭文件”。
- 没有为了测试而暴露文件对象或新增生产参数。

然后运行全部测试：

```powershell
python -m unittest discover -s tests -v
```

预期 20 个测试全部通过。

## 20. 手动验证完整 CLI

在 `projects/log-analyzer` 目录运行：

```powershell
python log_analyzer.py sample.log ERROR
$LASTEXITCODE
```

预期：

```text
2026-08-08T10:01:00|ERROR|database timeout
0
```

验证 INFO：

```powershell
python log_analyzer.py sample.log INFO
$LASTEXITCODE
```

再验证参数缺失：

```powershell
python log_analyzer.py
$LASTEXITCODE
```

预期用法提示写入标准错误，退出码为 `2`。流式重构不应改变 CLI 的可观察行为。

## 21. 常见错误与定位方法

### 在 `with` 外消费行迭代器

```python
with open_log_lines(path) as lines:
    pass

list(lines)
```

资源已经离开有效期。把消费管道缩进 `with` 内。

### 在 `@contextmanager` 函数里多次交出值

```python
@contextmanager
def open_log_lines(path):
    with open(path) as file:
        for line in file:
            yield line
```

上下文管理器的生成器只能 `yield` 一次。把多行放进另一个迭代器，再一次性交给调用者。

### 用 `readlines()` 假装流式处理

```python
for line in log_file.readlines():
    ...
```

`readlines()` 会先创建所有行的列表。直接写 `for line in log_file`。

### 使用 `rstrip()` 删除过多内容

```python
line.rstrip()
```

无参数 `rstrip()` 会删除行尾所有空白，可能改变日志消息。继续使用：

```python
line.rstrip("\r\n")
```

### 依赖 `__del__` 或垃圾回收关闭文件

不同 Python 实现和对象引用关系会影响回收时机。资源安全需要词法上明确的 `with`，不能把正确性建立在“对象很快会被回收”上。

### 在上下文管理器中吞掉业务异常

自定义 `__exit__()` 返回真值会抑制异常。除非接口明确要求错误恢复，否则让解析和 I/O 异常继续传播。

## 22. 小测

先不要运行代码，尝试直接回答：

1. 迭代器解决的问题和上下文管理器解决的问题分别是什么？
2. `with open(...) as file` 中，`as file` 接收的是什么？
3. `__exit__()` 为什么需要知道代码块中的异常信息？
4. Python 上下文管理器与 Java `try-with-resources` 的共同点和主要协议差异是什么？
5. `@contextmanager` 函数中，`yield` 前、`yield` 的值和 `yield` 后分别对应什么阶段？
6. 为什么上下文管理器生成器只能交出一次值？
7. 为什么不能在 `with open(...)` 中返回一个依赖该文件的生成器表达式？
8. 只实现 `iter_log_lines()` 生成器时，调用者提前停止消费可能带来什么资源问题？
9. 为什么 `read_log_lines()` 仍然保留返回列表的旧契约？
10. 在新的 `main()` 中，为什么解析、过滤和输出都必须位于 `with` 块内？

## 23. 完成检查

- [ ] 能解释 `with` 的进入和退出阶段。
- [ ] 能说明 `__enter__()` 返回值与 `as` 变量的关系。
- [ ] 能说明异常离开代码块时为什么仍会执行清理。
- [ ] 能对照 Python 上下文管理器与 Java `try-with-resources`。
- [ ] 已实现 `open_log_lines()`。
- [ ] 已通过测试证明行来源是迭代器。
- [ ] 已通过测试证明提前离开仍关闭文件。
- [ ] 已通过测试证明解析异常不会阻止文件关闭。
- [ ] 已让 `read_log_lines()` 复用新流式接口并保持返回列表。
- [ ] 已让 `main()` 在文件上下文内消费完整管道。
- [ ] 已运行全部 20 个自动化测试。
- [ ] 已手动验证 CLI 输出和退出码。
- [ ] 已回答小测的 10 个问题。

## 24. 视频与阅读材料

建议按“短讲解建立生命周期直觉 → 阅读讲义 → 完成 TDD → 官方文档查漏”的顺序学习。

### 推荐阅读

1. [Python 3.12 官方教程：文件读写](https://docs.python.org/zh-cn/3.12/tutorial/inputoutput.html#reading-and-writing-files)：重点阅读 `open()` 与 `with` 示例，理解官方为什么建议使用 `with` 保证文件正确关闭。
2. [Python 3.12 语言参考：`with` 语句](https://docs.python.org/zh-cn/3.12/reference/compound_stmts.html#the-with-statement)：查看 `__enter__()`、`__exit__()` 的精确定义和异常处理顺序。第一次阅读只需掌握协议主线。
3. [Python 3.12 标准库：`contextlib.contextmanager`](https://docs.python.org/zh-cn/3.12/library/contextlib.html#contextlib.contextmanager)：对照本课的生成器式上下文管理器实现，重点看“一次 `yield`”和异常在 `yield` 点重新抛出的说明。

### 推荐视频

1. [PyOhio 2021：The Enters and Exits of Context Managers](https://pyvideo.org/pyohio-2021/the-enters-and-exits-of-context-managers.html)：从 `with`、`__enter__()`、`__exit__()` 到 `contextlib` 的一手会议讲解。内容较长，可重点观看基础协议和生成器式上下文管理器部分。
2. [Real Python：Context Managers and Python's `with` Statement](https://realpython.com/python-with-statement/)：包含循序渐进的代码与配套讲解，可用于课前快速建立直觉；正文也适合遇到 `__enter__()` / `__exit__()` 时查阅。

### 按需查阅

- [Python 3.12 数据模型：上下文管理器类型](https://docs.python.org/zh-cn/3.12/reference/datamodel.html#context-managers)：查阅协议方法的完整定义。
- [Python 3.12 标准库：I/O 概述](https://docs.python.org/zh-cn/3.12/library/io.html)：了解文本 I/O、缓冲和编码层次。本课不要求自定义 I/O 类。
- [Python 3.12 标准库：`ExitStack`](https://docs.python.org/zh-cn/3.12/library/contextlib.html#contextlib.ExitStack)：用于动态管理数量不固定的上下文。本课不要求使用，等项目出现多资源组合时再学。

本课暂时不学习异步上下文管理器、`async with`、`AsyncExitStack`、自定义文件缓冲、内存映射文件和并发文件读取。先把同步、单文件、确定关闭的资源边界掌握扎实。

## 25. 提交给老师的内容

完成后发送：

1. 全部测试的运行结果和测试总数。
2. `open_log_lines()` 与兼容版 `read_log_lines()` 的实现。
3. 正常退出和异常退出都会关闭文件的测试。
4. 重构后的 `main()` 流式管道。
5. CLI 手动运行输出和 `$LASTEXITCODE`。
6. 小测第 1、4、5、7、8、10 题的答案。

我会从以下方面进行代码评审：上下文管理协议、资源所有权、异常传播、惰性消费、类型标注、旧接口兼容性、测试证据和 CLI 外部行为。
