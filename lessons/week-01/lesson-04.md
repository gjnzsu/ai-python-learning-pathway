# 第 1 周 · 第 4 课：文件读取与命令行入口

预计用时：90–120 分钟

## 本课目标

完成本课后，你能够：

- 使用 `with open(...)` 安全地读取文本文件。
- 解释文件模式、字符编码和换行符处理。
- 使用 `pathlib.Path` 和临时目录准备文件测试数据。
- 理解 `FileNotFoundError` 的异常传播。
- 区分模块导入和脚本直接执行。
- 使用 `sys.argv`、标准输出、标准错误和退出码构建简单 CLI。
- 完成文件读取与命令行入口的 RED → GREEN → REFACTOR 循环。

## 1. 从内存数据走向真实文件

前三课中的函数都接收内存里的字符串列表：

```python
lines = [
    "2026-08-08T10:00:00|INFO|server started",
    "2026-08-08T10:01:00|ERROR|database timeout",
]

events = filter_logs_by_level(lines, "ERROR")
```

真实的日志分析器通常接收文件路径。第四课要建立下面的数据流：

```text
命令行参数
    ↓
读取日志文件
    ↓
得到 list[str]
    ↓
复用 filter_logs_by_level()
    ↓
向终端输出匹配日志
```

我们不会把所有逻辑都塞进一个函数。文件读取、日志过滤和命令行协调各自只负责一件事：

```python
read_log_lines(file_path)       # 文件 → 字符串列表
filter_logs_by_level(lines, level)  # 字符串列表 → 事件列表
main(arguments)                 # 连接输入、处理和输出
```

这与 Java 项目中分离 I/O、业务逻辑和入口层的思路相同。

## 2. Python 如何安全地读取文件

Java 常使用 try-with-resources：

```java
try (BufferedReader reader = Files.newBufferedReader(path, UTF_8)) {
    // 使用 reader
}
```

Python 使用上下文管理器：

```python
with open(file_path, "r", encoding="utf-8") as log_file:
    content = log_file.read()
```

离开 `with` 代码块时，Python 会关闭文件。即使读取过程中发生异常，清理动作仍会执行。

参数含义：

- `file_path`：要打开的文件路径。
- `"r"`：只读文本模式。
- `encoding="utf-8"`：按 UTF-8 解码文件内容。
- `log_file`：本次打开的文件对象。

应当显式指定字符编码。否则 Python 可能使用操作系统默认编码，使同一程序在不同机器上表现不同。

### 逐行遍历文件

文件对象是可迭代对象，可以直接使用 `for`：

```python
with open(file_path, "r", encoding="utf-8") as log_file:
    for line in log_file:
        print(line)
```

读取到的每一行通常保留行尾换行符。Windows 文本文件常使用 `\r\n`，Linux 和 macOS 通常使用 `\n`。

只删除换行符可以写成：

```python
line.rstrip("\r\n")
```

不要在这里直接使用 `strip()`。它还会删除行首和行尾的空格，可能意外改变日志消息。

## 3. 第一轮 TDD：读取多行日志

目标函数：

```python
def read_log_lines(file_path: str) -> list[str]:
    ...
```

### RED：创建临时日志文件

在 `tests/test_log_analyzer.py` 中增加导入：

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from log_analyzer import (
    count_log_levels,
    filter_logs_by_level,
    parse_log_line,
    read_log_lines,
)
```

然后加入测试：

```python
class ReadLogLinesTest(unittest.TestCase):
    def test_reads_multiple_lines_from_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "app.log"
            file_path.write_text(
                "2026-08-08T10:00:00|INFO|server started\n"
                "2026-08-08T10:01:00|ERROR|database timeout\n",
                encoding="utf-8",
            )

            lines = read_log_lines(str(file_path))

        self.assertEqual(
            lines,
            [
                "2026-08-08T10:00:00|INFO|server started",
                "2026-08-08T10:01:00|ERROR|database timeout",
            ],
        )
