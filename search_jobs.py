"""
City-based job discovery: find the best companies for your profile in a target city.
Usage: python search_jobs.py <resume_path_or_text> <city> <position> [--salary-min N] [--salary-max N] [--industry X]

Outputs ranked JSON with company scores across 6 dimensions.
"""

import sys
import json
import asyncio
import re
import os
import subprocess
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    print(json.dumps({"error": "playwright not installed. Run: pip install playwright && python -m playwright install chromium"}))
    sys.exit(1)


def extract_skills_from_resume(resume_text: str) -> dict:
    """Extract key skills from resume text."""
    skills = {
        "languages": [],
        "frameworks": [],
        "databases": [],
        "devops": [],
        "yoe": 0,
    }

    text_lower = resume_text.lower()
    text = resume_text

    # Languages
    for lang in ["Go", "Golang", "Python", "Java", "C++", "Rust", "TypeScript", "JavaScript"]:
        if lang.lower() in text_lower:
            skills["languages"].append(lang)

    # Frameworks
    for fw in ["Gin", "Go-zero", "Kratos", "Echo", "gRPC", "Spring", "Django", "FastAPI"]:
        if fw.lower() in text_lower:
            skills["frameworks"].append(fw)

    # Databases
    for db in ["MySQL", "Redis", "PostgreSQL", "MongoDB", "Elasticsearch", "Kafka"]:
        if db.lower() in text_lower:
            skills["databases"].append(db)

    # DevOps
    for dev in ["Docker", "Kubernetes", "K8s", "CI/CD", "Jenkins", "Prometheus"]:
        if dev.lower() in text_lower:
            skills["devops"].append(dev)

    # YOE estimation
    yoe_match = re.search(r'(\d+)\s*年', text)
    if yoe_match:
        skills["yoe"] = int(yoe_match.group(1))

    return skills


