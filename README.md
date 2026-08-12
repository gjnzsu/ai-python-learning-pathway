# Python → Machine Learning → AI 学习路径

这是一个面向 Java / Spring Boot 工程师的 12 周 Python 与 AI 学习项目。

## 当前进度

- 已完成课程：第 2 周，第 2 课
- 当前项目：日志分析 CLI
- 下一步：第 2 周，第 3 课，上下文管理器与流式文件读取

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
python -m unittest discover -s tests -v
```

当前共有 17 个测试通过。日志分析器现在使用不可变数据类表示日志事件，并通过生成器惰性解析和过滤日志；CLI 继续支持 UTF-8 文件读取、按级别过滤、标准错误提示和进程退出码。
