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
    """Extract key skills from resume text. Handles OCR text with inter-character spaces."""
    skills = {
        "languages": [],
        "frameworks": [],
        "databases": [],
        "devops": [],
        "yoe": 0,
    }

    # Normalize: collapse inter-character spaces from OCR output
    # "G o l a n g" → "Golang", "M y S Q L" → "MySQL"
    normalized = re.sub(r'(?<=\w) (?=\w)', '', resume_text)
    text_lower = normalized.lower()

    # Languages
    for lang in ["Go", "Python", "Java", "Rust", "TypeScript", "JavaScript", "C++"]:
        if lang.lower() in text_lower:
            if lang not in skills["languages"]:
                skills["languages"].append(lang)

    # Frameworks
    for fw in ["Gin", "gozero", "Go-zero", "Kratos", "Echo", "gRPC", "Spring", "Django", "FastAPI"]:
        if fw.lower().replace("-", "") in text_lower.replace("-", "").replace(" ", ""):
            clean = fw.replace("gozero", "Go-zero").replace("Go-zero", "Go-zero")
            if clean not in skills["frameworks"]:
                skills["frameworks"].append(clean)

    # Databases
    for db in ["MySQL", "Redis", "PostgreSQL", "MongoDB", "Elasticsearch", "Kafka"]:
        if db.lower() in text_lower:
            skills["databases"].append(db)

    # DevOps
    for dev in ["Docker", "Kubernetes", "K8s", "CICD", "Jenkins", "Prometheus", "etcd", "Consul"]:
        if dev.lower() in text_lower:
            clean = "K8s" if dev == "Kubernetes" else dev
            if clean not in skills["devops"]:
                skills["devops"].append(clean)

    # YOE estimation - search in normalized text
    yoe_match = re.search(r'(\d+)\s*年', normalized)
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
        f"{city} Go 开发 招聘 薪资",
        f"{city} Golang 社招",
        f"site:zhipin.com {city} {position}",
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
        "网易有道", "网易互娱", "网易云音乐", "网易严选",
        "飞书", "抖音", "TikTok", "今日头条",
        "阿里云", "淘宝", "天猫", "钉钉", "菜鸟",
        "微信", "腾讯云", "腾讯游戏",
        "百度智能云", "百度地图",
        "京东科技", "京东物流",
        "斗鱼", "虎牙", "哈啰", "货拉拉", "满帮",
        "Soul", "最右", "喜马拉雅", "蜻蜓FM", "荔枝", "映客",
        "阅文", "趣头条", "虎扑", "毒", "nice",
        "商汤", "旷视", "依图", "云从",
        "第四范式", "明略", "百分点",
        "PingCAP", "TiDB", "涛思数据", "TDengine",
        "StreamNative", "Apache", "Pulsar",
        "EMQ", "NebulaGraph", "ZILLIZ", "Milvus",
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
    "网易": {"wlb":7,"stability":8,"growth":7,"life_perks":9,
        "tags":["猪场","免费四餐","国企背景","弹性工作"],
        "pros":["免费四餐+下午茶，伙食行业天花板","弹性工作制，WLB较字节阿里好","健身房/班车/按摩店，福利拉满","国企背景(浙报系)，相对稳定"],
        "cons":["近期外包裁员千人，非正式员工风险大","部分项目组有995加班","涨薪偏慢，晋升不如字节快","游戏行业受版号政策影响"],
        "note":"老牌互联网，杭州总部，WLB好，福利顶级，近期外包裁员需关注"},
    "字节跳动": {"wlb":4,"stability":6,"growth":9,"life_perks":8,
        "tags":["高薪资","晋升快","加班多","年轻化"],
        "pros":["薪资行业顶级，15薪起","晋升极快，每季度窗口","免费三餐+下午茶+房补","产品影响力大，跳槽含金量高"],
        "cons":["加班非常多，大小周文化","裁员频繁，多条业务线缩编","OKR驱动压力大，精神消耗高","内部竞争激烈，末尾淘汰"],
        "note":"薪资高晋升快但加班多裁员频繁，适合年轻人攒钱/攒履历"},
    "腾讯": {"wlb":6,"stability":8,"growth":8,"life_perks":8,
        "tags":["老牌大厂","福利好","稳定","深圳/北京"],
        "pros":["福利好，早餐免费+班车+健身房","游戏业务现金流稳定","技术沉淀深厚，团队专业","年终奖丰厚，16薪+项目奖"],
        "cons":["部分部门加班多(微信除外)","晋升通道比字节慢","内部竞争激烈，抢活现象","社招HC有限，门槛高"],
        "note":"老牌巨头，福利好，游戏业务稳，部分部门加班多"},
    "阿里巴巴": {"wlb":5,"stability":7,"growth":7,"life_perks":7,
        "tags":["电商巨头","食堂好","卷","杭州总部"],
        "pros":["食堂+下午茶+健身房，福利完善","技术生态丰富，学习资源多","阿里系背景跳槽认可度高","业务线众多，内部转岗灵活"],
        "cons":["卷度因部门而异，整体偏卷","PUA文化，部分主管强势","近年增长放缓，裁员时有发生","价值观考核，不习惯的人很难受"],
        "note":"电商巨头，技术强，卷，食堂好，近年有裁员调整"},
    "百度": {"wlb":7,"stability":7,"growth":6,"life_perks":6,
        "tags":["AI方向","相对不卷","免费三餐","北京"],
        "pros":["相对不卷，WLB较好","免费三餐，福利尚可","AI方向有成长空间","老牌稳定，极少裁员"],
        "cons":["增长乏力，移动互联网掉队","薪资竞争力不如字节阿里","技术氛围偏传统","部分业务边缘化风险"],
        "note":"老牌稳定不卷，AI方向可，增长放缓"},
    "美团": {"wlb":5,"stability":7,"growth":7,"life_perks":6,
        "tags":["业务稳定","加班多","北京/上海"],
        "pros":["业务稳定，本地生活基本盘牢固","技术成长快，系统复杂度高","食堂+下午茶，福利中等"],
        "cons":["部分部门加班较多(外卖/到店)","降本增效压力大","中层管理问题时有投诉"],
        "note":"业务稳定但加班多，适合积累高并发经验"},
    "京东": {"wlb":5,"stability":7,"growth":7,"life_perks":6,
        "tags":["物流电商","福利较好","加班较多"],
        "pros":["食堂+下午茶+健身房","物流业务稳，现金流好","福利较好(五险一金+补充医疗保险)"],
        "cons":["加班较多，尤其大促期间","东哥文化，管理风格较强硬","年终奖看业绩，波动大"],
        "note":"电商+物流，加班较多，福利还行"},
    "拼多多": {"wlb":3,"stability":6,"growth":8,"life_perks":5,
        "tags":["高压","薪资高","11116","上海"],
        "pros":["薪资高，年包很有竞争力","增长快，电商出海(Teum)势头猛","技术挑战大，成长快"],
        "cons":["11116工作制，加班严重","高压文化，精神消耗极大","内部管理激进，流动性大","负面口碑多"],
        "note":"薪资高但加班严重，11116文化，适合短期攒钱"},
    "快手": {"wlb":5,"stability":6,"growth":7,"life_perks":7,
        "tags":["短视频","福利好","有裁员","北京"],
        "pros":["免费三餐+下午茶+健身房，福利好","薪资在行业中上","技术氛围不错，很多字节阿里跳过来的"],
        "cons":["近两年有裁员调整","与抖音竞争压力大","部分部门加班多"],
        "note":"短视频老二，福利好，有裁员传言"},
    "滴滴": {"wlb":6,"stability":5,"growth":6,"life_perks":5,
        "tags":["出行","裁员多","北京"],
        "pros":["WLB中等，比字节阿里好","出行领域技术积累深"],
        "cons":["近年裁员频繁，组织动荡","下架事件后元气大伤","增长见顶，业务收缩","年终奖不稳定"],
        "note":"裁员频繁，业务收缩，WLB中等"},
    "小红书": {"wlb":6,"stability":6,"growth":8,"life_perks":7,
        "tags":["增长快","年轻化","上海"],
        "pros":["免费三餐+下午茶，福利不错","用户增长快，业务向好","年轻人多，文化活泼"],
        "cons":["中等规模，稳定性和大厂有差距","加班看部门，有的项目组很卷"],
        "note":"增长快，年轻化，福利不错"},
    "哔哩哔哩": {"wlb":6,"stability":6,"growth":7,"life_perks":7,
        "tags":["二次元","福利好","年轻化","上海"],
        "pros":["免费三餐+下午茶+健身房+撸猫","文化好，年轻人多","二次元氛围，适合ACG爱好者"],
        "cons":["盈利压力大，近年亏损","部分部门管理混乱","裁员时有发生"],
        "note":"文化好福利好，但盈利压力和裁员风险并存"},
    "米哈游": {"wlb":6,"stability":9,"growth":9,"life_perks":9,
        "tags":["游戏顶薪","不裁员","福利天花板","上海"],
        "pros":["游戏行业顶薪，远超BAT","不裁员，极度稳定","免费三餐+下午茶+零食+健身房","技术氛围极好，精英团队"],
        "cons":["面试难度大，门槛高","游戏行业，非热爱可能乏味","上海位置，选择范围窄"],
        "note":"游戏行业天花板，顶薪不裁员，福利无敌"},
    "华为": {"wlb":4,"stability":9,"growth":7,"life_perks":5,
        "tags":["狼性文化","稳定","年终奖多","深圳"],
        "pros":["极度稳定，极少裁员","年终奖丰厚，分红可观","技术积累深厚","全球化平台"],
        "cons":["加班文化严重(狼性)","等级制度森严","食堂+班车，福利一般","非研发岗压力大"],
        "note":"超级稳定+年终奖多，但狼性文化加班严重"},
    "蚂蚁集团": {"wlb":5,"stability":7,"growth":8,"life_perks":7,
        "tags":["金融科技","上市预期","福利好","杭州"],
        "pros":["食堂+下午茶，福利好","金融科技赛道，前景好","技术强，有上市预期"],
        "cons":["监管不确定性(金融牌照)","上市推迟，期权兑现周期长","卷度看部门","部分业务被拆分"],
        "note":"金融科技，福利好有上市预期，但监管风险"},
    "携程": {"wlb":8,"stability":7,"growth":5,"life_perks":6,
        "tags":["WLB好","旅游","增长慢","上海"],
        "pros":["WLB很好，相对不卷","旅游行业，工作氛围轻松","办公环境好，上海总部漂亮"],
        "cons":["增长放缓，上升空间有限","薪资竞争力一般","旅游行业周期性波动"],
        "note":"WLB极好但增长慢，适合追求生活质量"},
    "得物": {"wlb":6,"stability":5,"growth":7,"life_perks":6,
        "tags":["潮牌电商","年轻人多","上海"],
        "pros":["潮牌电商，年轻人多","增长中，机会多"],
        "cons":["中等规模，稳定性一般","加班看部门"],
        "note":"潮牌电商，年轻化，增长中"},
    "唯品会": {"wlb":7,"stability":7,"growth":4,"life_perks":5,
        "tags":["WLB好","增长慢","广州"],
        "pros":["WLB好，工作生活平衡"],
        "cons":["增长放缓，上升空间有限","薪资福利一般"],
        "note":"广州老牌电商，WLB好但增长慢"},
    "阿里云": {"wlb":5,"stability":8,"growth":8,"life_perks":7,
        "tags":["云计算","技术强","阿里系"],
        "pros":["云计算龙头，技术壁垒高","技术氛围好，学习机会多","食堂+下午茶","阿里系跳槽含金量高"],
        "cons":["加班看部门，有的很卷","阿里PUA文化可能延续","独立上市不确定"],
        "note":"云计算龙头，技术强，卷度看部门"},
    "菜鸟": {"wlb":5,"stability":7,"growth":7,"life_perks":6,
        "tags":["物流","阿里系"],
        "pros":["阿里旗下物流，业务增长","福利同阿里"],
        "cons":["加班中等","业务受阿里整体影响"],
        "note":"阿里系物流，增长不错"},
    "钉钉": {"wlb":5,"stability":7,"growth":7,"life_perks":7,
        "tags":["企业IM","阿里系"],
        "pros":["企业IM赛道，增长不错","福利同阿里(7)"],
        "cons":["加班看部门","竞争压力大(飞书/企微)"],
        "note":"阿里系企业IM，增长中"},
    "PingCAP": {"wlb":8,"stability":7,"growth":7,"life_perks":7,
        "tags":["开源","远程友好","技术好","杭州"],
        "pros":["TiDB，中国最成功的开源数据库","远程友好，WLB极好","技术氛围极佳，精英团队","分布式+数据库，技术栈匹配Go"],
        "cons":["中等规模，不如大厂稳定","薪资竞争力不如字节","商业化压力渐增","国内开源生态不成熟"],
        "note":"开源数据库，远程友好，WLB极好，技术栈完美对口"},
    "斗鱼": {"wlb":6,"stability":5,"growth":5,"life_perks":5,
        "tags":["直播","武汉"],
        "pros":["直播平台，武汉总部"],
        "cons":["增长放缓","福利一般"],
        "note":"武汉直播平台，增长放缓"},
    "哈啰": {"wlb":6,"stability":6,"growth":6,"life_perks":5,
        "tags":["共享出行","阿里系","上海"],
        "pros":["共享出行，阿里系"],
        "cons":["中等规模"],
        "note":"阿里系共享出行"},
    "Shopee": {"wlb":6,"stability":7,"growth":7,"life_perks":7,
        "tags":["东南亚电商","深圳/上海","福利好"],
        "pros":["东南亚电商龙头，福利好","薪资有竞争力"],
        "cons":["有裁员传闻","加班看部门"],
        "note":"东南亚电商，福利好，有裁员传闻"},
    "Soul": {"wlb":6,"stability":5,"growth":6,"life_perks":6,
        "tags":["社交App","年轻化","上海"],
        "pros":["社交赛道，年轻人多"],
        "cons":["中等规模，稳定性一般"],
        "note":"社交App，上海"},
    "大疆": {"wlb":5,"stability":8,"growth":7,"life_perks":6,
        "tags":["无人机","技术强","深圳"],
        "pros":["无人机全球龙头，技术壁垒极高","稳定，极少裁员"],
        "cons":["加班较多，技术驱动文化","深圳位置"],
        "note":"无人机龙头，技术强稳定，加班较多"},
    "商汤": {"wlb":6,"stability":5,"growth":6,"life_perks":6,
        "tags":["AI四小龙","北京/上海"],
        "pros":["AI方向，技术氛围好"],
        "cons":["有裁员调整","商业化困难"],
        "note":"AI四小龙，有裁员调整"},
    "Zoom": {"wlb":7,"stability":8,"growth":6,"life_perks":7,
        "tags":["外企","远程友好","WLB好","杭州/苏州"],
        "pros":["外企文化，WLB好","远程友好","杭州/苏州有研发中心"],
        "cons":["增长放缓(后疫情时代)","薪资在行业内中等","技术栈偏C++/WebRTC,Go岗位有限"],
        "note":"外企，WLB好，远程友好，但Go岗位不一定多"},
    "微软": {"wlb":9,"stability":9,"growth":6,"life_perks":8,
        "tags":["外企天花板","不加班","福利顶级","苏州/北京"],
        "pros":["外企天花板，WLB极好","福利顶级，年假多","几乎不裁员"],
        "cons":["成长偏慢，晋升周期长","薪资竞争力不如中资大厂","技术栈偏微软生态"],
        "note":"外企天花板，不加班福利顶级，成长偏慢"},
    "Shein": {"wlb":5,"stability":7,"growth":8,"life_perks":6,
        "tags":["快时尚电商","增长快","广州/南京"],
        "pros":["快时尚出海，增长极快","薪资高，有竞争力"],
        "cons":["加班较多","企业文化偏激进"],
        "note":"快时尚电商出海，增长快薪资高，加班较多"},
    "莉莉丝": {"wlb":6,"stability":7,"growth":8,"life_perks":7,
        "tags":["游戏","上海","万国觉醒"],
        "pros":["游戏行业，爆款率高","福利好，技术氛围好"],
        "cons":["加班看项目周期","游戏行业波动"],
        "note":"游戏公司(万国觉醒)，上海，福利好"},
    "完美世界": {"wlb":6,"stability":6,"growth":6,"life_perks":6,
        "tags":["老牌游戏","北京"],
        "pros":["老牌游戏公司"],
        "cons":["有裁员","福利中等"],
        "note":"北京老牌游戏公司，有裁员"},
    "喜马拉雅": {"wlb":6,"stability":5,"growth":6,"life_perks":6,
        "tags":["音频平台","上海"],
        "pros":["音频赛道，上海"],
        "cons":["增长中，中等规模"],
        "note":"音频平台，上海"},
    "Keep": {"wlb":6,"stability":5,"growth":6,"life_perks":7,
        "tags":["运动App","北京"],
        "pros":["有健身房福利"],
        "cons":["增长平缓"],
        "note":"运动App，北京"},
    "富途": {"wlb":6,"stability":7,"growth":7,"life_perks":7,
        "tags":["互联网券商","深圳","金融科技"],
        "pros":["金融科技，福利好","加班中等"],
        "cons":["金融监管风险"],
        "note":"互联网券商，深圳，福利好"},
    "贝壳": {"wlb":6,"stability":6,"growth":5,"life_perks":5,
        "tags":["房产平台","北京"],
        "pros":["房产平台"],
        "cons":["行业波动，增长放缓"],
        "note":"房产平台，北京"},
}


