# 第 2 周 · 第 4 课：协议、类型标注与静态检查

预计用时：90–120 分钟

## 本课目标

完成本课后，你能够：

- 解释动态类型、鸭子类型、名义子类型与结构化子类型的区别。
- 使用 `typing.Protocol` 定义只包含调用者所需能力的最小接口。
- 理解一个类无需继承协议，也可以静态满足协议。
- 使用 `AbstractContextManager[Iterator[str]]` 表达日志数据源的资源边界。
- 使用文件数据源和内存数据源替换同一个处理函数的输入。
- 使用 mypy 在不运行程序的情况下发现不兼容的调用。
- 区分单元测试、静态类型检查和运行时检查各自能证明什么。
- 在保持 CLI 输出、退出码和资源清理行为不变的前提下重构日志分析器。

## 1. 从固定文件路径走向可替换的数据源

上一课的 `main()` 直接依赖文件路径和 `open_log_lines()`：

```python
file_path, level = arguments

with open_log_lines(file_path) as lines:
    events = parse_log_lines(lines)
    matching_events = filter_events_by_level(events, level)

    for event in matching_events:
        print(f"{event.timestamp}|{event.level}|{event.message}")
```

这段代码能够流式处理文件，也能确定关闭文件，但“取得日志行”和“处理日志行”仍绑定在一起。如果以后日志来自压缩文件、对象存储或网络流，处理管道不应该知道每种来源如何打开和关闭。

本课把数据流演进为：

```text
FileLogSource ─┐
               ├─ LogSource 协议 ─ print_matching_events() ─ 解析、过滤、输出
MemoryLogSource┘
```

处理函数只要求数据源具备一种能力：打开一个上下文，并在上下文有效期间提供字符串迭代器。

## 2. 四个容易混淆的类型概念

### 动态类型

Python 对象在运行时有类型，变量名可以在不同时刻绑定到不同类型的对象：

```python
value = "ERROR"
value = 500
```

类型标注不会改变这条运行时规则。

### 鸭子类型

运行时调用通常关心对象“能做什么”，而不是“继承自谁”：

```python
def close_resource(resource: object) -> None:
    resource.close()  # object 的标注过宽，静态检查器会拒绝这一行
```

“如果它能像鸭子一样叫，就把它当作鸭子使用”描述了运行时的能力导向思路，但上面的 `object` 没有把所需能力告诉类型检查器。

### 名义子类型

Java 接口和普通继承主要依赖显式声明：

```java
final class FileLogSource implements LogSource {
    // ...
}
```

类型兼容性由名字和继承关系建立，这叫名义子类型。

### 结构化子类型

结构化子类型关心对象是否拥有协议要求的成员，并且签名兼容。实现类不需要显式继承协议：

```python
class SupportsClose(Protocol):
    def close(self) -> None: ...


class Connection:
    def close(self) -> None:
        print("closed")
```

`Connection` 没有继承 `SupportsClose`，但它拥有签名兼容的 `close()`，因此静态类型检查器可以把它当作 `SupportsClose`。可以把 `Protocol` 理解为“可静态检查的鸭子类型”。

## 3. 类型标注不会自动执行

下面的函数标注了 `str`：

```python
def normalize_level(level: str) -> str:
    return level.upper()
```

Python 默认不会在调用前检查参数：

```python
normalize_level(500)
```

程序会真正进入函数，然后因为整数没有 `upper()` 而抛出 `AttributeError`。类型检查器则可以在运行前指出参数不兼容。

三种验证不要互相替代：

| 手段 | 主要回答的问题 | 是否运行代码 |
|---|---|---|
| 单元测试 | 给定样例的运行时行为是否正确 | 是 |
| 静态类型检查 | 标注之间的调用契约是否兼容 | 否 |
| 运行时校验 | 外部输入在当前执行中是否有效 | 是 |

类型检查不能证明业务结果正确；单元测试也不会自动遍历所有类型不兼容的调用。

## 4. 从调用者反推最小协议

处理管道需要做两件事：

1. 进入资源上下文。
2. 在上下文内遍历字符串。

因此协议只需要一个方法：

```python
from collections.abc import Iterator
from contextlib import AbstractContextManager
from typing import Protocol


class LogSource(Protocol):
    def open_lines(
        self,
    ) -> AbstractContextManager[Iterator[str]]:
        ...
```

从内向外阅读返回类型：

