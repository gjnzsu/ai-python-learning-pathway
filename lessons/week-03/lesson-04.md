# 第 3 周 · 第 4 课：argparse、pathlib 与项目收尾

预计用时：120–150 分钟

## 本课目标

完成本课后，你能够：

- 解释为什么成熟 CLI 不应长期依赖手写 `sys.argv` 解析。
- 使用 `argparse.ArgumentParser` 定义位置参数、可选参数、帮助信息和退出行为。
- 在测试中处理 `argparse` 的 `SystemExit`，并保持 `main(arguments)` 易测试。
- 使用 `pathlib.Path` 表达文件路径，减少字符串拼接和跨平台路径问题。
- 区分“路径计算”和“真实 I/O”两个层次。
- 用 pytest 覆盖 CLI 帮助、参数错误、配置文件、I/O 失败和成功路径。
- 构建 wheel，理解源码、editable install、wheel 与 console script 的关系。
- 建立一个本地质量门禁：pytest、mypy、Ruff、手动 CLI 验收和 Git 状态检查。
- 完成第 3 周日志分析 CLI 的工程化收尾。

## 1. 为什么第四课要做项目收尾

第三周前三课已经把日志分析器从“可运行脚本”推进成了一个小型 Python 项目：

- 第 1 课：包结构、`src/` 布局、虚拟环境、`pyproject.toml`、可安装命令。
- 第 2 课：pytest、fixture、参数化测试、`tmp_path`、`capsys`。
- 第 3 课：logging、TOML 配置、可靠 I/O、`caplog`。

现在还剩几个真实项目迟早会碰到的问题：

- CLI 参数一多，手写 `if len(arguments) == ...` 会迅速变脆。
- 字符串路径可以用，但表达不出“这是路径”这个语义。
- 测试通过不等于项目可以交付，还要验证安装命令、构建产物和 Git 状态。
- 初学阶段容易把“能运行”和“可交付”混成一件事。

本课不继续扩展业务能力，而是完成第 3 周项目的收尾：把日志分析 CLI 整理到可以稳定演示、测试、安装和提交的状态。

## 2. 本课最终效果

本课结束后，命令行入口应该支持：

```powershell
python -m log_analyzer sample.log ERROR
```

也支持可安装命令：

```powershell
log-analyzer sample.log ERROR
```

也支持配置文件：

```powershell
log-analyzer sample.log ERROR --config log-analyzer.toml
```

还能显示帮助：

```powershell
log-analyzer --help
```

输出类似：

```text
usage: log-analyzer [-h] [--config CONFIG] log_file level
```

注意：帮助文本不需要和这里逐字一致。`argparse` 会根据 Python 版本和参数定义生成格式。测试应该验证关键内容，而不是死盯完整帮助文本。

## 3. 与 Spring Boot 的对照

Spring Boot 应用通常从这几个入口接收外部输入：

- 启动参数。
- 环境变量。
- `application.yml` 或 `application.properties`。
- profile。
- 文件系统、数据库、HTTP 请求等外部资源。

Python CLI 项目没有 Spring Boot 那么重的自动配置体系，但边界思路相同：

| 关注点 | Spring Boot 常见方式 | 本项目方式 |
| --- | --- | --- |
| 启动参数 | `ApplicationArguments` | `argparse` |
| 配置文件 | `application.yml` | `tomllib` 读取 TOML |
| 日志 | Logback + Boot 配置 | 标准库 `logging` |
| 路径 | `Path` / `Resource` | `pathlib.Path` |
| 构建产物 | jar | wheel |
| 质量门禁 | Maven/Gradle lifecycle | pytest + mypy + Ruff + build |

不要把 Python 项目想成“少了框架所以更随意”。更准确的说法是：Python 给你的默认积木更薄，你需要自己把边界搭清楚。

## 4. argparse 解决什么问题

第三课为了保持学习节奏，手写了简单参数解析：

```python
if len(arguments) == 2:
    file_path, level = arguments
    ...

if len(arguments) == 4 and arguments[2] == "--config":
    ...
```

这在两个参数时可以接受。一旦加入更多选项，它会变得难维护：

- `--config` 放在前面怎么办？
- 用户写 `--help` 怎么办？
- 缺少 `--config` 的值怎么办？
- 错误提示和 usage 谁来生成？
- 测试要不要覆盖每一种参数排列？

