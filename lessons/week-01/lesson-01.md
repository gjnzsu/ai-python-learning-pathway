# 第 1 周 · 第 1 课：从 Java 切换到 Python

预计用时：90–120 分钟

## 本课目标

完成本课后，你能够：

- 解释 Python 脚本、模块和函数的基本执行方式。
- 使用字符串、列表和字典表达简单数据。
- 识别 Python 动态类型与类型标注的区别。
- 运行标准库测试，并完成一次 RED → GREEN 循环。
- 实现日志分析项目的第一个行为。

## 1. 先建立正确的心智模型

Java 通常先把源码编译为字节码，再由 JVM 执行。Python 源码同样会被编译为字节码，但这个过程通常由解释器自动完成；日常开发中，你直接运行模块或脚本：

```powershell
python app.py
python -m package.module
```

`python -m ...` 的含义是“按照模块导入规则定位并执行模块”。后续运行工具时，我们会经常使用这种形式，例如：

```powershell
python -m unittest
python -m pip
```

这可以确保命令使用的是当前 Python 解释器所对应的工具，减少 Windows 上多个 Python 环境之间的混淆。

## 2. 第一组 Java → Python 映射

### 变量与类型

Java：

```java
String level = "ERROR";
int statusCode = 500;
```

Python：

```python
level = "ERROR"
status_code = 500
```

Python 变量名绑定到对象，不要求在赋值语句中声明静态类型。类型标注可以表达设计意图，但默认不会在运行时替你做 Java 式的类型检查：

```python
level: str = "ERROR"
status_code: int = 500
```

### 方法与函数

Python 不要求函数属于某个类。纯数据转换通常直接写成模块级函数：

```python
def normalize_level(level: str) -> str:
    return level.strip().upper()
```

需要留意：

- 使用缩进定义代码块，没有 `{}`。
- 函数使用 `def` 声明。
- 参数和返回值标注位于名称之后。
- 默认使用 `snake_case`，而不是 Java 常用的 `camelCase`。

### 字典与列表

Python 的 `dict` 很像 Java 的 `Map`，但字面量更加简洁：

```python
event = {
    "timestamp": "2026-08-01T10:15:00",
    "level": "ERROR",
    "message": "database timeout",
}

levels = ["INFO", "WARN", "ERROR"]
```

读取字典时有两种常用方式：

```python
event["level"]       # 键不存在时抛出 KeyError
event.get("level")   # 键不存在时返回 None
```

不要把 `.get()` 当作永远更安全的选择。若字段按业务规则必须存在，让错误尽早暴露通常更好。

## 3. 项目需求：解析一行日志

第一版日志格式固定为：

```text
2026-08-01T10:15:00|ERROR|database timeout
```

实现 `parse_log_line(line: str) -> dict[str, str]`，返回：

```python
{
    "timestamp": "2026-08-01T10:15:00",
    "level": "ERROR",
    "message": "database timeout",
}
```

本轮只实现这个正常场景，不提前处理空行、非法级别或缺失字段。那些行为会在后续测试中逐个加入。

## 4. 完成第一个 TDD 循环

进入项目目录：

```powershell
cd projects/log-analyzer
python -m unittest discover -s tests -v
```

你应当看到测试失败，因为当前函数只是一个占位实现。这就是 RED。

打开 `log_analyzer.py`，只写足以通过当前测试的实现。你可能会用到：

```python
parts = line.split("|")
```

然后重新运行测试。测试通过就是 GREEN。

不要一次加入尚未要求的校验逻辑。我们会通过新增测试推动设计演进。

## 5. 短练习

在 Python REPL 或临时文件中回答：

1. `"a|b|c".split("|")` 的结果是什么类型？
2. `timestamp, level, message = line.split("|")` 使用了什么能力？字段数量不对时会发生什么？
3. `event["source"]` 与 `event.get("source")` 的行为有何不同？
4. 类型标注 `dict[str, str]` 会不会自动阻止你返回 `{"status": 500}`？

## 6. 提交给老师的内容

完成后告诉我“第一课代码已完成”。我会读取你的实现、运行测试并做代码评审，然后进入非法日志输入和异常设计。

请同时给出短练习第 2、3 题的答案。第 1、4 题用于自查。

