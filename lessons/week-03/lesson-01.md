# 第 3 周 · 第 1 课：项目结构、模块、包与依赖环境

预计用时：120–150 分钟

## 本课目标

完成本课后，你能够：

- 区分 Python 模块、导入包与可安装发行包。
- 解释 `import` 如何根据模块搜索路径定位代码。
- 使用 `src/` 布局把单文件脚本重构为职责清晰的包。
- 使用 `__init__.py` 定义包的公开接口，使用 `__main__.py` 支持 `python -m`。
- 使用 `venv` 为项目创建隔离环境，并确认当前解释器和 `pip` 属于同一环境。
- 使用 `pyproject.toml` 描述项目元数据、Python 版本和直接依赖。
- 使用 editable install 进行本地开发。
- 保持现有 21 个测试、mypy 静态检查与 CLI 外部行为不变。

## 1. 为什么现在要拆分单文件

当前日志分析器只有一个实现文件：

```text
projects/log-analyzer/
├── log_analyzer.py
├── sample.log
└── tests/
    └── test_log_analyzer.py
```

这在学习早期非常合适：打开一个文件就能看到数据对象、解析、过滤、文件读取和 CLI。随着功能增长，它开始同时承担多种职责：

- 定义 `LogEvent` 数据结构。
- 定义 `LogSource` 协议与文件数据源。
- 解析和过滤日志。
- 在上下文管理器中流式读取文件。
- 处理命令行参数和输出。
- 作为可导入模块。
- 作为可执行脚本。

本课不增加业务功能，而是改善代码的组织、安装和运行方式。重构后的数据流不变：

```text
命令行参数
    → 读取文件
    → 惰性解析
    → 惰性过滤
    → 输出匹配事件
```

这相当于把一个逐渐变大的 Java 类拆进合适的 package，并为应用建立明确的构建与运行入口。不同的是，Python 的“package”还可能表示发行物，因此要先澄清术语。

## 2. 四个容易混淆的概念

### 2.1 模块 module

一个 `.py` 文件通常就是一个模块：

```text
core.py  →  模块 log_analyzer.core
cli.py   →  模块 log_analyzer.cli
```

模块提供自己的命名空间。导入模块：

```python
import log_analyzer.core

event = log_analyzer.core.parse_log_line(line)
```

也可以导入模块中的名称：

```python
from log_analyzer.core import parse_log_line
```

### 2.2 导入包 import package

包含模块的目录可以构成导入包：

```text
log_analyzer/
├── __init__.py
├── core.py
├── cli.py
└── __main__.py
```

这里的 `log_analyzer` 是导入名：

```python
import log_analyzer
from log_analyzer.core import LogEvent
```

本课使用普通包，并保留 `__init__.py`。Python 还支持没有 `__init__.py` 的 namespace package，但它主要解决一个逻辑包跨多个发行物或目录的问题，不是当前项目所需。

### 2.3 发行包 distribution package

`pip install ...` 安装的是发行包。发行名来自 `pyproject.toml`：

```toml
[project]
name = "course-log-analyzer"
```

安装命令和导入语句可以使用不同的名称：

```powershell
python -m pip install course-log-analyzer
```

```python
import log_analyzer
```

发行名常使用连字符，Python 导入名必须是合法标识符，因此通常使用下划线。不要根据 `pip` 名称机械猜测导入名。

### 2.4 虚拟环境 environment

虚拟环境不是代码包，也不是依赖清单。它是项目专用的 Python 解释器环境，拥有自己的已安装第三方包集合。

可以先建立这组对应关系：

| Python 概念 | 当前项目示例 | Java 近似类比 |
| --- | --- | --- |
| 模块 | `log_analyzer.core` | 一个源码文件中的类型与函数集合 |
| 导入包 | `log_analyzer` | Java package，但运行时机制不同 |
| 发行包 | `course-log-analyzer` | Maven/Gradle artifact |
| `pyproject.toml` | 项目元数据与依赖声明 | `pom.xml` / `build.gradle` 的一部分职责 |
| 虚拟环境 | `.venv` | 项目隔离的工具链与依赖目录；不是 JVM 的一比一对应物 |