```

这里没有依赖仓库中的固定测试文件：

- `TemporaryDirectory()` 创建测试专用目录。
- `Path(temp_dir) / "app.log"` 在该目录中构造文件路径。
- `write_text()` 准备真实的 UTF-8 文件。
- 离开 `with` 后，临时目录及文件会自动清理。

注意：`Path(temp_dir)` 只是目录，不能直接对它调用 `write_text()`；必须再拼接文件名。编码名称必须写成 `utf-8`，不是 `uft-8`。

运行测试：

```powershell
cd projects/log-analyzer
python -m unittest discover -s tests -v
```

如果函数尚不存在，你会看到 `ImportError: cannot import name 'read_log_lines'`。测试模块尚未成功导入，因此测试方法还没有真正开始执行；这仍然是有效的 RED。

### GREEN：只实现当前行为

在 `log_analyzer.py` 中加入：

```python
def read_log_lines(file_path: str) -> list[str]:
    lines: list[str] = []

    with open(file_path, "r", encoding="utf-8") as log_file:
        for line in log_file:
            lines.append(line.rstrip("\r\n"))

    return lines
```

再次运行全部测试。目标是原有 7 个测试和新增测试全部通过。

### REFACTOR：检查职责和命名

当前实现中：

- `read_log_lines()` 只负责文件读取。
- 它不负责解析日志格式。
- 它不负责过滤日志级别。
- 它不负责输出或捕获不存在的文件。

函数很短，变量含义清晰，不需要为了“完成重构”而强行修改。

## 4. 第二轮 TDD：空文件

文件读取还需要明确空文件的行为。期望空文件返回空列表，而不是 `None`。

### RED

在 `ReadLogLinesTest` 中增加：

```python
def test_returns_empty_list_for_empty_file(self) -> None:
    with TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / "empty.log"
        file_path.write_text("", encoding="utf-8")

        lines = read_log_lines(str(file_path))

    self.assertEqual(lines, [])
```

运行测试并观察结果。

这个测试可能直接通过，因为第一轮的循环在空文件中执行零次，初始空列表会被返回。测试直接通过不代表它没有价值：它明确记录了已有实现的边界行为。不过它不是一个新的 RED → GREEN 循环，因为没有观察到失败。

## 5. 文件不存在时会发生什么

如果路径不存在：

```python
read_log_lines("missing.log")
```

`open()` 会抛出 `FileNotFoundError`。当前版本不在 `read_log_lines()` 内捕获它，让异常自然传播给调用者。

这是一种 fail-fast 设计：底层函数不知道应该重试、忽略、打印提示还是终止进程，因此不擅自决定。

不要这样吞掉异常：

```python
try:
    ...
except FileNotFoundError:
    return []
```

“文件不存在”和“文件存在但没有日志”是两个不同状态。都返回空列表会丢失重要信息。

可选测试：

```python
def test_raises_error_when_file_does_not_exist(self) -> None:
    with TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / "missing.log"

        with self.assertRaises(FileNotFoundError):
            read_log_lines(str(file_path))
```

## 6. 模块导入与脚本执行

Python 文件既可以被导入，也可以直接执行。

导入模块：

```python
from log_analyzer import read_log_lines
```

直接执行：

```powershell
python log_analyzer.py
```

Python 执行文件时会设置特殊变量 `__name__`：

- 直接运行文件：`__name__ == "__main__"`
- 文件被其他模块导入：`__name__` 是模块名，例如 `"log_analyzer"`

因此命令行入口通常写成：

```python
if __name__ == "__main__":
    ...
```

这样测试导入 `log_analyzer` 时不会自动执行命令行代码。

## 7. 命令行参数、输出与退出码

本课 CLI 的使用方式：

```powershell
python log_analyzer.py <日志文件> <日志级别>
```

示例：

```powershell
python log_analyzer.py sample.log ERROR
```

Python 在 `sys.argv` 中保存命令行参数：

```python
import sys

print(sys.argv)
```

执行：

```powershell
python log_analyzer.py sample.log ERROR
```

大致得到：

```python
["log_analyzer.py", "sample.log", "ERROR"]
```

第一个元素是脚本名称。传给业务入口时通常使用：

```python
sys.argv[1:]
```

本课使用两个输出通道：

- 标准输出 `stdout`：正常结果，使用 `print(...)`。
- 标准错误 `stderr`：用法或错误提示，使用 `print(..., file=sys.stderr)`。

退出码约定：

- `0`：成功。
- 非 `0`：失败。
- `2`：本课用来表示命令行参数用法错误。

## 8. 第三轮 TDD：正确的命令行参数

为了让入口容易测试，不让 `main()` 在内部直接读取全局 `sys.argv`。设计为：

```python
def main(arguments: list[str]) -> int:
    ...
