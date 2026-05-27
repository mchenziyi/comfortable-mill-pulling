"""
Company precise analysis - search-driven, no pre-built data.
Usage: python search_jobs.py <resume> <company> [--avoid-exam]
"""

import sys, json, asyncio, re, os, subprocess
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    print(json.dumps({"error": "playwright not installed"}))
    sys.exit(1)


def extract_skills_from_resume(text: str) -> dict:
    skills = {"languages":[],"frameworks":[],"databases":[],"devops":[],"yoe":0}
    normalized = re.sub(r'(?<=\w) (?=\w)', '', text)
    tl = normalized.lower()
    for lang in ["Go","Python","Java","Rust","TypeScript","C++"]:
        if lang.lower() in tl: skills["languages"].append(lang)
    for fw in ["Gin","gozero","Go-zero","Kratos","Echo","gRPC","Spring","Django"]:
        if fw.lower().replace("-","").replace(" ","") in tl.replace("-","").replace(" ",""):
            skills["frameworks"].append(fw.replace("gozero","Go-zero"))
    for db in ["MySQL","Redis","PostgreSQL","MongoDB","Elasticsearch","Kafka"]:
        if db.lower() in tl: skills["databases"].append(db)
    for dev in ["Docker","Kubernetes","K8s","CICD","Jenkins","Prometheus","etcd","Consul"]:
        if dev.lower() in tl: skills["devops"].append(dev.replace("Kubernetes","K8s").replace("CICD","CI/CD"))
    m = re.search(r'(\d+)\s*年', normalized)
    if m: skills["yoe"] = int(m.group(1))
    return skills

def load_resume(path_or_text: str) -> str:
    if os.path.exists(path_or_text):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        extractor = os.path.join(script_dir, "extract_resume.py")
        if os.path.exists(extractor):
            try:
                r = subprocess.run([sys.executable, extractor, path_or_text], capture_output=True, text=True, timeout=90)
                if r.returncode == 0 and r.stdout.strip(): return r.stdout.strip()
            except: pass
        try:
            with open(path_or_text, "r", encoding="utf-8") as f: return f.read()
        except: pass
    return path_or_text

async def search_ddg(page, query: str, max_results: int = 8) -> list[dict]:
    url = f"https://html.duckduckgo.com/html/?q={query}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1000)
    except: return []
    results = []
    try:
        for item in (await page.query_selector_all(".result"))[:max_results]:
            try:
                title_el = await item.query_selector(".result__title a")
                title = await title_el.inner_text() if title_el else ""
                href = await title_el.get_attribute("href") if title_el else ""
                snippet_el = await item.query_selector(".result__snippet")
                snippet = await snippet_el.inner_text() if snippet_el else ""
                if title and href:
                    source_type = identify_source(href, title)
                    source_weight = get_source_weight(href, title)
                    results.append({
                        "title": title.strip(),
                        "url": href,
                        "snippet": snippet.strip(),
                        "source_type": source_type,
                        "source_weight": source_weight,
                    })
            except: continue
    except: pass
    return results

def extract_salary_range(text: str) -> list[int] | None:
    for pat in [r'(\d+)[kK]\s*[-−到]\s*(\d+)[kK]', r'(\d+)\s*[-−到]\s*(\d+)\s*[kK]']:
        m = re.search(pat, text)
        if m: return [int(m.group(1)), int(m.group(2))]
    return None

# 信源权重：不同来源的信息可信度不同
SOURCE_WEIGHTS = {
    "official": 1.0,    # 官方网站
    "interview": 0.9,   # 面经网站（牛客、力扣）
    "employee": 0.85,   # 员工评价（知乎、脉脉）
    "anonymous": 0.75,  # 匿名论坛（V2EX）
    "news": 0.6,        # 新闻/博客
    "unknown": 0.5,     # 未知来源
}

