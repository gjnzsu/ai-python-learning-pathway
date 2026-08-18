# 第 3 周 · 第 3 课：logging、配置与可靠 I/O

预计用时：120–150 分钟

## 本课目标

完成本课后，你能够：

- 区分 `print()` 输出、异常和日志各自适合承担的职责。
- 解释 Python logging 的 logger、handler、level、formatter 与 propagation。
- 使用模块级 logger 记录诊断信息，而不是在库代码中直接配置全局 root logger。
- 让 CLI 的正常结果继续写入 stdout，让错误诊断写入 stderr。
- 使用 TOML 文件描述应用配置，并用标准库 `tomllib` 读取配置。
- 用数据类表达配置对象，并为缺省值、非法值和缺失文件建立清晰边界。
- 在 CLI 边界捕获常见 I/O 错误，返回稳定退出码。
- 使用 pytest 的 `tmp_path`、`capsys` 和 `caplog` 编写隔离、可重复的测试。
- 保持日志分析器的核心解析、过滤和流式读取模型不变。

## 1. 为什么现在要引入 logging 和配置

到上一课为止，日志分析器已经具备：

- `LogEvent` 数据类。
- 惰性解析和惰性过滤。
- `LogSource` 协议。
- `FileLogSource` 文件来源。
- 可测试的 `main(arguments)`。
- pytest 风格的 21 个测试。

目前 CLI 的成功路径很清楚：

```powershell
python -m log_analyzer sample.log ERROR
```

匹配的业务结果输出到 stdout：

```text
2026-08-01T10:16:00|ERROR|database timeout
```

但失败路径还不够像一个真实命令行程序：

```powershell
python -m log_analyzer missing.log ERROR
```

现在会让 `FileNotFoundError` 直接冒出，终端看到 Python traceback。这对开发调试有帮助，但对使用 CLI 的人不友好。一个更稳定的命令行程序应该：

- 参数错误返回 `2`，并打印 usage。
- 文件不存在、权限不足、无法读取等运行时 I/O 错误返回 `1`。
- 正常匹配结果仍然只进入 stdout，方便管道处理。
- 诊断信息进入 stderr，方便人和脚本区分。
- 是否打印更多诊断由配置控制。

这就是本课的主题：把“能跑的脚本”推进到“更像应用的小程序”。

## 2. print、异常与日志的分工

Python 初学阶段常用 `print()` 观察程序执行：

```python
print("reading file", file_path)
```

这没有错，但它不适合长期留在应用代码里。因为 `print()` 只有一个动作：把文本写出去。它很难表达：

- 这条信息是调试、普通信息、警告还是错误？
- 它应该写到控制台、文件，还是测试捕获器？
- 线上环境是否应该关闭它？
- 日志格式是否需要统一加时间、级别和模块名？

异常也不是日志。异常表示“当前路径无法按正常方式继续”，它应该被抛出或捕获；日志表示“记录发生了什么”，它不一定改变控制流。

本课采用这条边界：

| 信息类型 | 写到哪里 | 由谁负责 |
| --- | --- | --- |
| 匹配到的日志事件 | stdout | `print_matching_events()` |
| 参数用法错误 | stderr | `main()` |
| I/O 失败诊断 | stderr 日志 | `main()` 的 CLI 边界 |
| 解析和过滤内部过程 | logger | 核心模块按需记录 |
| 程序是否成功 | 退出码 | `main()` 返回整数 |

这与 Java/Spring Boot 中的分工类似：业务返回值、异常和日志是三条不同通道。不要把日志当返回值，也不要把返回给用户的数据塞进日志。

## 3. Python logging 的五个核心概念

### 3.1 logger

logger 是代码发出日志记录的入口：

```python
import logging

logger = logging.getLogger(__name__)
```

`__name__` 会得到当前模块名，例如：

```text
log_analyzer.core
log_analyzer.cli
```

