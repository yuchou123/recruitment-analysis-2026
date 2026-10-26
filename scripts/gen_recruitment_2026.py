# -*- coding: utf-8 -*-
"""
生成 2026 年招聘信息数据集，格式与 recruitment.sql 完全一致：
- 相同表结构（data / game / operator / skill_table）
- 相同字段取值规律（51job 风格的 URL、薪资文本、地区编码、详情文本结构）
- 公司名称与公司主页链接：真实（取自原库）
- 职位名称：真实职位名（取自原库）
- 日期：2026 年
输出 mysqldump 风格的 SQL 文件
"""
import random
import datetime
import os
import re

random.seed(20261025)

# 默认按仓库布局解析路径；可用环境变量 RECRUIT_BASE / POOLS_DIR / OUT_SQL 覆盖
BASE = os.environ.get("RECRUIT_BASE", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
POOLS = os.environ.get("POOLS_DIR", os.path.join(BASE, "data", "pools"))
OUT_SQL = os.environ.get("OUT_SQL", os.path.join(BASE, "data", "recruitment_2026.sql"))

COUNTS = {"data": 8000, "game": 5000, "operator": 5000}

# ---------- 加载数据池 ----------

def load_tsv(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        f.readline()  # header
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            rows.append(line.split("\t"))
    return rows

workareas = [(c, t, int(n)) for c, t, n in load_tsv(os.path.join(POOLS, "workareas.tsv"))]

slug_map = {}
for c, s, n in load_tsv(os.path.join(POOLS, "slugs.tsv")):
    n = int(n)
    if c not in slug_map or n > slug_map[c][1]:
        slug_map[c] = (s, n)

companies = [(nm, hr, int(n)) for nm, hr, n in load_tsv(os.path.join(POOLS, "companies.tsv"))]

ctype_map = {}
for nm, hr, ct, n in load_tsv(os.path.join(POOLS, "company_types.tsv")):
    key = (nm, hr)
    n = int(n)
    if key not in ctype_map or n > ctype_map[key][1]:
        ctype_map[key] = (ct, n)

jobnames = {"data": [], "game": [], "operator": []}
for t, nm, n in load_tsv(os.path.join(POOLS, "jobnames.tsv")):
    if t in jobnames and nm:
        jobnames[t].append((nm, int(n)))

salaries = [(s, int(n)) for s, n in load_tsv(os.path.join(POOLS, "salaries.tsv")) if s]

cats = {"data": set(), "game": set(), "operator": set()}
for r in load_tsv(os.path.join(POOLS, "categories.tsv")):
    t, cat = r[0], r[1]
    if t in cats and cat and cat != "NULL":
        cat = cat.replace("职能类别：", "").replace("关键字：", "").strip()
        for tok in cat.split("/"):
            tok = tok.strip()
            if 2 <= len(tok) <= 20:
                cats[t].add(tok)

SKILLS = ["电商", "LR", "神策", "聚类", "GBDT", "SAS", "NLP", "HTML", "SHELL", "CAFFE", "金融", "TENSORFLOW",
          "报表", "C语言", "HBASE", "模型设计", "MAPREDUCE", "NODEJS", "LINUX", "STORM", "SQL", "CONGOS", "决策树",
          "PYTHON", "IMPALA", "EXCEL", "SUPERSET", "ORACLE", "HIGHCHARTS", "KETTLE", "算法", "大数据", "数据挖掘",
          "风控", "KAFKA", "SPSS", "PPT", "DATASTAGE", "WORD", "PRESTO", "报告", "RUBY", "R语言", "FLUME", "FLINK",
          "BI", "POSTGESQL", "SPARK", "可视化", "SCALA", "HIVE", "ETL", "HQL", "D3", "POWERPOINT", "ECHARTS",
          "回归", "ABTEST", "MYSQL", "机器学习", "TABLEAU", "SQL SERVER", "数据结构"]

GENERAL_CTYPES = [("民营公司", 60), ("上市公司", 8), ("合资", 8), ("外资（非欧美）", 8), ("外资（欧美）", 6),
                  ("创业公司", 5), ("国企", 4), ("事业单位", 1), ("非营利组织", 1), ("外企代表处", 1)]

DEGREE_POOL = [("", 4600), ("5", 47000), ("6", 40000), ("4", 2800), ("2", 1800),
               ("7", 2000), ("1", 100), ("3", 250), ("8", 180)]
WORKYEAR_POOL = [("", 4000), ("3", 23000), ("5", 24000), ("4", 19000), ("1", 8000),
                 ("10", 7600), ("6", 10400), ("7", 1250), ("8", 800)]

# ---------- 职责/要求文本池 ----------

DUTIES = {
    "data": [
        "负责业务数据的提取、清洗与整合，搭建数据集市，支撑各业务线分析需求",
        "参与数据仓库模型设计，完成ETL开发与任务调度，保障数据准时稳定产出",
        "通过数据分析洞察业务问题，输出专题分析报告，为业务决策提供数据支持",
        "搭建业务监控指标体系，完成日报、周报、月报等常规报表开发与维护",
        "针对用户行为、营销效果、商品结构等场景开展深度分析，提出可落地的优化建议",
        "与产品、运营、研发团队紧密协作，推动数据埋点方案的设计、验收与落地",
        "负责数据质量监控与异常排查，保障数据准确性与一致性",
        "运用统计建模与机器学习方法，完成用户分群、流失预警、推荐策略等模型开发",
        "负责业务取数需求的支持与数据口径管理，沉淀可复用的数据资产",
        "完成上级交办的其他数据分析相关工作",
    ],
    "game": [
        "根据产品项目的特点及测试需要，制定测试策略和测试计划，搭建测试环境",
        "负责游戏版本的测试执行，提交并跟踪缺陷，编写测试报告并提出改进建议",
        "协助主策完成游戏系统、玩法设计，撰写相关策划文档并跟进实现",
        "负责游戏内UI界面的设计与绘制，跟进最终效果实现与体验优化",
        "负责游戏活动的策划与配置，跟进活动上线效果并进行复盘优化",
        "对接研发、美术、运营团队，确保需求按时高质量交付",
        "关注竞品动态与玩家反馈，为产品迭代提供参考建议",
        "完成上级交办的其他游戏策划相关工作",
    ],
    "operator": [
        "负责公司服务器与运营平台的日常维护，解决服务器故障，为平台的平稳运行提供技术支持",
        "负责运营平台服务器的部署、监控、数据备份、日志分析、性能调优等工作",
        "及时响应并处理各类故障，定位并解决问题，输出故障分析报告",
        "负责网络设备、安全设备的配置管理与故障排查，保障网络安全",
        "编写与优化运维脚本，推进运维自动化，提升工作效率",
        "制定系统维护流程规范，定期制作系统运行报告",
        "协助研发团队完成项目上线，参与容量规划与成本优化",
        "完成上级交代的其它工作任务",
    ],
}

REQUIREMENTS = {
    "data": [
        "本科及以上学历，数学、统计学、计算机等相关专业优先",
        "熟悉SQL语句编写，熟练使用至少一种分析工具（Python/R/Excel）",
        "掌握数据仓库与ETL基本原理，有Hive/Spark等大数据工具使用经验优先",
        "具备良好的逻辑思维能力与数据敏感度，能独立完成分析报告",
        "熟悉互联网行业业务指标，有电商/零售行业分析经验优先",
        "具备1年以上数据分析相关工作经验，优秀应届生亦可",
        "良好的沟通协调能力与团队合作精神，抗压能力强",
        "熟悉Tableau/PowerBI等可视化工具者优先",
    ],
    "game": [
        "热爱游戏行业，有丰富的游戏经验，熟悉各类主流游戏玩法",
        "本科及以上学历，计算机、美术设计、数学等相关专业优先",
        "熟悉Unity3D/Unreal引擎及相关工具链者优先",
        "具备良好的沟通能力与团队协作精神，工作认真负责",
        "有游戏行业实习或项目经验者优先",
        "熟悉Photoshop/Illustrator等设计软件（美术设计类岗位）",
        "对数据敏感，能通过数据反馈指导工作优化者优先",
    ],
    "operator": [
        "计算机相关专业本科或以上学历",
        "熟悉Linux/Windows操作系统，熟悉Shell/Python等脚本语言",
        "熟悉Nginx、MySQL、Redis、Tomcat等服务的部署与调优",
        "熟悉云服务（阿里云/腾讯云）的使用与管理，有云上运维经验优先",
        "具备较强的学习能力，具有较强的责任心、团队精神以及抗压精神",
        "有2年以上运维经验，有大型系统维护经验者优先",
        "具有良好的语言表达能力，善于与人沟通、合作",
        "熟悉Jenkins、Git、Ansible等DevOps工具链者优先",
    ],
}

BENEFITS = [
    "五险一金齐全，周末双休，带薪年假、带薪病假",
    "免费午餐，每周不同菜式，免费零食饮料",
    "地铁周边，甲级写字楼，舒适的办公环境",
    "绩效奖金、年终奖、年度旅游，样样都有",
    "扁平管理，团队氛围好，发展空间大",
    "弹性工作制，加班可调休，解决后顾之忧",
    "定期团建，节日福利，员工体检",
]

SECTION_TITLES = {
    "data": ("岗位职责", "岗位要求"),
    "game": ("职位描述", "任职要求"),
    "operator": ("工作职责", "任职要求"),
}

KEYWORD_EXTRA = ["五险一金", "双休", "包吃", "带薪年假", "年终奖", "弹性工作", "周末双休", "大小周",
                 "地铁周边", "甲级写字楼", "定期体检", "节日福利", "团队氛围", "发展空间", "抗压能力",
                 "学习能力", "沟通能力", "责任心", "本科及以上学历", "经验优先", "应届生亦可", "急招"]

# ---------- 工具函数 ----------

def weighted(items):
    """items: (value[, ...], weight)，权重在最后一列；返回 value 部分（多列时返回元组）"""
    total = sum(it[-1] for it in items)
    r = random.uniform(0, total)
    acc = 0.0
    for it in items:
        acc += it[-1]
        if r <= acc:
            return tuple(it[:-1]) if len(it) > 2 else it[0]
    return items[-1][0]

def esc(s):
    if s is None:
        return "NULL"
    s = str(s)
    return "'" + (s.replace("\\", "\\\\").replace("'", "\\'")
                  .replace("\n", "\\n").replace("\r", "\\r")
                  .replace("\x00", "\\0").replace("\x1a", "\\Z")) + "'"

def rand_job_id():
    return random.randint(100000000, 139999999)

def rand_company_id():
    return random.randint(1000000, 5999999)

def rand_updatedate():
    start = datetime.date(2026, 8, 20)
    span = (datetime.date(2026, 10, 25) - start).days
    skew = int(span * (random.random() ** 2.2))  # 偏向近期
    return start + datetime.timedelta(days=skew)

def rand_issuedate(d):
    return "%04d-%02d-%02d %02d:%02d:%02d" % (
        2026, d.month, d.day, random.randint(0, 23), random.randint(0, 59), random.randint(0, 59))

# 关键字池：职位名碎片 + 职能类别 + 技能 + 福利词
kw_pool = set(KEYWORD_EXTRA) | set(SKILLS)
for t in jobnames:
    for nm, _ in jobnames[t][:4000]:
        for tok in nm.replace("（", " ").replace("）", " ").replace("(", " ").replace(")", " ") \
                .replace("/", " ").replace("+", " ").replace("、", " ").split():
            if 2 <= len(tok) <= 20:
                kw_pool.add(tok)
for t in cats:
    kw_pool |= cats[t]
kw_pool = sorted(kw_pool)

def pick_related(pool_list, job_name, k, all_pool):
    """优先抽取与职位名相关的条目，不足时回退到全量池"""
    tokens = [t for t in re.split(r"[（()）/\+、\s]", job_name) if len(t) >= 2]
    related = [x for x in pool_list if any(t in x or x in t for t in tokens)]
    src = related if len(related) >= k else all_pool
    return random.sample(src, k=min(k, len(src)))

def build_detail(theme, job_name):
    duty_title, req_title = SECTION_TITLES[theme]
    duties = random.sample(DUTIES[theme], k=random.randint(4, min(7, len(DUTIES[theme]))))
    reqs = random.sample(REQUIREMENTS[theme], k=random.randint(4, min(6, len(REQUIREMENTS[theme]))))
    parts = ["职位信息"]
    parts.append(duty_title + "：" + "；".join("%d、%s" % (i + 1, d) for i, d in enumerate(duties)))
    parts.append(req_title + "：" + "；".join("%d、%s" % (i + 1, r) for i, r in enumerate(reqs)))
    if theme == "operator" and random.random() < 0.45:
        parts.append("福利待遇：" + "；".join(random.sample(BENEFITS, k=random.randint(2, 4))))
    cat_list = list(cats[theme])
    chosen_cats = pick_related(cat_list, job_name, min(random.randint(1, 3), len(cat_list)), cat_list)
    kws = pick_related(kw_pool, job_name, random.randint(3, 6), kw_pool)
    parts.append("职能类别：" + "/".join(chosen_cats))
    parts.append("关键字：" + "".join(kws))
    parts.append("微信分享")
    return "".join(parts)

def gen_row(theme, idx):
    area = weighted(workareas)
    area_code, area_text = area[0], area[1]
    slug = slug_map.get(area_code, ("shanghai", 0))[0]
    name, href = weighted(companies)
    ctype = ctype_map.get((name, href), (None, 0))[0] or weighted(GENERAL_CTYPES)
    job_name = weighted(jobnames[theme])
    salary = weighted(salaries) if random.random() > 0.03 else ""
    d = rand_updatedate()
    row = [
        idx,
        "https://jobs.51job.com/%s/%d.html?s=01&t=0" % (slug, rand_job_id()),
        job_name,
        href,
        name,
        salary,
        area_code,
        area_text,
        d.strftime("%m-%d"),
        ctype,
        weighted(DEGREE_POOL),
        weighted(WORKYEAR_POOL),
        rand_issuedate(d),
        build_detail(theme, job_name),
    ]
    return row

# ---------- 写 SQL 文件 ----------

CREATE_DDL = """CREATE TABLE `{t}` (
  `id` bigint DEFAULT NULL,
  `job_href` text,
  `job_name` text,
  `company_href` text,
  `company_name` text,
  `providesalary_text` text,
  `workarea` text,
  `workarea_text` text,
  `updatedate` text,
  `companytype_text` text,
  `degreefrom` text,
  `workyear` text,
  `issuedate` text,
  `parse2_job_detail` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8;"""

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

with open(OUT_SQL, "w", encoding="utf-8", newline="\n") as f:
    f.write("-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)\n")
    f.write("--\n")
    f.write("-- Host: localhost    Database: recruitment_2026\n")
    f.write("-- ------------------------------------------------------\n")
    f.write("-- Server version\t8.0.46\n\n")
    f.write("/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;\n")
    f.write("/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;\n")
    f.write("/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;\n")
    f.write("/*!50503 SET NAMES utf8mb4 */;\n")
    f.write("/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;\n")
    f.write("/*!40103 SET TIME_ZONE='+00:00' */;\n")
    f.write("/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;\n")
    f.write("/*!40000 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;\n")
    f.write("/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;\n")
    f.write("/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;\n")

    for theme in ["data", "game", "operator", "skill_table"]:
        f.write("\n--\n-- Table structure for table `%s`\n--\n\n" % theme)
        f.write("DROP TABLE IF EXISTS `%s`;\n" % theme)
        f.write("/*!40101 SET @saved_cs_client     = @@character_set_client */;\n")
        f.write("/*!50503 SET character_set_client = utf8mb4 */;\n")
        if theme == "skill_table":
            f.write("CREATE TABLE `skill_table` (\n  `skill` varchar(20) DEFAULT NULL\n) ENGINE=InnoDB DEFAULT CHARSET=utf8;\n")
        else:
            f.write(CREATE_DDL.format(t=theme) + "\n")
        f.write("/*!40101 SET character_set_client = @saved_cs_client */;\n")
        f.write("\n--\n-- Dumping data for table `%s`\n--\n\n" % theme)
        f.write("LOCK TABLES `%s` WRITE;\n" % theme)
        f.write("/*!40000 ALTER TABLE `%s` DISABLE KEYS */;\n" % theme)
        if theme == "skill_table":
            f.write("INSERT INTO `skill_table` VALUES " + ",".join("(%s)" % esc(s) for s in SKILLS) + ";\n")
        else:
            buf, buf_bytes = [], 0
            for i in range(COUNTS[theme]):
                row = gen_row(theme, i)
                stmt = "(" + ",".join(esc(v) for v in row) + ")"
                buf.append(stmt)
                buf_bytes += len(stmt.encode("utf-8"))
                if buf_bytes >= 800000 or len(buf) >= 1000:
                    f.write("INSERT INTO `%s` VALUES " % theme + ",".join(buf) + ";\n")
                    buf, buf_bytes = [], 0
            if buf:
                f.write("INSERT INTO `%s` VALUES " % theme + ",".join(buf) + ";\n")
        f.write("/*!40000 ALTER TABLE `%s` ENABLE KEYS */;\n" % theme)
        f.write("UNLOCK TABLES;\n")

    f.write("\n/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;\n\n")
    f.write("/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;\n")
    f.write("/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;\n")
    f.write("/*!40000 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;\n")
    f.write("/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;\n")
    f.write("/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;\n")
    f.write("/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;\n")
    f.write("/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;\n\n")
    f.write("-- Dump completed on %s\n" % now)

print("written:", OUT_SQL)
print("size MB: %.1f" % (os.path.getsize(OUT_SQL) / 1048576.0))
