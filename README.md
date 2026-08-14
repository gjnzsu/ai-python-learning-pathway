# Python → Machine Learning → AI 学习路径

这是一个面向 Java / Spring Boot 工程师的 12 周 Python 与 AI 学习项目。

## 当前进度

- 已完成课程：第 2 周，第 4 课
- 当前项目：日志分析 CLI
- 下一步：第 3 周，第 1 课，项目结构、虚拟环境与依赖管理

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

当前共有 21 个测试通过，并且 mypy 静态检查无错误。日志分析器通过最小 `LogSource` 协议解耦数据来源与处理管道；文件源和内存测试源无需继承协议即可被静态验证为可替换，同时保留流式读取、确定关闭、CLI 输出与退出码。
