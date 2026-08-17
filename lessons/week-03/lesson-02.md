# 第 3 周 · 第 2 课：pytest、fixture 与参数化测试

预计用时：120–150 分钟

## 本课目标

完成本课后，你能够：

- 解释 pytest 如何发现和执行测试，并用节点 ID 精确选择测试。
- 使用 pytest 直接运行现有 `unittest.TestCase`，建立渐进迁移的安全基线。
- 使用普通测试函数和 Python 原生 `assert` 编写清晰的测试。
- 使用 `pytest.raises()` 验证异常类型与消息。
- 理解 fixture 的请求、依赖注入、作用域和清理边界。
- 使用内置 fixture `tmp_path` 与 `capsys` 测试文件 I/O 和 CLI 输出。
- 使用 `@pytest.mark.parametrize` 将同一行为的多组输入输出表达为独立测试用例。
- 判断何时应该使用 fixture、参数化或普通辅助函数。
- 在不修改业务行为的前提下，将现有 21 个 `unittest` 测试渐进迁移到 pytest 风格。
- 保持 21 个测试、mypy 静态检查和 CLI 外部行为全部通过。

## 1. 为什么现在迁移测试框架

日志分析器已经拥有 21 个测试，覆盖：

- 单行与多行日志解析。
- 日志级别统计和过滤。
- 生成器的惰性执行。
- 文件读取与资源关闭。
- `LogSource` 协议的结构化替换。
- CLI 标准输出、标准错误和退出码。

这些测试已经形成回归保护网。本课的任务不是增加业务功能，而是改善测试的表达和复用方式。

当前写法基于标准库 `unittest`：

```python
class ParseLogLineTest(unittest.TestCase):
    def test_parses_a_valid_log_line(self) -> None:
        event = parse_log_line(
            "2026-08-01T10:15:00|ERROR|database timeout"
        )

        self.assertEqual(
            event,
            LogEvent(
                timestamp="2026-08-01T10:15:00",
                level="ERROR",
                message="database timeout",
            ),
        )
```

pytest 风格可以写成普通函数：

```python
def test_parses_a_valid_log_line() -> None:
    event = parse_log_line(
        "2026-08-01T10:15:00|ERROR|database timeout"
    )

    assert event == LogEvent(
        timestamp="2026-08-01T10:15:00",
        level="ERROR",
        message="database timeout",
    )
```

代码更短并不是最重要的收益。更重要的是 pytest 提供：

- 对普通 `assert` 的失败表达式分析。
- 通过函数参数请求 fixture 的依赖机制。
- 临时目录、输出捕获等内置 fixture。
- 参数化测试与清晰的独立用例报告。
- 灵活的测试发现、筛选和失败控制。

## 2. 与 JUnit 的快速对照

| 测试意图 | JUnit 5 | `unittest` | pytest |
| --- | --- | --- | --- |
| 测试单元 | `@Test` 方法 | `TestCase.test_*` 方法 | `test_*` 函数或方法 |
| 相等断言 | `assertEquals` | `self.assertEqual` | `assert actual == expected` |
| 异常断言 | `assertThrows` | `self.assertRaises` | `pytest.raises` |
| 测试准备 | `@BeforeEach` | `setUp` | fixture，默认 function scope |
| 临时目录 | `@TempDir` | `TemporaryDirectory` | `tmp_path` fixture |
| 输出捕获 | 扩展或重定向 | `redirect_stdout` | `capsys` fixture |
| 参数化 | `@ParameterizedTest` | `subTest` 或手写循环 | `@pytest.mark.parametrize` |

这只是概念映射，不是一一等价。pytest fixture 不是把 `setUp()` 换一个装饰器名称；它可以显式声明依赖、组合其他 fixture，并按作用域缓存结果。

## 3. 第零轮：不改代码，先用 pytest 建立基线

进入项目并确认开发依赖已经安装：

```powershell
cd projects/log-analyzer
python -m pip install -e ".[dev]"
python -m pytest --version
```

运行现有测试：

```powershell
python -m pytest -q
```

当前预期结果：

```text
21 passed
```

pytest 能直接收集符合命名规则的 `unittest.TestCase` 子类和 `test_*` 方法。因此迁移可以逐个类进行：一部分测试保持 `unittest`，另一部分已经使用 pytest，两者仍可在同一次运行中执行。

同时保留原运行方式作为迁移期对照：

```powershell
python -m unittest discover -s tests -v
```

