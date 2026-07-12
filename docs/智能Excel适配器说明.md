# 智能 Excel 适配器说明

## 定位

当前适配器是“规则识别版”，不是大模型 AI 版。它通过字段别名词典、表头识别、样例行扫描、宽表/长表判断，把外部 Excel 转换成系统已有导入功能可识别的标准模板。

适配器只做：

- 读取 Excel
- 识别工作表类型
- 推断字段映射
- 转换学生导入模板
- 转换成绩导入模板
- 生成课程清单
- 生成错误清单和转换报告

适配器不做：

- 不写数据库
- 不调用学生导入 confirm
- 不调用成绩导入 confirm
- 不调用外部 AI API
- 不接入 DeepSeek
- 不修改原始 Excel

## 支持的表格类型

### 1. 学生基础信息表

典型字段：

- 学号、学生编号、学生ID、学籍号、编号
- 姓名、学生姓名
- 班级、班别、行政班
- 年级、学校、校区、性别、手机号、用户名、初始密码

输出：

- `students_import_ready.xlsx`

### 2. 成绩长表

典型字段：

- 学号、姓名、班级
- 课程编号、课程名称、科目、学科
- 分数、成绩、考试成绩
- 考试日期、考试批次、学期

输出：

- `students_import_ready.xlsx`
- `scores_import_ready.xlsx`
- `courses_required.xlsx`

### 3. 成绩宽表

典型字段：

- 学号、姓名、班级、年级
- 语文、数学、英语、物理、化学、生物、历史、地理、政治、信息技术、计算机、计算机基础
- 也支持 `语文成绩`、`数学成绩`、`英语成绩` 这类列名

输出：

- 学生信息拆到 `students_import_ready.xlsx`
- 单科成绩转成长表，写入 `scores_import_ready.xlsx`
- 课程清单写入 `courses_required.xlsx`

### 4. 混合表

一个表同时包含学生信息和多科成绩时，按混合表处理，自动拆分学生、成绩和课程。

### 5. 统计表

班级统计、科目统计这类表通常只有平均分、最高分、最低分、及格率等派生字段。适配器会识别并记录到报告，不生成导入成绩。

## 字段别名

### 学生字段

| 标准字段 | 支持别名 |
|----------|----------|
| student_id | 学号、学生编号、学生ID、学籍号、编号、id、stu_id、student_id、student_no |
| real_name | 姓名、学生姓名、name、real_name、student_name |
| class_name | 班级、班别、行政班、年级班级、class、class_name |
| grade | 年级、grade |
| school_name | 学校、校区、school、school_name |
| gender | 性别、gender |
| phone | 手机号、电话、phone、mobile |
| username | 用户名、username、login_name |
| password | 密码、初始密码、password |

### 成绩字段

| 标准字段 | 支持别名 |
|----------|----------|
| course_id | 课程编号、课程号、course_id |
| course_name | 课程名称、科目、学科、subject、course_name |
| score | 分数、成绩、考试成绩、score |
| exam_date | 考试日期、日期、exam_date |
| exam_batch | 考试批次、批次、考试名称、考试类型、exam_batch |
| term | 学期、学年、term |

### 学科列映射

| 学科列 | course_id |
|--------|-----------|
| 语文 | CHN01 |
| 数学 | MATH01 |
| 英语 | ENG01 |
| 物理 | PHY01 |
| 化学 | CHEM01 |
| 生物 | BIO01 |
| 历史 | HIS01 |
| 地理 | GEO01 |
| 政治 | POL01 |
| 信息技术 / 计算机 / 计算机基础 | CS01 |

非预置中文课程会生成稳定课程编号，例如 `C89220`，并写入 `courses_required.xlsx`，用户需要先在课程管理中创建或确认这些课程。

## 输出文件

默认脚本会扫描：

```text
Score test/
```

并输出到：

```text
Score test/converted/
```

生成文件：

| 文件 | 说明 |
|------|------|
| students_import_ready.xlsx | 学生基础信息标准导入模板 |
| scores_import_ready.xlsx | 成绩标准导入模板 |
| courses_required.xlsx | 转换后需要存在的课程清单 |
| conversion_errors.xlsx | 错误行、警告行和无法直接导入的值 |
| 真实数据集转换报告.md | 每个文件和工作表的识别、映射、统计与导入建议 |

## 默认补齐规则

- 缺少学号但有姓名/班级时，生成稳定学号 `S0001`、`S0002`。
- 缺少姓名时，用学号作为姓名占位，并写入错误/警告报告。
- 缺少班级时，用 `未分班` 占位，并写入错误/警告报告。
- 缺少用户名时，默认等于学号。
- 缺少初始密码时，默认 `123456`。
- 缺少考试日期时，默认 `2026-06-20`。
- 缺少考试批次时，默认 `数据集测试`；如果工作表标题包含考试名称，则优先使用标题。
- 缺少学期时，默认 `2025-2026-2`。

## 分数规则

当前成绩导入标准要求分数为 `0-100`。

- 空分数不导入。
- 非数字不导入。
- 超出 0-100 的值不导入，并写入 `conversion_errors.xlsx`。
- 总分、平均分、排名、等级、评语等派生字段不写入成绩模板。

## 使用命令

```bash
cd "<PROJECT_ROOT>"
python backend/scripts/convert_score_test_excels.py
```

如需指定目录：

```bash
python backend/scripts/convert_score_test_excels.py --input-dir "<PROJECT_ROOT>\Score test" --output-dir "<PROJECT_ROOT>\Score test\converted"
```

## 推荐导入顺序

1. 管理员进入“用户管理 → 批量导入学生”，导入 `students_import_ready.xlsx`。
2. 导入后确认用户管理中出现学生。
3. 确认成绩查询中的班级候选项出现真实班级。
4. 打开 `courses_required.xlsx`，检查课程是否已存在。
5. 不存在的课程先在管理员课程管理中手动新增。
6. 教师或管理员进入“成绩录入 → 批量导入成绩”，导入 `scores_import_ready.xlsx`。
7. 导入后测试成绩查询、统计分析、预警名单和 AI 学情分析。

## 后续优化

- 后续可增加管理后台“字段映射确认”界面；当前规则识别已经支持宽表、长表、混合表、K12 课程白名单和错误行 Excel。

## 导入批次账本

适配器仍只生成标准模板，不写数据库。模板经过现有 preview/confirm 后，confirm 会生成独立 `import_batch_id`，并记录安全快照。管理员可在“导入批次”页面查看及执行快照保护的安全撤销。密码、密码哈希、Token、API Key 不进入账本。
- 增加课程批量导入，直接处理 `courses_required.xlsx`。
- 针对不同满分制支持比例换算，例如 150 分制转换为 100 分制，但需要业务确认。
- 可选增加 AI 辅助字段识别，但不作为当前依赖，且 API Key 必须只放在后端。