- `str`：每次取得一行文本。
- `Iterator[str]`：日志行按需产生并会被消费。
- `AbstractContextManager[...]`：迭代器只能在显式资源上下文中使用。

协议没有要求 `file_path`、`close()`、`read()` 或具体类名，因为处理函数不需要这些成员。接口越小，实现和测试替身越容易满足。

### 为什么这次使用 `AbstractContextManager`

上一课的 `@contextmanager` 函数使用生成器返回标注：

```python
@contextmanager
def open_log_lines(file_path: str) -> Iterator[Iterator[str]]:
    ...
```

这里标注的是被装饰前的生成器函数体。调用 `open_log_lines(...)` 得到的对象则是上下文管理器。协议描述调用结果，所以使用：

```python
AbstractContextManager[Iterator[str]]
```

两处标注观察的是不同层次，并不冲突。

## 5. `Protocol` 与 Java `interface` 对照

| 关注点 | Java `interface` | Python `Protocol` |
|---|---|---|
| 建立兼容关系 | 通常显式 `implements` | 成员结构和类型兼容即可 |
| 主要检查时机 | 编译期 | 外部静态检查工具运行时 |
| Python 运行时强制 | 不适用 | 默认不强制 |
| 可否包含实现 | 可以有默认方法 | 可以有方法实现，但本课不需要 |
| 常见用途 | 公开契约、依赖倒置 | 静态鸭子类型、窄接口、测试替身 |

不要把每个类都配一个同名协议。只有调用者需要接收多个实现，或你需要把依赖缩小为一组能力时，协议才有明显价值。

## 6. 开始前确认基线

进入项目目录：

```powershell
cd projects/log-analyzer
python -m unittest discover -s tests -v
```

开始本课前应看到：

```text
Ran 20 tests

OK
```

如果基线失败，先修复或记录已有问题，不要把它与本课重构混在一起。

## 7. 安装并首次运行 mypy

本课首次引入第三方静态类型检查器：

```powershell
python -m pip install mypy
python -m mypy --version
```

使用 `python -m` 能确保安装和运行使用当前 Python 解释器。虚拟环境、依赖锁定和项目配置会在第三周系统学习；本课先只掌握一次明确的静态检查。

在未修改代码前运行：

```powershell
python -m mypy log_analyzer.py tests
```

记录输出。若检查器报告现有标注问题，先阅读“文件:行号”和错误类别，不要通过批量添加 `# type: ignore` 让输出消失。

## 8. 第一轮 TDD：让处理管道接受内存数据源

先在 `tests/test_log_analyzer.py` 的导入列表中增加：

```python
from log_analyzer import print_matching_events
```

测试文件中加入一个不继承任何项目类的内存数据源：

```python
from collections.abc import Iterator
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
```

```python
@dataclass(frozen=True)
class MemoryLogSource:
    lines: tuple[str, ...]

    def open_lines(
        self,
    ) -> AbstractContextManager[Iterator[str]]:
        return nullcontext(iter(self.lines))
```

`nullcontext(...)` 不创建需要关闭的外部资源，但提供与真实文件源相同的 `with` 使用方式。它适合内存测试替身。

### RED

加入测试：

```python
class PrintMatchingEventsTest(unittest.TestCase):
    def test_prints_events_from_a_structural_log_source(self) -> None:
        source = MemoryLogSource(
            lines=(
                "2026-08-08T10:00:00|INFO|server started",
                "2026-08-08T10:01:00|ERROR|database timeout",
            )
        )
        output = StringIO()

        with redirect_stdout(output):
            print_matching_events(source, "ERROR")

        self.assertEqual(
            output.getvalue(),
            "2026-08-08T10:01:00|ERROR|database timeout\n",
        )
```

运行测试。预期因为 `print_matching_events` 尚不存在而导入失败，这是本轮 RED。

### GREEN：定义协议与处理函数

在 `log_analyzer.py` 增加导入：

```python
from contextlib import AbstractContextManager, contextmanager
from typing import Protocol
```

保留已有的 `contextmanager` 导入，只把同一模块的导入合并。然后定义协议：

```python
class LogSource(Protocol):
    def open_lines(
        self,
    ) -> AbstractContextManager[Iterator[str]]:
        ...
```

增加处理函数：

```python
def print_matching_events(source: LogSource, level: str) -> None:
    with source.open_lines() as lines:
        events = parse_log_lines(lines)
        matching_events = filter_events_by_level(events, level)

        for event in matching_events:
            print(f"{event.timestamp}|{event.level}|{event.message}")
```

