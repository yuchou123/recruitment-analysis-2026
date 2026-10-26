-- =====================================================================
-- game 表 & operator 表 全流程分析脚本
-- 与 data 表的分析流程完全一致：清洗空值 → 去重 → 城市限制 → 岗位筛选
--   → 市场需求/企业类型/薪资/技能 四大分析
-- 数据库：recruitment_2026
-- 注意：MySQL 不支持 CREATE OR REPLACE VIEW，统一用 DROP + CREATE
-- =====================================================================

-- =====================================================================
-- 第一部分：game 表（游戏岗位）
-- =====================================================================

-- 1. 清洗空值：筛选公司名字为空、工作地点为空、岗位为空等数据（保留全字段非空的记录）
drop view if exists v_game_clean_null;
create view v_game_clean_null as
select *
from game
where
job_href is not null and job_href != '' and
job_name is not null and job_name != '' and
company_href is not null and company_href != '' and
company_name is not null and company_name != '' and
providesalary_text is not null and providesalary_text != '' and
workarea is not null and workarea != '' and
workarea_text is not null and workarea_text != '' and
companytype_text is not null and companytype_text != '' and
degreefrom is not null and degreefrom != '' and
workyear is not null and workyear != '' and
updatedate is not null and updatedate != '' and
issuedate is not null and issuedate != '' and
parse2_job_detail is not null and parse2_job_detail != '';
select count(*) as game_clean_null from v_game_clean_null;

-- 2. 通过新加字段 row1，筛选重复的公司和岗位名称（保留 issuedate 最新的一条）
drop view if exists v_clean_game_distinct;
create view v_clean_game_distinct as
with p as
(select
  *,row_number() over (partition by company_name,job_name order by issuedate desc) as row1
  from v_game_clean_null)
select
  id,job_href,job_name,company_href,company_name,providesalary_text,workarea,workarea_text,updatedate,companytype_text,degreefrom,workyear,issuedate,parse2_job_detail
from p
where row1 = 1;
select count(*) as game_distinct from v_clean_game_distinct;

-- 3. 限制地区（北上广深）以及去除 null
drop view if exists v_game_clean_workplace;
create view v_game_clean_workplace as
with p as
(select
  *,(case
       when workarea_text like '%北京%' then '北京'
       when workarea_text like '%上海%' then '上海'
       when workarea_text like '%广州%' then '广州'
       when workarea_text like '%深圳%' then '深圳'
   end) as workplace
 from v_clean_game_distinct)
select
  *
from p where workplace is not null;
select count(*) as game_workplace from v_game_clean_workplace;

-- 4. 过滤周边岗位（game 表对应筛选“游戏”岗位）
drop view if exists v_game_clean_jobname;
create view v_game_clean_jobname as
select *
from v_game_clean_workplace
where job_name like '%游戏%';
select count(*) as game_jobname from v_game_clean_jobname;

-- 5. 汇总视图
drop view if exists v_game_clean;
create view v_game_clean as
(select * from v_game_clean_jobname);
select count(*) as game_clean from v_game_clean;

-- 6. 市场（城市）需求分析
drop view if exists v_game_market_demand;
create view v_game_market_demand as
select
      workplace as '城市',
      sum(degreefrom) as '招聘总数',
      count(*) as '职位数目'
from v_game_clean
group by workplace;
select * from v_game_market_demand;

-- 7. 市场量分析以及企业类型分布
drop view if exists v_game_companytype_degree;
create view v_game_companytype_degree as
select
  companytype_text as '企业类型',
  degreefrom as '招聘量',
  concat(cast(degreefrom/sum_degreefrom * 100 as decimal(4,2)),'%')  as '招聘占比'
from
(select
      companytype_text,sum(degreefrom) as degreefrom
from
  v_game_clean
group by
  companytype_text
order by
  degreefrom desc) f1,
(select sum(degreefrom) as sum_degreefrom from v_game_clean) f2;
select * from v_game_companytype_degree;

-- 8. 薪资单位换算（万/月=10000，千/月=1000，万/年=833）
drop view if exists v_game_salary_unit;
create view v_game_salary_unit as
select * ,
       (case when providesalary_text like '%万/月%' then 10000
             when providesalary_text like '%千/月%' then 1000
             when providesalary_text like '%万/年%' then 833
        end
       ) as unit
from v_game_clean;
select * from v_game_salary_unit;