## 3. 目标项目结构

本课结束时，`projects/log-analyzer` 将演进为：

```text
projects/log-analyzer/
├── pyproject.toml
├── README.md
├── sample.log
├── src/
│   └── log_analyzer/
│       ├── __init__.py
│       ├── __main__.py
│       ├── core.py
│       └── cli.py
└── tests/
    └── test_log_analyzer.py
```

各文件职责如下：

- `core.py`：`LogEvent`、解析、过滤和文件读取等核心逻辑。
- `cli.py`：参数检查、管道组合、终端输出和退出码。
- `__init__.py`：声明稳定的包级公开接口。
- `__main__.py`：让 `python -m log_analyzer` 成为正式执行入口。
- `pyproject.toml`：项目元数据、Python 版本、依赖和命令行脚本配置。

这不是“每个函数一个文件”。边界应按变化原因划分：核心处理规则与 CLI 交互规则分别变化，所以先拆成两个主要模块已经足够。

## 4. `import` 到底在找什么

执行：

```python
import log_analyzer
```

Python 会沿 `sys.path` 中的目录寻找匹配的模块或包。可以观察搜索路径：

```powershell
python -c "import sys; print(*sys.path, sep='\n')"
```

也可以确认实际导入了哪个文件：

```powershell
python -c "import log_analyzer; print(log_analyzer.__file__)"
```

第二条命令是排查“我明明改了代码，为什么运行的还是旧版本”的利器。如果输出指向另一个项目、全局 `site-packages` 或旧的 `log_analyzer.py`，说明当前导入的不是你以为的代码。

### 导入时会执行模块顶层代码

模块第一次被当前 Python 进程导入时，Python 会执行它的顶层语句，用这些结果初始化模块对象。因此不要在核心模块顶层执行 CLI、访问网络或读取业务文件。

下面的保护仍然有意义：

```python
if __name__ == "__main__":
    ...
```

不过包化以后，我们会把正式入口放进 `__main__.py` 和 console script，不再让核心模块同时扮演入口。

### 包内导入

`cli.py` 引用同一个包中的 `core.py` 时，可以使用显式相对导入：

```python
from .core import filter_events_by_level, parse_log_lines, read_log_lines
```

开头的 `.` 表示当前包。它依赖包上下文，所以不要直接运行：

```powershell
python src/log_analyzer/cli.py
```

应通过包入口运行：

```powershell
python -m log_analyzer
```

## 5. 创建项目虚拟环境

进入项目目录：

```powershell
cd projects/log-analyzer
```

确认基础解释器：

```powershell
py --version
```

创建名为 `.venv` 的环境：

```powershell
py -m venv .venv
```

PowerShell 中激活：

```powershell
.\.venv\Scripts\Activate.ps1
```

如果公司策略禁止执行激活脚本，不需要修改全局执行策略。可以直接调用环境中的解释器：

```powershell
.\.venv\Scripts\python.exe --version
```

激活的本质是调整当前终端的 `PATH`，让 `python` 和相关命令优先指向 `.venv`。即使不激活，直接写完整解释器路径也能获得相同的环境隔离。

### 验证当前环境

不要只根据提示符前面的 `(.venv)` 判断。直接检查：

```powershell
python -c "import sys; print(sys.executable)"
python -m pip --version
```

两条输出都应指向当前项目的 `.venv`。本课程优先使用：

```powershell
python -m pip ...
```

它明确要求“让当前这个 Python 运行它所对应的 pip”，比裸写 `pip ...` 更不容易装错环境。

退出环境：

```powershell
deactivate
```

`.venv/` 是可重建产物，不提交到 Git。仓库根目录的 `.gitignore` 已经忽略它。

## 6. 用 `pyproject.toml` 描述项目

在 `projects/log-analyzer/pyproject.toml` 写入：

```toml
[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[project]
name = "course-log-analyzer"
version = "0.1.0"
description = "A tested log analysis CLI built during the Python learning pathway"
requires-python = ">=3.12"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=8.3,<10",
    "mypy>=2.3,<3",
]

[project.scripts]
log-analyzer = "log_analyzer.cli:run"

[tool.setuptools.packages.find]
where = ["src"]
```