这让日志天然形成层级。`log_analyzer.core` 是 `log_analyzer` 的子 logger。

官方 Logging HOWTO 建议库代码使用清晰唯一的 logger 名称，常见做法就是使用 `__name__`。不要在库模块里直接对 root logger 做随意配置，否则应用层会很难统一控制日志行为。

### 3.2 level

level 表示日志严重程度。常见级别从低到高是：

| Python level | 常见含义 | Java 对照 |
| --- | --- | --- |
| `DEBUG` | 开发诊断，默认通常不显示 | `DEBUG` |
| `INFO` | 正常但值得记录的运行事件 | `INFO` |
| `WARNING` | 可继续运行，但需要注意 | `WARN` |
| `ERROR` | 当前操作失败 | `ERROR` |
| `CRITICAL` | 程序级严重故障 | `FATAL` |

本课只配置 `DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL` 这些标准级别。

### 3.3 handler

handler 决定日志记录写到哪里：

- `StreamHandler`：写到终端流，常用于 stderr。
- `FileHandler`：写到文件。
- 测试里的 `caplog`：pytest 捕获日志记录。

一个 logger 可以有多个 handler。比如同一条 `ERROR` 可以同时写入 stderr 和文件。不过本课先保持简单：CLI 只配置一个写入 stderr 的 `StreamHandler`。

### 3.4 formatter

formatter 决定日志长什么样：

```text
ERROR log_analyzer.cli failed to read log file: missing.log
```

本课推荐格式：

```text
%(levelname)s %(name)s %(message)s
```

它包含级别、logger 名称和消息，足够教学，也不会被时间戳干扰测试断言。

### 3.5 propagation

logger 默认会把日志记录传给父 logger，这叫 propagation。

例如 `log_analyzer.cli` 记录一条 `ERROR`，它可以传给 `log_analyzer`，再传给 root logger。真实项目中，重复日志常常来自“子 logger 自己有 handler，同时又传播给父 logger”。

本课用一个最小应用级配置：

- 配置 root logger 的 handler 和 level。
- 模块内只创建 logger，不添加 handler。
- 让 propagation 保持默认。

这足以避免重复日志，也贴近许多 Python 应用的入门实践。

## 4. 本课要完成的功能

本课结束时，CLI 行为应该变成：

```powershell
python -m log_analyzer sample.log ERROR
```

stdout：

```text
2026-08-01T10:16:00|ERROR|database timeout
```

stderr：

```text

```

退出码：

```text
0
```

参数缺失：

```powershell
python -m log_analyzer
```

stderr：

```text
usage: python -m log_analyzer <log-file> <level> [--config <config-file>]
```

退出码：

```text
2
```

文件不存在：

```powershell
python -m log_analyzer missing.log ERROR
```

stderr：

```text
ERROR log_analyzer.cli failed to read log file: missing.log
```

退出码：

```text
1
```

使用配置文件：

```powershell
python -m log_analyzer sample.log ERROR --config log-analyzer.toml
```

示例配置：

```toml
[logging]
level = "DEBUG"
```

当配置为 `DEBUG` 时，程序可以额外记录诊断日志，例如正在读取哪个文件、目标日志级别是什么。正常匹配结果仍然只写 stdout。

## 5. 设计配置对象

我们先不要把 TOML 字典散落到 CLI 逻辑里。更好的边界是：

```python
@dataclass(frozen=True)
class AppConfig:
    log_level: str = "WARNING"
```

为什么默认是 `WARNING`？

- 成功路径不应默认产生诊断输出。
- `ERROR` 仍会在失败路径显示。
- `DEBUG` 可以由配置文件显式打开。

TOML 文件只负责表达外部配置：

```toml
[logging]
level = "INFO"
```

加载函数负责把外部配置转换成内部对象：

```python
def load_config(file_path: str | None) -> AppConfig:
    ...
```

建议规则：