-- 9. 薪资最低/最高/平均（统一换算成月薪，单位：元）
drop view if exists v_game_salary_min_max_mean;
create view v_game_salary_min_max_mean as
with p as
(select
  *,(case
      when unit = 1000 then
        cast(substring_index(
          substring_index(providesalary_text,'千/月',1),'-',1
        ) as decimal(6,2)) * unit
      when unit = 10000 then
        cast(substring_index(
          substring_index(providesalary_text,'万/月',1),'-',1
        ) as decimal(6,2)) * unit
      when unit = 833 then
        cast(substring_index(
          substring_index(providesalary_text,'万/年',1),'-',1
        ) as decimal(6,2)) * unit
    end
  ) as salary_min,
  (case
      when unit = 1000 then
        cast(substring_index(
          substring_index(providesalary_text,'千/月',1),'-',-1
        ) as decimal(6,2)) * unit
      when unit = 10000 then
        cast(substring_index(
          substring_index(providesalary_text,'万/月',1),'-',-1
        ) as decimal(6,2)) * unit
      when unit = 833 then
        cast(substring_index(
          substring_index(providesalary_text,'万/年',1),'-',-1
        ) as decimal(6,2)) * unit
    end
  ) as salary_max
from v_game_salary_unit)
select
  *,cast((salary_min + salary_max)/2 as decimal(10,2))as salary_mean
from p;
select * from v_game_salary_min_max_mean;

-- 10. 工作年限与平均薪资的关系
drop view if exists v_game_workyear_salary;
create view v_game_workyear_salary as
select
      workyear as '工作年限',
      avg(salary_mean) as '平均薪资'
from   v_game_salary_min_max_mean
group by workyear
order by length(workyear),workyear;
select * from v_game_workyear_salary;

-- 11. 企业类型与平均薪资的关系
drop view if exists v_game_companytype_salary;
create view v_game_companytype_salary as
select
      companytype_text as '企业类型',
      avg(salary_mean) as '平均薪资'
from   v_game_salary_min_max_mean
group by companytype_text
order by avg(salary_mean) desc;
select * from v_game_companytype_salary;

-- 12. 岗位核心技能点分析（出现频数 top 30）
drop view if exists v_game_skill_quantity;
create view v_game_skill_quantity as
select
      skill,
      count(*) as quantity
from skill_table as st
inner join v_game_clean as v
on v.parse2_job_detail like concat('%',st.skill,'%')
group by st.skill order by quantity desc
limit 30;

-- 13. 技能点出现频率
drop view if exists v_game_skill;
create view v_game_skill as
select
     skill as '技能点',
     quantity as '出现频数',
     concat(cast(quantity/total_quantity * 100 as decimal(4,2)),'%') as '出现频率'
from v_game_skill_quantity as f1,
     (select count(*) as total_quantity from v_game_clean) as f2;
select * from v_game_skill;


-- =====================================================================
-- 第二部分：operator 表（运维岗位）
-- 与 game 部分结构完全一致，仅三处不同：
--   ① 表名 game -> operator
--   ② 视图名前缀 v_game_* -> v_operator_*
--   ③ 岗位筛选 like '%游戏%' -> like '%运维%'
-- =====================================================================

-- 1. 清洗空值
drop view if exists v_operator_clean_null;
create view v_operator_clean_null as
select *
from operator
where
job_href is not null and job_href != '' and
job_name is not null and job_name != '' and
company_href is not null and company_href != '' and
company_name is not null and company_name != '' and
providesalary_text is not null and providesalary_text != '' and
workarea is not null and workarea != '' and
workarea_text is not null and workarea_text != '' and
companytype_text is not null and companytype_text != '' and
degreefrom is not null and degreefrom != '' and
workyear is not null and workyear != '' and
updatedate is not null and updatedate != '' and
issuedate is not null and issuedate != '' and
parse2_job_detail is not null and parse2_job_detail != '';
select count(*) as operator_clean_null from v_operator_clean_null;

-- 2. 去重（公司+岗位，保留最新发布）
drop view if exists v_clean_operator_distinct;
create view v_clean_operator_distinct as
with p as
(select
  *,row_number() over (partition by company_name,job_name order by issuedate desc) as row1
  from v_operator_clean_null)
select
  id,job_href,job_name,company_href,company_name,providesalary_text,workarea,workarea_text,updatedate,companytype_text,degreefrom,workyear,issuedate,parse2_job_detail
from p
where row1 = 1;
select count(*) as operator_distinct from v_clean_operator_distinct;

-- 3. 限制地区（北上广深）以及去除 null
drop view if exists v_operator_clean_workplace;
create view v_operator_clean_workplace as
with p as
(select
  *,(case
       when workarea_text like '%北京%' then '北京'
       when workarea_text like '%上海%' then '上海'
       when workarea_text like '%广州%' then '广州'
       when workarea_text like '%深圳%' then '深圳'
   end) as workplace
 from v_clean_operator_distinct)
select
  *
from p where workplace is not null;
select count(*) as operator_workplace from v_operator_clean_workplace;

-- 4. 过滤周边岗位（operator 表对应筛选“运维”岗位）
drop view if exists v_operator_clean_jobname;
create view v_operator_clean_jobname as
select *
from v_operator_clean_workplace
where job_name like '%运维%';
select count(*) as operator_jobname from v_operator_clean_jobname;

-- 5. 汇总视图
drop view if exists v_operator_clean;
create view v_operator_clean as
(select * from v_operator_clean_jobname);
select count(*) as operator_clean from v_operator_clean;

