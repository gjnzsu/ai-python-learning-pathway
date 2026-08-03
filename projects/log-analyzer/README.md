# Log Analyzer

第一个贯穿项目：从单行日志解析开始，逐步演化为带统计、过滤、错误处理和 CLI 接口的日志分析工具。

## 当前状态

已完成单行日志解析和多行日志级别统计，包括未知日志级别与空输入测试。

## 运行测试

```powershell
python -m unittest discover -s tests -v
```

第二课完成后应有 5 个测试通过。
