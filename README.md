# Resume Company Evaluator

> AI 求职分析助手 —— 用你的简历 + 目标公司，自动分析匹配度、全网搜集风评、生成决策报告。

一个 opencode / Claude Code / Cursor 可用的 Skill，帮你评估一家公司值不值得去。

## 功能

1. **简历解析** —— 自动提取 PDF 简历中的技能、经验、项目（支持文本 + 图片型 PDF）
2. **岗位匹配** —— 搜索目标岗位 JD，逐项对比简历，输出匹配度评分
3. **风评搜索** —— 浏览器自动搜索脉脉、知乎、Boss直聘、牛客等平台评价
4. **报告生成** —— 结构化的 Markdown 分析报告（匹配度 + 正负面评价 + 薪资 + 推荐等级）
5. **面经搜集** —— 可选：搜索面试流程、真题、避坑指南

## 安装

```bash
# 下载到 skills 目录
git clone https://github.com/<your-username>/resume-company-evaluator.git ~/.agents/skills/resume-company-evaluator
```

目录结构：
```
~/.agents/skills/resume-company-evaluator/
├── SKILL.md              # 主文件，AI 工作流指引
├── extract_resume.py     # PDF 简历解析脚本
├── search_company.py     # 公司风评搜索脚本
└── search_interview.py   # 面经面试题搜索脚本
```

## 使用

在 opencode / Claude Code / Cursor 中对话：

```
帮我分析一下字节跳动，岗位是 Go 后端开发
```

Skill 会自动：
1. 读取你的简历（首次使用会询问简历文件路径）
2. 搜索岗位 JD 并对比匹配度
3. 全网搜索公司评价、薪资、加班情况
4. 生成 Markdown 报告并给出推荐等级
5. 询问是否需要搜集面经和面试题

## 依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| Python 3.10+ | 运行脚本 | 系统自带 |
| Playwright | 浏览器搜索 | `pip install playwright` |
| Chrome/Edge | 浏览器引擎 | 系统自带即可 |
| Tesseract OCR | 图片型 PDF 识别（可选） | `winget install tesseract` |

首次运行会自动安装缺失的 Python 包。

## 示例报告

```
reports/
├── 边锋集团-Golang开发工程师-分析报告.md
└── 字节跳动-AI-Agent开发-分析报告.md
```

报告包含：公司概况、岗位匹配度 X/10、正负面评价汇总、薪资分布、推荐等级、面经真题。

## 搜索原理

- 使用 Playwright 启动 headless Chrome，绕过 JS 渲染和反爬
- DuckDuckGo + Bing 双引擎中文搜索
- 直接抓取目标页面（知乎、脉脉、Boss直聘、猎聘等）获取详细内容
- 如果 Playwright 不可用，回退到环境自带的 Web Search MCP

## License

MIT
