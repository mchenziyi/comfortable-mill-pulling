---
name: comfortable-mill-pulling
description: Use when the user wants to evaluate job opportunities - analyzing resume fit with target companies, researching company reputation, collecting interview experiences, or discovering the best matching companies in a target city
---

# 我想拉磨拉得舒服

> 互联网打工人的求职决策助手。不将就，拉磨也要挑个好磨。

## 两种模式

| | 🎯 精准分析 | 🔍 城市发现 |
|------|------|------|
| 触发 | "分析 网易 Go开发" | "杭州 找 Go后端 20-35K" |
| 目的 | 一家公司值不值得去 | 哪些公司值得投 |
| 输出 | 完整报告 + 面经 | Top 5 排名 + 关键指标 |
| 耗时 | 10-15 分钟 | 3-5 分钟 |

---

## 🔍 模式 B：城市发现

### 输入条件

用户提供：**城市 + 岗位 + 薪资范围**。可附加：公司规模、行业、远程偏好。

### 评分体系

| 维度 | 权重 | 考察内容 |
|------|:--:|------|
| 技术匹配 | 30% | 技能栈、经验年数、学历 |
| 薪酬福利 | 25% | 底薪、年终奖、五险一金、补助 |
| WLB | 20% | 加班、双休、弹性、工作强度 |
| 稳定性 | 15% | 裁员历史、公司规模、成立年限、融资 |
| 成长空间 | 10% | 晋升、技术氛围、核心业务线 |
| 🌟 生活福利 | +10% | 食堂/包餐、下午茶、午休、健身房、班车、零食柜 |

### 执行

```bash
python <skill_dir>/search_jobs.py "<简历路径>" "<城市>" "<岗位>" [--salary-min N] [--salary-max N]
```

### 输出格式

```
🏆 杭州 Go 后端 Top 5

#1 网易 有道 | 匹配 8.0 | 28-55K·18薪 | 综合 8.3
    WLB 7 · 免费四餐 · 猪场 · 近期外包裁员

#2 字节 飞书 | 匹配 7.5 | 30-50K·15薪 | 综合 7.8
    加班较多 · 福利好 · 晋升快

...

💡 输入 "分析 网易 Go开发" 可查看完整报告
```

---

## 🎯 模式 A：精准分析

### Configuration

首次使用时确认：
- 简历文件路径
- 公司名称
- 目标岗位

### Stage 1: 简历解析

```bash
python <skill_dir>/extract_resume.py <resume_path>
```

四级回退：PyPDF2 → pdfplumber → PyMuPDF → OCR（Tesseract）

### Stage 2: 岗位匹配

```bash
python <skill_dir>/search_company.py "<公司名>" "<岗位名>"
```

从 JSON 输出中提取 JD，逐项对比简历。输出匹配度 X/10。

### Stage 3: 风评搜索

同上 `search_company.py`，13 组搜索词覆盖所有维度。
回退方案：Web Search MCP → 手动搜索列表。

### Stage 4: 生成报告

保存到 `reports/[公司名]-[岗位名]-分析报告.md`

报告模板：
```markdown
# 📊 [公司名] [岗位名] 求职分析报告

## 一、公司概况
## 二、岗位匹配度：X/10
### 2.1 JD 摘要 | 2.2 匹配分析 | 2.3 优势 | 2.4 差距
## 三、公司风评调研
### 3.1 正面评价 | 3.2 负面评价 | 3.3 薪资福利 | 3.4 加班与文化
## 四、面经与面试题
### 4.1 面试流程 | 4.2 高频考点 | 4.3 真题
## 五、综合建议 — 推荐等级 + 理由
```

### Stage 5: 面经搜集（可选）

```bash
python <skill_dir>/search_interview.py "<公司名>" "<岗位名>"
```

或者直接从 `search_company.py` 的输出中拉取已知面经页面。

---

## 脚本列表

| 脚本 | 用途 | 依赖 |
|------|------|------|
| `extract_resume.py` | PDF 简历解析 | PyPDF2/pdfplumber/pymupdf/pytesseract |
| `search_company.py` | 公司风评 + JD 搜索 | Playwright + Chrome/Edge |
| `search_interview.py` | 面经面试题搜索 | Playwright + Chrome/Edge |
| `search_jobs.py` | 城市岗位发现 | Playwright + Chrome/Edge |

所有脚本自动安装缺失的 Python 包。

---

## 搜索策略

- 优先 Playwright 浏览器搜索（绕过 JS 渲染和反爬）
- 回退到环境 Web Search MCP
- 最后回退到用户手动搜索关键词列表
- 强调交叉验证，单一来源不可信

## 报告存储

- 目录：`reports/`
- 文件名：`[公司名]-[岗位名]-分析报告.md`
- 冲突时追加 `-2`、`-3`
