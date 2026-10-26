# -*- coding: utf-8 -*-
"""Extract all analysis results from recruitment_2026 into one JSON for the Excel build.

用法：
    set MYSQL_PWD=<你的MySQL密码>        (Windows)
    export MYSQL_PWD=<你的MySQL密码>     (Linux/macOS)
    python extract.py [输出json路径]

可通过环境变量覆盖：MYSQL_BIN（mysql 客户端路径）、MYSQL_USER、DB_NAME。
密码只经环境变量 MYSQL_PWD 传给客户端，不出现在命令行中。
"""
import json
import os
import subprocess
import sys

_WIN_MYSQL = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
MYSQL = os.environ.get("MYSQL_BIN", _WIN_MYSQL if os.path.exists(_WIN_MYSQL) else "mysql")
DB = os.environ.get("DB_NAME", "recruitment_2026")
OUT = sys.argv[1] if len(sys.argv) > 1 else "analysis_data.json"

if not os.environ.get("MYSQL_PWD"):
    raise SystemExit("请先设置环境变量 MYSQL_PWD（MySQL 密码）后再运行。")


def q(sql):
    """Run a query, return list of tab-split rows (header stripped)."""
    cmd = [MYSQL, "-u", os.environ.get("MYSQL_USER", "root"),
           "--default-character-set=utf8mb4", "--batch", "--raw", DB, "-e", sql]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"query failed: {sql}\n{r.stderr}")
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    return [l.split("\t") for l in lines[1:]] if lines else []


data = {}

# ---------- 1. funnel counts ----------
f = q("""SELECT
 (SELECT COUNT(*) FROM data) AS data_raw,
 (SELECT COUNT(*) FROM v_data_clean_null) AS data_null,
 (SELECT COUNT(*) FROM v_clean_data_distinct) AS data_dist,
 (SELECT COUNT(*) FROM v_data_clean_workplace) AS data_wp,
 (SELECT COUNT(*) FROM v_data_clean) AS data_final,
 (SELECT COUNT(*) FROM game) AS game_raw,
 (SELECT COUNT(*) FROM v_game_clean_null) AS game_null,
 (SELECT COUNT(*) FROM v_clean_game_distinct) AS game_dist,
 (SELECT COUNT(*) FROM v_game_clean_workplace) AS game_wp,
 (SELECT COUNT(*) FROM v_game_clean) AS game_final,
 (SELECT COUNT(*) FROM operator) AS op_raw,
 (SELECT COUNT(*) FROM v_operator_clean_null) AS op_null,
 (SELECT COUNT(*) FROM v_clean_operator_distinct) AS op_dist,
 (SELECT COUNT(*) FROM v_operator_clean_workplace) AS op_wp,
 (SELECT COUNT(*) FROM v_operator_clean) AS op_final""")[0]
keys = ["data_raw", "data_null", "data_dist", "data_wp", "data_final",
        "game_raw", "game_null", "game_dist", "game_wp", "game_final",
        "op_raw", "op_null", "op_dist", "op_wp", "op_final"]
data["funnel"] = {k: int(v) for k, v in zip(keys, f)}

# ---------- 2. city demand (职位数目 = col index 2) ----------
data["city"] = {}
for job, view in [("data", "v_data_market_demand"),
                  ("game", "v_game_market_demand"),
                  ("operator", "v_operator_market_demand")]:
    rows = q(f"SELECT * FROM {view}")
    data["city"][job] = {r[0]: int(r[2]) for r in rows}

# ---------- 3. company type: counts (from clean views) + avg salary ----------
data["ctype"] = {}
for job, clean, sal in [("data", "v_data_clean", "v_data_companytype_salary"),
                        ("game", "v_game_clean", "v_game_companytype_salary"),
                        ("operator", "v_operator_clean", "v_operator_companytype_salary")]:
    counts = {r[0]: int(r[1]) for r in q(f"SELECT companytype_text, COUNT(*) FROM {clean} GROUP BY companytype_text")}
    sals = {r[0]: float(r[1]) for r in q(f"SELECT * FROM {sal}")}
    data["ctype"][job] = [
        {"type": t, "count": c, "avg_salary": sals.get(t)}
        for t, c in counts.items()
    ]

# ---------- 4. workyear salary + sample counts ----------
data["workyear"] = {}
for job, view in [("data", "v_data_workyear_salary"),
                  ("game", "v_game_workyear_salary"),
                  ("operator", "v_operator_workyear_salary")]:
    data["workyear"][job] = {r[0]: float(r[1]) for r in q(f"SELECT * FROM {view}")}
data["workyear_count"] = {}
for job, clean in [("data", "v_data_clean"),
                   ("game", "v_game_clean"),
                   ("operator", "v_operator_clean")]:
    data["workyear_count"][job] = {
        r[0]: int(r[1]) for r in q(f"SELECT workyear, COUNT(*) FROM {clean} GROUP BY workyear")
    }

# ---------- 5. skills: complete frequencies for ALL skills x 3 jobs ----------
skill_rows = q("""SELECT st.skill,
 (SELECT COUNT(*) FROM v_data_clean v WHERE v.parse2_job_detail LIKE CONCAT('%',st.skill,'%')),
 (SELECT COUNT(*) FROM v_game_clean v WHERE v.parse2_job_detail LIKE CONCAT('%',st.skill,'%')),
 (SELECT COUNT(*) FROM v_operator_clean v WHERE v.parse2_job_detail LIKE CONCAT('%',st.skill,'%'))
 FROM skill_table st""")
data["skills_all"] = [
    {"skill": r[0], "data": int(r[1]), "game": int(r[2]), "operator": int(r[3])}
    for r in skill_rows if r[0] != "报告"
]

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, indent=1)

print("funnel:", data["funnel"])
print("city:", {j: data["city"][j] for j in data["city"]})
print("workyear data:", data["workyear"]["data"])
print("workyear_count data:", data["workyear_count"]["data"])
print("workyear_count game:", data["workyear_count"]["game"])
print("workyear_count op:", data["workyear_count"]["operator"])
print("skills_all top8:", sorted(data["skills_all"], key=lambda s: -max(s["data"], s["game"], s["operator"]))[:8])
print("OK ->", OUT)