`argparse` 是 Python 标准库中的 CLI 参数解析器。它负责：

- 定义位置参数和可选参数。
- 解析 `sys.argv` 风格的字符串列表。
- 生成 usage 和 help。
- 在参数错误时给出诊断并退出。
- 支持默认值、类型转换、choices 等常见 CLI 需求。

官方文档对它的定位很直接：用来创建用户友好的命令行界面，程序定义需要哪些参数，`argparse` 负责解析和生成帮助。

## 5. 第零轮：确认第三课完成后的基线

进入项目：

```powershell
cd projects/log-analyzer
```

运行测试：

```powershell
python -m pytest -q
```

第三课完成后的预期：

```text
27 passed
```

运行静态检查：

```powershell
python -m mypy src tests
python -m ruff check .
```

如果第三课还没有实际实现，先完成第三课。第四课默认代码已经拥有：

- `config.py`。
- `AppConfig` 与 `load_config()`。
- `--config` 支持。
- logging 配置。
- I/O 失败返回退出码 `1`。

## 6. 第一轮 RED：帮助参数应显示 help 并退出 0

`argparse` 遇到 `--help` 时会打印帮助并抛出 `SystemExit(0)`。这和我们之前的 `main(arguments) -> int` 风格不完全一样。

为了保留可测试边界，本课采用两层函数：

- `parse_arguments(arguments)` 可以保留 `argparse` 的自然行为。
- `main(arguments)` 捕获 `SystemExit`，把退出码转成返回值。

先写测试：

```python
def test_returns_zero_for_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["--help"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "usage:" in captured.out
    assert "log_file" in captured.out
    assert "level" in captured.out
    assert captured.err == ""
```

当前预期失败：手写解析不知道 `--help`，通常会把它当作参数错误。

## 7. 第一轮 GREEN：引入 ArgumentParser

在 `cli.py` 中创建 parser：

```python
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="log-analyzer",
        description="Filter log events by level.",
    )
    parser.add_argument("log_file")
    parser.add_argument("level")
    parser.add_argument(
        "--config",
        dest="config_path",
        help="Path to a TOML configuration file.",
    )
    return parser
```

然后让 `parse_arguments()` 使用它：

```python
def parse_arguments(arguments: list[str]) -> CliArguments:
    parser = build_parser()
    namespace = parser.parse_args(arguments)

    return CliArguments(
        file_path=namespace.log_file,
        level=namespace.level,
        config_path=namespace.config_path,
    )
```

`main()` 捕获 `SystemExit`：

```python
try:
    cli_arguments = parse_arguments(arguments)
except SystemExit as error:
    return int(error.code)
```

运行：

```powershell
python -m pytest tests/test_log_analyzer.py::test_returns_zero_for_help -q
```

再运行全部测试：

```powershell
python -m pytest -q
```

预期：帮助测试通过，已有成功路径和配置路径仍通过。

## 8. 第二轮 RED：参数错误仍返回 2

`argparse` 参数错误默认写 stderr，并抛出 `SystemExit(2)`。这和我们前几课约定的参数错误退出码一致。

测试：

```python
def test_returns_usage_error_when_level_is_missing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["sample.log"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "usage:" in captured.err
    assert "the following arguments are required" in captured.err
```

如果这个测试失败，通常说明 `main()` 没有正确捕获 `SystemExit`，或者测试还在断言旧的手写 usage 文本。

这里要接受一个现实：切换到 `argparse` 后，错误信息由标准库生成，文本会比手写版本更丰富。测试应关注契约：

- 返回 `2`。
- stdout 为空。
- stderr 有 usage。
- stderr 提到缺失参数。

## 9. choices：限制可查询的日志级别吗？

可以给 `level` 增加 choices：

```python
parser.add_argument(
    "level",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
)
```

但本课暂时不这么做。原因是当前日志分析器可以处理任意日志级别：

```text
SECURITY
AUDIT
TRACE
```

如果用 `choices` 限死，反而缩小了业务能力。配置里的 logging level 应该限制为 Python logging 的标准级别；被筛选的日志事件 level 可以更自由。

这是一个重要区别：

- 应用日志级别：控制程序自身诊断，应符合 logging 标准级别。
- 被分析日志级别：来自输入数据，是业务数据，不应轻易限制。

## 10. pathlib 解决什么问题

目前代码里路径多半是字符串：

