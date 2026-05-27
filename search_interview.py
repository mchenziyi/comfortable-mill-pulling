"""
Targeted interview experience search for a specific company + position.
Usage: python search_interview.py <company_name> <position>
"""
import sys, json, asyncio, re

try:
    from playwright.async_api import async_playwright
except ImportError:
    print(json.dumps({"error": "playwright not installed"}))
    sys.exit(1)

INTERVIEW_QUERIES = [
    "{company} {position} 面试题",
    "{company} {position} 面经",
    "{company} {position} 面试 真题",
    "{company} {position} 面试流程",
    "{company} {position} 技术面",
    "{company} {position} HR面",
    "{company} 面试 几轮",
    "{company} 面试难度",
]

async def search_bing(page, query):
    url = f"https://www.bing.com/search?q={query}&setlang=zh-cn"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1000)
    except:
        return []
    results = []
    try:
        items = await page.query_selector_all("li.b_algo")
        if not items:
            items = await page.query_selector_all(".b_algo, ol#b_results > li")
        for item in items[:3]:
            try:
                title_el = await item.query_selector("h2 a")
                title = await title_el.inner_text() if title_el else ""
                href = await title_el.get_attribute("href") if title_el else ""
                snippet_el = await item.query_selector(".b_caption p, .b_lineclamp2")
                snippet = await snippet_el.inner_text() if snippet_el else ""
                if title and href:
                    results.append({"title": title.strip(), "url": href, "snippet": snippet.strip()})
            except:
                continue
    except:
        pass
    return results

async def fetch_page(page, url):
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)
        text = await page.evaluate("""() => {
            const body = document.body;
            if (!body) return '';
            const clone = body.cloneNode(true);
            for (const el of clone.querySelectorAll('script, style, nav, footer, header, .nav, .footer, .header, .sidebar, .ad, .recommend')) {
                el.remove();
            }
            return clone.innerText.substring(0, 8000);
        }""")
        return text.strip()
    except:
        return ""

async def main():
    company = sys.argv[1] if len(sys.argv) > 1 else ""
    position = sys.argv[2] if len(sys.argv) > 2 else ""
    if not company:
        print(json.dumps({"error": "Usage: python search_interview.py <company> [position]"}))
        sys.exit(1)

    output = {"company": company, "position": position, "items": []}

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN"
        )
        page = await context.new_page()
        seen_urls = set()

        for query_template in INTERVIEW_QUERIES:
            query = query_template.format(company=company, position=position)
            print(f"[Interview] {query}", file=sys.stderr)
            results = await search_bing(page, query)
            for r in results:
                if r["url"] in seen_urls:
                    continue
                seen_urls.add(r["url"])
                print(f"  -> {r['title'][:80]}", file=sys.stderr)
                page_text = await fetch_page(page, r["url"])
                output["items"].append({
                    "query": query,
                    "title": r["title"],
                    "url": r["url"],
                    "snippet": r["snippet"],
                    "page_content": page_text[:5000] if page_text else ""
                })
                await page.wait_for_timeout(800)

        await browser.close()

    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