| 场景 | 结果 |
| --- | --- |
| 未传配置文件 | 返回默认 `AppConfig()` |
| 配置文件存在且合法 | 返回对应 `AppConfig` |
| 配置文件不存在 | 抛出 `FileNotFoundError`，由 CLI 捕获 |
| TOML 语法错误 | 抛出 `ValueError` 或让 CLI 转为错误 |
| 日志级别非法 | 抛出 `ValueError("invalid log level: ...")` |

注意：`tomllib` 读取 TOML 时需要二进制文件对象：

```python
import tomllib

with open(file_path, "rb") as config_file:
    data = tomllib.load(config_file)
```

这和普通文本日志文件的 `open(..., "r", encoding="utf-8")` 不一样，是一个很好的小坑点。

## 6. 配置 logging

本课先用代码构造 logging 配置，不让学习者一开始就面对完整 `dictConfig` 结构。

```python
def configure_logging(config: AppConfig) -> None:
    logging.basicConfig(
        level=config.log_level,
        format="%(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("log_analyzer").setLevel(config.log_level)
```

`basicConfig()` 适合小 CLI 入门，但要知道它不是大型应用配置的终点。等项目更复杂时，可以使用 `logging.config.dictConfig()`，用字典统一描述 formatter、handler、filter 和 logger。

本课重点不是把 logging 配置写到最复杂，而是理解：

- 应用入口负责配置 logging。
- 业务模块只负责创建 logger 和记录事件。
- 测试可以捕获日志，而不是读取真实终端。

最后一行显式设置 `log_analyzer` 包 logger 的级别，是为了让 pytest 的 `caplog` 和应用自己的配置配合得更稳定。pytest 会安装自己的日志捕获 handler，因此测试中不要假设 logging 一定能被 `capsys` 当作普通 stderr 文本捕获。

## 7. 第零轮：确认当前基线

进入项目目录：

```powershell
cd projects/log-analyzer
```

运行测试：

```powershell
python -m pytest -q
```

当前预期：

```text
21 passed
```

运行类型检查：

```powershell
python -m mypy src tests
```

运行格式检查：

```powershell
python -m ruff check .
```

如果这里不通过，先不要进入本课功能。logging 和配置会碰到 CLI 边界、文件系统和测试捕获，如果基线不干净，后面的失败很难判断是新问题还是旧问题。

## 8. 第一轮 RED：缺失文件应返回退出码 1

先写测试。上一课已经有 `tmp_path` 和 `capsys`，这次继续用它们验证 CLI 外部行为。

```python
def test_returns_error_when_log_file_does_not_exist(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_file = tmp_path / "missing.log"

    exit_code = main([str(missing_file), "ERROR"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "failed to read log file" in captured.err
    assert str(missing_file) in captured.err
```

运行单个测试：

```powershell
python -m pytest tests/test_log_analyzer.py::test_returns_error_when_log_file_does_not_exist -q
```

预期失败：当前 `main()` 没有捕获 `FileNotFoundError`，所以测试不会得到退出码 `1`。

## 9. 第一轮 GREEN：在 CLI 边界捕获 OSError

`FileNotFoundError`、`PermissionError` 等文件系统错误都是 `OSError` 的子类。CLI 边界可以先捕获 `OSError`：

```python
def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        print(
            "usage: python -m log_analyzer <log-file> <level> [--config <config-file>]",
            file=sys.stderr,
        )
        return 2

    file_path, level = arguments
    source = FileLogSource(file_path)

    try:
        print_matching_events(source, level)
    except OSError:
        print(f"failed to read log file: {file_path}", file=sys.stderr)
        return 1

    return 0
```

这一步先用 `print(..., file=sys.stderr)` 通过测试，暂时还没有引入 logging。TDD 的节奏是一次只改变一个维度。

运行测试：

```powershell
python -m pytest -q
```

预期新增测试通过，总数变为：

```text
22 passed
```

## 10. 第一轮 REFACTOR：用日志表达诊断