### 每一段负责什么

- `[build-system]`：声明构建前端需要调用哪个构建后端，以及后端自身的最低依赖。
- `[project]`：声明发行名、版本、描述、Python 版本和运行时依赖。
- `[project.optional-dependencies]`：声明可选依赖组；`dev` 供开发和测试使用。
- `[project.scripts]`：安装一个名为 `log-analyzer` 的终端命令。
- `[tool.setuptools.packages.find]`：告诉 setuptools 从 `src/` 下发现导入包。

`pytest` 在本课只是为下一课准备的开发依赖，`mypy` 延续第二周已经建立的静态检查。二者都不应放进 `dependencies`，因为日志分析器运行时不需要测试框架或类型检查器。

### 直接依赖与传递依赖

如果将来代码直接执行：

```python
import requests
```

那么 `requests` 是项目的直接依赖，应由项目声明。`requests` 自己依赖的包是传递依赖，通常由安装工具解析，不应因为它们出现在 `pip freeze` 里就全部手工写成直接依赖。

本课使用版本范围表达兼容意图：

```toml
"pytest>=9,<10"
```

这与完全锁定环境不是同一个问题：

- 项目元数据描述“允许安装哪些兼容版本”。
- 锁文件描述“一次可复现环境实际解析到了哪些精确版本”。

标准 `venv` 和 `pip` 本身不为项目定义通用锁文件。本阶段先掌握依赖声明与环境隔离；进入机器学习项目时再根据工具链选择锁定方案。

## 7. 重构前先确认安全网

当前基线是 21 个测试通过，并且 mypy 检查无错误：

```powershell
cd projects/log-analyzer
python -m unittest discover -s tests -v
```

预期结尾：

```text
Ran 21 tests

OK
```

再运行静态检查：

```powershell
python -m mypy log_analyzer.py tests/test_log_analyzer.py
```

如果基线失败，先不要移动文件。项目结构重构应改变代码位置，不应掩盖原有行为错误。

本课的 RED 与之前略有不同：它不是先写一个失败的业务断言，而是先定义新的运行方式，再观察它在包尚未建立时失败：

```powershell
python -m log_analyzer sample.log ERROR
```

在包尚不存在或尚未安装时，预期失败并提示找不到 `log_analyzer` 或无法执行包。这就是本轮工程化目标的 RED。

## 8. 第一轮迁移：建立核心包

创建目录和空文件：

```text
src/
└── log_analyzer/
    ├── __init__.py
    └── core.py
```

把原 `log_analyzer.py` 中以下内容移动到 `core.py`：

- `LogEvent`
- `LogSource`
- `FileLogSource`
- `parse_log_line()`
- `count_log_levels()`
- `filter_logs_by_level()`
- `read_log_lines()`
- `open_log_lines()`
- `parse_log_lines()`
- `filter_events_by_level()`
- `print_matching_events()`

不要把 `sys`、`main()` 或 `if __name__ == "__main__"` 移进核心模块。`core.py` 不负责终端交互。

### 用 `__init__.py` 保持公开接口

现有测试从顶层名称导入：

```python
from log_analyzer import LogEvent, parse_log_line
```

在 `src/log_analyzer/__init__.py` 显式重新导出核心名称：

```python
from .core import (
    FileLogSource,
    LogEvent,
    LogSource,
    count_log_levels,
    filter_events_by_level,
    filter_logs_by_level,
    open_log_lines,
    parse_log_line,
    parse_log_lines,
    print_matching_events,
    read_log_lines,
)

__all__ = [
    "FileLogSource",
    "LogEvent",
    "LogSource",
    "count_log_levels",
    "filter_events_by_level",
    "filter_logs_by_level",
    "open_log_lines",
    "parse_log_line",
    "parse_log_lines",
    "print_matching_events",
    "read_log_lines",
]
```

这样调用者不必知道 `LogEvent` 当前位于 `core.py`。以后内部再次拆分模块时，只要顶层公开接口不变，调用者就不需要一起修改。

`__all__` 主要表达模块作者认定的公开名称，也影响 `from log_analyzer import *`。它不会把未列出的名称变成真正的 private；Python 的 API 边界更多依赖命名约定、文档和类型工具。

