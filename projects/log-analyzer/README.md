# Log Analyzer

第一个贯穿项目：从单行日志解析开始，逐步演化为带统计、过滤、错误处理和 CLI 接口的日志分析工具。

## 当前状态

已完成日志解析、级别统计、日志过滤、UTF-8 文件读取和命令行入口。CLI 支持按日志级别输出匹配事件，并在参数数量错误时返回用法提示和退出码 `2`。

## 运行测试

```powershell
python -m unittest discover -s tests -v
```

第四课完成后应有 12 个测试通过。

## 运行 CLI

```powershell
python log_analyzer.py sample.log ERROR
```

参数格式：

```text
python log_analyzer.py <log-file> <level>
```