当测试全部改为普通 pytest 函数后，`unittest discover` 不再是正式入口；最终以 `python -m pytest` 为准。

### 为什么使用 `python -m pytest`

`pytest` 与 `python -m pytest` 通常会启动同一工具，但后者明确使用当前 Python 环境中的 pytest，并会把当前目录加入 `sys.path`。本项目已经使用 editable install，导入不应依赖这个额外路径；统一使用 `python -m pytest` 仍然更容易确认解释器来源。

## 4. pytest 如何发现测试

在默认规则下，pytest 会寻找：

- 名为 `test_*.py` 或 `*_test.py` 的测试文件。
- 文件中名为 `test_*` 的函数。
- 名为 `Test*` 且没有自定义 `__init__` 的类中的 `test_*` 方法。
- `unittest.TestCase` 子类中的测试方法。

只查看收集结果，不执行测试：

```powershell
python -m pytest --collect-only -q
```

输出中的每一项都是节点 ID，例如：

```text
tests/test_log_analyzer.py::ParseLogLineTest::test_parses_a_valid_log_line
```

可以精确运行它：

```powershell
python -m pytest "tests/test_log_analyzer.py::ParseLogLineTest::test_parses_a_valid_log_line" -v
```

也可以按名称子串筛选：

```powershell
python -m pytest -k "parse and not lazy" -v
```

常用反馈选项：

- `-q`：减少成功输出，适合频繁回归。
- `-v`：显示每个用例，适合学习测试发现。
- `-x`：第一次失败后停止。
- `--maxfail=2`：达到两个失败后停止。
- `-k expression`：按测试名称表达式筛选。
- `--fixtures`：查看可用 fixture。

不要把 `-k` 当成长期跳过其他测试的办法。局部开发时可以筛选，提交前必须运行完整套件。

## 5. 第一轮：从 `TestCase` 迁移为普通测试函数

先迁移 `ParseLogLineTest`，范围小且同时包含成功与异常路径。

### 5.1 成功路径使用普通 `assert`

把类删除，将方法改为模块级函数：

```python
def test_parses_a_valid_log_line() -> None:
    line = "2026-08-01T10:15:00|ERROR|database timeout"

    event = parse_log_line(line)

    assert event == LogEvent(
        timestamp="2026-08-01T10:15:00",
        level="ERROR",
        message="database timeout",
    )
```

pytest 在导入测试模块时重写 `assert`，从表达式中生成失败细节。临时把预期级别改成 `"INFO"`，运行这个测试，观察它如何展示两个数据类对象的字段差异；然后立即恢复正确值。

### 不要给 `assert` 加无信息量消息

下面的消息没有帮助：

```python
assert event == expected, "event should equal expected"
```

pytest 已经会显示 `event` 和 `expected`。只有当领域背景无法从表达式和变量名看出时，才添加自定义说明。

### 5.2 异常路径使用 `pytest.raises()`

在测试文件顶部导入 pytest：

```python
import pytest
```

将异常测试改为：

```python
def test_rejects_log_line_with_missing_fields() -> None:
    line = "2026-08-01T10:15:00|ERROR"

    with pytest.raises(
        ValueError,
        match="expected exactly 3 fields",
    ):
        parse_log_line(line)
```

`match` 按正则表达式搜索异常字符串，并不是普通字符串全等比较。如果要匹配的消息含有 `(`、`[`、`.` 等正则元字符，应使用原始字符串并正确转义，或使用 `re.escape()`。

异常断言的 `with` 块应尽可能小：

```python
with pytest.raises(ValueError):
    parse_log_line(line)
```

如果把准备数据等无关操作也放进去，测试可能被错误位置抛出的同类型异常“误通过”。

运行这一组：

```powershell
python -m pytest -k "parses_a_valid or missing_fields" -v
python -m pytest -q
```

两个局部测试和完整 21 个测试都应通过。

## 6. 普通 `assert` 的几种常见表达

pytest 不要求记忆一组断言方法，直接写出所需条件：

```python
assert counts == {"INFO": 2, "ERROR": 1}
assert lines == []
assert first_event.level == "INFO"
assert iter(lines) is lines
assert not log_file.closed
assert log_file.closed
assert exit_code == 0
```

对应现有 `unittest` 写法：

| `unittest` | pytest 风格 |
| --- | --- |
| `self.assertEqual(a, b)` | `assert a == b` |
| `self.assertIs(a, b)` | `assert a is b` |
| `self.assertTrue(value)` | `assert value` |
| `self.assertFalse(value)` | `assert not value` |
| `self.assertIn(item, values)` | `assert item in values` |
| `self.assertRaises(Error)` | `pytest.raises(Error)` |