def load_resume(path_or_text: str) -> str:
    """Load resume from file or use text directly."""
    if os.path.exists(path_or_text):
        # Try to extract with bundled script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        extractor = os.path.join(script_dir, "extract_resume.py")
        if os.path.exists(extractor):
            try:
                result = subprocess.run(
                    [sys.executable, extractor, path_or_text],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except Exception:
                pass

        # Fallback: try reading as text
        try:
            with open(path_or_text, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass

    # Assume it's resume text directly
    return path_or_text


async def search_jobs_playwright(page, city: str, position: str, salary_min: int = 0, salary_max: int = 0) -> list[dict]:
    """Search job listings on BOSS直聘 via DuckDuckGo."""
    jobs = []
    seen_companies = set()

    queries = [
        f"{city} {position} 招聘",
        f"{city} {position} 社招 薪资",
        f"{city} Go 后端 招聘",
    ]

    for query in queries:
        url = f"https://html.duckduckgo.com/html/?q={query}"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1500)

            items = await page.query_selector_all(".result")
            for item in items[:10]:
                try:
                    title_el = await item.query_selector(".result__title a")
                    title = await title_el.inner_text() if title_el else ""
                    snippet_el = await item.query_selector(".result__snippet")
                    snippet = await snippet_el.inner_text() if snippet_el else ""

                    # Extract company name from title/snippet
                    company = extract_company_name(title, snippet)
                    if not company or company in seen_companies:
                        continue
                    seen_companies.add(company)

                    # Extract salary from snippet
                    salary = extract_salary(snippet)

                    # Skip if salary is below min or above max
                    if salary:
                        mid = (salary[0] + salary[1]) / 2
                        if salary_min and mid < salary_min:
                            continue
                        if salary_max and mid > salary_max * 1.5:  # allow some over
                            continue

                    jobs.append({
                        "company": company,
                        "title": title.strip(),
                        "snippet": snippet.strip()[:500],
                        "salary_range": salary,
                        "source": "DuckDuckGo"
                    })
                except Exception:
                    continue
            await page.wait_for_timeout(800)
        except Exception:
            continue

    return jobs


def extract_company_name(title: str, snippet: str) -> str | None:
    """Extract company name from job listing."""
    known_companies = [
        "字节跳动", "腾讯", "阿里巴巴", "百度", "网易", "美团", "京东",
        "拼多多", "快手", "滴滴", "小红书", "B站", "bilibili", "携程",
        "蚂蚁集团", "华为", "小米", "OPPO", "vivo", "大疆", "蔚来",
        "理想汽车", "小鹏", "Shein", "Shopee", "米哈游", "莉莉丝",
        "完美世界", "昆仑万维", "搜狐", "新浪", "360",
        "陌陌", "探探", "Keep", "知乎", "得物", "唯品会",
        "同程", "去哪儿", "58同城", "贝壳", "汽车之家",
        "微众银行", "众安", "老虎证券", "富途",
        "Zoom", "微软", "亚马逊", "Google", "Apple",
    ]

    text = title + " " + snippet
    for c in known_companies:
        if c in text:
            return c
    return None


def extract_salary(text: str) -> list[int] | None:
    """Extract salary range from text. Returns [min, max] in K/month."""
    # Pattern: 20-30K / 20k-30k / 20-30k·16薪
    patterns = [
        r'(\d+)[kK]\s*[-−到]\s*(\d+)[kK]',
        r'(\d+)\s*[-−到]\s*(\d+)\s*[kK]',
        r'(\d+)K\s*[-−到]\s*(\d+)K',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return [int(m.group(1)), int(m.group(2))]
    return None


def score_company(job: dict, skills: dict) -> dict:
    """Score a company based on 6 dimensions. Returns scores and total."""
    scores = {
        "tech_match": 0,
        "salary": 0,
        "wlb": 0,
        "stability": 0,
        "growth": 0,
        "life_perks": 0,
    }

    # Tech match (30%): based on skills overlap
    if skills["languages"]:
        scores["tech_match"] = min(len(skills["languages"]) * 2 + len(skills["frameworks"]) + len(skills["databases"]), 10)

    # Salary (25%): normalize to 0-10
    salary = job.get("salary_range")
    if salary:
        mid = (salary[0] + salary[1]) / 2
        if mid >= 50:
            scores["salary"] = 10
        elif mid >= 40:
            scores["salary"] = 9
        elif mid >= 30:
            scores["salary"] = 8
        elif mid >= 25:
            scores["salary"] = 7
        elif mid >= 20:
            scores["salary"] = 6
        elif mid >= 15:
            scores["salary"] = 5
        else:
            scores["salary"] = 4
    else:
        scores["salary"] = 5  # unknown

    # WLB (20%) & Stability (15%) & Growth (10%) & Life perks (+bonus)
    # These require reputation search - set defaults, update later
    scores["wlb"] = 5
    scores["stability"] = 5
    scores["growth"] = 5
    scores["life_perks"] = 0

    # Weighted total
    total = (
        scores["tech_match"] * 0.30 +
        scores["salary"] * 0.25 +
        scores["wlb"] * 0.20 +
        scores["stability"] * 0.15 +
        scores["growth"] * 0.10 +
        scores["life_perks"] * 0.10  # bonus dimension
    )

    return {
        "scores": scores,
        "total": round(total, 1),
        "total_max": 10,
    }


# Reputation signals for top Chinese tech companies
COMPANY_REPUTATION = {
    "字节跳动": {
        "wlb": 4, "stability": 6, "growth": 9,
        "life_perks": 8, "note": "免费三餐+下午茶+房补+健身房, 加班较多, 晋升快, 有裁员",
    },
    "腾讯": {
        "wlb": 6, "stability": 8, "growth": 8,
        "life_perks": 8, "note": "早餐免费+班车+健身房, WLB中等, 游戏部门较稳, 福利好",
    },
    "阿里巴巴": {
        "wlb": 5, "stability": 7, "growth": 7,
        "life_perks": 7, "note": "食堂+下午茶+健身房, 卷度因部门而异, 福利完善",
    },
    "百度": {
        "wlb": 7, "stability": 7, "growth": 6,
        "life_perks": 6, "note": "相对不卷, 免费三餐, AI方向有成长, 老牌稳定",
    },
    "网易": {
        "wlb": 7, "stability": 8, "growth": 7,
        "life_perks": 9, "note": "免费四餐+班车+健身房+下午茶+按摩店, 猪场名不虚传, WLB好, 近期外包裁员",
    },
    "美团": {
        "wlb": 5, "stability": 7, "growth": 7,
        "life_perks": 6, "note": "食堂+下午茶, 部分部门加班多, 业务稳定, 福利中等",
    },
    "京东": {
        "wlb": 5, "stability": 7, "growth": 7,
        "life_perks": 6, "note": "食堂+下午茶+健身房, 加班较多, 物流业务稳, 福利较好",
    },
    "拼多多": {
        "wlb": 3, "stability": 6, "growth": 8,
        "life_perks": 5, "note": "食堂+零食, 加班严重, 薪资高, 成长快",
    },
    "快手": {
        "wlb": 5, "stability": 6, "growth": 7,
        "life_perks": 7, "note": "免费三餐+下午茶+健身房, 福利好, 有裁员传闻",
    },
    "滴滴": {
        "wlb": 6, "stability": 5, "growth": 6,
        "life_perks": 5, "note": "食堂, 近年有裁员调整, WLB中等",
    },
    "小红书": {
        "wlb": 6, "stability": 6, "growth": 8,
        "life_perks": 7, "note": "免费三餐+下午茶, 年轻化, 增长快, 福利不错",
    },
    "哔哩哔哩": {
        "wlb": 6, "stability": 6, "growth": 7,
        "life_perks": 7, "note": "免费三餐+下午茶+健身房+撸猫, 文化好, 年轻化",
    },
    "米哈游": {
        "wlb": 6, "stability": 9, "growth": 9,
        "life_perks": 9, "note": "免费三餐+下午茶+零食+健身房, 游戏行业顶薪, 不裁员, 福利天花板",
    },
    "华为": {
        "wlb": 4, "stability": 9, "growth": 7,
        "life_perks": 5, "note": "食堂+班车, 加班较多, 狼性文化, 稳定性高, 年终奖丰厚",
    },
    "蚂蚁集团": {
        "wlb": 5, "stability": 7, "growth": 8,
        "life_perks": 7, "note": "食堂+下午茶, 金融科技, 福利好, 上市预期",
    },
    "携程": {
        "wlb": 8, "stability": 7, "growth": 5,
        "life_perks": 6, "note": "相对不卷, 旅游行业, 稳定但增长慢, 办公环境好",
    },
    "得物": {
        "wlb": 6, "stability": 5, "growth": 7,
        "life_perks": 6, "note": "潮牌电商, 年轻人多, 增长中, 中等规模",
    },
    "唯品会": {
        "wlb": 7, "stability": 7, "growth": 4,
        "life_perks": 5, "note": "广州总部, WLB好, 增长放缓, 福利一般",
    },
}


def enrich_company(job: dict) -> dict:
    """Add reputation data to a company."""
    company = job.get("company", "")
    if company in COMPANY_REPUTATION:
        rep = COMPANY_REPUTATION[company]
        job["wlb"] = rep["wlb"]
        job["stability"] = rep["stability"]
        job["growth"] = rep["growth"]
        job["life_perks"] = rep["life_perks"]
        job["note"] = rep["note"]
    else:
        job["wlb"] = 5
        job["stability"] = 5
        job["growth"] = 5
        job["life_perks"] = 3
        job["note"] = "无预置数据，建议用精准分析深入了解"
    return job


async def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(json.dumps({"error": "Usage: python search_jobs.py <resume> <city> <position> [--salary-min N] [--salary-max N] [--industry X]"}))
        sys.exit(1)

    resume_path = args[0]
    city = args[1]
    position = args[2]

    salary_min = 0
    salary_max = 0
    industry = ""

    i = 3
    while i < len(args):
        if args[i] == "--salary-min" and i + 1 < len(args):
            salary_min = int(args[i + 1])
            i += 2
        elif args[i] == "--salary-max" and i + 1 < len(args):
            salary_max = int(args[i + 1])
            i += 2
        elif args[i] == "--industry" and i + 1 < len(args):
            industry = args[i + 1]
            i += 2
        else:
            i += 1

    # Load and parse resume
    resume_text = load_resume(resume_path)
    skills = extract_skills_from_resume(resume_text)

    print(f"[Discovery] {city} | {position} | Skills: {skills['languages']}", file=sys.stderr)

    output = {
        "city": city,
        "position": position,
        "salary_range": [salary_min, salary_max],
        "industry": industry,
        "skills_found": skills,
        "timestamp": datetime.now().isoformat(),
        "companies": [],
        "recommendations": [],
    }

    # Search for jobs
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN"
        )
        page = await ctx.new_page()

        jobs = await search_jobs_playwright(page, city, position, salary_min, salary_max)
        await browser.close()

    # Enrich and score
    for job in jobs:
        job = enrich_company(job)
        scoring = score_company(job, skills)
        # Update scores from reputation
        scoring["scores"]["wlb"] = job.get("wlb", 5)
        scoring["scores"]["stability"] = job.get("stability", 5)
        scoring["scores"]["growth"] = job.get("growth", 5)
        scoring["scores"]["life_perks"] = job.get("life_perks", 0)
        # Recalculate total
        scoring["total"] = round(
            scoring["scores"]["tech_match"] * 0.30 +
            scoring["scores"]["salary"] * 0.25 +
            scoring["scores"]["wlb"] * 0.20 +
            scoring["scores"]["stability"] * 0.15 +
            scoring["scores"]["growth"] * 0.10 +
            scoring["scores"]["life_perks"] * 0.10,
            1
        )

        output["companies"].append({
            "company": job["company"],
            "title": job["title"],
            "salary_range": job.get("salary_range"),
            "note": job.get("note", ""),
            "scores": scoring["scores"],
            "total": scoring["total"],
        })

    # Sort by total score
    output["companies"].sort(key=lambda x: x["total"], reverse=True)

    # Top 5 recommendations + next 5 backup
    top5 = output["companies"][:5]
    backup5 = output["companies"][5:10]
    output["recommendations"] = top5
    output["backups"] = backup5

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
