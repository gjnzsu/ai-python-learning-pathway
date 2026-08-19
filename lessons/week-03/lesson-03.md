# 第 3 周 · 第 3 课（30 分钟版）：logging、配置与可靠 I/O

## 课程目标（今天要拿下的）

通过最小改动完成一个可交付的 CLI 体验：

1. 用标准库 logging 替代“散落的 print 诊断”。
2. 用 `tomllib` 从 TOML 读取日志配置（仅记录日志级别）。
3. 改进 `main(arguments)` 错误边界：  
   - I/O 读取失败返回 `1`。  
   - 参数错误返回 `2`。  
4. 使用 pytest 的 `tmp_path`、`capsys`、`caplog` 验证行为。

目标是**30 分钟内完成一次 RED → GREEN → REFACTOR**。

## 先讲清楚

- `stdout`：给下游程序/管道的“业务结果”。  
- `stderr`：给人/运维看的诊断与错误。  
- `print()`：适合临时调试。  
- `logging`：适合可配置、可分级、可重定向的长期日志。

我们不会大改结构，只加一层可靠的入口边界和配置层。

## 先跑基线

进入项目后先确认：

```powershell
cd projects/log-analyzer
python -m pytest -q
```

预期：既有测试通过（`21` 或当前仓库实际数）。

## RED：先写失败测试（10 分钟）

在 `tests/test_log_analyzer.py` 新增/调整 5 个最小测试（不追求完全覆盖）：

1. `main([])` 仍返回 `2`，`stdout` 为空，`stderr` 有 usage。  
2. 正常路径不受影响：`main([sample.log, "ERROR"])` 业务输出不变。  
3. 文件不存在返回 `1`，`stderr` 包含读取失败提示。  
4. `--config` 生效：`main([sample.log, "ERROR", "--config", "log-analyzer.toml"])` 成功。  
5. 配置非法 level 返回 `2`（例如 `VERBOSE`）。

这些测试要能明确表达“教学目标”，不是追求大量边界。

示例测试骨架（按需精简）：

```python
def test_returns_usage_error_when_arguments_missing(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "usage:" in captured.err

def test_returns_io_error_code_for_missing_log_file(tmp_path, capsys):
    exit_code = main([str(tmp_path / "missing.log"), "ERROR"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "failed to read log file" in captured.err
```

运行这个测试块应当失败，这是我们想要的红灯。

## GREEN：最小实现（12 分钟）

### 1) 加一个 `AppConfig` + `load_config`

新增 `projects/log-analyzer/src/log_analyzer/config.py`：

```python
from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class AppConfig:
    log_level: str = "WARNING"


def load_config(file_path: str | None) -> AppConfig:
    if file_path is None:
        return AppConfig()

    with Path(file_path).open("rb") as config_file:
        data = tomllib.load(config_file)

    logging_section = data.get("logging", {})
    level = logging_section.get("level", "WARNING")
    normalized = str(level).upper()
    if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError(f"invalid log level: {level}")
    return AppConfig(log_level=normalized)
```

### 2) `cli.py` 加可选配置参数与异常码

- `main(arguments)` 用 `try/except`：
  - 参数解析失败：`return 2`
  - 配置加载失败：`return 2`
  - 文件读取/流读取 `OSError`：`return 1`
- 成功时返回 `0`。

### 3) 配置 logging

```python
import logging

def configure_logging(config: AppConfig) -> None:
    logging.basicConfig(
        level=config.log_level,
        format="%(levelname)s %(name)s %(message)s",
    )
```

`main()` 先加载配置再执行业务逻辑，确保后续日志按配置输出。

### 4) 在核心路径加一条 debug 日志

`core.py` 中 `print_matching_events` 里加：

```python
import logging
logger = logging.getLogger(__name__)
...
logger.debug("filtering log events by level: %s", level)
```

不要在测试里断言完整日志格式，先断言关键短语在输出中。

## REFACTOR：把职责收敛（5 分钟）

1. 保持 `core.py` 不做 CLI 参数解析。  
2. 把 I/O 解析、日志配置、退出码留在 `cli.py`。  
3. `run()` 只负责 `raise SystemExit(main(sys.argv[1:]))`。  

再次运行：

```powershell
python -m pytest -q
```

本课目标：测试通过且行为闭环正确。

## 统一验收（剩余 3 分钟）

手工验证 4 条命令：

1. 成功路径  
   `python -m log_analyzer sample.log ERROR`  
2. 参数错误  
   `python -m log_analyzer`  
3. 文件不存在  
   `python -m log_analyzer missing.log ERROR`  
4. 配置路径  
   `python -m log_analyzer sample.log ERROR --config log-analyzer.toml`

验收标准：

- 成功路径 stdout 有匹配日志，`stderr` 为空。  
- 参数错误返回码 `2`，`stderr` 有 usage。  
- 文件 I/O 失败返回码 `1`，`stderr` 有 I/O 错误。  
- `--config` 能控制日志级别。  
- `python -m pytest` 全部通过。

## 课程小练习（选做）

1. 让 `--config` 支持小写 `debug` 并转换为 `DEBUG`。  
2. 加一条测试：`caplog` 可以看到 `"filtering log events by level"`。  
3. 在日志里增加一条 warning（例如文件存在但不可读时的额外提示）。

## 参考

- `tomllib`：`https://docs.python.org/3/library/tomllib.html`  
- `logging`：`https://docs.python.org/3/library/logging.html`  
- `logging HOWTO`：`https://docs.python.org/3/howto/logging.html`  
- `pytest`: `capsys` / `caplog`：`https://docs.pytest.org/en/stable/reference/fixtures.html`  

以上是“可在半小时内完成一轮 RED/GREEN/REFACTOR”的版式。下一课如果想接着走，可直接衔接 `argparse` 与 `pathlib`（week-03/lesson-04）。