不要机械地把所有断言都改成 `assert bool(...)`。保留原始表达式，pytest 才能给出更好的失败诊断：

```python
# 信息更完整
assert actual_events == expected_events

# 丢失了两侧对象的直接比较结构
assert bool(actual_events == expected_events)
```

## 7. fixture 的核心：测试显式请求依赖

fixture 是 pytest 按名称提供给测试的依赖。先写一个最小例子：

```python
@pytest.fixture
def error_event() -> LogEvent:
    return LogEvent(
        timestamp="2026-08-08T10:01:00",
        level="ERROR",
        message="database timeout",
    )


def test_yields_matching_events(error_event: LogEvent) -> None:
    info_event = LogEvent(
        timestamp="2026-08-08T10:00:00",
        level="INFO",
        message="server started",
    )

    events = filter_events_by_level(
        [info_event, error_event],
        "ERROR",
    )

    assert list(events) == [error_event]
```

执行流程是：

```text
pytest 收集测试
    → 看到测试需要 error_event
    → 查找同名 fixture
    → 调用 fixture
    → 把返回值传给测试参数
    → 执行测试
```

这里的参数不是调用者手写传入，也不是 pytest 根据类型标注匹配。pytest 主要按参数名 `error_event` 查找 fixture；`LogEvent` 标注是给阅读者、IDE 和 mypy 使用的。

### fixture 可以依赖另一个 fixture

```python
@pytest.fixture
def log_lines() -> tuple[str, ...]:
    return (
        "2026-08-08T10:00:00|INFO|server started",
        "2026-08-08T10:01:00|ERROR|database timeout",
    )


@pytest.fixture
def memory_source(log_lines: tuple[str, ...]) -> MemoryLogSource:
    return MemoryLogSource(lines=log_lines)
```

测试只请求自己直接需要的对象：

```python
def test_prints_events_from_a_structural_log_source(
    memory_source: MemoryLogSource,
    capsys: pytest.CaptureFixture[str],
) -> None:
    print_matching_events(memory_source, "ERROR")

    captured = capsys.readouterr()
    assert captured.out == (
        "2026-08-08T10:01:00|ERROR|database timeout\n"
    )
    assert captured.err == ""
```

依赖图保持小而显式。不要创建一个返回所有测试数据的巨型 `test_context` fixture。

## 8. fixture、辅助函数与参数化如何选择

这三个机制解决的问题不同：

- fixture：提供测试依赖、环境或生命周期管理。
- 辅助函数：执行普通、显式调用的计算或对象构造。
- 参数化：让同一个行为契约针对多组数据独立执行。

如果只是为了少写四行对象构造，普通函数可能更清楚：

```python
def make_event(level: str, message: str) -> LogEvent:
    return LogEvent(
        timestamp="2026-08-08T10:00:00",
        level=level,
        message=message,
    )
```

调用关系一眼可见：

```python
event = make_event("ERROR", "database timeout")
```

而 fixture 更适合由 pytest 管理、多个测试请求的资源或稳定样本。不要因为 pytest 提供 fixture，就把每个常量都变成 fixture。

## 9. fixture 作用域与隔离

fixture 默认是 `function` 作用域：每个测试调用一次，测试之间不会共享返回对象。

pytest 支持常见作用域：

| 作用域 | 创建频率 | 典型用途 |
| --- | --- | --- |
| `function` | 每个测试一次 | 可变测试数据、临时资源，默认首选 |
| `class` | 每个测试类一次 | 少量类级兼容场景 |
| `module` | 每个测试模块一次 | 构建成本较高且安全只读的数据 |
| `package` | 每个测试包一次 | 跨模块的包级资源 |
| `session` | 整次 pytest 会话一次 | 极昂贵且可安全共享的资源 |

声明示例：

```python
@pytest.fixture(scope="module")
def shared_lines() -> tuple[str, ...]:
    return (...)
```

不要为了“更快”过早扩大作用域。共享可变对象会造成测试顺序依赖：某个测试修改数据，后续测试看到被污染的状态。当前项目的 fixture 都很便宜，保留默认 `function` 作用域即可。

## 10. 使用 `yield` fixture 管理清理

需要在测试后清理资源时，可以在 fixture 中使用一次 `yield`：