再次运行全部测试。新的测试应该通过。

这个测试证明 `MemoryLogSource` 在运行时能被处理函数使用；稍后的 mypy 检查证明它的静态签名满足 `LogSource`。

## 9. 第二轮：实现真实文件数据源

在 `log_analyzer.py` 中加入：

```python
@dataclass(frozen=True)
class FileLogSource:
    file_path: str

    def open_lines(
        self,
    ) -> AbstractContextManager[Iterator[str]]:
        return open_log_lines(self.file_path)
```

`FileLogSource` 只保存文件路径，并把资源管理委托给上一课已经测试过的 `open_log_lines()`。它没有重复打开、去除换行或关闭文件的逻辑。

注意它没有写：

```python
class FileLogSource(LogSource):
```

显式继承协议是允许的，但本课刻意省略，以证明结构化子类型不依赖继承声明。

### 重构 `main()`

把原来的文件处理块替换为：

```python
file_path, level = arguments
source = FileLogSource(file_path)
print_matching_events(source, level)

return 0
```

完整 `main()` 应保持参数校验不变：

```python
def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        print(
            "usage: python log_analyzer.py <log-file> <level>",
            file=sys.stderr,
        )
        return 2

    file_path, level = arguments
    source = FileLogSource(file_path)
    print_matching_events(source, level)

    return 0
```

运行全部测试：

```powershell
python -m unittest discover -s tests -v
```

目标是 21 个测试通过。已有 `MainTest` 继续证明真实文件路径、CLI 输出和退出码没有改变；上一课的 `OpenLogLinesTest` 继续证明资源正常与异常退出时都会关闭。

## 10. 第三轮：让静态检查器验证可替换性

运行：

```powershell
python -m mypy log_analyzer.py tests
```

目标输出类似：

```text
Success: no issues found in 2 source files
```

具体文件计数可能随 mypy 版本和参数展开方式不同。关键是没有类型错误。

mypy 在这一轮验证了两条关系：

- `FileLogSource` 能传给接收 `LogSource` 的 `print_matching_events()`。
- 测试中的 `MemoryLogSource` 也能传入，即使它没有继承 `LogSource`。

### 故意制造一个类型错误

临时在测试文件中加入：

```python
class BrokenLogSource:
    def open_lines(self) -> list[str]:
        return []


broken_source: LogSource = BrokenLogSource()
```

同时从 `log_analyzer` 导入 `LogSource`，然后重新运行 mypy。你应该看到类似“不兼容赋值”的错误，并指出 `open_lines()` 的期望返回类型是上下文管理器，而实际是列表。

这里的问题不是“列表不能遍历”。列表可以遍历，但调用者会这样使用：

```python
with source.open_lines() as lines:
    ...
```

普通列表不支持这个资源协议。类型检查器在这条执行路径真正发生前就发现了边界不匹配。

观察错误后删除 `BrokenLogSource` 和 `broken_source`，再次运行 mypy，恢复无错误状态。

## 11. 通过赋值显式检查协议实现

调用函数通常已经足以触发检查。设计协议时，也可以临时写“静态断言”：

```python
file_source: LogSource = FileLogSource("sample.log")
memory_source: LogSource = MemoryLogSource(lines=())
```

这不是运行时断言，也不会调用任何方法；它只是让类型检查器明确验证右侧是否可赋给协议类型。生产代码若没有实际用途，不需要保留这些变量。

不要使用下面的转换来掩盖问题：

```python
from typing import cast

source = cast(LogSource, BrokenLogSource())
```

`cast()` 只告诉类型检查器“相信我”，不会改变对象，也不会补上上下文管理能力。

## 12. 为什么本课不使用 `@runtime_checkable`

普通协议不能直接用于：

```python
isinstance(source, LogSource)
```

可以用 `@runtime_checkable` 开启有限的运行时结构检查，但它主要检查成员是否存在，不会完整验证参数和返回类型签名。

例如，一个对象即使有名字相同但返回错误类型的 `open_lines()`，也可能通过这种浅层成员检查，却在真正进入 `with` 时失败。本课要验证的是静态调用契约，因此直接运行 mypy，不把 `isinstance()` 当作替代品。

## 13. 协议应该放在谁附近

本课把 `LogSource` 放在单文件模块中，重点是学习语义。更大的项目里，可以遵循一个实用原则：协议由使用它的边界拥有，而不是由某个具体实现拥有。

原因是调用者最清楚自己需要哪些能力：