## 9. 第二轮迁移：分离 CLI

创建 `src/log_analyzer/cli.py`，把 `main()` 移入其中。包内导入核心函数：

```python
import sys

from .core import (
    FileLogSource,
    print_matching_events,
)


def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        print(
            "usage: log-analyzer <log-file> <level>",
            file=sys.stderr,
        )
        return 2

    file_path, level = arguments
    source = FileLogSource(file_path)
    print_matching_events(source, level)

    return 0


def run() -> None:
    raise SystemExit(main(sys.argv[1:]))
```

这里保留两个层次：

- `main(arguments)` 显式接收参数并返回退出码，负责组装真实文件源，便于测试。
- `run()` 才读取真实 `sys.argv` 并把返回值转换成进程退出状态。

`print_matching_events()` 仍然依赖 `LogSource` 协议，包化不应破坏第二周已经建立的结构化替换边界。

为了保持现有测试的 `from log_analyzer import main` 不变，在 `__init__.py` 再加入：

```python
from .cli import main
```

并把 `"main"` 加入 `__all__`。

### 是否修改 usage 文本

现有测试期待：

```text
usage: python log_analyzer.py <log-file> <level>
```

如果现在直接改成：

```text
usage: log-analyzer <log-file> <level>
```

测试会失败，这是可观察行为发生了变化。为确保本课是纯结构重构，第一轮先保留旧文本。确认所有行为绿色后，再单独用一个 RED → GREEN 循环更新 CLI 文案和测试。不要在文件迁移时顺手混入行为变化。

## 10. 增加 `python -m` 入口

创建 `src/log_analyzer/__main__.py`：

```python
from .cli import run


run()
```

当执行：

```powershell
python -m log_analyzer sample.log ERROR
```

Python 会找到 `log_analyzer` 包，并执行其中的 `__main__.py`。

`__main__.py` 应保持极薄。参数解析与协调逻辑放在可测试的 `cli.py`，不要复制一份 `main()`。

## 11. Editable install：让源码与环境连接起来

`src/` 布局故意不让项目根目录直接暴露导入包。先安装项目：

```powershell
python -m pip install --editable ".[dev]"
```

简写是：

```powershell
python -m pip install -e ".[dev]"
```

含义：

- `.`：安装当前目录中的项目。
- `-e` / `--editable`：建立适合开发的可编辑安装；修改 `src/` 中的 Python 源码后通常不需要反复重装。
- `[dev]`：同时安装 `pyproject.toml` 中的开发依赖组。

验证安装来源：

```powershell
python -c "import log_analyzer; print(log_analyzer.__file__)"
python -m pip show course-log-analyzer
```

第一条应指向当前项目的 `src/log_analyzer/__init__.py`。

### 为什么使用 `src/` 布局

如果导入包直接放在项目根目录，测试可能因为当前工作目录恰好在 `sys.path` 中而成功，即使项目元数据或安装配置已经损坏。`src/` 布局要求先正确安装项目，更接近用户实际使用发行包的方式，因此更容易提前暴露遗漏包、错误导入和构建配置问题。

## 12. GREEN：验证所有入口

### 12.1 验证导入

```powershell
python -c "from log_analyzer import LogEvent; print(LogEvent.__module__)"
```

预期输出类似：

```text
log_analyzer.core
```

### 12.2 运行现有测试

```powershell
python -m unittest discover -s tests -v
```

仍应有 21 个测试通过。测试数量没变是合理的，因为本课没有增加业务规则；测试保护的是重构前已经存在的契约。

再对新包和测试执行静态检查：

```powershell
python -m mypy src/log_analyzer tests/test_log_analyzer.py
```

预期 mypy 不报告错误。特别检查 `FileLogSource` 和测试中的内存数据源仍能结构化满足 `LogSource`。

### 12.3 通过模块运行

```powershell
python -m log_analyzer sample.log ERROR
$LASTEXITCODE
```

预期输出：

```text
2026-08-08T10:01:00|ERROR|database timeout
0
```

### 12.4 通过安装的命令运行

```powershell
log-analyzer sample.log INFO
$LASTEXITCODE
```