```python
@pytest.fixture
def managed_resource() -> Iterator[Resource]:
    resource = Resource()
    yield resource
    resource.close()
```

- `yield` 前：准备资源。
- `yield` 的值：传给测试。
- `yield` 后：测试结束后的清理。

这与第二周学过的 `@contextmanager` 生命周期非常相似。不同之处在于驱动者：上下文管理器由 `with` 驱动，fixture 由 pytest 驱动。

如果 fixture 在 `yield` 之前失败，后面的清理代码不会执行，因为资源尚未成功交付。多个资源最好拆成多个 fixture，或使用上下文管理器、`try/finally`，让每一步清理责任清楚。

本课的临时文件优先使用内置 `tmp_path`，无需自己写清理 fixture。

## 11. 第二轮：用 `tmp_path` 替代 `TemporaryDirectory`

现有文件测试重复创建和清理临时目录：

```python
with TemporaryDirectory() as temp_dir:
    file_path = Path(temp_dir) / "app.log"
    ...
```

pytest 内置的 `tmp_path` 为每个测试提供独立的 `pathlib.Path` 临时目录：

```python
def test_reads_multiple_lines_from_file(tmp_path: Path) -> None:
    file_path = tmp_path / "app.log"
    file_path.write_text(
        "2026-08-08T10:00:00|INFO|server started\n"
        "2026-08-08T10:01:00|ERROR|database timeout\n",
        encoding="utf-8",
    )

    lines = read_log_lines(str(file_path))

    assert lines == [
        "2026-08-08T10:00:00|INFO|server started",
        "2026-08-08T10:01:00|ERROR|database timeout",
    ]
```

空文件测试：

```python
def test_returns_empty_list_for_empty_file(tmp_path: Path) -> None:
    file_path = tmp_path / "empty.log"
    file_path.write_text("", encoding="utf-8")

    lines = read_log_lines(str(file_path))

    assert lines == []
```

不存在的文件测试不需要先创建文件：

```python
def test_raises_error_when_file_does_not_exist(tmp_path: Path) -> None:
    file_path = tmp_path / "missing.log"

    with pytest.raises(FileNotFoundError):
        read_log_lines(str(file_path))
```

`tmp_path` 已经是 `Path`，不要再写 `Path(tmp_path)`。旧的 `tmpdir` fixture 返回 pytest 自己的旧路径类型；新代码优先使用标准库 `pathlib.Path` 的 `tmp_path`。

### 提取可复用的临时日志文件

CLI 和文件读取测试都需要相同文件时，可以定义：

```python
@pytest.fixture
def log_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "app.log"
    file_path.write_text(
        "2026-08-08T10:00:00|INFO|server started\n"
        "2026-08-08T10:01:00|ERROR|database timeout\n",
        encoding="utf-8",
    )
    return file_path
```

测试只表达行为：

```python
def test_reads_multiple_lines_from_file(log_file: Path) -> None:
    assert read_log_lines(str(log_file)) == [
        "2026-08-08T10:00:00|INFO|server started",
        "2026-08-08T10:01:00|ERROR|database timeout",
    ]
```

fixture 名称应说明它提供什么，而不是说明内部如何创建。`log_file` 比 `setup_data` 更清楚。

## 12. 第三轮：用 `capsys` 测试 stdout 与 stderr

现有 CLI 测试使用 `StringIO` 和 `redirect_stdout`。pytest 的 `capsys` 会捕获写入 `sys.stdout` 与 `sys.stderr` 的文本。

### 正常输出

```python
def test_prints_logs_matching_requested_level(
    log_file: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([str(log_file), "ERROR"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == (
        "2026-08-08T10:01:00|ERROR|database timeout\n"
    )
    assert captured.err == ""
```

### 错误输出

```python
def test_returns_usage_error_when_arguments_are_missing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == (
        "usage: python log_analyzer.py <log-file> <level>\n"
    )
```

`capsys.readouterr()` 返回捕获到的 `out` 和 `err`，并建立一个读取边界。若测试中多次调用，应明确每一次调用验证的是哪个阶段产生的输出。

`capsys` 捕获 Python 层的 `sys.stdout` / `sys.stderr`；若未来需要捕获直接写入操作系统文件描述符 `1` 和 `2` 的子进程或扩展代码，再考虑 `capfd`。当前项目只需要 `capsys`。

## 13. 第四轮：用参数化表达数据变化

当前 `CountLogLevelsTest` 的三个测试只有输入和预期结果不同，行为契约相同：