现在把错误诊断从 `print()` 改成 logging：

```python
import logging
import sys

from .core import FileLogSource, print_matching_events

logger = logging.getLogger(__name__)
```

在 `main()` 中：

```python
try:
    print_matching_events(source, level)
except OSError:
    logger.error("failed to read log file: %s", file_path)
    return 1
```

但只这样改，测试可能看不到 stderr，因为还没有配置 handler。小 CLI 可以先在入口配置：

```python
def main(arguments: list[str]) -> int:
    logging.basicConfig(
        level="WARNING",
        format="%(levelname)s %(name)s %(message)s",
    )
    ...
```

这会让 `ERROR log_analyzer.cli failed to read log file: ...` 出现在 stderr。

同时把测试改为用 `caplog` 断言日志记录：

```python
def test_returns_error_when_log_file_does_not_exist(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    missing_file = tmp_path / "missing.log"

    exit_code = main([str(missing_file), "ERROR"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "failed to read log file" in caplog.text
    assert str(missing_file) in caplog.text
```

这里 `capsys` 只负责 stdout，`caplog` 负责 logging。手动运行 CLI 时，logging 配置仍会把错误诊断写到 stderr。

再次运行：

```powershell
python -m pytest -q
```

如果测试仍然用 `captured.err` 断言日志文本，建议现在改掉。pytest 会单独捕获 logging，`caplog` 是更准确的工具。

## 11. 第二轮 RED：支持配置文件参数

现在开始支持可选参数：

```powershell
python -m log_analyzer sample.log ERROR --config log-analyzer.toml
```

先写测试：

```python
def test_accepts_config_file_argument(
    log_file: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_file = tmp_path / "log-analyzer.toml"
    config_file.write_text(
        "[logging]\nlevel = \"DEBUG\"\n",
        encoding="utf-8",
    )

    exit_code = main(
        [str(log_file), "ERROR", "--config", str(config_file)]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == (
        "2026-08-08T10:01:00|ERROR|database timeout\n"
    )
```

这个测试先只验证参数形状被接受，不急着断言 debug 日志。否则我们会同时引入配置解析、logging 捕获和 CLI 参数解析三个失败原因。

当前预期失败：`main()` 只接受两个参数，四个参数会返回 usage 错误。

## 12. 第二轮 GREEN：解析可选 --config

保持手写解析即可。项目还小，暂时不引入 `argparse`：

```python
@dataclass(frozen=True)
class CliArguments:
    file_path: str
    level: str
    config_path: str | None = None
```

解析函数：

```python
def parse_arguments(arguments: list[str]) -> CliArguments:
    if len(arguments) == 2:
        file_path, level = arguments
        return CliArguments(file_path=file_path, level=level)

    if len(arguments) == 4 and arguments[2] == "--config":
        file_path, level, _, config_path = arguments
        return CliArguments(
            file_path=file_path,
            level=level,
            config_path=config_path,
        )

    raise ValueError("invalid arguments")
```

`main()` 负责把解析错误转成 usage：

```python
try:
    cli_arguments = parse_arguments(arguments)
except ValueError:
    print(
        "usage: python -m log_analyzer <log-file> <level> [--config <config-file>]",
        file=sys.stderr,
    )
    return 2
```

运行测试：

```powershell
python -m pytest -q
```

预期：

```text
23 passed
```

## 13. 第三轮 RED：读取 TOML 配置

先写配置加载的单元测试。它不需要跑完整 CLI：

```python
def test_loads_log_level_from_config_file(tmp_path: Path) -> None:
    config_file = tmp_path / "log-analyzer.toml"
    config_file.write_text(
        "[logging]\nlevel = \"INFO\"\n",
        encoding="utf-8",
    )

    config = load_config(str(config_file))

    assert config.log_level == "INFO"
```

还要补默认配置：

```python
def test_uses_default_config_when_config_path_is_missing() -> None:
    config = load_config(None)

    assert config == AppConfig(log_level="WARNING")
```

