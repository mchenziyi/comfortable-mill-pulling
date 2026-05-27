---
name: resume-company-evaluator
description: Use when the user wants to evaluate whether a company is worth applying to by analyzing their resume fit, researching company reputation across multiple platforms, and optionally collecting interview experiences
---

# Resume Company Evaluator

## Overview

Evaluate a target company and position by: (1) analyzing how well the user's resume matches the role, (2) researching company reputation and employee reviews from multiple platforms, (3) generating a structured report with a recommendation, and (4) optionally collecting interview questions and experiences if the user decides to apply.

## Configuration

At the start, ask the user for:

- **Resume file path** (e.g., `~/resume.pdf`, `./Golang-陈子异.pdf`) — if not provided, check common paths in the workspace
- **Company name**
- **Target position**

If the user has used this skill before, remind them of the last-used resume path and offer to reuse it.

## Workflow

### Stage 1: Resume Parsing

Read the resume file using the bundled `extract_resume.py` script:

```bash
python <skill_dir>/extract_resume.py <resume_path>
```

This script tries four extraction methods in order:
1. **PyPDF2** — fast, works for text-based PDFs
2. **pdfplumber** — better table/layout handling
3. **PyMuPDF (fitz)** — handles more Chinese font encodings
4. **OCR (pytesseract + pymupdf renderer)** — handles image-based/scanned PDFs (requires Tesseract system install)

The script auto-installs missing Python libraries if needed. If OCR is needed, ensure Tesseract is installed (`choco install tesseract` on Windows, `brew install tesseract` on macOS, `apt install tesseract-ocr tesseract-ocr-chi-sim` on Linux).

If all methods fail, ask the user to paste their resume content directly.

Once text is extracted, parse and summarize:
- Skills (languages, frameworks, tools)
- Work experience (years, roles, industries)
- Education background
- Project highlights
- Any stated career objectives

Present a brief summary to the user and confirm before proceeding.

### Stage 2: Position Fit Analysis

**Primary method: Use the bundled search script**

```bash
python <skill_dir>/search_company.py "<公司名>" "<岗位名>"
```

The script searches 12 queries including JD and position-specific terms. From the JSON output, extract the job descriptions found (especially from Boss直聘、猎聘、LearnKu etc.).

**Fallback: Manual search**

If the script is unavailable, search with these queries:
- "[公司名] [岗位名] 招聘 JD"
- "[公司名] [岗位名] 岗位要求"
- "site:liepin.com [公司名] [岗位名]"

Compare the resume against the job description point by point:
- **Hard skills match**: Which required skills does the candidate have? Which are missing?
- **Experience match**: Does YOE, industry background, role level align?
- **Education match**: Degree requirements met?
- **Overall score**: X/10 with explanation

### Stage 3: Company Reputation Research

**Primary method: Bundled Playwright search script**

Run the bundled `search_company.py` which uses a headless Chrome browser to bypass JS rendering and anti-crawling:

```bash
python <skill_dir>/search_company.py "<公司名>" "<岗位名>"
```

This script:
- Uses Playwright with system Chrome/Edge (no extra browser download needed)
- Searches Bing + DuckDuckGo with 13 targeted Chinese queries
- Tests direct access to 知乎、看准网、Boss直聘 etc.
- Fetches full page text of top results for deeper analysis
- Outputs structured JSON with search results + platform accessibility report

**Fallback: Web Search MCP**

If Playwright is not available or the script fails, fall back to environment search tools (Web Search MCP, Browser MCP, or the `webfetch` tool).

**Fallback: Manual mode**

If all automated methods fail, present the user with a list of search queries to run manually on their browser:

```
请手动在浏览器搜索以下关键词，并将结果反馈给我：
- [公司名] 怎么样 脉脉
- [公司名] 避雷 知乎
- [公司名] [岗位名] 薪资
- ...
```

