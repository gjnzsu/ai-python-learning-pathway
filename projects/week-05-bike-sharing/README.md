# Bike Sharing Data Analysis

## 数据来源

- 数据集：Bike Sharing Dataset
- 提供方：UCI Machine Learning Repository
- 原始系统：Capital Bikeshare，Washington D.C.
- 时间范围：2011-01-01 至 2012-12-31
- 下载日期：2026-08-27
- 官方页面：https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset

## 原始文件

| 文件 | 观察单位 | 记录数 |
| --- | --- | ---: |
| `hour.csv` | 一个自然日中的一个有租赁记录的小时 | 17,379 |
| `day.csv` | 一个自然日 | 731 |
| `Readme.txt` | 官方数据说明 | — |

## 目录约定

- `data/raw/`：原始文件，不手工修改。
- `data/processed/`：后续课程生成的清洗数据。
- `notebooks/`：数据审计和分析 Notebook。

## 已确认的数据契约

- `instant` 唯一。
- `dteday + hr` 唯一。
- 原始17个字段不存在列内缺失值。
- 类别字段和归一化字段均处于说明文档定义的范围。
- `cnt == casual + registered` 对全部17,379条记录成立。
- 小时表按日聚合后的三个租赁计数字段与日表完全一致。

## 已知的数据特征与限制

- 完整时间范围理论上包含17,544个小时，小时表实际包含17,379条记录。
- 时间轴存在75处断点，共缺少165个小时，涉及76个不完整日期。
- 缺失主要集中在凌晨，且现有小时记录的 `cnt` 最小值为1。
- 结合日表总量验证，缺失小时对应的租赁量应为0。
- 数据没有站点、单次骑行时长和出行目的字段。
- `workingday=0` 同时包含周末与法定节假日。
- `casual` 和 `registered` 是 `cnt` 的组成部分，预测 `cnt` 时不能作为输入特征。
- 后续模型评估应优先采用时间切分，避免未来数据进入训练集。