def identify_source(url: str, title: str) -> str:
    """识别搜索结果的来源类型"""
    url_lower = url.lower()
    title_lower = title.lower()
    
    # 官方网站
    if any(kw in url_lower for kw in [".com/", ".cn/", "career", "jobs", "recruit"]):
        if any(kw in url_lower for kw in ["xiaohongshu", "baidu", "alibaba", "tencent", "bytedance"]):
            return "official"
    
    # 面经网站
    if any(kw in url_lower for kw in ["nowcoder", "leetcode", "cnblogs", "jianshu"]):
        return "interview"
    if any(kw in title_lower for kw in ["面经", "面试题", "笔试"]):
        return "interview"
    
    # 员工评价
    if any(kw in url_lower for kw in ["zhihu", "maimai", "kanzhun", "jobui"]):
        return "employee"
    if any(kw in title_lower for kw in ["工作体验", "员工评价", "在职"]):
        return "employee"
    
    # 匿名论坛
    if any(kw in url_lower for kw in ["v2ex", "tieba", "douban"]):
        return "anonymous"
    
    # 新闻/博客
    if any(kw in url_lower for kw in ["36kr", "techcrunch", "reuters", "sina", "sohu"]):
        return "news"
    
    return "unknown"

def get_source_weight(url: str, title: str) -> float:
    """获取信源权重"""
    source_type = identify_source(url, title)
    return SOURCE_WEIGHTS.get(source_type, 0.5)

# 风险标签系统：识别真实风险信号
RISK_PATTERNS = [
    (r'加班[严很]|996|大小周|强制加班|无偿加班', "加班严重"),
    (r'看[组部]|组[长导]决定|运气成分', "看组"),
    (r'PUA|精神控制|打压|贬低|否定', "leader PUA"),
    (r'裁员|优化|毕业|人员调整|缩编', "裁员风险"),
    (r'晋升[慢难]|天花板|晋升无望|晋升周期长', "晋升慢"),
    (r'HC[冻停]|暂停招聘|无HC|没有HC', "HC冻结"),
    (r'拖欠工资|欠薪|延迟发放', "薪资风险"),
    (r'内卷|恶性竞争|抢功|甩锅', "内卷严重"),
    (r'管理混乱|朝令夕改|目标不清', "管理混乱"),
    (r'技术[落后旧]|维护老代码|没有技术含量', "技术落后"),
]

def extract_risk_tags(text: str) -> list[str]:
    """从文本中提取风险标签"""
    tags = []
    text_lower = text.lower()
    for pattern, tag in RISK_PATTERNS:
        if re.search(pattern, text_lower):
            if tag not in tags:
                tags.append(tag)
    return tags

def calculate_confidence(results: list, sentiment: dict) -> float:
    """计算分析置信度（0-1）
    基于：
    1. 搜索结果数量（越多越可信）
    2. 信源质量（高权重来源越多越可信）
    3. 风险标签数量（有明确风险信号更可信）
    """
    if not results:
        return 0.1

    # 基础分：基于结果数量
    count_score = min(len(results) / 20, 0.4)  # 20条结果得满分0.4

    # 信源质量分
    high_weight_count = sum(1 for r in results if r.get("source_weight", 0.5) >= 0.8)
    source_score = min(high_weight_count / 10, 0.3)  # 10条高权重来源得满分0.3

    # 风险标签分（有明确风险信号说明信息足够）
    risk_count = len(sentiment.get("risk_tags", []))
    risk_score = min(risk_count / 3, 0.2)  # 3个风险标签得满分0.2

    # 基础可信度
    base_score = 0.1

    total = base_score + count_score + source_score + risk_score
    return round(min(total, 1.0), 2)

def generate_summary(company: str, research: dict, scoring: dict) -> str:
    """生成一句话摘要"""
    total = scoring["total"]
    wlb = research.get("wlb", 5)
    risk_tags = research.get("risk_tags", [])
    confidence = research.get("confidence", 0.1)

    # 评级
    if total >= 8:
        rating = "强烈推荐"
    elif total >= 6:
        rating = "推荐"
    elif total >= 4:
        rating = "一般"
    else:
        rating = "不推荐"

    # WLB描述
    if wlb >= 7:
        wlb_desc = "WLB好"
    elif wlb >= 5:
        wlb_desc = "WLB中等"
    else:
        wlb_desc = "加班较多"

    # 风险提示
    risk_hint = ""
    if risk_tags:
        risk_hint = f"，需注意：{','.join(risk_tags[:2])}"

    # 置信度提示
    conf_hint = ""
    if confidence < 0.5:
        conf_hint = "（数据不足，仅供参考）"

    return f"{company} {rating}，总分{total}/10，{wlb_desc}{risk_hint}{conf_hint}"

