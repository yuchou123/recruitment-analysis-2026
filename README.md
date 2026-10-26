# recruitment-analysis-2026

2026 年招聘信息数据分析项目。基于 51job 风格的招聘数据集（`recruitment`），在 MySQL 中完成数据清洗、去重、城市/岗位筛选与四大维度分析，覆盖 **data（数据岗）、game（游戏岗）、operator（运维岗）** 三张表，并产出三表对比分析报表（Excel）。

## 目录结构

```
recruitment-analysis-2026/
├── data/
│   ├── recruitment.sql.gz.part00~02   原始数据集（260MB，gzip 压缩后切分，见下方还原方法）
│   ├── recruitment_2026.sql           按原格式生成的 2026 年数据集（24MB）
│   ├── analysis_data.json             从 MySQL 视图提取的分析结果（建报表的数据源）
│   └── pools/                         生成器数据池（真实公司/地区/职位名等，取自原库）
├── queries/
│   ├── 招聘项目查询.sql                data 表（数据岗）全流程：13 个视图
│   ├── 招聘项目查询1.sql               game 表（游戏岗）全流程：13 个视图
│   ├── 招聘项目查询2.sql               operator 表（运维岗）全流程：13 个视图
│   └── game_operator_analysis.sql      game + operator 两表 26 视图合并脚本（可整体执行）
├── analysis/
│   └── 招聘项目三表对比分析.xlsx        三表对比分析报表（6 个工作表，142 个公式）
└── scripts/
    ├── gen_recruitment_2026.py         2026 数据集生成器
    ├── extract.py                      从 MySQL 视图提取分析数据 → analysis_data.json
    └── build.py                        用 openpyxl 生成对比分析报表
```

## 环境要求

- MySQL 8.0+（Navicat Premium 可选，仅作客户端）
- Python 3.13+；重建报表需要 `openpyxl`（build.py 会自动安装）

## 使用步骤

### 1. 还原并导入原始数据

`recruitment.sql` 原始文件 260MB，超出 GitHub 单文件 100MB 上限，已压缩并切分为 3 块。还原：

```bash
cat data/recruitment.sql.gz.part* > recruitment.sql.gz
gunzip recruitment.sql.gz        # 得到 260MB 的 recruitment.sql（Windows 可用 7-Zip 解压）
```

导入 MySQL（脚本内含建库和建表语句，无需手动建库）：

```bash
mysql -u root -p < recruitment.sql
```

### 2. 运行分析代码（三张表）

`queries/` 下四个文件均为 Navicat 查询格式，在 Navicat 中打开后点「运行」，或用 mysql 客户端执行：

```bash
mysql -u root -p recruitment_2026 < "queries/game_operator_analysis.sql"
```

| 文件 | 对应表 | 岗位筛选 |
|---|---|---|
| 招聘项目查询.sql | data | `job_name LIKE '%数据%'` |
| 招聘项目查询1.sql | game | `job_name LIKE '%游戏%'` |
| 招聘项目查询2.sql | operator | `job_name LIKE '%运维%'` |

注意事项：
- MySQL **不支持** `CREATE OR REPLACE VIEW`（PostgreSQL 语法），脚本统一采用 `DROP VIEW IF EXISTS` + `CREATE VIEW`，可反复执行；
- `招聘项目查询.sql` 开头的 `create database recruitmernt;` 为原始练习脚本笔误（多建一个空库，无害），`use recruitment_2026;` 已指向正确库。

### 3.（可选）重新生成 2026 数据集

```bash
python scripts/gen_recruitment_2026.py      # 输出到 data/recruitment_2026.sql
```

格式与原文件完全一致（相同表结构、相同字段取值规律）；公司名称与主页链接、职位名称取自原库真实数据，日期替换为 2026 年。

### 4.（可选）重建对比分析报表

```bash
set MYSQL_PWD=<你的MySQL密码>               # Windows；Linux/macOS 用 export
python scripts/extract.py                    # 从 recruitment_2026 提取分析数据
python scripts/build.py                      # 生成 analysis/招聘项目三表对比分析.xlsx
```

`extract.py` 的密码仅经环境变量 `MYSQL_PWD` 传递，不出现在命令行；可用 `MYSQL_BIN` / `MYSQL_USER` / `DB_NAME` 覆盖客户端路径、用户名与库名。

## 分析流程（每张表 13 个视图）

```
原始表 → v_*_clean_null（13 个关键字段非空）
      → v_clean_*_distinct（ROW_NUMBER 按 公司名+职位名 取 issuedate 最新）
      → v_*_clean_workplace（限北上广深，去 NULL）
      → v_*_clean_jobname（岗位关键词筛选）
      → v_*_clean（最终分析集）
      → 四大分析：market_demand（城市需求）/ companytype_degree（企业类型）
                 / workyear_salary + companytype_salary（薪资）/ skill（核心技能）
```

## 主要结论

| 指标 | data（数据岗） | game（游戏岗） | operator（运维岗） |
|---|---|---|---|
| 原始记录 | 8,000 | 5,000 | 5,000 |
| 清洗空值后 | 7,081 | 4,425 | 4,432 |
| 去重后 | 7,058 | 4,425 | 4,400 |
| 限北上广深 | 6,813 | 4,279 | 4,252 |
| 最终分析集 | 495 | 1,116 | 1,195 |
| 平均月薪（元） | 11,566 | 11,312 | 11,489 |
| 主力城市 | 广州 | 广州 | 广州 |
| 主导企业类型 | 民营公司 | 民营公司 | 民营公司 |
| TOP 技能 | ETL（85.5%） | 电商（5.0%） | LINUX（67.4%） |

- 薪资口径：千/月 ×1000、万/月 ×10000、万/年 ×833（≈÷12），salary_mean = (min+max)/2；
- 技能口径：职位详情文本 LIKE 匹配 `skill_table` 的 63 个技能关键词；「报告」一词因高频出现于「测试报告/运行报告」等文本、并非真实技能，报表中已剔除；
- 数据岗「8 年」样本仅 1 条，年限薪资解读需谨慎。

## 说明

- 原始数据来自课程资料（百度网盘），其中公司名称与 51job 职位链接为真实数据；`recruitment_2026.sql` 为按相同格式生成的练习数据；
- 本仓库所有脚本已移除本地密码等敏感信息；
- 数据分析流程与对比报表由生成式 AI 辅助完成（2026-10-26）。