这两个测试会失败，因为 `AppConfig` 和 `load_config()` 还不存在。

## 14. 第三轮 GREEN：实现 AppConfig 和 load_config

可以新建 `src/log_analyzer/config.py`：

```python
import tomllib
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    log_level: str = "WARNING"


VALID_LOG_LEVELS = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}


def load_config(file_path: str | None) -> AppConfig:
    if file_path is None:
        return AppConfig()

    with open(file_path, "rb") as config_file:
        data = tomllib.load(config_file)

    logging_section = data.get("logging", {})
    raw_level = logging_section.get("level", "WARNING")

    if not isinstance(raw_level, str):
        raise ValueError("logging.level must be a string")

    log_level = raw_level.upper()

    if log_level not in VALID_LOG_LEVELS:
        raise ValueError(f"invalid log level: {raw_level}")

    return AppConfig(log_level=log_level)
```

在包公开接口里导出：

```python
from .config import AppConfig, load_config
```

运行：

```powershell
python -m pytest -q
python -m mypy src tests
```

预期测试变为：

```text
25 passed
```

## 15. 第四轮 RED：非法配置返回退出码 2

配置语法或配置值错误，属于“用户输入不合法”，比文件读取失败更接近参数错误，因此本课将它映射为退出码 `2`。

测试非法日志级别：

```python
def test_returns_usage_error_for_invalid_log_level_config(
    log_file: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_file = tmp_path / "log-analyzer.toml"
    config_file.write_text(
        "[logging]\nlevel = \"VERBOSE\"\n",
        encoding="utf-8",
    )

    exit_code = main(
        [str(log_file), "ERROR", "--config", str(config_file)]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "invalid log level: VERBOSE" in captured.err
```

这个测试会失败，因为 `main()` 还没有调用 `load_config()`，也没有处理配置错误。

## 16. 第四轮 GREEN：把配置接入 CLI

`main()` 的顺序建议是：

1. 解析 CLI 参数。
2. 加载配置。
3. 配置 logging。
4. 组装 `FileLogSource`。
5. 执行业务流程。
6. 把边界错误转换成退出码。

示意代码：

```python
try:
    config = load_config(cli_arguments.config_path)
except (OSError, ValueError) as error:
    print(str(error), file=sys.stderr)
    return 2

configure_logging(config)
```

这里有一个取舍：配置文件不存在算 `2` 还是 `1`？

本课建议把“配置文件不存在”归为 `2`。因为用户显式传入了 `--config`，这个路径就是命令行输入的一部分。日志文件不存在归为 `1`，因为主操作执行时读取目标数据失败。

运行：

```powershell
python -m pytest -q
```

预期：

```text
26 passed
```

## 17. 第五轮 RED：用 caplog 验证 debug 日志

`capsys` 捕获 stdout/stderr，`caplog` 捕获 logging 记录。不要用 `capsys` 去测试所有日志细节，否则测试会和 handler 格式强绑定。

先在核心流程加一条 debug 日志：

```python
logger.debug("filtering log events by level: %s", level)
```

测试：

```python
def test_logs_debug_message_when_debug_is_enabled(
    log_file: Path,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG", logger="log_analyzer")

    config_file = tmp_path / "log-analyzer.toml"
    config_file.write_text(
        "[logging]\nlevel = \"DEBUG\"\n",
        encoding="utf-8",
    )

    exit_code = main(
        [str(log_file), "ERROR", "--config", str(config_file)]
    )

    assert exit_code == 0
    assert "filtering log events by level: ERROR" in caplog.text
```

当前预期失败：核心代码还没有记录 debug 日志，或者 logging 配置没有影响到 pytest 捕获器。

## 18. 第五轮 GREEN：在业务代码中记录低噪声日志

在 `core.py` 顶部：

```python
import logging

logger = logging.getLogger(__name__)
```

在 `print_matching_events()` 中：

