# Log Analyzer

第一个贯穿项目：从单行日志解析开始，逐步演化为带统计、过滤、错误处理和 CLI 接口的日志分析工具。

## 当前状态

日志分析器已迁移为采用 `src/` 布局的可安装 Python 包。核心逻辑与 CLI 入口分离，同时保留 `LogSource` 协议、惰性解析与过滤、文件资源确定关闭、按级别输出和退出码。

## 准备开发环境

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

项目使用 editable install；修改 `src/log_analyzer/` 下的 Python 源码后通常不需要重新安装。依赖或 console script 配置改变后，应重新执行安装命令。

## 运行测试

```powershell
python -m unittest discover -s tests -v
python -m mypy src\log_analyzer tests\test_log_analyzer.py
```

当前应有 21 个测试通过，mypy 检查 5 个源文件无错误。

## 运行 CLI

```powershell
python -m log_analyzer sample.log ERROR
log-analyzer sample.log INFO
```

参数格式：

```text
log-analyzer <log-file> <level>
```

正常执行返回 `0`；参数数量错误时向标准错误输出 usage，并返回 `2`。

## 项目结构

```text
pyproject.toml
src/
└── log_analyzer/
    ├── __init__.py    # 包级公开接口
    ├── __main__.py    # python -m 入口
    ├── cli.py         # 参数、退出码和 console script
    └── core.py        # 数据对象、协议、数据源与处理逻辑
tests/
└── test_log_analyzer.py
```