```

### RED

在测试文件中增加：

```python
from contextlib import redirect_stdout
from io import StringIO
```

并在 `log_analyzer` 的导入列表中加入 `main`。然后增加测试：

```python
class MainTest(unittest.TestCase):
    def test_prints_logs_matching_requested_level(self) -> None:
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "app.log"
            file_path.write_text(
                "2026-08-08T10:00:00|INFO|server started\n"
                "2026-08-08T10:01:00|ERROR|database timeout\n",
                encoding="utf-8",
            )
            output = StringIO()

            with redirect_stdout(output):
                exit_code = main([str(file_path), "ERROR"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            output.getvalue(),
            "2026-08-08T10:01:00|ERROR|database timeout\n",
        )
```

`StringIO` 是内存中的文本流。`redirect_stdout(output)` 临时把 `print()` 的标准输出重定向到这个流，使测试能够检查输出内容。

运行测试，确认它因为 `main` 尚不存在而失败。

### GREEN

在 `log_analyzer.py` 顶部加入：

```python
import sys
```

然后实现当前测试所需的最少行为：

```python
def main(arguments: list[str]) -> int:
    file_path, level = arguments
    lines = read_log_lines(file_path)
    events = filter_logs_by_level(lines, level)

    for event in events:
        print(
            f'{event["timestamp"]}|{event["level"]}|{event["message"]}'
        )

    return 0
```

再次运行全部测试，确认进入 GREEN。

### REFACTOR

`main()` 当前只做三件协调工作：读取、过滤、输出。实际解析和过滤规则仍由原有函数负责，没有重复业务逻辑。

## 9. 第四轮 TDD：错误的参数数量

当前实现使用序列解包：

```python
file_path, level = arguments
```

参数数量不是两个时会抛出 `ValueError`，但 CLI 用户更需要清晰的用法提示和退出码。

### RED

在测试文件中增加：

```python
from contextlib import redirect_stderr, redirect_stdout
```

然后在 `MainTest` 中增加：

```python
def test_returns_usage_error_when_arguments_are_missing(self) -> None:
    error_output = StringIO()

    with redirect_stderr(error_output):
        exit_code = main([])

    self.assertEqual(exit_code, 2)
    self.assertEqual(
        error_output.getvalue(),
        "usage: python log_analyzer.py <log-file> <level>\n",
    )
```

运行测试。预期现有实现因序列解包失败而产生 ERROR，而不是返回 `2`。这说明目标行为尚未实现。

### GREEN

在 `main()` 最前面加入参数校验：

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
    events = filter_logs_by_level(lines, level)

    for event in events:
        print(
            f'{event["timestamp"]}|{event["level"]}|{event["message"]}'
        )

    return 0
```

重新运行全部测试，确认新旧测试全部通过。

## 10. 添加真正的脚本入口

在 `log_analyzer.py` 最后加入：

```python
if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`main()` 返回整数；`SystemExit` 把这个整数转换成进程退出码。

不要在导入时直接调用 `main()`：

```python
# 错误示例：测试导入模块时也会执行
main(sys.argv[1:])
```

## 11. 手动运行完整 CLI

在 `projects/log-analyzer` 中创建 `sample.log`：

```text
2026-08-08T10:00:00|INFO|server started
2026-08-08T10:01:00|ERROR|database timeout
2026-08-08T10:02:00|INFO|request completed
```

运行：

```powershell
python log_analyzer.py sample.log ERROR
```

预期输出：

```text
2026-08-08T10:01:00|ERROR|database timeout
```

检查成功退出码：

```powershell
$LASTEXITCODE
```

预期为：

```text
0
```

再运行错误参数：

```powershell
python log_analyzer.py
$LASTEXITCODE
```

预期看到用法提示，退出码为 `2`。

## 12. 小测

先不要运行代码，尝试直接回答：

1. `with open(...)` 解决了什么资源管理问题？
2. 为什么读取文本文件时应该显式指定 `encoding="utf-8"`？
3. `rstrip("\r\n")` 和 `strip()` 的行为有什么差别？
4. `Path(temp_dir)` 与 `Path(temp_dir) / "app.log"` 分别表示什么？
5. 文件不存在和空文件为什么不应该都返回 `[]`？
6. 直接运行 `log_analyzer.py` 时，`__name__` 的值是什么？
7. 为什么调用 `main(sys.argv[1:])` 时要排除 `sys.argv[0]`？
8. 标准输出和标准错误分别适合输出什么？
9. 退出码 `0` 和非 `0` 通常分别表示什么？
10. 为什么让 `main()` 接收参数列表比在函数内部直接读取 `sys.argv` 更容易测试？

## 13. 完成检查

- [ ] 能解释 `with open(...)` 与 Java try-with-resources 的对应关系。
- [ ] 能解释文件模式和 UTF-8 编码的作用。
- [ ] 已实现 `read_log_lines()` 并通过多行与空文件测试。
- [ ] 理解 `FileNotFoundError` 为什么暂时自然传播。
- [ ] 能解释 `__name__ == "__main__"` 的用途。
- [ ] 已实现 `main(arguments)`。
- [ ] 正确参数会输出匹配日志并返回 `0`。
- [ ] 错误参数会向标准错误输出用法并返回 `2`。
- [ ] 已手动运行 CLI 并检查 `$LASTEXITCODE`。
- [ ] 已运行全部自动化测试并确认通过。
- [ ] 已回答小测的 10 个问题。

## 14. 视频与阅读材料

建议按“短视频 → 动手实践 → 官方文档查漏”的顺序学习。

### 推荐视频

1. [Microsoft Learn：Working with files（概念）](https://learn.microsoft.com/en-us/shows/more-python-for-beginners/working-with-files--more-python-for-beginners-14-of-20)：介绍 Python 文件读写的基本思路。
2. [Microsoft Learn：Demo—Working with files（实操）](https://learn.microsoft.com/en-us/shows/more-python-for-beginners/demo-working-with-files--more-python-for-beginners-15-of-20)：通过代码演示文件的读取与写入。

视频为英文。建议先看概念篇，再看实操篇，然后完成 `read_log_lines()`。

### 中文官方文档

- [Python 3.12 官方教程：读写文件](https://docs.python.org/zh-cn/3.12/tutorial/inputoutput.html#reading-and-writing-files)：本课最重要的文档，重点阅读 `open()`、`with`、编码和逐行遍历。
- [Python 3.12 官方教程：将模块作为脚本执行](https://docs.python.org/zh-cn/3.12/tutorial/modules.html#executing-modules-as-scripts)：解释 `if __name__ == "__main__"`。
- [Python 3.12 官方教程：命令行参数](https://docs.python.org/zh-cn/3.12/tutorial/interpreter.html#argument-passing)：解释脚本名称和其他参数如何进入 `sys.argv`。
- [Python 3.12 官方文档：`pathlib`](https://docs.python.org/zh-cn/3.12/library/pathlib.html)：当前重点查看路径拼接、`write_text()` 和文件读取方法。
- [Python 3.12 官方教程：标准库与命令行参数](https://docs.python.org/zh-cn/3.12/tutorial/stdlib.html#command-line-arguments)：包含 `sys.argv` 示例，并简单介绍后续会学习的 `argparse`。
- [Python 3.12 官方文档：`tempfile`](https://docs.python.org/zh-cn/3.12/library/tempfile.html)：按需查看 `TemporaryDirectory()` 的行为。

不需要提前通读所有文档。完成文件读取时看“读写文件”和 `pathlib`；开始 CLI 时再看模块执行与命令行参数。

## 15. 提交给老师的内容

完成第一轮文件读取后，发送：

1. 全部测试的运行结果。
2. `read_log_lines()` 的实现。
3. 小测第 1、3、5 题的答案。

完成整课后，再发送：

1. CLI 正常运行与错误参数运行的输出。
2. `$LASTEXITCODE` 的结果。
3. 小测第 6、7、8、10 题的答案。