```text
给定若干日志行，count_log_levels 返回各级别出现次数
```

可合并为参数化测试：

```python
@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        pytest.param(
            [
                "2026-08-01T10:15:00|INFO|server started",
                "2026-08-01T10:16:00|ERROR|database timeout",
                "2026-08-01T10:17:00|INFO|request completed",
            ],
            {"INFO": 2, "ERROR": 1},
            id="repeated-level",
        ),
        pytest.param(
            [
                "2026-08-01T10:15:00|INFO|server started",
                "2026-08-01T10:16:00|ERROR|database timeout",
                "2026-08-01T10:17:00|WARN|request completed",
            ],
            {"INFO": 1, "ERROR": 1, "WARN": 1},
            id="previously-unseen-level",
        ),
        pytest.param([], {}, id="empty-input"),
    ],
)
def test_counts_log_levels(
    lines: list[str],
    expected: dict[str, int],
) -> None:
    assert count_log_levels(lines) == expected
```

运行：

```powershell
python -m pytest -k counts_log_levels -v
```

pytest 会收集三个独立用例：

```text
test_counts_log_levels[repeated-level]
test_counts_log_levels[previously-unseen-level]
test_counts_log_levels[empty-input]
```

因此“一个测试函数”不等于“一次测试执行”。原来三个测试合并为一个参数化函数后，总收集数仍然是 21。

### 参数名称必须与函数参数一致

```python
@pytest.mark.parametrize(("lines", "expected"), [...])
def test_counts_log_levels(
    lines: list[str],
    expected: dict[str, int],
) -> None:
    ...
```

装饰器中的名称决定 pytest 向函数注入哪些值。类型标注不参与匹配。

### 参数对象不会被自动复制

pytest 会把参数值原样传入。如果测试修改列表或字典，同一个对象可能在其他位置被观察到。测试应优先把输入当作不可变数据；必须修改时，在测试内显式复制或使用 fixture 为每次执行创建新对象。

### 什么时候不要参数化

不要仅因为两个测试都调用同一个函数就合并。以下情况更适合保留独立测试：

- 验证的是不同业务规则。
- 准备过程明显不同。
- 断言结构不同。
- 合并后需要大量条件分支。
- 用例名称比参数表更能表达意图。

如果参数化测试出现：

```python
if case == "error":
    ...
else:
    ...
```

通常说明它包含多个行为，应拆开。

## 14. 参数化与 fixture 的组合

fixture 管理环境，参数化提供数据变化，两者可以同时使用：

```python
@pytest.mark.parametrize(
    ("level", "expected_output"),
    [
        (
            "INFO",
            "2026-08-08T10:00:00|INFO|server started\n",
        ),
        (
            "ERROR",
            "2026-08-08T10:01:00|ERROR|database timeout\n",
        ),
    ],
)
def test_prints_requested_level(
    log_file: Path,
    capsys: pytest.CaptureFixture[str],
    level: str,
    expected_output: str,
) -> None:
    exit_code = main([str(log_file), level])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == expected_output
    assert captured.err == ""
```

这会把原来的一个正常 CLI 用例扩展成两个参数用例，使测试总数增加一。为了先完成等价迁移，本课必做部分保留原来的 `ERROR` 用例；上面的 `INFO` / `ERROR` 参数化作为选做增强。不要在迁移框架和扩展覆盖面同时进行时混淆测试数量变化的原因。

## 15. `conftest.py`：共享 fixture 的可见范围

当 fixture 只服务一个测试模块时，直接放在 `test_log_analyzer.py` 中最容易阅读。

如果未来拆成多个测试文件，并且多个文件都需要 `log_file`，可以将 fixture 移到：

```text
tests/
├── conftest.py
├── test_cli.py
└── test_core.py
```

pytest 会自动发现适用目录层级中的 `conftest.py`，测试文件不需要也不应该写：

```python
from conftest import log_file
```

`conftest.py` 不是普通的项目公共 API。不要过早建立仓库根级 `conftest.py`；fixture 放得越高，影响范围越大，依赖来源也越不直观。

本课不要求拆测试文件。先完成风格迁移，保持一次只改变一个维度。

## 16. 与 `unittest.mock.patch` 的关系

切换到 pytest 不意味着必须删除标准库 `unittest.mock.patch`。现有资源关闭测试可以只改断言和异常语法，继续使用 `patch`：