def _match_patterns(text: str, patterns: list[tuple[str, float]]) -> float:
    score = 0.0
    for pat, weight in patterns:
        if re.search(pat, text):
            score += weight
    return score

def analyze_wlb(text: str) -> tuple[float, list[str]]:
    positive = [
        (r'不加班', 2.0), (r'准时下班', 1.5), (r'双休', 1.5), (r'弹性[工上]', 1.0),
        (r'不卷', 1.5), (r'养老', 1.0), (r'轻松', 1.0), (r'wlb[好棒]', 1.5),
        (r'work\s*life\s*balance', 1.5), (r'朝九晚[五六]', 1.5), (r'偶尔加班', 0.3),
    ]
    negative = [
        (r'996', -2.0), (r'大小周', -1.5), (r'加班[多严]', -1.5), (r'加班[严]重', -2.0),
        (r'卷$', -1.0), (r'很卷', -1.5), (r'内卷', -1.5), (r'累$', -1.0), (r'很累', -1.5),
        (r'通宵', -2.0), (r'凌晨', -1.5), (r'11点', -1.0), (r'12点', -1.5),
        (r'周末[加值]', -1.5), (r'无偿加班', -2.0), (r'强制加班', -2.0),
    ]
    delta = _match_patterns(text, positive) + _match_patterns(text, negative)
    delta = max(-3.0, min(3.0, delta))
    tags = []
    if re.search(r'996|大小周|加班[多严]|内卷|很卷', text): tags.append("加班重")
    if re.search(r'不加班|双休|不卷|wlb[好棒]|准时下班', text): tags.append("WLB好")
    if re.search(r'偶尔加班', text): tags.append("偶尔加班")
    return delta, tags

def analyze_stability(text: str) -> tuple[float, list[str]]:
    positive = [
        (r'国企', 2.0), (r'央企', 2.5), (r'上市[了公司]', 1.5), (r'不裁员', 2.0),
        (r'稳定', 1.0), (r'现金流[充沛充裕]', 1.5), (r'不差钱', 1.0), (r'盈利', 1.0), (r'行业龙头', 1.0),
    ]
    negative = [
        (r'裁员', -2.0), (r'倒闭', -3.0), (r'欠薪', -3.0), (r'拖欠', -2.5), (r'爆雷', -3.0),
        (r'收缩', -1.5), (r'撤出', -2.0), (r'解散', -3.0), (r'亏损', -1.5), (r'关停', -2.5), (r'大幅裁员', -3.0),
    ]
    delta = _match_patterns(text, positive) + _match_patterns(text, negative)
    delta = max(-3.0, min(3.0, delta))
    tags = []
    if re.search(r'国企|央企', text): tags.append("国企")
    if re.search(r'裁员|倒闭|欠薪|爆雷', text): tags.append("有风险")
    return delta, tags

def analyze_growth(text: str) -> tuple[float, list[str]]:
    positive = [
        (r'增长[强劲快速]', 2.0), (r'高速增长', 2.0), (r'上市[了预期]', 1.5),
        (r'融资', 1.0), (r'扩张', 1.0), (r'新业务', 1.0), (r'晋升[快空间]', 1.5), (r'行业领先', 1.0),
    ]
    negative = [
        (r'增长放缓', -1.5), (r'停滞', -2.0), (r'天花板', -1.0),
        (r'裁员', -1.0), (r'收缩', -1.5), (r'下行', -1.5), (r'寒冬', -1.0),
    ]
    delta = _match_patterns(text, positive) + _match_patterns(text, negative)
    delta = max(-3.0, min(3.0, delta))
    tags = []
    if re.search(r'增长|融资|上市', text): tags.append("增长中")
    return delta, tags