预期输出两条 INFO 日志，退出码为 `0`。

### 12.5 验证错误参数

```powershell
log-analyzer
$LASTEXITCODE
```

预期向标准错误输出 usage，退出码为 `2`。

## 13. 清理旧模块的正确时机

项目根目录中的旧 `log_analyzer.py` 会与新包同名，可能遮蔽已安装的 `src/log_analyzer` 包。

迁移时按这个顺序操作：

1. 先把实现移动到新包，并补齐 `__init__.py`、`cli.py` 和 `__main__.py`。
2. 确认 Git 已记录原文件，必要时可以恢复。
3. 删除项目根目录的旧 `log_analyzer.py`，避免同名冲突。
4. 执行 editable install。
5. 检查 `log_analyzer.__file__` 指向 `src/`。
6. 运行全部测试和两种 CLI 入口。

删除旧文件不是删除功能；代码已经移动到包中。但在确认新文件完整以前不要提前删除。

## 14. 常见错误与定位方法

### `No module named log_analyzer`

先确认：

```powershell
python -c "import sys; print(sys.executable)"
python -m pip show course-log-analyzer
```

常见原因是项目尚未安装，或者安装项目时使用的 `pip` 不属于当前 `python`。

### 导入了旧的 `log_analyzer.py`

检查：

```powershell
python -c "import log_analyzer; print(log_analyzer.__file__)"
```

如果仍指向项目根目录的旧文件，删除迁移完成后的旧模块，并确认 editable install 正确。

### 直接运行 `cli.py` 导致相对导入失败

错误方式：

```powershell
python src/log_analyzer/cli.py
```

正确方式：

```powershell
python -m log_analyzer
```

前者把 `cli.py` 当作没有父包的独立脚本；后者在 `log_analyzer` 包上下文中运行。

### `pip` 显示已安装，但 Python 仍然导入失败

比较：

```powershell
python -c "import sys; print(sys.executable)"
python -m pip --version
```

不要只运行裸 `pip --version`。机器上可能同时存在系统 Python、Python Launcher 选择的版本、IDE 环境和多个虚拟环境。

### 修改 `pyproject.toml` 后行为没有更新

editable install 主要让 Python 源码修改立即生效。改变依赖、console script 或构建配置后，应重新运行：

```powershell
python -m pip install -e ".[dev]"
```

### 把 `.venv` 提交进 Git

`.venv` 体积大、包含平台相关路径，并且可以由依赖声明重建。检查：

```powershell
git status --short
```

输出中不应出现 `.venv/`。

## 15. REFACTOR：检查包边界

全部测试通过后，再检查：

- `core.py` 不读取 `sys.argv`，也不负责打印 CLI 用法。
- `cli.py` 只协调输入、核心处理和输出，不重复日志解析规则。
- `LogSource` 协议、`FileLogSource` 与 `print_matching_events()` 的依赖方向保持不变。
- `__main__.py` 只委托给 `run()`。
- `__init__.py` 只暴露希望调用者使用的稳定名称。
- 测试从公开接口导入，而不是依赖无必要的内部文件位置。
- `pyproject.toml` 中运行时依赖与开发依赖分开。
- `.venv`、缓存和构建产物没有进入 Git。
- `log_analyzer.__file__` 指向当前项目的 `src/`。

不要为了显得“工程化”继续拆成 `models.py`、`parser.py`、`filters.py`、`readers.py` 等大量小文件。当前规模下，`core.py` 与 `cli.py` 已经表达了主要边界。后续只有在模块拥有独立职责和变化原因时再拆分。

## 16. 本课小测

先不要运行代码，尝试直接回答：

1. `core.py`、`log_analyzer/` 和 `course-log-analyzer` 分别属于模块、导入包还是发行包？
2. 为什么 `pip install` 的名称与 `import` 名称可能不同？
3. 激活虚拟环境实际改变了当前终端的什么？
4. 为什么推荐 `python -m pip`，而不是只写 `pip`？
5. `.venv` 为什么不应提交到 Git？
6. `__init__.py` 在本项目中承担哪两个作用？
7. `__main__.py` 与 `if __name__ == "__main__"` 都解决什么类型的问题？
8. 为什么不能直接运行包含相对导入的 `src/log_analyzer/cli.py`？
9. editable install 解决了本地开发中的什么问题？
10. 为什么 `src/` 布局更容易暴露错误的安装配置？
11. `pytest` 为什么属于开发依赖，而不是运行时依赖？
12. 依赖版本范围和锁文件分别表达什么？