```python
def test_closes_file_when_context_exits() -> None:
    log_file = StringIO(
        "2026-08-08T10:00:00|INFO|server started\n"
        "2026-08-08T10:01:00|ERROR|database timeout\n"
    )

    with patch("builtins.open", return_value=log_file):
        with open_log_lines("app.log") as lines:
            next(lines)
            assert not log_file.closed

    assert log_file.closed
```

pytest 也提供 `monkeypatch` fixture，但本课重点是 fixture 模型，不需要为了追求“纯 pytest”机械替换已经清楚、可靠的 `patch`。选择工具时看测试意图和可读性。

## 17. `TestCase` 与 pytest fixture 的迁移边界

pytest 可以运行 `unittest.TestCase`，但普通 fixture 参数不能直接注入 `TestCase` 测试方法：

```python
class MainTest(unittest.TestCase):
    # 不要在 TestCase 迁移一半时这样写
    def test_output(self, capsys) -> None:
        ...
```

要使用 `tmp_path`、`capsys` 等参数式 fixture，应把对应方法迁移为 pytest 普通函数，或迁移到不继承 `unittest.TestCase` 的 pytest 测试类。

本项目没有依赖类级共享状态，优先使用模块级测试函数。仅为分组而创建测试类通常没有必要，清楚的函数名已经可以表达行为。

## 18. 推荐的渐进迁移顺序

每一步都运行完整测试，不进行“大爆炸”重写：

1. 用 pytest 原样运行现有 21 个 `unittest` 测试。
2. 迁移 `ParseLogLineTest`，练习普通 `assert` 与 `pytest.raises()`。
3. 迁移纯函数测试：过滤、统计、数据类和惰性解析。
4. 将三个统计测试改为一个包含三组参数的参数化测试。
5. 迁移文件测试，用 `tmp_path` 替换 `TemporaryDirectory`。
6. 迁移 CLI 与打印测试，用 `capsys` 替换输出重定向。
7. 迁移资源关闭测试，保留 `StringIO` 与 `patch`。
8. 删除不再使用的 `unittest`、`redirect_stdout`、`redirect_stderr` 和 `TemporaryDirectory` 导入。
9. 删除文件末尾的 `unittest.main()` 入口。
10. 运行 pytest、mypy、CLI 和补丁格式检查；若当前环境已经配置 Ruff，再补充运行 Ruff。

每一步若测试数突然减少，先运行：

```powershell
python -m pytest --collect-only -q
```

检查是否因文件、函数或类命名不符合发现规则而漏收集，而不是把“没有执行”误认为“通过”。

## 19. 测试代码的最终结构建议

迁移完成后，单个测试文件可以按以下顺序组织：

```text
导入
    ↓
测试替身 MemoryLogSource
    ↓
少量复用 fixture
    ↓
解析与统计测试
    ↓
过滤与生成器测试
    ↓
文件和资源生命周期测试
    ↓
处理管道与 CLI 测试
```

具体原则：

- 测试名描述可观察行为，不复述实现步骤。
- Arrange、Act、Assert 三段用空行区分即可，不必添加机械注释。
- 一个测试可以有多个共同描述同一行为的断言，例如同时检查退出码、stdout 和 stderr。
- fixture 保持小而聚焦，不隐藏测试的关键输入。
- 参数 ID 使用领域含义，如 `empty-input`，不要只写 `case-1`。
- 测试从 `log_analyzer` 的公开接口导入，继续保护包级 API。
- 不因迁移测试框架而修改 `src/log_analyzer/` 中的生产代码。

## 20. 常见错误与定位方法

### `fixture 'x' not found`

先检查测试函数参数名是否与 fixture 函数名一致，再运行：

```powershell
python -m pytest --fixtures
```

类型标注相同不代表名称能自动匹配。

### fixture 定义了但没有执行

普通 fixture 只有被测试或其他 fixture 请求时才执行。不要依赖一个“无人请求”的 fixture 产生全局副作用。`autouse=True` 虽可自动执行，但会隐藏依赖，本课不使用。

### `capsys` 得到空字符串

确认在调用被测函数之后执行 `capsys.readouterr()`，并确认代码写的是 `sys.stdout` / `sys.stderr`。若是子进程或底层文件描述符输出，应判断是否需要 `capfd`。

### 临时文件在测试结束后找不到

这是预期行为。`tmp_path` 面向测试隔离，不是持久输出目录。调试时查看 pytest 失败报告中的路径，不要让测试依赖上一次运行留下的文件。

### 参数化测试只显示难懂的值

为参数添加领域化 `id`：

