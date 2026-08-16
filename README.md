# Python → Machine Learning → AI 学习路径

这是一个面向 Java / Spring Boot 工程师的 12 周 Python 与 AI 学习项目。

## 当前进度

- 已完成课程：第 3 周，第 1 课
- 当前项目：日志分析 CLI
- 下一步：第 3 周，第 2 课，pytest、fixture 与参数化测试

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
python -m unittest discover -s tests -v
```

当前共有 21 个测试通过，mypy 检查 5 个源文件无错误。日志分析器已经从单文件迁移为可编辑安装的 `src/` 包，支持 `python -m log_analyzer` 与 `log-analyzer` 两种入口，同时保留 `LogSource` 协议、流式读取、确定关闭、CLI 输出与退出码。