```python
def read_log_lines(file_path: str) -> list[str]:
    ...
```

字符串可以表示路径，但它也可以表示用户名、URL、日志级别或任何文本。`pathlib.Path` 把“这是一个文件系统路径”的意图写进类型里：

```python
from pathlib import Path

file_path = Path("sample.log")
```

它有几个好处：

- 使用 `/` 拼接路径，跨平台更清楚。
- `read_text()`、`write_text()` 等方法让测试更简洁。
- 类型标注能表达函数需要的是路径。
- Pure path 和 concrete path 的区别能帮助区分“只计算路径”和“真的访问文件系统”。

官方 `pathlib` 文档把路径类分成两类：

- pure paths：只做路径计算，不做 I/O。
- concrete paths：继承 pure paths，并能执行真实 I/O。

本项目主要使用 `Path` 这个 concrete path。

## 11. 第三轮 RED：让配置加载接受 Path

先写测试：

```python
def test_loads_config_from_path_object(tmp_path: Path) -> None:
    config_file = tmp_path / "log-analyzer.toml"
    config_file.write_text(
        "[logging]\nlevel = \"INFO\"\n",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.log_level == "INFO"
```

当前如果 `load_config()` 标注为 `str | None`，运行时可能已经能工作，因为 `open()` 接受 path-like 对象。但类型检查会提醒我们接口表达不完整。

## 12. 第三轮 GREEN：使用 os.PathLike 类型

为了同时接受 `str` 和 `Path`，可以定义类型别名：

```python
from os import PathLike

ConfigPath = str | PathLike[str]
```

然后修改：

```python
def load_config(file_path: ConfigPath | None) -> AppConfig:
    if file_path is None:
        return AppConfig()

    with open(file_path, "rb") as config_file:
        data = tomllib.load(config_file)
```

也可以在函数内部立即转换为 `Path`：

```python
path = Path(file_path)

with path.open("rb") as config_file:
    data = tomllib.load(config_file)
```

本课推荐第二种。它让后续错误信息、路径方法和类型标注更集中：

```python
from pathlib import Path

ConfigPath = str | Path


def load_config(file_path: ConfigPath | None) -> AppConfig:
    if file_path is None:
        return AppConfig()

    path = Path(file_path)

    with path.open("rb") as config_file:
        data = tomllib.load(config_file)
```

运行：

```powershell
python -m pytest -q
python -m mypy src tests
```

## 13. 第四轮 RED：FileLogSource 使用 Path

现在把文件日志来源也升级为 `Path`。

测试可以先表达期望：

```python
def test_file_log_source_accepts_path(log_file: Path) -> None:
    source = FileLogSource(log_file)

    with source.open_lines() as lines:
        assert next(lines) == "2026-08-08T10:00:00|INFO|server started"
```

如果 `FileLogSource.file_path` 仍标注为 `str`，mypy 会提示类型不匹配。这正是我们想要的信号。

## 14. 第四轮 GREEN：把核心 I/O 边界改成 Path

在 `core.py` 中：

```python
from pathlib import Path

LogPath = str | Path
```

修改读取函数：

```python
def read_log_lines(file_path: LogPath) -> list[str]:
    with open_log_lines(file_path) as lines:
        return list(lines)
```

`open_log_lines()`：

```python
@contextmanager
def open_log_lines(file_path: LogPath) -> Iterator[Iterator[str]]:
    path = Path(file_path)

    with path.open("r", encoding="utf-8") as log_file:

        def stripped_lines() -> Iterator[str]:
            for line in log_file:
                yield line.rstrip("\r\n")

        yield stripped_lines()
```

`FileLogSource`：

```python
@dataclass(frozen=True)
class FileLogSource:
    file_path: LogPath

    def open_lines(
        self,
    ) -> AbstractContextManager[Iterator[str]]:
        return open_log_lines(self.file_path)
```

这一步仍保持外部兼容：旧测试传 `str(log_file)` 可以继续工作，新测试传 `Path` 也可以工作。

## 15. 第五轮 RED：用 monkeypatch 验证入口调用

`run()` 负责从真实 `sys.argv` 进入应用：

```python
def run() -> None:
    raise SystemExit(main(sys.argv[1:]))
```

这个函数很薄，但它是 console script 会调用的入口。可以用 `monkeypatch` 做一个小测试：