```python
pytest.param([], {}, id="empty-input")
```

### 一个参数用例污染另一个

参数值按原对象传入，不自动深拷贝。避免修改参数，或在测试内复制需要修改的列表和字典。

### 测试通过数从 21 变少

运行 `--collect-only -q`，检查是否删除了 `test_` 前缀、使用了带 `__init__` 的普通测试类，或把测试移出了发现路径。

### 同时迁移测试并重构生产代码

这会让失败原因难以定位。本课保持生产代码不变；测试框架迁移完成并建立新基线后，再进行新的业务迭代。

### 为所有数据建立 fixture

fixture 过多会让关键输入藏在文件其他位置。一次性且短小的数据直接放在测试中；需要生命周期或被多个测试稳定复用时再提取。

### 断言只检查“没有抛异常”

测试正常结束只能说明路径可运行。还应验证返回值、输出、状态变化或资源关闭等可观察结果。

## 21. REFACTOR：检查测试设计

完成迁移后检查：

- 测试文件不再继承 `unittest.TestCase`。
- 使用普通 `assert`，没有无意义的自定义断言消息。
- 异常测试的 `pytest.raises()` 范围足够小。
- `tmp_path` 测试不依赖固定机器路径。
- `capsys` 同时区分 stdout 与 stderr。
- 参数化只合并相同契约的不同数据。
- 参数 ID 能说明场景。
- fixture 名称说明提供的对象或资源。
- fixture 没有不必要的宽作用域和隐藏副作用。
- `unittest.mock.patch` 只在需要替换全局文件打开函数的资源测试中保留。
- 没有为了适应测试而改变生产接口。
- 测试仍从公开包接口导入。

## 22. 最终验证

### 22.1 pytest

```powershell
python -m pytest -q
```

必做迁移保持原有场景数量，预期：

```text
21 passed
```

如果完成了选做的 CLI 双级别参数化，预期测试数会相应增加；应能解释每个新增用例来自哪里。

### 22.2 查看收集结果

```powershell
python -m pytest --collect-only -q
```

确认参数化的三个统计场景都拥有独立节点 ID。

### 22.3 mypy

```powershell
python -m mypy src tests
```

目标是 5 个源文件无错误。fixture 参数添加精确标注：

```python
tmp_path: Path
capsys: pytest.CaptureFixture[str]
```

### 22.4 可选：Ruff

```powershell
python -m ruff check src tests
```

当前 `.venv` 的开发依赖没有声明 Ruff，因此它不是本课必做验收。如果环境已经安装并配置 Ruff，可以补充运行；如果命令提示 `No module named ruff`，记录为未配置即可，不要仅为本课临时改变依赖范围。

### 22.5 CLI 回归

```powershell
python -m log_analyzer sample.log ERROR
$LASTEXITCODE

log-analyzer sample.log INFO
$LASTEXITCODE

log-analyzer
$LASTEXITCODE
```

前两条正常路径退出码应为 `0`，错误参数路径应在 stderr 输出 usage 并返回 `2`。

### 22.6 补丁格式

回到仓库根目录运行：

```powershell
git diff --check
git status --short
```

确认没有尾随空格，也没有提交 `.venv/`、缓存或临时测试文件。

## 23. 小测

先不要运行代码，尝试直接回答：

1. 为什么可以先不改任何测试，就用 pytest 运行现有 `unittest.TestCase`？
2. `python -m pytest --collect-only -q` 能帮助发现什么问题？
3. pytest 如何知道应把哪个 fixture 传给测试参数？类型标注参与匹配吗？
4. fixture 与普通辅助函数分别适合什么场景？
5. 为什么默认的 function scope 通常比 session scope 更安全？
6. `tmp_path` 提供的是什么类型？为什么不优先使用旧的 `tmpdir`？
7. `capsys.readouterr()` 返回的 `out` 和 `err` 分别对应什么？
8. 为什么 `pytest.raises()` 的 `with` 块应该尽可能小？
9. 一个参数化测试函数为什么可能产生多个测试节点？
10. 为什么参数化值包含可变列表或字典时需要格外小心？
11. 哪些迹象说明两个用例不应该合并为参数化测试？
12. 为什么迁移到 pytest 后仍可以保留 `unittest.mock.patch`？
13. 为什么不能直接给 `unittest.TestCase` 方法增加 `tmp_path` 参数？
14. 从 21 passed 变成 18 passed 且没有失败，为什么仍可能是回归？

## 24. 完成检查