```python
class LogSource(Protocol):
    def open_lines(...) -> ...:
        ...
```

如果由文件实现反向定义一个庞大的接口，容易把处理函数不需要的文件细节也暴露进去，例如 `seek()`、`file_name` 和 `encoding`。

这与依赖倒置的方向相似，但不需要为了套用架构模式建立额外包和抽象层。

## 14. `Any`：静态检查的逃生门与盲区

`Any` 会允许几乎所有操作，并向后传播不确定性：

```python
from typing import Any


def load_source() -> Any:
    return BrokenLogSource()


print_matching_events(load_source(), "ERROR")
```

这段调用可能绕过有价值的检查。`Any` 在对接缺少类型信息的第三方库时有用途，但不应为了“让 mypy 通过”而把精确标注改成 `Any`。

同样，不要无差别添加：

```python
# type: ignore
```

如果确实需要忽略，应先理解具体错误，并尽可能限定错误代码和作用行。本课不需要任何忽略指令。

## 15. 测试替身为什么适合协议

Java 测试中常见两种做法：实现接口的 fake，或使用 mocking 框架生成 mock。Python 的结构化协议允许测试替身只写实际需要的行为：

```python
@dataclass(frozen=True)
class MemoryLogSource:
    lines: tuple[str, ...]

    def open_lines(
        self,
    ) -> AbstractContextManager[Iterator[str]]:
        return nullcontext(iter(self.lines))
```

这个 fake：

- 不访问磁盘。
- 不需要 patch 全局函数。
- 保留 `with` 资源边界。
- 用真实日志行执行解析和过滤管道。
- 不依赖具体的 `FileLogSource`。

协议不是专门为了测试而存在，但窄协议自然会降低测试成本。

## 16. 常见错误与定位方法

### 把 `Protocol` 当成运行时校验器

```python
def handle(source: LogSource) -> None:
    ...
```

这个标注不会在函数入口自动拒绝错误对象。需要执行 mypy 才有静态检查；不可信外部输入仍需运行时解析与校验。

### 要求实现类必须继承协议

```python
class FileLogSource(LogSource):
    ...
```

这不是错误，但若认为只有继承后才兼容，就错过了本课的结构化子类型核心。先尝试不继承并运行 mypy。

### 协议包含调用者不需要的成员

```python
class LogSource(Protocol):
    file_path: str
    encoding: str
    def open_lines(...): ...
    def close(...): ...
```

这会让内存源被迫伪造文件属性。回到调用者代码，只保留它真正访问的成员。

### 返回 `Iterable[str]` 丢失资源边界

```python
class LogSource(Protocol):
    def lines(self) -> Iterable[str]: ...
```

这个类型没有表达何时关闭文件，也无法要求调用者在 `with` 内消费。上一课建立的资源生命周期不能因为抽象数据源而消失。

### 只运行测试，不运行 mypy

测试覆盖到的路径可以全部通过，未执行的不兼容调用仍然存在。最终检查必须同时包含测试和 mypy。

### 只运行 mypy，不运行测试

类型兼容不等于过滤结果正确，也不保证输出文本和退出码符合要求。静态检查不能替代运行时行为测试。

### 为了通过检查改成 `Any`

这通常只是关闭检查。优先修正协议、实现或调用者的真实不兼容。

## 17. REFACTOR：检查边界是否真的变清楚

最终代码应满足：

- `LogSource` 只描述 `open_lines()`。
- `FileLogSource` 只保存路径并委托已有资源管理函数。
- `print_matching_events()` 只依赖 `LogSource`，不知道具体来源。
- `main()` 仍然负责参数校验和依赖组装。
- `open_log_lines()` 仍然负责文件生命周期和换行处理。
- `parse_log_lines()` 与 `filter_events_by_level()` 不感知数据源类型。
- 没有为协议添加当前调用者不需要的成员。
- 没有 `Any`、`cast()` 或无说明的 `# type: ignore`。

运行格式检查：

```powershell
git diff --check
```

无输出表示没有检测到尾随空格等补丁格式问题。

## 18. 最终验证

先运行运行时测试：

```powershell
python -m unittest discover -s tests -v
```

再运行静态检查：

```powershell
python -m mypy log_analyzer.py tests
```

最后手动验证 CLI：

```powershell
python log_analyzer.py sample.log ERROR
$LASTEXITCODE
```

预期输出：

```text
2026-08-08T10:01:00|ERROR|database timeout
0
```

再验证参数错误：