```python
def print_matching_events(source: LogSource, level: str) -> None:
    logger.debug("filtering log events by level: %s", level)

    with source.open_lines() as lines:
        events = parse_log_lines(lines)
        matching_events = filter_events_by_level(events, level)

        for event in matching_events:
            print(f"{event.timestamp}|{event.level}|{event.message}")
```

这条日志只在 DEBUG 打开时出现。它不会污染 stdout，也不会改变函数返回值。

运行：

```powershell
python -m pytest -q
python -m mypy src tests
python -m ruff check .
```

预期：

```text
27 passed
```

## 19. 和 Spring Boot 配置的对照

Spring Boot 常见配置：

```yaml
logging:
  level:
    com.example: DEBUG
```

Python 这节课的 TOML：

```toml
[logging]
level = "DEBUG"
```

二者都在做同一件事：把环境差异从代码里拿出来。

差异在于：

- Spring Boot 有完整自动配置体系。
- Python 标准库提供 logging 和 TOML 解析，但不会替你规定应用结构。
- 小项目可以手写 `AppConfig`，大项目再引入 Pydantic、Dynaconf、Hydra 等配置库。
- 本课优先学习标准库能力，避免把“配置管理框架”误认为“配置边界”本身。

## 20. 常见坑

### 20.1 在模块导入时调用 basicConfig

不要这样写：

```python
logging.basicConfig(level="DEBUG")
```

如果这行位于模块顶层，导入模块就会改变全局 logging 状态。测试和其他应用都会受影响。

更好的做法是应用入口显式调用：

```python
def main(arguments: list[str]) -> int:
    ...
    configure_logging(config)
```

### 20.2 用 print 测试日志

日志不是普通 stdout。pytest 提供 `caplog` 捕获 logging 记录：

```python
assert "filtering log events" in caplog.text
```

stdout/stderr 仍用 `capsys`：

```python
captured = capsys.readouterr()
assert captured.out == expected_output
```

### 20.3 把所有异常都吞掉

不要这样写：

```python
try:
    print_matching_events(source, level)
except Exception:
    return 1
```

这会隐藏编程错误。例如 `TypeError`、`AttributeError` 很可能是代码 bug，不应该被伪装成文件读取失败。

本课只捕获边界上明确预期的异常：

```python
except OSError:
    ...
```

### 20.4 让配置字典到处传

不要让核心函数接收原始字典：

```python
def run_pipeline(config: dict[str, object]) -> None:
    ...
```

配置加载层应该尽早把外部数据转换成明确类型：

```python
AppConfig(log_level="DEBUG")
```

这会让 IDE、mypy 和测试都更容易帮你发现问题。

### 20.5 断言完整日志格式

测试日志时，不一定要断言整行：

```python
assert caplog.text == "DEBUG log_analyzer.core filtering log events by level: ERROR\n"
```

这种测试和格式强绑定，后续改 formatter 会造成无意义失败。

更稳的断言：

```python
assert "filtering log events by level: ERROR" in caplog.text
```

如果本课目标正是 formatter，则再断言完整格式。

## 21. 完成本课后的目标结构

```text
projects/log-analyzer/
├── pyproject.toml
├── sample.log
├── src/
│   └── log_analyzer/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       └── core.py
└── tests/
    └── test_log_analyzer.py
```

新增职责：

| 文件 | 职责 |
| --- | --- |
| `config.py` | 读取 TOML，验证配置，返回 `AppConfig` |
| `cli.py` | 解析 CLI 参数，配置 logging，转换退出码 |
| `core.py` | 保持解析、过滤、读取和输出管道，按需记录业务诊断 |
| `test_log_analyzer.py` | 覆盖配置、I/O 错误和日志捕获 |

## 22. 最终验收

运行测试：

```powershell
python -m pytest -q
```

预期：

```text
27 passed
```

运行类型检查：

```powershell
python -m mypy src tests
```

预期：

