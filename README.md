# 我想拉磨拉得舒服

> 互联网打工人的 AI 求职决策助手。不将就，拉磨也要挑个好磨。

一个 opencode / Claude Code / Cursor 可用的 Skill。

## 两种模式

### 🔍 城市发现
"杭州 找 Go 后端 20-35K"
→ 自动搜索该城市最适合你的 Top 5 公司，按综合评分排名

### 🎯 精准分析
"分析 网易 Go 开发"
→ 深度分析一家公司：匹配度 + 全网风评 + 薪资 + 面经真题

## 评分体系

| 维度 | 权重 | 内容 |
|------|:--:|------|
| 技术匹配 | 30% | 技能栈、经验、学历 |
| 薪酬福利 | 25% | 底薪、年终奖、五险一金 |
| WLB | 20% | 加班、双休、弹性 |
| 稳定性 | 15% | 裁员、规模、年限 |
| 成长空间 | 10% | 晋升、技术氛围 |
| 🌟 生活福利 | +10% | 食堂、下午茶、午休、健身房 |

## 安装

```bash
git clone https://github.com/mchenziyi/comfortable-mill-pulling.git ~/.agents/skills/comfortable-mill-pulling
```

## 依赖

- Python 3.10+
- Playwright (`pip install playwright`)
- Chrome/Edge 浏览器
- Tesseract OCR（可选，用于图片型 PDF 简历）

## 示例

```
📂 reports/
├── 边锋集团-Golang开发工程师-分析报告.md
├── 字节跳动-AI-Agent开发-分析报告.md
└── 网易-Golang开发工程师-分析报告.md
```

## License

MIT