Aggregate findings into categories:
- **Positive signals**: Good culture, fair pay, growth opportunities, WLB
- **Negative signals**: Layoffs, toxic culture, 996/加班 culture, delayed salary, bad management
- **Compensation info**: Salary range, bonus structure, benefits
- **Source reference**: Always include where each piece of information came from

### Stage 4: Generate Report

**Output both a conversational summary AND a Markdown file.**

Save the report to the current working directory: `reports/[公司名]-[岗位名]-分析报告.md`
(Replace special characters and spaces in the filename with hyphens)

**Report template:**

```markdown
# 📊 [公司名] [岗位名] 求职分析报告

> 分析时间：YYYY-MM-DD
> 目标岗位：[岗位名]
> 目标公司：[公司名]

---

## 一、岗位匹配度：X/10

### 1.1 目标岗位 JD 摘要
[从搜索结果中提取的岗位要求摘要]

### 1.2 简历匹配分析

| 维度 | 岗位要求 | 我的条件 | 匹配 |
|------|----------|----------|------|
| 技能 A | ... | ... | ✅/⚠️/❌ |
| ... | ... | ... | ... |

### 1.3 优势
- ...

### 1.4 差距与建议
- ...

---

## 二、公司风评调研

### 2.1 正面评价
| 评价内容 | 来源 |
|----------|------|
| ... | 脉脉/知乎/... |

### 2.2 负面评价 / 风险提示
| 评价内容 | 来源 | 风险等级 |
|----------|------|----------|
| ... | ... | 🔴🟡🟢 |

### 2.3 薪资福利参考
- 薪资范围：...
- 年终奖：...
- 五险一金：...
- 其他福利：...

### 2.4 加班与工作环境
- ...

---

## 三、综合建议

**推荐等级：🏆 强烈推荐 / 👍 可以考虑 / ⚠️ 谨慎 / 🚫 不推荐**

**理由：**
[3-5 条总结性理由]

---

## 四、面经与面试题（待搜集）

> 此部分为可选内容。如果确认投递，请告知，我将为你搜集该岗位的面经和面试题。
```

After generating the report, present the key findings in conversation and ask:

> "报告已生成。是否需要我继续搜集 **[公司名] [岗位名]** 的面试题和面经？"

### Stage 5: Interview Preparation (Optional)

Only proceed if the user explicitly confirms.

**Primary method: Bundled interview search script**

```bash
python <skill_dir>/search_interview.py "<公司名>" "<岗位名>"
```

This script searches 8 interview-specific queries and fetches full page content from each result.

Alternatively, use `search_company.py` output (which already includes interview-related queries) and direct-fetch the most promising pages (职朋面经、职Q面试、V2EX、知乎).

**If scripts are unavailable**, search for:
- "[公司名] [岗位名] 面试题 / 面经 / 面试 真题"
- "[公司名] 面试流程 / 几轮面试 / 面试难度"
- "site:nowcoder.com [公司名] [岗位名]"

Aggregate by:
- **面试流程**: How many rounds, what types (phone screen, technical, system design, behavioral, HR)
- **面试真题**: Actual questions reported, organized by topic (algorithms, system design, language-specific, behavioral)
- **面试难度**: Overall difficulty rating and common pain points
- **准备建议**: Key areas to focus on based on collected experiences

Append findings to the report file under Section 4, and present a summary in conversation.

## Search Strategy Notes

- Always run platform-specific searches in parallel — they are independent
- For each search result, open the most relevant 3-5 pages for detailed reading
- Prioritize recent content (within 1-2 years) — company culture can change
- Cross-reference: one person's complaint may be an outlier; look for patterns across platforms
- If search returns no results for a platform, note it and move on — don't retry
- In China, platforms like 知乎、脉脉、小红书 may have more candid reviews than Glassdoor-style sites

## Report Storage

- Directory: `reports/` (create if not exists)
- Filename: `[公司名]-[岗位名]-分析报告.md`
- If filename conflicts, append `-2`, `-3`, etc.
