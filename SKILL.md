---
name: 拉磨也要舒服拉
description: 程序员职场 Intelligence Skill - 专为技术岗位（Go/Java/AI/后端/Infra/大模型）打造的求职决策助手
---

# 拉磨也要舒服拉

> 程序员职场 Intelligence Skill —— 专为技术岗位打造的求职决策助手。

## 定位

**当前版本聚焦程序员岗位，优先把技术岗位职场 Intelligence 做深，而不是泛化所有行业。**

重点服务：
- 软件工程师（Go/Java/Python/C++/Rust）
- AI 工程师（大模型/推荐/NLP/CV）
- 后端开发
- Infra / 平台工程
- 全栈开发
- 大模型相关岗位

## 核心能力

### 0. 简历 PDF 解析
自动从 PDF 简历中提取文本，支持四级回退：

| 优先级 | 方法 | 适用场景 | 依赖 |
|:--:|------|----------|------|
| 1 | PyPDF2 | 文字型 PDF | PyPDF2（自动安装） |
| 2 | pdfplumber | 表格/复杂布局 | pdfplumber（自动安装） |
| 3 | pymupdf | 中文编码特殊字体 | pymupdf（自动安装） |
| 4 | OCR | 图片型 PDF | Tesseract + pymupdf + PIL |

**使用方式**：
```bash
python <skill_dir>/extract_resume.py <pdf_path>
```

**自动安装**：脚本会自动检测并安装缺失的 Python 包。

**OCR 说明**（仅图片型 PDF 需要）：
- 安装 Tesseract：`winget install UB-Mannheim.TesseractOCR`
- 需要中文语言包：`chi_sim.traineddata`
- 脚本会自动查找 Tesseract 路径和语言包

### 1. 公司与岗位风险分析
- WLB（工作生活平衡）
- 管理风险
- 裁员风险
- 技术成长性
- 稳定性

### 2. JD Intelligence
- 技术栈提取
- 岗位真实强度
- 缝合岗识别（岗位脏度）
- 岗位真实级别分析
- 简历匹配度

### 3. Interview Intelligence
- 高频技术问题
- 系统设计倾向
- Redis / MQ / 分布式等高频主题
- 项目深挖程度
- 算法难度
- 面试风格推断
- 团队类型推断

### 4. 程序员黑话 Signal Engine
识别技术岗位常见黑话，映射为真实风险：

| 黑话 | 真实含义 | 风险等级 |
|------|----------|:--:|
| owner 意识 | 职责不清，可能甩锅 | 🔴 高 |
| 节奏快 | 可能加班 | 🟡 中 |
| 高成长 | 可能不稳定 | 🟡 中 |
| 自驱 | 缺乏指导 | 🟡 中 |
| 扁平化 | 管理混乱 | 🟡 中 |
| 抗压能力 | 高强度工作 | 🔴 高 |
| 快速响应 | 随时待命 | 🔴 高 |
| 创业心态 | 画饼 | 🟡 中 |

## 使用方式

### 基础分析
```bash
python <skill_dir>/search_jobs.py "<简历路径>" "<公司名>" "<岗位名>" [--avoid-exam]
```

### 部门级分析
```bash
python <skill_dir>/search_jobs.py "<简历路径>" "<公司名>" "<部门>" "<岗位名>" [--avoid-exam]
```

### 示例
```bash
# 分析腾讯 Golang 后端岗位
python search_jobs.py "D:\Golang-陈子异.pdf" "腾讯" "Golang开发" --avoid-exam

# 分析小红书电商部大模型岗位
python search_jobs.py "D:\Golang-陈子异.pdf" "小红书" "电商部" "大模型开发" --avoid-exam
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
  "detailed_signals": {
    "wlb": [
      {"signal": "996", "weight": -2.0, "type": "negative"},
      {"signal": "加班多", "weight": -1.5, "type": "negative"},
      {"signal": "双休", "weight": 1.5, "type": "positive"}
    ],
    "stability": [
      {"signal": "上市公司", "weight": 1.5, "type": "positive"}
    ],
    "growth": [
      {"signal": "增长强劲", "weight": 2.0, "type": "positive"}
    ],
    "perks": [
      {"signal": "免费三餐", "weight": 1.5, "type": "positive"}
    ]
  },
  "jd_analysis": {
    "tech_stack": ["Go", "微服务"],
    "risks": [
      {"type": "高强度", "evidence": ["抗压能力", "能承受高强度工作"]},
      {"type": "职责不清", "evidence": ["owner意识", "自驱力"]}
    ],
    "job_dirtiness": {"job_type": "专精", "workload_risk": "low"},
    "job_level": {"level": "高级", "is_real_level": true}
  },
  "resume_match": {
    "match_score": 80.0,
    "matched_skills": ["go", "mysql", "redis"],
    "missing_skills": ["微服务"]
  },
  "interview_intelligence": {
    "interview_rounds": ["一面", "二面", "HR面"],
    "coding_difficulty": "中等",
    "project_deep_dive": true,
    "system_design_focus": ["高并发", "分布式"],
    "tech_stack_mentioned": ["Go", "Redis", "MySQL"],
    "interview_style": ["偏算法", "偏系统设计"],
    "team_type": "基础设施团队"
  }
}
```

### Markdown（给人看）
报告保存到 `D:\GoProject\src\superAgent\reports\<公司名>-<岗位名>-分析报告.md`

包含 7 个章节：
1. 综合评估（含评分详情表 + 加减分明细）
2. 风险详情（负面/正面证据数量、状态）
3. 技术匹配详情（技能栈、匹配度、岗位详情）
4. 数据来源（各来源数量和占比）
5. JD 风险分析
6. 综合建议（核心指标、需要确认的问题）
7. 面试智能分析（风格、难度、问题、团队类型）

#### 加减分明细示例
```
WLB（工作生活平衡）：基础5分
  - 996（-2.0分）
  - 加班多（-1.5分）
  + 双休（+1.5分）
  = 3.0分

福利（生活福利）：0-5分
  + 免费三餐（+1.5分）
  + 下午茶（+1.0分）
  + 健身房（+1.0分）
  = 4.5分
```

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

## 后续扩展

预留扩展层，为未来支持更多岗位类型：
- `industry_profile` - 行业画像
- `signal_profile` - 风险信号库
- `interview_profile` - 面试特征库

## 依赖

- Python 3.10+
- Playwright (`pip install playwright`)
- Chrome/Edge 浏览器

## License

MIT