def analyze_perks(text: str) -> tuple[float, list[str]]:
    perks = [
        (r'免费[三一]餐', 1.5, "免费三餐"), (r'四餐', 1.0, "包四餐"), (r'包吃', 1.0, "包吃"),
        (r'食堂', 0.8, "食堂"), (r'下午茶', 1.0, "下午茶"), (r'健身房', 1.0, "健身房"),
        (r'班车', 0.8, "班车"), (r'零食[饮料无限]', 0.8, "零食"), (r'房补', 1.5, "房补"),
        (r'餐补', 0.8, "餐补"), (r'体检', 0.5, "体检"), (r'年假\d+天', 1.0, None),
        (r'团建', 0.3, "团建"), (r'远程[办公工]', 1.5, "远程"), (r'外企', 1.0, "外企"),
    ]
    score = 0.0
    tags = []
    for pat, weight, tag in perks:
        if re.search(pat, text):
            score += weight
            if tag and tag not in tags:
                tags.append(tag)
    return min(score, 5.0), tags

def analyze_exam_difficulty(text: str) -> str:
    hard_kw = [r'很难', r'难度大', r'hard', r'手撕', r'hard题', r'困难', r'hard模式',
               r'动态规划', r'图论', r'算法题[难]', r'代码题[难]', r'acm']
    easy_kw = [r'简单', r'不难', r'easy', r'容易', r'没有笔试', r'无笔试', r'免笔试',
               r'不考算法', r'重项目', r'笔试简单', r'选择题']
    has_hard = any(re.search(kw, text) for kw in hard_kw)
    has_easy = any(re.search(kw, text) for kw in easy_kw)
    if has_hard and has_easy: return "中等"
    if has_hard: return "困难"
    if has_easy: return "简单"
    return "中等"

def analyze_sentiment(snippets: list) -> dict:
    """分析情感，支持加权摘要。
    snippets: list of str (旧格式) 或 list of dict (新格式，含 text/weight/source)
    """
    # 兼容旧格式（纯字符串列表）
    if snippets and isinstance(snippets[0], str):
        weighted = [{"text": s, "weight": 1.0, "source": "unknown"} for s in snippets]
    else:
        weighted = snippets

    # 按权重排序，高权重的排前面
    weighted.sort(key=lambda x: x.get("weight", 0.5), reverse=True)

    # 合并所有文本（高权重的重复出现以增加影响力）
    all_text = " ".join([w["text"] for w in weighted]).lower()
    
    result = {"wlb":5.0,"stability":5.0,"growth":5.0,"perks":0.0,"tags":[],"risk_tags":[],"pros":[],"cons":[]}

    wlb_delta, wlb_tags = analyze_wlb(all_text)
    result["wlb"] = max(1.0, min(10.0, 5.0 + wlb_delta))
    result["tags"].extend(wlb_tags)

    stab_delta, stab_tags = analyze_stability(all_text)
    result["stability"] = max(1.0, min(10.0, 5.0 + stab_delta))
    result["tags"].extend(stab_tags)

    grow_delta, grow_tags = analyze_growth(all_text)
    result["growth"] = max(1.0, min(10.0, 5.0 + grow_delta))
    result["tags"].extend(grow_tags)

    perks_score, perks_tags = analyze_perks(all_text)
    result["perks"] = perks_score
    result["tags"].extend(perks_tags)

    # 提取风险标签
    risk_tags = extract_risk_tags(all_text)
    result["risk_tags"] = risk_tags

    # 提取正面/负面摘要，优先使用高权重来源
    for w in weighted[:10]:
        s_clean = w["text"].strip()
        if len(s_clean) < 10 or len(s_clean) > 100: continue
        if re.search(r'不加班|双休|不卷|福利好|福利不错|下午茶|免费[三一]餐|包吃', s_clean):
            if s_clean not in result["pros"]:
                result["pros"].append(s_clean)
        if re.search(r'996|加班多|大小周|裁员|倒闭|欠薪|内卷|很卷|很累', s_clean):
            if s_clean not in result["cons"]:
                result["cons"].append(s_clean)

    return result