```python
def test_run_uses_command_line_arguments(
    log_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["log-analyzer", str(log_file), "ERROR"],
    )

    with pytest.raises(SystemExit) as error:
        run()

    captured = capsys.readouterr()

    assert error.value.code == 0
    assert captured.out == (
        "2026-08-08T10:01:00|ERROR|database timeout\n"
    )
```

如果测试文件还没有导入 `sys` 和 `run`，需要补上。

`monkeypatch` fixture 会在测试结束后恢复被修改的对象，因此比手动改全局变量更安全。它适合测试依赖环境变量、当前目录、`sys.argv` 等全局状态的边界。

## 16. 第五轮 GREEN：保持 run 足够薄

如果 `run()` 已经是下面这样，可能不需要改生产代码：

```python
def run() -> None:
    raise SystemExit(main(sys.argv[1:]))
```

这就是好设计：入口越薄，测试越少需要碰真实全局状态。

本轮重点不是写复杂实现，而是确认 console script 的入口没有绕开 `main()`，也没有重复业务逻辑。

## 17. 构建 wheel

editable install 适合本地开发：

```powershell
python -m pip install -e ".[dev]"
```

但交付时通常会构建发行产物。Python 常见发行格式有：

- sdist：源码发行包。
- wheel：构建好的二进制发行格式；纯 Python 项目的 wheel 通常可跨平台安装。

先安装构建工具：

```powershell
python -m pip install build
```

构建：

```powershell
python -m build
```

构建后会出现：

```text
dist/
├── course_log_analyzer-0.1.0-py3-none-any.whl
└── course_log_analyzer-0.1.0.tar.gz
```

本课只本地构建，不上传 PyPI 或 TestPyPI。

## 18. 验证 wheel 内容

可以先列出 wheel 文件：

```powershell
Get-ChildItem dist
```

然后用临时虚拟环境安装 wheel：

```powershell
py -m venv .venv-wheel-test
.\.venv-wheel-test\Scripts\python -m pip install dist\course_log_analyzer-0.1.0-py3-none-any.whl
.\.venv-wheel-test\Scripts\log-analyzer sample.log ERROR
```

预期：

```text
2026-08-01T10:16:00|ERROR|database timeout
```

验证完成后删除临时环境：

```powershell
Remove-Item -Recurse -Force .venv-wheel-test
```

注意：`.venv-wheel-test/`、`dist/`、`build/`、`*.egg-info/` 都是可重建产物，不应提交。

如果 `.gitignore` 还没有包含这些目录，需要补充：

```gitignore
.venv/
.venv-wheel-test/
.pytest_cache/
.mypy_cache/
.ruff_cache/
build/
dist/
*.egg-info/
```

## 19. 本地质量门禁

本课建立一个固定收尾清单。以后每次准备提交前都按这个顺序跑：

```powershell
python -m pytest -q
python -m mypy src tests
python -m ruff check .
python -m build
git diff --check
git status --short
```

手动 CLI 验收：

```powershell
python -m log_analyzer sample.log ERROR
log-analyzer sample.log INFO
log-analyzer --help
log-analyzer missing.log ERROR
```

对于最后一条，PowerShell 查看退出码：

```powershell
$LASTEXITCODE
```

质量门禁不是为了仪式感。它解决的是“我觉得没问题”和“项目在可交付状态”之间的差距。

## 20. Git 收尾

提交前确认：

```powershell
git status --short
```

应该只看到源代码、测试、讲义或 `.gitignore` 等需要提交的文件，不应该看到：

```text
.venv/
.venv-wheel-test/
dist/
build/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
```

查看差异：

```powershell
git diff --stat
git diff --check
```

如果 `git diff --check` 报尾随空格或冲突标记，先修掉再提交。

提交：

```powershell
git add src tests pyproject.toml .gitignore
git commit -m "Polish log analyzer CLI"
```

如果本课只改讲义，就只提交讲义。不要用 `git add .` 盲目提交缓存、构建产物或临时虚拟环境。

## 21. 本课小测