## 17. 完成检查

- [ ] 能区分模块、导入包、发行包与虚拟环境。
- [ ] 已创建并验证项目专用 `.venv`。
- [ ] 能解释 `python -m pip` 如何避免解释器与安装器错配。
- [ ] 已添加 `pyproject.toml`，并区分运行时与开发依赖。
- [ ] 已把单文件迁移到 `src/log_analyzer/` 包。
- [ ] 已通过 `__init__.py` 保持公共导入接口。
- [ ] 已通过 `__main__.py` 支持 `python -m log_analyzer`。
- [ ] 已通过 `[project.scripts]` 支持 `log-analyzer` 命令。
- [ ] 已完成 editable install。
- [ ] `log_analyzer.__file__` 指向当前项目的 `src/`。
- [ ] 现有 21 个测试全部通过，mypy 检查无错误。
- [ ] 模块入口和 console script 的正常路径均返回 `0`。
- [ ] 错误参数路径返回 `2`。
- [ ] `.venv` 未出现在 Git 变更中。
- [ ] 已回答小测的 12 个问题。

## 18. 视频与阅读材料

建议按“先完成环境与包迁移 → 再用官方资料校正术语”的顺序学习。打包生态的工具很多，本课只使用标准库 `venv`、`pip`、`setuptools` 和 `pyproject.toml`，暂不比较 Poetry、PDM、Hatch、uv 或 Conda。

### 必读

- [Python 3.14 官方教程：模块](https://docs.python.org/zh-cn/3.14/tutorial/modules.html)：重点阅读 6、6.1、6.1.2 和 6.4，理解模块、搜索路径与包。
- [Python 官方打包指南：使用 pip 与 venv 安装包](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)：跟随 Windows 段落完成 `.venv` 创建、激活和验证。
- [Python 官方打包指南：安装包](https://packaging.python.org/en/latest/tutorials/installing-packages/)：重点阅读 `python -m pip`、版本约束、requirements file、wheel 与 source distribution 的区别。

### 按需查阅

- [Python 3.14 官方文档：`venv`](https://docs.python.org/zh-cn/3.14/library/venv.html)：查阅环境创建、激活脚本和 `EnvBuilder`；本课不要求自定义 `EnvBuilder`。
- [Python Packaging User Guide：编写 `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)：查阅 `[build-system]`、`[project]`、依赖和命令行入口的完整格式。
- [Python Packaging User Guide：打包 Python 项目](https://packaging.python.org/en/latest/tutorials/packaging-projects/)：观察标准 `src/` 项目结构；本课不上传 PyPI 或 TestPyPI。
- [pytest 官方入门](https://docs.pytest.org/en/stable/getting-started.html)：只预览安装方式和测试函数形式，下一课正式迁移。

官方打包指南在 2026-08-15 已重新核验。本课不需要把项目发布到 PyPI，也不需要选择第三方一体化依赖管理工具。

## 19. 提交给老师的内容

完成后发送：

1. `python -c "import sys; print(sys.executable)"` 与 `python -m pip --version` 的输出。
2. 重构后的目录树。
3. `pyproject.toml`、`__init__.py`、`__main__.py` 和 `cli.py`。
4. `python -c "import log_analyzer; print(log_analyzer.__file__)"` 的输出。
5. 21 个测试和 mypy 静态检查的完整通过结果。
6. `python -m log_analyzer sample.log ERROR` 与 `log-analyzer sample.log INFO` 的输出和退出码。
7. 小测第 1、3、4、8、10、11、12 题的答案。

我会从以下方面进行代码评审：术语理解、导入路径、包的公开接口、核心逻辑与 CLI 边界、`LogSource` 协议的保留、环境隔离、依赖分类、入口一致性、测试与静态检查回归和可重建性。
