# Python → Machine Learning → AI 学习路径

这是一个面向具有 Java / Spring Boot 背景的银行 AI 平台项目经理的 6 周 AI 应用工程核心学习项目。目标是能够理解架构、独立验证小型 AI 原型，并从质量、安全、成本和工程边界参与技术方案 Review。

## 当前进度

- 当前路线：正在从原 12 周通用路线切换到 6 周 AI 应用工程核心路线
- 当前成果：`projects/week-05-bike-sharing/notebooks/03_group_comparison.ipynb`
- 下一步：进入 AI API 工程，实现具备输入契约、超时、重试和错误分类的可靠模型 API 调用器

完整路线：[6 周 AI 应用工程核心路线](docs/ai-application-core-6-week-roadmap.md)

既有 1–5 周讲义和项目保留为历史成果与查阅资料，不再要求逐课全部完成。

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