```powershell
python log_analyzer.py
$LASTEXITCODE
```

预期用法提示写入标准错误，退出码为 `2`。

本课最终证据应同时包含：21 个单元测试通过、mypy 无类型错误、CLI 外部行为未变化。

## 19. 小测

先不要运行代码，尝试直接回答：

1. Python 是动态类型语言，为什么类型标注仍然有价值？
2. 鸭子类型与结构化子类型的共同点和区别是什么？
3. `FileLogSource` 为什么无需继承 `LogSource` 也能满足协议？
4. `LogSource` 为什么不应该要求 `file_path` 属性？
5. `AbstractContextManager[Iterator[str]]` 同时表达了哪两个维度？
6. 单元测试通过，为什么仍然需要运行 mypy？
7. mypy 无错误，为什么仍然不能删除单元测试？
8. `@runtime_checkable` 为什么不能替代静态签名检查？
9. 把错误类型改成 `Any` 会给后续检查带来什么影响？
10. `MemoryLogSource` 相比 patch 文件读取函数，有什么设计优势？

## 20. 完成检查

- [ ] 能区分动态类型、鸭子类型、名义子类型和结构化子类型。
- [ ] 已安装 mypy，并能使用 `python -m mypy` 运行检查。
- [ ] 已定义只包含 `open_lines()` 的 `LogSource`。
- [ ] 能从内向外解释 `AbstractContextManager[Iterator[str]]`。
- [ ] 已实现不显式继承协议的 `FileLogSource`。
- [ ] 已使用 `MemoryLogSource` 测试同一个处理管道。
- [ ] 已通过故意错误观察 mypy 如何报告协议不兼容。
- [ ] 已删除故意错误，恢复静态检查无错误。
- [ ] 已运行全部自动化测试并确认 21 个测试通过。
- [ ] 已手动验证 CLI 输出与退出码没有改变。
- [ ] 没有使用 `Any`、`cast()` 或 `# type: ignore` 掩盖问题。
- [ ] 已回答小测的 10 个问题。

## 21. 视频与阅读材料

建议按“概念短读 → 动手定义协议 → 观察 mypy 错误 → 官方规范查漏”的顺序学习。

### 必读

1. [Python 3.12 官方文档：`typing`](https://docs.python.org/3.12/library/typing.html)：先阅读开头关于类型标注不会由运行时强制执行的说明，再定位 `Protocol` 与 `runtime_checkable`。
2. [mypy：Getting started](https://mypy.readthedocs.io/en/stable/getting_started.html)：重点查看安装、运行、静态检查与严格模式。本课先运行基础检查，不要求立即启用全部严格选项。
3. [mypy：Protocols and structural subtyping](https://mypy.readthedocs.io/en/stable/protocols.html)：重点阅读简单自定义协议，以及实现类无需继承协议的示例。

### 按需查阅

- [Typing 官方规范：Protocols](https://typing.python.org/en/latest/spec/protocol.html)：查阅结构化可赋值、显式与隐式实现等精确定义。
- [Typing 官方规范：Type system concepts](https://typing.python.org/en/latest/spec/concepts.html)：对照名义类型和结构化类型的定义。
- [Python 3.12 官方文档：`contextlib`](https://docs.python.org/3.12/library/contextlib.html)：复习 `AbstractContextManager`、`contextmanager` 与 `nullcontext`。
- [PEP 544：Protocols: Structural subtyping](https://peps.python.org/pep-0544/)：协议最初的设计说明，适合想理解设计动机时阅读。

本课暂时不学习泛型协议、协变与逆变、回调协议、重载、`TypeVar`、自定义 mypy 插件、完整严格模式配置和 CI 集成。先掌握一个非泛型的最小业务协议，以及测试与静态检查的互补关系。

## 22. 提交给老师的内容

完成后发送：

1. 21 个测试的运行结果。
2. mypy 最终无错误的输出。
3. `LogSource`、`FileLogSource` 与 `print_matching_events()` 的实现。
4. 测试中的 `MemoryLogSource` 和对应测试。
5. 故意使用 `BrokenLogSource` 时 mypy 的关键错误信息。
6. CLI 手动运行输出和 `$LASTEXITCODE`。
7. 小测第 2、3、5、6、8、9 题的答案。

我会从以下方面进行代码评审：协议是否最小、结构化替换是否成立、资源边界是否保留、类型标注是否精确、静态错误是否被真正理解、测试是否验证运行时行为，以及 CLI 外部行为是否兼容。
