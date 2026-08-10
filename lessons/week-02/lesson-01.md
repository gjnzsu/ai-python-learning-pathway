# 第 2 周 · 第 1 课：类、实例属性与数据类

预计用时：90–120 分钟

## 本课目标

完成本课后，你能够：

- 定义 Python 类，并使用 `__init__` 初始化实例属性。
- 解释 `self`、类对象、实例对象和实例方法之间的关系。
- 区分类属性与实例属性，避免共享可变类属性。
- 使用 `@dataclass` 定义以数据为主的对象。
- 说明普通类、数据类、Java POJO 与 Java `record` 的主要差异。
- 将日志事件从普通字典演进为类型更明确的 `LogEvent`。
- 在保持 CLI 外部行为不变的前提下完成一次跨函数重构。

## 1. 从字典进入领域对象

第一周使用字典表示日志事件：

```python
event = {
    "timestamp": "2026-08-08T10:01:00",
    "level": "ERROR",
    "message": "database timeout",
}
```

这种表示适合快速开始，但它有几个限制：

- 字段名只是字符串，`event["levle"]` 这样的拼写错误只能在运行时暴露。
- `dict[str, str]` 只说明键和值都是字符串，没有表达必须包含哪三个字段。
- 编辑器难以准确提示有哪些业务属性。
- 任意调用者都可以添加或删除键，事件的结构不够明确。

本课把它演进为：

```python
event = LogEvent(
    timestamp="2026-08-08T10:01:00",
    level="ERROR",
    message="database timeout",
)
```

读取字段时使用属性访问：

```python
event.level
```

这不是为了把所有函数都放进类里。解析、过滤和文件读取仍然可以是模块级函数；`LogEvent` 首先负责准确表达一条日志事件的数据结构。

## 2. Python 普通类的基本结构

Java 类通常先声明字段，再在构造器中赋值：

```java
public final class LogEvent {
    private final String timestamp;
    private final String level;
    private final String message;

    public LogEvent(String timestamp, String level, String message) {
        this.timestamp = timestamp;
        this.level = level;
        this.message = message;
    }
}
```

Python 普通类可以写成：

```python
class LogEvent:
    def __init__(
        self,
        timestamp: str,
        level: str,
        message: str,
    ) -> None:
        self.timestamp = timestamp
        self.level = level
        self.message = message
```

创建实例：

```python
event = LogEvent(
    "2026-08-08T10:01:00",
    "ERROR",
    "database timeout",
)
```

读取实例属性：

```python
print(event.level)
```

### `self` 是什么

`self` 表示当前实例，大致对应 Java 的 `this`，但需要显式写在实例方法的第一个参数位置：

```python
event.level
event.describe()
```

调用 `event.describe()` 时，Python 会把 `event` 自动作为第一个参数传给方法。概念上可以理解为：

```python
LogEvent.describe(event)
```

`self` 不是关键字，但它是所有 Python 开发者都遵循的命名约定，不应换成其他名称。

### `__init__` 不是 Java 构造器的完全等价物

`LogEvent(...)` 创建实例后，Python 调用 `__init__` 初始化它。对本阶段来说，可以把它理解为接近 Java 构造器；更准确地说，实例创建主要由 `__new__` 完成，`__init__` 负责初始化已有实例。本课不需要重写 `__new__`。

### 属性默认不是 Java 式 `private`

Python 通常直接访问公开属性：

```python
event.level
```

不需要为每个字段机械地生成 getter 和 setter。Python 更依赖约定、类型标注和清晰的对象边界；需要校验或计算属性时，后续可以使用 `property`。

## 3. 实例属性与类属性

实例属性属于单个对象：

```python
class LogEvent:
    def __init__(self, level: str) -> None:
        self.level = level
```

不同实例有自己的值：

```python
info_event = LogEvent("INFO")
error_event = LogEvent("ERROR")
```

类属性由所有实例共享：

```python
class LogEvent:
    separator = "|"

    def __init__(self, level: str) -> None:
        self.level = level
```

可以通过类读取共享值：

```python
LogEvent.separator
```

### 避免共享可变类属性

下面的写法会让所有实例共享同一个列表：

```python
class LogEvent:
    tags: list[str] = []
```

一个实例执行 `event.tags.append("database")` 后，其他实例也能看到这个标签。这通常不是预期行为。

普通类应在 `__init__` 中为每个实例创建列表：

```python
class LogEvent:
    def __init__(self) -> None:
        self.tags: list[str] = []
```

本课的 `LogEvent` 只有字符串字段，不需要列表。这里先建立“类属性是共享状态”的警觉。

## 4. 为什么使用数据类

如果类的主要职责是保存数据，手写 `__init__`、对象显示和字段相等比较会产生重复样板代码。标准库的 `dataclasses` 可以根据字段标注生成这些行为：

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class LogEvent:
    timestamp: str
    level: str
    message: str