```text
Success: no issues found in 5 source files
```

如果新增 `config.py` 后 mypy 检查源文件数量变为 6，也正常。关键是 no issues。

运行 Ruff：

```powershell
python -m ruff check .
```

预期：

```text
All checks passed!
```

手动验证正常路径：

```powershell
python -m log_analyzer sample.log ERROR
```

预期 stdout 有匹配日志，退出码为 `0`。

手动验证错误路径：

```powershell
python -m log_analyzer missing.log ERROR
```

预期 stderr 有错误日志，退出码为 `1`。

手动验证配置路径：

```powershell
@"
[logging]
level = "DEBUG"
"@ | Set-Content -Encoding UTF8 log-analyzer.toml

python -m log_analyzer sample.log ERROR --config log-analyzer.toml
```

预期 stdout 仍然只包含匹配事件；stderr 可以出现 DEBUG 诊断。

## 23. 小测

1. 为什么 CLI 的正常业务结果应该写 stdout，而诊断信息应该写 stderr？
2. `logger = logging.getLogger(__name__)` 中的 `__name__` 有什么好处？
3. logger、handler、formatter 分别负责什么？
4. 为什么不建议在库模块导入时调用 `logging.basicConfig()`？
5. `FileNotFoundError` 和 `PermissionError` 与 `OSError` 有什么关系？
6. `tomllib.load()` 为什么要读取二进制文件对象？
7. `capsys` 和 `caplog` 分别适合测试什么？
8. 为什么配置加载函数应该返回 `AppConfig`，而不是到处传 `dict[str, object]`？
9. 配置文件不存在时，本课为什么把它视为退出码 `2`？
10. 为什么不要用 `except Exception` 包住整个 CLI？

## 24. 课后练习

### 练习 1：支持小写日志级别

让配置文件允许：

```toml
[logging]
level = "debug"
```

内部仍转换成：

```python
AppConfig(log_level="DEBUG")
```

为 `"debug"`、`"Info"`、`"WARNING"` 写参数化测试。

### 练习 2：为配置文件缺失补测试

当用户传入：

```powershell
python -m log_analyzer sample.log ERROR --config missing.toml
```

程序应返回 `2`，stderr 包含缺失配置路径。

### 练习 3：使用 dictConfig 重写 logging 配置

阅读 `logging.config.dictConfig()` 文档，把：

```python
logging.basicConfig(...)
```

替换成：

```python
logging.config.dictConfig(...)
```

保持测试通过。

提示：这是进阶练习，不是本课主线必做内容。

## 25. 官方参考资料

- Python 官方文档：[`logging` 标准库](https://docs.python.org/3/library/logging.html)
- Python 官方 HOWTO：[`Logging HOWTO`](https://docs.python.org/3/howto/logging.html)
- Python 官方文档：[`logging.config`](https://docs.python.org/3/library/logging.config.html)
- Python 官方文档：[`tomllib`](https://docs.python.org/3/library/tomllib.html)
- pytest 官方文档：[`tmp_path`、`capsys`、`caplog` 等 fixture 参考](https://docs.pytest.org/en/stable/reference/fixtures.html)

## 26. 完成清单

- [ ] 能解释 stdout、stderr、异常和日志的边界。
- [ ] 能说出 logger、handler、level、formatter 和 propagation 的作用。
- [ ] CLI 缺失参数返回 `2`。
- [ ] CLI 日志文件读取失败返回 `1`。
- [ ] 成功路径 stdout 只包含匹配日志事件。
- [ ] 诊断信息通过 logging 写入 stderr。
- [ ] 支持 `--config <config-file>` 可选参数。
- [ ] 使用 TOML 配置日志级别。
- [ ] 配置加载返回明确的 `AppConfig` 对象。
- [ ] 非法配置有测试覆盖。
- [ ] 使用 `caplog` 验证日志记录。
- [ ] pytest、mypy 和 Ruff 全部通过。