-- 6. 市场（城市）需求分析
drop view if exists v_operator_market_demand;
create view v_operator_market_demand as
select
      workplace as '城市',
      sum(degreefrom) as '招聘总数',
      count(*) as '职位数目'
from v_operator_clean
group by workplace;
select * from v_operator_market_demand;

-- 7. 市场量分析以及企业类型分布
drop view if exists v_operator_companytype_degree;
create view v_operator_companytype_degree as
select
  companytype_text as '企业类型',
  degreefrom as '招聘量',
  concat(cast(degreefrom/sum_degreefrom * 100 as decimal(4,2)),'%')  as '招聘占比'
from
(select
      companytype_text,sum(degreefrom) as degreefrom
from
  v_operator_clean
group by
  companytype_text
order by
  degreefrom desc) f1,
(select sum(degreefrom) as sum_degreefrom from v_operator_clean) f2;
select * from v_operator_companytype_degree;

-- 8. 薪资单位换算（万/月=10000，千/月=1000，万/年=833）
drop view if exists v_operator_salary_unit;
create view v_operator_salary_unit as
select * ,
       (case when providesalary_text like '%万/月%' then 10000
             when providesalary_text like '%千/月%' then 1000
             when providesalary_text like '%万/年%' then 833
        end
       ) as unit
from v_operator_clean;
select * from v_operator_salary_unit;

-- 9. 薪资最低/最高/平均（统一换算成月薪，单位：元）
drop view if exists v_operator_salary_min_max_mean;
create view v_operator_salary_min_max_mean as
with p as
(select
  *,(case
      when unit = 1000 then
        cast(substring_index(
          substring_index(providesalary_text,'千/月',1),'-',1
        ) as decimal(6,2)) * unit
      when unit = 10000 then
        cast(substring_index(
          substring_index(providesalary_text,'万/月',1),'-',1
        ) as decimal(6,2)) * unit
      when unit = 833 then
        cast(substring_index(
          substring_index(providesalary_text,'万/年',1),'-',1
        ) as decimal(6,2)) * unit
    end
  ) as salary_min,
  (case
      when unit = 1000 then
        cast(substring_index(
          substring_index(providesalary_text,'千/月',1),'-',-1
        ) as decimal(6,2)) * unit
      when unit = 10000 then
        cast(substring_index(
          substring_index(providesalary_text,'万/月',1),'-',-1
        ) as decimal(6,2)) * unit
      when unit = 833 then
        cast(substring_index(
          substring_index(providesalary_text,'万/年',1),'-',-1
        ) as decimal(6,2)) * unit
    end
  ) as salary_max
from v_operator_salary_unit)
select
  *,cast((salary_min + salary_max)/2 as decimal(10,2))as salary_mean
from p;
select * from v_operator_salary_min_max_mean;

-- 10. 工作年限与平均薪资的关系
drop view if exists v_operator_workyear_salary;
create view v_operator_workyear_salary as
select
      workyear as '工作年限',
      avg(salary_mean) as '平均薪资'
from   v_operator_salary_min_max_mean
group by workyear
order by length(workyear),workyear;
select * from v_operator_workyear_salary;

-- 11. 企业类型与平均薪资的关系
drop view if exists v_operator_companytype_salary;
create view v_operator_companytype_salary as
select
      companytype_text as '企业类型',
      avg(salary_mean) as '平均薪资'
from   v_operator_salary_min_max_mean
group by companytype_text
order by avg(salary_mean) desc;
select * from v_operator_companytype_salary;

-- 12. 岗位核心技能点分析（出现频数 top 30）
drop view if exists v_operator_skill_quantity;
create view v_operator_skill_quantity as
select
      skill,
      count(*) as quantity
from skill_table as st
inner join v_operator_clean as v
on v.parse2_job_detail like concat('%',st.skill,'%')
group by st.skill order by quantity desc
limit 30;

-- 13. 技能点出现频率
drop view if exists v_operator_skill;
create view v_operator_skill as
select
     skill as '技能点',
     quantity as '出现频数',
     concat(cast(quantity/total_quantity * 100 as decimal(4,2)),'%') as '出现频率'
from v_operator_skill_quantity as f1,
     (select count(*) as total_quantity from v_operator_clean) as f2;
select * from v_operator_skill;


-- =====================================================================
-- 第三部分：三张表各阶段行数对比（data / game / operator）
-- =====================================================================
select 'data' as 表名,
       (select count(*) from v_data_clean_null) as 清洗空值后,
       (select count(*) from v_clean_data_distinct) as 去重后,
       (select count(*) from v_data_clean_workplace) as 限城市后,
       (select count(*) from v_data_clean) as 最终分析集
union all
select 'game',
       (select count(*) from v_game_clean_null),
       (select count(*) from v_clean_game_distinct),
       (select count(*) from v_game_clean_workplace),
       (select count(*) from v_game_clean)
union all
select 'operator',
       (select count(*) from v_operator_clean_null),
       (select count(*) from v_clean_operator_distinct),
       (select count(*) from v_operator_clean_workplace),
       (select count(*) from v_operator_clean);