# City-office mapping for fallback discovery
COMPANY_CITIES = {
    "杭州": ["网易", "阿里巴巴", "蚂蚁集团", "字节跳动", "快手", "华为", "滴滴", "菜鸟", "阿里云", "钉钉",
             "Zoom", "哔哩哔哩", "同程", "微店", "有赞", "蘑菇街", "网易云音乐", "网易严选", "网易有道",
             "海康威视", "大华", "新华三", "PingCAP", "涂鸦智能", "微策略"],
    "北京": ["字节跳动", "腾讯", "阿里巴巴", "百度", "美团", "京东", "快手", "小米", "滴滴", "华为",
             "蚂蚁集团", "小红书", "哔哩哔哩", "360", "新浪", "搜狐", "陌陌", "探探", "Keep", "知乎",
             "完美世界", "昆仑万维", "贝壳", "58同城", "汽车之家", "商汤", "旷视", "微软", "Amazon"],
    "上海": ["字节跳动", "腾讯", "阿里巴巴", "拼多多", "美团", "小红书", "哔哩哔哩", "携程", "滴滴",
             "蚂蚁集团", "华为", "京东", "百度", "米哈游", "莉莉丝", "Soul", "喜马拉雅", "得物", "蔚来",
             "Shopee", "Zoom", "微软", "Apple"],
    "深圳": ["腾讯", "字节跳动", "华为", "大疆", "Shopee", "富途", "微众银行", "百度", "阿里巴巴", "京东",
             "快手", "OPPO", "vivo", "平安科技", "顺丰", "深信服", "中兴"],
    "广州": ["微信", "腾讯", "网易", "字节跳动", "阿里巴巴", "Shein", "唯品会", "京东", "百度", "华为",
             "酷狗", "三七互娱", "虎牙", "斗鱼", "4399", "多益网络"],
    "成都": ["字节跳动", "腾讯", "阿里巴巴", "美团", "京东", "华为", "百度", "快手", "蚂蚁集团", "OPPO"],
    "武汉": ["小米", "字节跳动", "腾讯", "斗鱼", "华为", "百度", "京东", "金山", "ThoughtWorks"],
    "南京": ["字节跳动", "阿里巴巴", "Shein", "华为", "小米", "京东", "苏宁", "途牛", "满帮"],
    "苏州": ["微软", "Zoom", "华为", "同程", "科大讯飞", "Momenta"],
}