async def research_company(page, company: str, avoid_exam: bool = False) -> dict:
    queries = [
        f"{company} 工作 体验 评价",
        f"{company} 加班 福利 薪资",
        f"{company} 996 WLB",
    ]
    if avoid_exam:
        queries.append(f"{company} 笔试 难度 面试")

    all_results = []
    for q in queries:
        results = await search_ddg(page, q, 5)
        all_results.extend(results)
        await page.wait_for_timeout(500)

    # 按信源权重排序，高权重的排前面
    all_results.sort(key=lambda x: x.get("source_weight", 0.5), reverse=True)

    # 提取带权重的摘要
    weighted_snippets = []
    for r in all_results:
        weighted_snippets.append({
            "text": r["snippet"],
            "weight": r.get("source_weight", 0.5),
            "source": r.get("source_type", "unknown"),
        })

    sentiment = analyze_sentiment(weighted_snippets)
    exam = analyze_exam_difficulty(" ".join([r["snippet"] for r in all_results])) if avoid_exam else "未评估"

    # 统计信源分布
    source_counts = {}
    for r in all_results:
        st = r.get("source_type", "unknown")
        source_counts[st] = source_counts.get(st, 0) + 1

    # 计算置信度
    confidence = calculate_confidence(all_results, sentiment)

    return {
        "wlb": round(sentiment["wlb"], 1),
        "stability": round(sentiment["stability"], 1),
        "growth": round(sentiment["growth"], 1),
        "perks": round(sentiment["perks"], 1),
        "tags": sentiment["tags"],
        "risk_tags": sentiment.get("risk_tags", []),
        "pros": sentiment["pros"][:3],
        "cons": sentiment["cons"][:3],
        "exam": exam,
        "snippets_count": len(all_results),
        "source_distribution": source_counts,
        "confidence": confidence,
    }

def score_company(skills: dict, research: dict, avoid_exam: bool) -> dict:
    s = {}
    s["tech_match"] = min(len(skills["languages"])*2 + len(skills["frameworks"]) + len(skills["databases"]), 10)
    s["wlb"] = research.get("wlb",5)
    s["stability"] = research.get("stability",5)
    s["growth"] = research.get("growth",5)
    s["perks"] = research.get("perks",5)

    exam_pen = 0
    if avoid_exam:
        e = research.get("exam","中等")
        s["exam"] = 10 if e=="简单" else (6 if e=="中等" else 2)
        exam_pen = 0 if e=="简单" else (-1 if e=="中等" else -2.5)

    total = round(
        s["tech_match"]*0.30 +
        s["wlb"]*0.25 +
        s["stability"]*0.15 +
        s["growth"]*0.10 +
        s["perks"]*0.20 +
        exam_pen, 1
    )
    return {"scores":s, "total":total, "total_max":10}

async def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(json.dumps({"error":"Usage: python search_jobs.py <resume> <company> [--avoid-exam]"}))
        sys.exit(1)

    resume_path, company = args[0], args[1]
    avoid_exam = "--avoid-exam" in args

    resume_text = load_resume(resume_path)
    skills = extract_skills_from_resume(resume_text)
    print(f"[Analysis] {company} | Skills: {skills['languages']}", file=sys.stderr)

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36", locale="zh-CN")
        page = await ctx.new_page()

        print(f"[Research] Searching {company}...", file=sys.stderr)
        research = await research_company(page, company, avoid_exam)
        scoring = score_company(skills, research, avoid_exam)

        await browser.close()

    # 生成摘要
    summary = generate_summary(company, research, scoring)

    # 固定输出 Schema
    output = {
        # 核心评分
        "overall_score": scoring["total"],
        "wlb_score": research.get("wlb", 5),
        "growth_score": research.get("growth", 5),
        "stability_score": research.get("stability", 5),
        "perks_score": research.get("perks", 0),
        "tech_match_score": scoring["scores"].get("tech_match", 0),
        # 风险与标签
        "risk_tags": research.get("risk_tags", []),
        "tags": research.get("tags", []),
        # 摘要
        "summary": summary,
        "confidence": research.get("confidence", 0.1),
        # 详细信息
        "company": company,
        "position": args[2] if len(args) > 2 else "",
        "skills_found": skills,
        "avoid_exam": avoid_exam,
        "exam": research.get("exam", "未评估"),
        "pros": research.get("pros", []),
        "cons": research.get("cons", []),
        "source_distribution": research.get("source_distribution", {}),
        "snippets_count": research.get("snippets_count", 0),
        "timestamp": datetime.now().isoformat(),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
