---
name: 拉磨也要舒服拉
description: Use when the user wants to evaluate job opportunities - analyzing resume fit with target companies, researching company reputation, collecting interview experiences
---

# 拉磨也要舒服拉

> 互联网打工人的求职决策助手。不将就，拉磨也要挑个好磨。

## 功能概览

| 功能 | 说明 |
|------|------|
| 精准岗位匹配 | 分析你适不适合该公司的该岗位 |
| JD 分析 | 提取技术栈、识别风险信号、岗位脏度 |
| 简历匹配度 | 对比简历技能 vs JD 要求 |
| 风险标签 | 6核心维度 + 证据数量 + 冲突检测 |
| 面经整理 | 面试流程、高频考点、薪资参考 |
| Markdown 报告 | 生成给人看的详细文档 |

## 使用方式

### 基础用法
```bash
python <skill_dir>/search_jobs.py "<简历路径>" "<公司名>" "<岗位名>" [--avoid-exam]
```

### 部门级分析
```bash
python <skill_dir>/search_jobs.py "<简历路径>" "<公司名>" "<部门>" "<岗位名>" [--avoid-exam]
```

### 示例
```bash
# 分析腾讯 Golang 开发岗位
python search_jobs.py "D:\Golang-陈子异.pdf" "腾讯" "Golang开发" --avoid-exam

# 分析小红书电商部 Golang 开发
python search_jobs.py "D:\Golang-陈子异.pdf" "小红书" "电商部" "Golang开发" --avoid-exam
```

## 输出格式

### JSON（给程序/AI 用）
```json
{
  "overall_score": 5.5,
  "wlb_score": 2.0,
  "growth_score": 5.0,
  "stability_score": 6.0,
  "perks_score": 2.9,
  "tech_match_score": 10,
  "risk_tags": ["WLB风险", "稳定风险"],
  "risk_details": [
    {
      "dimension": "WLB",
      "label": "WLB风险",
      "evidence_count": 10,
      "positive_count": 3,
      "controversial": true
    }
  ],
  "controversial": true,
  "summary": "腾讯 一般，总分5.5/10，加班较多",
  "confidence": 1.0,
  "jd_analysis": {
    "tech_stack": ["Go", "微服务"],
    "risks": [],
    "job_dirtiness": {"job_type": "专精", "workload_risk": "low"}
  },
  "resume_match": {
    "match_score": 50.0,
    "matched_skills": ["go"],
    "missing_skills": ["微服务"]
  }
}
```

### Markdown（给人看）
报告保存到 `D:\GoProject\src\superAgent\reports\<公司名>-<岗位名>-分析报告.md`

包含 7 个章节：
1. 综合评估
2. 风险提示
3. 技术匹配分析
4. 数据来源
5. JD 风险分析
6. 综合建议
7. 面经与面试准备

## 评分体系

| 维度 | 权重 | 考察内容 |
|------|:--:|------|
| 技术匹配 | 30% | 技能栈、经验年数、学历 |
| WLB | 25% | 加班、双休、弹性、工作强度（±3 cap） |
| 生活福利 | 20% | 食堂/包餐、下午茶、健身房、班车（0-5 cap） |
| 稳定性 | 15% | 裁员历史、公司规模、融资（±3 cap） |
| 成长空间 | 10% | 晋升、技术氛围、核心业务线（±3 cap） |

## 信源权重

| 来源类型 | 权重 | 说明 |
|----------|:--:|------|
| JD | 1.0 | 招聘信息（官方） |
| 官方网站 | 0.95 | 公司官网 |
| 面经网站 | 0.85 | 牛客、力扣 |
| 员工评价 | 0.8 | 知乎、脉脉 |
| 匿名论坛 | 0.7 | V2EX |
| 新闻媒体 | 0.6 | 36氪等 |

## 风险标签系统（6 核心维度）

| 维度 | 说明 | 示例信号 |
|------|------|----------|
| WLB | 工作生活平衡 | 996、大小周、高强度、push |
| 管理风险 | 管理问题 | PUA、看组、朝令夕改 |
| 成长性 | 职业发展 | 晋升慢、天花板、技术落后 |
| 稳定性 | 公司稳定 | 裁员、HC冻结、欠薪 |
| 薪资 | 薪酬问题 | 拖欠工资、薪资低 |
| 面试难度 | 面试门槛 | 面试难、笔试难、hard |

### 冲突检测
当正反评价同时存在时，标记为 `controversial`，不强行下结论。

### 证据数量
每个风险标签带 `evidence_count`，降低幻觉风险。

## JD 分析功能

### JD 提取
- 技术栈（tech_stack）
- 岗位要求（requirements）
- 工作职责（responsibilities）

### JD 风险识别
识别危险信号：
- 抗压能力 → 高强度
- owner意识 → 职责不清
- 多线程 → 职责不清
- 快速响应 → 可能加班
- 创业心态 → 可能加班

### 岗位脏度
检测是否是"缝合岗"：
- 专精：单一技术栈
- 全栈：前后端
- 多面手：3+技术栈
- 缝合岗：4+技术栈

## 简历匹配度

对比简历技能 vs JD 要求：
```json
{
  "match_score": 50.0,
  "matched_skills": ["go"],
  "missing_skills": ["微服务"]
}
```

## 分析维度详解

### WLB（Work-Life Balance）
- **正面信号**：不加班(+2)、双休(+1.5)、准时下班(+1.5)、弹性(+1)、不卷(+1.5)
- **负面信号**：996(-2)、大小周(-1.5)、高强度(-1)、push(-1)、通宵(-2)

### 稳定性
- **正面信号**：国企(+2)、央企(+2.5)、上市(+1.5)、不裁员(+2)
- **负面信号**：裁员(-2)、倒闭(-3)、欠薪(-3)、HC冻结(-1.5)

### 成长性
- **正面信号**：增长强劲(+2)、晋升快(+1.5)、技术领先(+1)
- **负面信号**：晋升慢(-2)、天花板(-1)、技术落后(-1.5)

### 笔试难度（--avoid-exam 模式）
- **困难**：手撕、hard、动态规划、图论
- **简单**：没有笔试、免笔试、不考算法
- **惩罚**：简单=0，中等=-1，困难=-2.5

## 文件位置

| 文件 | 用途 |
|------|------|
| `search_jobs.py` | 主分析脚本 |
| `extract_resume.py` | 简历解析 |
| `search_company.py` | 公司风评搜索 |
| `search_interview.py` | 面经搜索 |
| `reports/*.json` | JSON 报告（程序用） |
| `reports/*.md` | Markdown 报告（人看） |
