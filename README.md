# Python → Machine Learning → AI 学习路径

这是一个面向 Java / Spring Boot 工程师的 12 周 Python 与 AI 学习项目。

## 当前进度

- 已完成课程：第 2 周，第 3 课
- 当前项目：日志分析 CLI
- 下一步：第 2 周，第 4 课，协议、类型标注与静态检查

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

当前共有 20 个测试通过。日志分析器现在通过上下文管理器安全地流式读取 UTF-8 文件，并使用生成器惰性解析和过滤日志；正常退出、提前退出和解析异常都能确定关闭文件，同时保持 CLI 输出与退出码不变。