```

`@dataclass` 会根据带类型标注的字段生成常用方法，包括：

- `__init__`：接收三个字段并初始化实例。
- `__repr__`：生成便于调试的对象表示。
- `__eq__`：按字段值比较两个 `LogEvent`。

因此下面的断言成立：

```python
self.assertEqual(
    LogEvent("2026-08-08T10:01:00", "ERROR", "database timeout"),
    LogEvent("2026-08-08T10:01:00", "ERROR", "database timeout"),
)
```

普通类若没有自己实现 `__eq__`，两个字段值相同但独立创建的实例默认不会按字段判等。

### `frozen=True`

数据类默认可变。本项目中的一条日志事件在解析完成后不应再被随意改写，因此使用：

```python
@dataclass(frozen=True)
```

这会阻止重新给字段赋值：

```python
event.level = "INFO"  # 抛出 FrozenInstanceError
```

它与 Java `record` 的不可重新赋值语义比较接近，但不要把两者视为完全相同。`frozen=True` 也不是“深度不可变”：如果字段本身是列表，列表内容仍然可能被修改。

### 数据类字段必须有类型标注

数据类根据带标注的类变量识别字段：

```python
@dataclass(frozen=True)
class LogEvent:
    timestamp: str
    level: str
    message: str
```

这些标注主要表达设计意图，并供编辑器、类型检查器和 `dataclass` 处理；Python 默认不会因为传入整数就自动执行 Java 式运行时类型检查。

## 5. Java POJO、Java `record` 与 Python 数据类

| 关注点 | Java POJO | Java `record` | Python `@dataclass(frozen=True)` |
|---|---|---|---|
| 字段声明 | 显式字段 | 记录组件 | 带类型标注的字段 |
| 初始化代码 | 通常手写或生成 | 编译器生成 | 装饰器生成 |
| 值相等比较 | 需要实现或生成 | 自动生成 | 默认按字段生成 |
| 字符串表示 | 需要实现或生成 | 自动生成 | 默认生成 `repr` |
| 不可重新赋值 | 由 `final` 控制 | 组件为 `final` | 由 `frozen=True` 模拟 |
| 运行时类型检查 | JVM/编译器约束较强 | JVM/编译器约束较强 | 类型标注默认不强制检查 |

可以把数据类理解为“减少数据对象样板代码的 Python 工具”，而不是 Java `record` 的一比一复制。

## 6. 第一轮 TDD：定义 `LogEvent`

本课继续使用现有 `unittest`，不引入新测试框架。

进入项目目录并确认基线：

```powershell
cd projects/log-analyzer
python -m unittest discover -s tests -v
```

开始本课前应有 12 个测试通过。如果数量不同或有失败，先不要继续重构，保存并检查当前输出。

### RED：先测试数据对象

在 `tests/test_log_analyzer.py` 的导入列表中加入 `LogEvent`，然后新增：

```python
class LogEventTest(unittest.TestCase):
    def test_compares_events_by_field_values(self) -> None:
        first_event = LogEvent(
            timestamp="2026-08-08T10:01:00",
            level="ERROR",
            message="database timeout",
        )
        second_event = LogEvent(
            timestamp="2026-08-08T10:01:00",
            level="ERROR",
            message="database timeout",
        )

        self.assertEqual(first_event, second_event)
```

运行全部测试。因为 `LogEvent` 尚不存在，预期看到导入失败。这是本轮 RED。

### GREEN：实现最小数据类

在 `log_analyzer.py` 顶部加入导入和类定义：

```python
from dataclasses import dataclass
import sys


@dataclass(frozen=True)
class LogEvent:
    timestamp: str
    level: str
    message: str
```

再次运行测试。预期原有 12 个测试和新增测试全部通过。

### 可选边界测试：事件不可重新赋值

先增加导入：

```python
from dataclasses import FrozenInstanceError
```

再增加测试：

```python
def test_cannot_reassign_event_fields(self) -> None:
    event = LogEvent(
        timestamp="2026-08-08T10:01:00",
        level="ERROR",
        message="database timeout",
    )

    with self.assertRaises(FrozenInstanceError):
        event.level = "INFO"
```

静态类型检查器可能同时提示这次赋值不合法；测试验证的是运行时行为。

## 7. 第二轮 TDD：让解析函数返回 `LogEvent`

当前接口是：

```python
def parse_log_line(line: str) -> dict[str, str]:
    ...
```

目标接口是：

```python
def parse_log_line(line: str) -> LogEvent:
    ...
