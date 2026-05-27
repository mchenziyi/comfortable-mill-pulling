"""
Company review search using Playwright headless browser.
Usage: python search_company.py <company_name> <position> [--no-ocr]
Outputs search results as JSON to stdout.
"""

import sys
import json
import asyncio
import re
import time
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    print(json.dumps({"error": "playwright not installed. Run: pip install playwright"}))
    sys.exit(1)

SEARCH_QUERIES = [
    # Reputation
    "{company} 怎么样",
    "{company} 工作体验 员工评价",
    "{company} 值得去吗",
    # Negative signals
    "{company} 避雷",
    "{company} 裁员 加班",
    # Position-specific
    "{company} {position} 面试",
    "{company} {position} 招聘 JD",
    # Platform-specific
    "site:zhihu.com {company} 工作",
    "site:maimai.cn {company}",
    "{company} 脉脉 评价",
    "{company} 牛客 工作体验",
    # Compensation
    "{company} {position} 薪资",
]

MAX_RESULTS_PER_QUERY = 5
PAGE_TIMEOUT = 15000  # ms


async def search_bing(page, query: str) -> list[dict]:
    """Search Bing and return results."""
    url = f"https://www.bing.com/search?q={query}&setlang=zh-cn"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
        await page.wait_for_timeout(1000)
    except Exception:
        return []

    results = []
    try:
        items = await page.query_selector_all("li.b_algo")
        if not items:
            items = await page.query_selector_all(".b_algo, ol#b_results > li")
        for item in items[:MAX_RESULTS_PER_QUERY]:
            try:
                title_el = await item.query_selector("h2 a")
                title = await title_el.inner_text() if title_el else ""
                href = await title_el.get_attribute("href") if title_el else ""
                snippet_el = await item.query_selector(".b_caption p, .b_lineclamp2")
                snippet = await snippet_el.inner_text() if snippet_el else ""
                if title and href:
                    results.append({"title": title.strip(), "url": href, "snippet": snippet.strip()})
            except Exception:
                continue
    except Exception:
        pass
    return results


async def search_ddg(page, query: str) -> list[dict]:
    """Search DuckDuckGo and return results."""
    url = f"https://html.duckduckgo.com/html/?q={query}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
        await page.wait_for_timeout(1000)
    except Exception:
        return []

    results = []
    try:
        items = await page.query_selector_all(".result")
        for item in items[:MAX_RESULTS_PER_QUERY]:
            try:
                title_el = await item.query_selector(".result__title a")
                title = await title_el.inner_text() if title_el else ""
                href = await title_el.get_attribute("href") if title_el else ""
                snippet_el = await item.query_selector(".result__snippet")
                snippet = await snippet_el.inner_text() if snippet_el else ""
                if title and href:
                    results.append({"title": title.strip(), "url": href, "snippet": snippet.strip()})
            except Exception:
                continue
    except Exception:
        pass
    return results


async def fetch_page_text(page, url: str) -> str:
    """Fetch a page and extract readable text."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
        await page.wait_for_timeout(2000)
        text = await page.evaluate("""() => {
            const body = document.body;
            if (!body) return '';
            const clone = body.cloneNode(true);
            for (const el of clone.querySelectorAll('script, style, nav, footer, header, .nav, .footer, .header, .sidebar, .ad')) {
                el.remove();
            }
            return clone.innerText.substring(0, 5000);
        }""")
        return text.strip()
    except Exception:
        return ""


async def try_platform_direct(page, company: str) -> list[dict]:
    """Try direct access to Chinese review platforms."""
    results = []
    platforms = [
        ("知乎", f"https://www.zhihu.com/search?type=content&q={company}"),
        ("看准网", f"https://www.kanzhun.com/search/?q={company}"),
    ]

    for name, url in platforms:
        try:
            text = await fetch_page_text(page, url)
            if text and len(text) > 100:
                results.append({
                    "platform": name,
                    "url": url,
                    "text": text[:3000],
                    "accessible": True
                })
            else:
                results.append({
                    "platform": name,
                    "url": url,
                    "accessible": False,
                    "reason": "No content returned or blocked"
                })
        except Exception as e:
            results.append({
                "platform": name,
                "url": url,
                "accessible": False,
                "reason": str(e)[:200]
            })

    return results


async def main():
    company = sys.argv[1] if len(sys.argv) > 1 else ""
    position = sys.argv[2] if len(sys.argv) > 2 else ""

    if not company:
        print(json.dumps({"error": "Usage: python search_company.py <company_name> [position]"}))
        sys.exit(1)

    output = {
        "company": company,
        "position": position,
        "timestamp": datetime.now().isoformat(),
        "search_results": [],
        "platform_access": [],
        "summary": {}
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = await context.new_page()

        # Phase 1: Search for reviews
        for query_template in SEARCH_QUERIES:
            query = query_template.format(company=company, position=position)
            print(f"[Searching] {query}", file=sys.stderr)

            # Try Bing first
            results = await search_bing(page, query)
            if not results:
                results = await search_ddg(page, query)

            for r in results:
                r["query"] = query

            output["search_results"].append({
                "query": query,
                "results_count": len(results),
                "results": results
            })

            if results:
                # Fetch top 2 result pages for more detail
                for r in results[:2]:
                    try:
                        text = await fetch_page_text(page, r["url"])
                        if text and len(text) > 50:
                            r["page_text"] = text[:2000]
                    except Exception:
                        pass

            await page.wait_for_timeout(500)

        # Phase 2: Test platform accessibility
        print("[Testing] Platform accessibility...", file=sys.stderr)
        output["platform_access"] = await try_platform_direct(page, company)

        await browser.close()

    # Generate summary
    total_results = sum(len(q["results"]) for q in output["search_results"])
    queries_with_results = sum(1 for q in output["search_results"] if q["results"])
    accessible_platforms = [p for p in output["platform_access"] if p.get("accessible")]

    output["summary"] = {
        "total_queries": len(SEARCH_QUERIES),
        "queries_with_results": queries_with_results,
        "total_results": total_results,
        "accessible_platforms": len(accessible_platforms),
        "note": "Results from Bing/DDG search. Direct platform access tested separately."
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