- [ ] 已用 pytest 原样运行迁移前的 21 个 `unittest` 测试。
- [ ] 能解释 pytest 的文件、函数、类和方法发现规则。
- [ ] 能使用节点 ID 和 `-k` 运行局部测试。
- [ ] 已将所有 `TestCase` 迁移为普通测试函数。
- [ ] 已使用普通 `assert` 替代 `self.assert*`。
- [ ] 已使用 `pytest.raises()` 验证异常类型与消息。
- [ ] 已定义至少一个小而聚焦的自定义 fixture。
- [ ] 已使用 `tmp_path` 测试文件读取。
- [ ] 已使用 `capsys` 分别验证 stdout 与 stderr。
- [ ] 已将三个日志统计场景改为带可读 ID 的参数化测试。
- [ ] 能解释 fixture、辅助函数和参数化各自解决的问题。
- [ ] 已删除不再使用的 `unittest` 与输出重定向相关代码。
- [ ] 必做部分仍收集并通过 21 个测试。
- [ ] mypy 检查 5 个源文件无错误。
- [ ] 若当前环境已经配置 Ruff，Ruff 检查通过；否则已记录为未配置。
- [ ] 三条 CLI 路径的输出与退出码未改变。
- [ ] 已回答小测的 14 个问题。

## 25. 视频与阅读材料

建议按“先直接运行旧测试 → 迁移断言 → 使用内置 fixture → 最后参数化”的顺序学习。先掌握 pytest 核心机制，本课不引入第三方插件。

### 必读

1. [pytest 官方入门](https://docs.pytest.org/en/stable/getting-started.html)：完成测试发现、普通 `assert`、异常断言和临时目录示例。
2. [pytest：在 pytest 中运行 unittest 测试](https://docs.pytest.org/en/stable/how-to/unittest.html)：重点理解为什么现有套件可以渐进迁移，以及 `TestCase` 使用 fixture 的限制。
3. [pytest：fixture 使用指南](https://docs.pytest.org/en/stable/how-to/fixtures.html)：重点阅读请求 fixture、fixture 依赖、作用域与清理。
4. [pytest：参数化测试](https://docs.pytest.org/en/stable/how-to/parametrize.html)：重点阅读 `@pytest.mark.parametrize`、参数 ID，以及参数值不会被复制的提醒。

### 按需查阅

- [pytest：断言与异常](https://docs.pytest.org/en/stable/how-to/assert.html)：查阅断言重写、`pytest.raises()` 与 `match` 的正则语义。
- [pytest：临时目录与文件](https://docs.pytest.org/en/stable/how-to/tmp_path.html)：查阅 `tmp_path`、保留策略和 `tmp_path_factory`；当前项目不需要扩大到 session scope。
- [pytest：内置 fixture 参考](https://docs.pytest.org/en/stable/reference/fixtures.html)：对照 `capsys`、`capfd`、`tmp_path` 和 `monkeypatch` 的职责。
- [pytest：调用与筛选测试](https://docs.pytest.org/en/stable/how-to/usage.html)：查阅节点 ID、`-k`、`-m` 与不同调用形式。

官方 pytest 文档已于 2026-08-17 重新核验。当前项目实测使用 pytest 9.1.1；`pyproject.toml` 允许 `pytest>=8.3,<10`。本课只依赖此范围内稳定的核心能力，不学习插件开发、hook、并行执行、覆盖率插件、异步测试插件、marker 治理或 CI 集成。

## 26. 提交给老师的内容

完成后发送：

1. 迁移前用 pytest 直接运行 21 个 `unittest` 测试的结果。
2. 迁移后的 `tests/test_log_analyzer.py`。
3. `python -m pytest --collect-only -q` 的完整输出，包含三个统计参数节点。
4. `python -m pytest -q` 与 mypy 的最终结果；若环境已经配置 Ruff，再附 Ruff 结果。
5. `log_file` fixture，以及使用 `tmp_path` 和 `capsys` 的测试。
6. 带 `id` 的日志统计参数化测试。
7. 三条 CLI 手动回归的输出和 `$LASTEXITCODE`。
8. 小测第 3、4、5、8、9、10、13、14 题的答案。

我会从以下方面进行代码评审：迁移是否渐进且可回归、测试发现是否完整、断言是否表达可观察行为、异常断言范围是否准确、fixture 边界与命名、测试隔离、参数化是否合并了同一契约、类型标注、公共接口依赖，以及生产行为是否保持不变。