```

日志文本的输入格式和异常规则都不改变：

```text
2026-08-08T10:01:00|ERROR|database timeout
```

仍然必须恰好包含三个字段；字段数量不正确时仍然抛出：

```text
ValueError: expected exactly 3 fields
```

### RED：修改解析结果的期望

把 `test_parses_a_valid_log_line` 中的字典期望改成：

```python
self.assertEqual(
    event,
    LogEvent(
        timestamp="2026-08-01T10:15:00",
        level="ERROR",
        message="database timeout",
    ),
)
```

运行这个测试：

```powershell
python -m unittest tests.test_log_analyzer.ParseLogLineTest -v
```

现有函数仍返回字典，因此测试失败。这是本轮 RED。

### GREEN：修改返回类型和构造逻辑

保留原有字段数量校验，只修改返回对象：

```python
def parse_log_line(line: str) -> LogEvent:
    """Parse one log line into a structured event."""

    log_parts = line.split("|")

    if len(log_parts) != 3:
        raise ValueError("expected exactly 3 fields")

    timestamp, level, message = log_parts

    return LogEvent(
        timestamp=timestamp,
        level=level,
        message=message,
    )
```

再次只运行解析测试，确认正常解析与非法字段两个测试都通过。

## 8. 第三轮 TDD：迁移依赖解析结果的函数

现在运行全部测试：

```powershell
python -m unittest discover -s tests -v
```

你应该看到部分原有测试失败。这不是随机回归，而是返回类型改变后，调用者仍然使用字典访问方式：

```python
event["level"]
```

`LogEvent` 不支持字典下标；应改为：

```python
event.level
```

按下面的顺序迁移，每完成一步都运行相应测试。

### 8.1 迁移日志级别统计

把：

```python
level = parse_log_line(line)["level"]
```

改为：

```python
level = parse_log_line(line).level
```

运行：

```powershell
python -m unittest tests.test_log_analyzer.CountLogLevelsTest -v
```

统计结果仍然是 `dict[str, int]`，因此测试期望不需要改变。

### 8.2 迁移日志过滤

修改函数签名：

```python
def filter_logs_by_level(
    line_array: list[str],
    level: str,
) -> list[LogEvent]:
    ...
```

把条件判断改为属性访问：

```python
if event.level == level:
    result_list.append(event)
