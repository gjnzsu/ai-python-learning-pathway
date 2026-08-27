# Python → Machine Learning → AI 学习路径

这是一个面向 Java / Spring Boot 工程师的 12 周 Python 与 AI 学习项目。

## 当前进度

- 已完成课程：第 5 周，第 1 课，真实公开数据集、数据来源与数据契约
- 当前成果：`projects/week-05-bike-sharing/notebooks/01_data_audit.ipynb`
- 下一步：第 5 周第 2 课，系统化数据清洗与可追踪转换

## 目录

```text
lessons/       课程讲义
exercises/     短练习
projects/      阶段项目
resources/     已核验的公开资源
progress/      学习进度与复盘
```

## 开始学习

```powershell
cd projects/log-analyzer
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
```

当前共有 30 个 pytest 测试通过，mypy 检查 5 个源文件无错误，Ruff 检查与项目构建通过。日志分析 CLI 已使用 `argparse` 生成帮助和处理参数，文件接口兼容 `str` 与 `pathlib.Path`，并通过隔离 wheel 环境验证 `log-analyzer` 可在项目目录外独立运行。