1. 为什么手写 `len(arguments)` 解析在 CLI 选项变多后容易出问题？
2. `argparse.ArgumentParser` 主要负责哪几件事？
3. 为什么 `argparse` 遇到 `--help` 会抛出 `SystemExit(0)`？
4. `main(arguments) -> int` 和 `run() -> None` 分别适合承担什么职责？
5. 为什么测试 `argparse` 的错误信息时不应逐字断言完整文本？
6. 被分析日志的 level 为什么不一定要限制在 Python logging 标准级别中？
7. `Path("a") / "b"` 比字符串拼接路径好在哪里？
8. `pathlib` 中 pure path 和 concrete path 的区别是什么？
9. 为什么把 `str | Path` 转成 `Path` 后再打开文件，通常比到处传字符串更清楚？
10. `monkeypatch` 适合测试哪些全局状态？
11. editable install 和 wheel 分别适合什么阶段？
12. 为什么 `dist/` 和 `build/` 不应该提交？
13. 本地质量门禁里，pytest、mypy、Ruff 分别覆盖什么风险？
14. 为什么手动 CLI 验收仍然有价值，即使测试已经通过？

## 22. 完成清单

- [ ] `argparse` 已替代手写 CLI 参数解析。
- [ ] `--help` 返回 `0`，并输出帮助文本。
- [ ] 缺失必需参数返回 `2`。
- [ ] `--config` 可以位于日志文件和级别之后，并被正确解析。
- [ ] `main(arguments)` 仍返回整数退出码，方便测试。
- [ ] `run()` 仍只负责读取 `sys.argv` 并抛出 `SystemExit`。
- [ ] 配置加载函数支持 `Path`。
- [ ] 文件日志来源支持 `Path`。
- [ ] 旧的字符串路径调用仍保持兼容。
- [ ] 使用 `monkeypatch` 验证 console script 入口边界。
- [ ] wheel 构建成功。
- [ ] 临时 wheel 环境安装和运行成功。
- [ ] `dist/`、`build/`、虚拟环境和缓存未提交。
- [ ] pytest、mypy、Ruff、build、`git diff --check` 全部通过。
- [ ] 已完成手动 CLI 验收。

## 23. 课后练习

### 练习 1：支持 `--level`

当前 level 是位置参数：

```powershell
log-analyzer sample.log ERROR
```

尝试额外支持：

```powershell
log-analyzer sample.log --level ERROR
```

要求保持旧调用方式仍可用。思考：这会不会让 CLI 解析变复杂？是否值得？

### 练习 2：增加 `--version`

让 CLI 支持：

```powershell
log-analyzer --version
```

输出项目版本。提示：可以先直接使用 `pyproject.toml` 中的版本常量，后续再学习 `importlib.metadata.version()`。

### 练习 3：用 subprocess 做黑盒测试

使用 `subprocess.run()` 调用真实命令：

```python
subprocess.run(
    ["python", "-m", "log_analyzer", str(log_file), "ERROR"],
    capture_output=True,
    text=True,
)
```

比较它和直接调用 `main(arguments)` 的优缺点。不要把所有测试都改成 subprocess；它更慢，也更难定位失败原因。

## 24. 官方参考资料

- Python 官方文档：[`argparse`](https://docs.python.org/3/library/argparse.html)
- Python 官方文档：[`pathlib`](https://docs.python.org/3/library/pathlib.html)
- pytest 官方文档：[`monkeypatch`](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)
- Python Packaging User Guide：[`Packaging Python Projects`](https://packaging.python.org/tutorials/packaging-projects/)
- Python Packaging User Guide：[`Writing your pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- Python Packaging User Guide：[`Tool recommendations`](https://packaging.python.org/guides/tool-recommendations/)

官方资料已于 2026-08-19 核验。本课只做本地构建和安装验证，不发布到 PyPI。

## 25. 提交给老师的内容

完成后发送：

1. `argparse` 版本的 `cli.py`。
2. `Path` 版本的 `config.py` 和 `core.py` 相关片段。
3. `--help`、缺失参数、配置文件、I/O 失败和成功路径的测试。
4. `monkeypatch` 测试 `run()` 的用例。
5. `python -m pytest -q`、mypy、Ruff、`python -m build` 的完整通过结果。
6. wheel 临时环境安装和 `log-analyzer sample.log ERROR` 的输出。
7. `git status --short` 的输出，证明没有提交构建产物或缓存。
8. 小测第 2、4、5、6、8、11、12、14 题的答案。

我会从以下方面进行代码评审：CLI 契约是否清晰、`argparse` 使用是否过度、`main()` 与 `run()` 边界、路径类型是否表达准确、测试是否覆盖用户可见行为、构建产物是否可重建、质量门禁是否完整，以及第 3 周项目是否真正处于可交付状态。

