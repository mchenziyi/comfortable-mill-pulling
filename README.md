# 我想拉磨拉得舒服

> 互联网打工人的 AI 求职决策助手。不将就，拉磨也要挑个好磨。

一个 opencode / Claude Code / Cursor 可用的 Skill。

## 功能

### 🎯 精准公司分析
"分析 小红书 Golang开发"
→ 深度分析一家公司：匹配度 + 全网风评 + 薪资 + 面经真题

## 评分体系

| 维度 | 权重 | 内容 |
|------|:--:|------|
| 技术匹配 | 30% | 技能栈、经验、学历 |
| WLB | 25% | 加班、双休、弹性（±3 cap） |
| 生活福利 | 20% | 食堂、下午茶、房补、远程（0-5 cap） |
| 稳定性 | 15% | 裁员、规模、融资（±3 cap） |
| 成长空间 | 10% | 晋升、技术氛围（±3 cap） |

## 安装

```bash
git clone https://github.com/mchenziyi/comfortable-mill-pulling.git ~/.agents/skills/comfortable-mill-pulling
```

## 依赖

- Python 3.10+
- Playwright (`pip install playwright`)
- Chrome/Edge 浏览器
- Tesseract OCR（可选，用于图片型 PDF 简历）

## 使用

```bash
# 精准公司分析
python ~/.agents/skills/comfortable-mill-pulling/search_jobs.py "<简历路径>" "<公司名>" [--avoid-exam]

# 简历解析
python ~/.agents/skills/comfortable-mill-pulling/extract_resume.py <简历路径>

# 公司风评搜索
python ~/.agents/skills/comfortable-mill-pulling/search_company.py "<公司名>" "<岗位名>"

# 面经搜索
python ~/.agents/skills/comfortable-mill-pulling/search_interview.py "<公司名>" "<岗位名>"
```

## 特点

- **完全实时搜索**：不依赖预置数据库，每次分析都是最新的
- **细粒度情感分析**：加权正则匹配，±3 分浮动
- **笔试难度分析**：`--avoid-exam` 标识规避难笔试公司
- **面试策略生成**：根据公司特点定制面试准备

## 示例

```
📂 reports/
├── 小红书-Golang开发-分析报告.md
├── 网易-Golang开发-分析报告.md
└── 字节跳动-AI-Agent开发-分析报告.md
```

## License

MIT