def get_city_companies(city: str) -> list[str]:
    """Get all known companies with offices in a city."""
    for key, companies in COMPANY_CITIES.items():
        if city in key or key in city:
            return companies
    # Partial match
    for key, companies in COMPANY_CITIES.items():
        if city[:2] in key:
            return companies
    return list(COMPANY_REPUTATION.keys())  # fallback: all known companies


def enrich_company(job: dict) -> dict:
    """Add reputation data to a company."""
    company = job.get("company", "")
    if company in COMPANY_REPUTATION:
        rep = COMPANY_REPUTATION[company]
        job["wlb"] = rep.get("wlb", 5)
        job["stability"] = rep.get("stability", 5)
        job["growth"] = rep.get("growth", 5)
        job["life_perks"] = rep.get("life_perks", 0)
        job["tags"] = rep.get("tags", [])
        job["pros"] = rep.get("pros", [])
        job["cons"] = rep.get("cons", [])
        job["note"] = rep.get("note", "")
    else:
        job["wlb"] = 5
        job["stability"] = 5
        job["growth"] = 5
        job["life_perks"] = 3
        job["tags"] = []
        job["pros"] = []
        job["cons"] = []
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
        scoring["scores"]["wlb"] = job.get("wlb", 5)
        scoring["scores"]["stability"] = job.get("stability", 5)
        scoring["scores"]["growth"] = job.get("growth", 5)
        scoring["scores"]["life_perks"] = job.get("life_perks", 0)
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
            "tags": job.get("tags", []),
            "pros": job.get("pros", []),
            "cons": job.get("cons", []),
            "note": job.get("note", ""),
            "scores": scoring["scores"],
            "total": scoring["total"],
        })

    # Fallback: if DDG found < 5 companies, add all known companies in the city
    if len(output["companies"]) < 5:
        seen = {c["company"] for c in output["companies"]}
        city_companies = get_city_companies(city)
        print(f"[Fallback] Adding {len(city_companies)} candidates for {city}", file=sys.stderr)
        for company_name in city_companies:
            if company_name in seen:
                continue
            job = {"company": company_name, "title": "", "snippet": "", "salary_range": None}
            job = enrich_company(job)
            scoring = score_company(job, skills)
            scoring["scores"]["wlb"] = job.get("wlb", 5)
            scoring["scores"]["stability"] = job.get("stability", 5)
            scoring["scores"]["growth"] = job.get("growth", 5)
            scoring["scores"]["life_perks"] = job.get("life_perks", 0)
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
                "title": "",
                "salary_range": None,
                "tags": job.get("tags", []),
                "pros": job.get("pros", []),
                "cons": job.get("cons", []),
                "note": job.get("note", ""),
                "scores": scoring["scores"],
                "total": scoring["total"],
                "source": "city_db_fallback",
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
