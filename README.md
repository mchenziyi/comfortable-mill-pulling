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

| 黑话 | 真实含义 |
|------|----------|
| owner 意识 | 职责不清，可能甩锅 |
| 节奏快 | 可能加班 |
| 高成长 | 可能不稳定 |
| 自驱 | 缺乏指导 |
| 扁平化 | 管理混乱 |
| 抗压能力 | 高强度工作 |
| 快速响应 | 随时待命 |
| 创业心态 | 画饼 |

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
  "risk_details": [...],
  "detailed_signals": {
    "wlb": [
      {"signal": "996", "weight": -2.0, "type": "negative"},
      {"signal": "双休", "weight": 1.5, "type": "positive"}
    ]
  },
  "jd_analysis": {
    "tech_stack": ["Go", "微服务"],
    "job_dirtiness": {"job_type": "专精"},
    "job_level": {"level": "高级"}
  },
  "resume_match": {"match_score": 80.0},
  "interview_intelligence": {
    "coding_difficulty": "中等",
    "interview_style": ["偏算法", "偏系统设计"],
    "team_type": "基础设施团队"
  }
}
```

### Markdown（给人看）
报告包含 7 个章节：
1. 综合评估（含评分详情表 + 加减分明细）
2. 风险详情（负面/正面证据数量、状态）
3. 技术匹配详情（技能栈、匹配度、岗位详情）
4. 数据来源（各来源数量和占比）
5. JD 风险分析
6. 综合建议（核心指标、需要确认的问题）
7. 面试智能分析（风格、难度、问题、团队类型）

## 评分体系

| 维度 | 权重 | 考察内容 |
|------|:--:|------|
| 技术匹配 | 30% | 技能栈、经验年数、学历 |
| WLB | 25% | 加班、双休、弹性、工作强度（±3 cap） |
| 生活福利 | 20% | 食堂/包餐、下午茶、健身房、班车（0-5 cap） |
| 稳定性 | 15% | 裁员历史、公司规模、融资（±3 cap） |
| 成长空间 | 10% | 晋升、技术氛围、核心业务线（±3 cap） |

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