```

结果列表的局部类型也应改为：

```python
result_list: list[LogEvent] = []
```

过滤测试的期望值从事件字典改成 `LogEvent(...)`，然后运行：

```powershell
python -m unittest tests.test_log_analyzer.FilterLogsByLevelTest -v
```

空目标级别的 `ValueError` 行为必须保持不变。

### 8.3 迁移 CLI 输出

CLI 对用户输出的文本格式不能因为内部对象变化而改变。把：

```python
f'{event["timestamp"]}|{event["level"]}|{event["message"]}'
```

改为：

```python
f"{event.timestamp}|{event.level}|{event.message}"
```

运行：

```powershell
python -m unittest tests.test_log_analyzer.MainTest -v
```

原有 CLI 测试不需要修改。它负责证明外部行为仍然是：

```text
2026-08-08T10:01:00|ERROR|database timeout
```

## 9. REFACTOR：检查对象边界，而不是把函数都变成方法

所有测试恢复为绿色后，检查：

- `LogEvent` 是否只表达一条日志的数据，没有文件读取或终端输出职责？
- 所有事件字段访问是否都使用 `.timestamp`、`.level` 和 `.message`？
- `count_log_levels()` 是否仍然返回计数字典，而不是为了统一而返回新对象？
- `read_log_lines()` 是否仍然只负责文件读取？
- `main()` 的标准输出、标准错误和退出码是否保持不变？
- 是否保留了非法日志和空目标级别的原有异常行为？

不要为了“面向对象”把所有模块级函数塞入 `LogEvent`。当函数的职责是协调文件、事件集合或 CLI 时，保留为模块级函数通常更清楚。

## 10. 手动验证完整 CLI

运行全部测试：

```powershell
cd projects/log-analyzer
python -m unittest discover -s tests -v
```

如果完成必做测试，预期共有 13 个测试通过；如果也完成不可变性测试，预期共有 14 个测试通过。

手动运行：

```powershell
python log_analyzer.py sample.log ERROR
$LASTEXITCODE
```

预期输出和第一周完全相同：

```text
2026-08-08T10:01:00|ERROR|database timeout
0
```

这次重构改变了程序内部的数据模型，没有改变 CLI 的对外契约。

## 11. 小测

先不要运行代码，尝试直接回答：

1. Python 实例方法为什么要显式声明 `self`，调用时却不需要手动传入它？
2. `self.level` 与类属性 `LogEvent.separator` 的归属有什么不同？
3. 为什么不应把 `tags: list[str] = []` 直接作为共享类属性？
4. `@dataclass` 默认生成了哪些本课使用到的方法？
5. 普通类的两个不同实例字段值相同，为什么默认不一定相等？
6. `frozen=True` 能保证包含列表字段的数据类“深度不可变”吗？
7. 类型标注为 `str` 后，Python 默认会不会在运行时自动拒绝整数？
8. 将 `parse_log_line()` 改为返回 `LogEvent` 后，为什么 `count_log_levels()` 的返回类型仍应是 `dict[str, int]`？
9. 哪一个现有测试能证明本次内部重构没有改变 CLI 输出？
10. 为什么不应该为了使用类而把 `read_log_lines()` 强行变成 `LogEvent` 的实例方法？

## 12. 完成检查

- [ ] 能定义普通类并解释 `__init__` 与 `self`。
- [ ] 能区分类对象、实例对象、类属性和实例属性。
- [ ] 能解释共享可变类属性的风险。
- [ ] 已使用 `@dataclass(frozen=True)` 定义 `LogEvent`。
- [ ] 能解释数据类生成的 `__init__`、`__repr__` 和 `__eq__`。
- [ ] 已将 `parse_log_line()` 的返回类型改为 `LogEvent`。
- [ ] 已将统计、过滤和 CLI 迁移到属性访问。
- [ ] 原有异常行为和 CLI 输出保持不变。
- [ ] 已运行全部自动化测试并确认 13 个或 14 个测试通过。
- [ ] 已手动运行 CLI 并确认退出码为 `0`。
- [ ] 已回答小测的 10 个问题。

## 13. 视频与阅读材料

本课优先“讲义 → 动手重构 → 官方文档查漏”，不要求通读完整类章节。

### 推荐视频

1. [Microsoft Learn：Classes | More Python for Beginners（概念，11:55）](https://learn.microsoft.com/en-us/shows/more-python-for-beginners/classes--more-python-for-beginners-6-of-20)：介绍类、初始化方法、实例方法和属性。重点观察 `self` 如何把数据绑定到具体实例；播放结束后不必继续该系列的继承课程。
2. [Microsoft Learn：Demo: Classes | More Python for Beginners（实操，7:16）](https://learn.microsoft.com/en-us/shows/more-python-for-beginners/demo-classes--more-python-for-beginners-7-of-20)：演示创建类并添加方法和属性。看完后再完成本课 `LogEvent` 的第一轮 TDD。

两段视频均为英文，总时长约 19 分钟。推荐先看概念篇，再看实操篇；不需要继续观看该系列后面的继承和多重继承课程。

### 数据类选看

- [PyCon US 2018：Dataclasses—The code generator to end all code generators](https://pyvideo.org/pycon-us-2018/dataclasses-the-code-generator-to-end-all-code-generators.html)：Python 核心开发者 Raymond Hettinger 讲解数据类要解决的样板代码问题，以及从元组、字典、普通类到数据类的演进。内容较长，本课只需看懂“为什么需要数据类”和生成 `__init__`、`__repr__`、`__eq__` 的部分，其余设计细节留作课后选看。

推荐学习顺序：阅读第 1–4 节 → 观看两段 Microsoft Learn 视频 → 完成第 6–10 节项目重构 → 按需查看官方文档。PyCon 演讲不影响本课验收。

### 必读

- [Python 3.12 官方教程：初探类](https://docs.python.org/zh-cn/3.12/tutorial/classes.html#first-look-at-classes)：重点阅读类定义语法、类对象、实例对象和方法对象。
- [Python 3.12 官方教程：类和实例变量](https://docs.python.org/zh-cn/3.12/tutorial/classes.html#class-and-instance-variables)：重点理解实例独有数据与共享类属性，以及共享列表示例。
- [Python 3.12 官方文档：`dataclasses` 数据类](https://docs.python.org/zh-cn/3.12/library/dataclasses.html)：先阅读开头示例和 `@dataclass` 参数说明，重点关注 `init`、`repr`、`eq` 和 `frozen`。

### 按需查阅

- [Python 3.12 官方教程：名称和对象](https://docs.python.org/zh-cn/3.12/tutorial/classes.html#a-word-about-names-and-objects)：理解多个名称绑定到同一可变对象时的影响。
- [Python 3.12 官方教程：补充说明](https://docs.python.org/zh-cn/3.12/tutorial/classes.html#random-remarks)：查看 `self` 约定和 Python 属性访问方式。

本课暂时不学习继承、多重继承、描述器、元类、`slots`、协议、迭代器和生成器。它们会在有项目需求时逐步引入。

## 14. 提交给老师的内容

完成后发送：

1. 全部测试的运行结果和测试总数。
2. `LogEvent` 与 `parse_log_line()` 的实现。
3. CLI 手动运行输出和 `$LASTEXITCODE`。
4. 小测第 1、3、6、8、10 题的答案。

我会从以下方面进行代码评审：数据类定义、类型标注、对象职责、依赖函数迁移、测试完整性和外部行为兼容性。
