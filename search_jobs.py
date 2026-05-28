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
    "jd": 1.0,          # JD（官方招聘信息）
    "official": 0.95,   # 官方网站
    "interview": 0.85,  # 面经网站（牛客、力扣）
    "employee": 0.8,    # 员工评价（知乎、脉脉）
    "anonymous": 0.7,   # 匿名论坛（V2EX）
    "news": 0.6,        # 新闻/博客
    "unknown": 0.5,     # 未知来源
}

def identify_source(url: str, title: str) -> str:
    """识别搜索结果的来源类型"""
    url_lower = url.lower()
    title_lower = title.lower()
    
    # JD（招聘信息）
    if any(kw in url_lower for kw in ["zhipin", "lagou", "liepin", "boss", "job", "career", "recruit"]):
        return "jd"
    if any(kw in title_lower for kw in ["招聘", "职位", "岗位", "急招", "诚招"]):
        return "jd"
    
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

# JD 分析功能
JD_RISK_KEYWORDS = {
    "高强度": ["抗压能力", "抗压", "能承受高强度", "能承受压力", "高压环境"],
    "职责不清": ["owner意识", "主人翁意识", "自驱力", "主动性强", "多线程", "同时处理"],
    "可能加班": ["快速响应", "响应迅速", "创业心态", "创业公司", "弹性工作", "结果导向"],
    "画饼": ["期权激励", "未来可期", "快速发展", "成长空间大", "扁平化管理"],
    "模糊要求": ["有责任心", "团队合作", "沟通能力强", "学习能力强"],
}

JD_TECH_KEYWORDS = {
    "Go": ["Go", "Golang", "go语言"],
    "Java": ["Java", "java", "Spring", "SpringBoot", "SpringCloud"],
    "Python": ["Python", "python", "Django", "Flask", "FastAPI"],
    "JavaScript": ["JavaScript", "JS", "TypeScript", "TS", "Node.js"],
    "C++": ["C++", "cpp"],
    "Rust": ["Rust", "rust"],
    "MySQL": ["MySQL", "mysql", "SQL"],
    "Redis": ["Redis", "redis"],
    "PostgreSQL": ["PostgreSQL", "postgres", "PG"],
    "MongoDB": ["MongoDB", "mongodb"],
    "Kafka": ["Kafka", "kafka", "消息队列"],
    "RabbitMQ": ["RabbitMQ", "rabbitmq"],
    "Docker": ["Docker", "docker", "容器"],
    "Kubernetes": ["Kubernetes", "K8s", "k8s", "容器编排"],
    "AWS": ["AWS", "aws", "Amazon"],
    "GCP": ["GCP", "gcp", "Google Cloud"],
    "Azure": ["Azure", "azure", "微软云"],
    "gRPC": ["gRPC", "grpc", "GRPC"],
    "微服务": ["微服务", "microservice", "分布式"],
    "AI/ML": ["AI", "机器学习", "深度学习", "NLP", "LLM", "大模型"],
    "前端": ["React", "Vue", "Angular", "前端", "H5"],
    "运维": ["运维", "DevOps", "CI/CD", "SRE", "监控"],
    "测试": ["测试", "QA", "自动化测试", "性能测试"],
    "产品": ["产品经理", "产品设计", "需求分析"],
}

def extract_jd_tech_stack(jd_text: str) -> list[str]:
    """从 JD 中提取技术栈"""
    found = []
    text_lower = jd_text.lower()
    for tech, keywords in JD_TECH_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                if tech not in found:
                    found.append(tech)
                break
    return found

def extract_jd_risks(jd_text: str) -> list[dict]:
    """从 JD 中提取风险信号"""
    risks = []
    text_lower = jd_text.lower()
    for risk_type, keywords in JD_RISK_KEYWORDS.items():
        hits = []
        for kw in keywords:
            if kw.lower() in text_lower:
                hits.append(kw)
        if hits:
            risks.append({
                "type": risk_type,
                "evidence": hits,
                "evidence_count": len(hits),
            })
    return risks

def analyze_job_dirtiness(jd_text: str) -> dict:
    """分析岗位脏度（是否是缝合岗）"""
    tech_stack = extract_jd_tech_stack(jd_text)
    
    # 分类技术栈
    categories = {
        "backend": ["Go", "Java", "Python", "C++", "Rust"],
        "frontend": ["JavaScript", "前端"],
        "ai": ["AI/ML"],
        "devops": ["运维", "Docker", "Kubernetes"],
        "data": ["MySQL", "Redis", "Kafka", "MongoDB"],
        "test": ["测试"],
    }
    
    matched_categories = []
    for cat, techs in categories.items():
        if any(t in tech_stack for t in techs):
            matched_categories.append(cat)
    
    # 判断脏度
    if len(matched_categories) >= 4:
        job_type = "缝合岗"
        workload_risk = "high"
    elif len(matched_categories) == 3:
        job_type = "多面手"
        workload_risk = "medium"
    elif len(matched_categories) == 2:
        job_type = "全栈"
        workload_risk = "medium"
    else:
        job_type = "专精"
        workload_risk = "low"
    
    return {
        "job_type": job_type,
        "workload_risk": workload_risk,
        "categories": matched_categories,
        "tech_count": len(tech_stack),
    }

def extract_jd_requirements(jd_text: str) -> list[str]:
    """从 JD 中提取要求"""
    requirements = []
    lines = jd_text.split("\n")
    in_requirements = False
    for line in lines:
        line = line.strip()
        if any(kw in line for kw in ["任职要求", "岗位要求", "要求", "必备", "需要"]):
            in_requirements = True
            continue
        if in_requirements and line:
            if any(kw in line for kw in ["职责", "工作内容", "我们提供", "福利"]):
                in_requirements = False
            elif len(line) > 5 and len(line) < 100:
                requirements.append(line)
    return requirements[:10]

def extract_jd_responsibilities(jd_text: str) -> list[str]:
    """从 JD 中提取职责"""
    responsibilities = []
    lines = jd_text.split("\n")
    in_responsibilities = False
    for line in lines:
        line = line.strip()
        if any(kw in line for kw in ["工作职责", "岗位职责", "职责", "工作内容", "你将"]):
            in_responsibilities = True
            continue
        if in_responsibilities and line:
            if any(kw in line for kw in ["要求", "任职", "我们提供", "福利"]):
                in_responsibilities = False
            elif len(line) > 5 and len(line) < 100:
                responsibilities.append(line)
    return responsibilities[:10]

def analyze_jd(jd_text: str) -> dict:
    """完整 JD 分析"""
    return {
        "tech_stack": extract_jd_tech_stack(jd_text),
        "requirements": extract_jd_requirements(jd_text),
        "responsibilities": extract_jd_responsibilities(jd_text),
        "risks": extract_jd_risks(jd_text),
        "job_dirtiness": analyze_job_dirtiness(jd_text),
    }

def calculate_resume_match(resume_skills: dict, jd_tech_stack: list[str]) -> dict:
    """计算简历与 JD 的匹配度"""
    resume_all = set()
    for k in ["languages", "frameworks", "databases", "devops"]:
        for skill in resume_skills.get(k, []):
            resume_all.add(skill.lower())
    
    jd_set = set(t.lower() for t in jd_tech_stack)
    
    matched = resume_all & jd_set
    missing = jd_set - resume_all
    
    match_score = len(matched) / len(jd_set) * 100 if jd_set else 0
    
    return {
        "match_score": round(match_score, 1),
        "matched_skills": list(matched),
        "missing_skills": list(missing),
        "resume_skills": list(resume_all),
        "jd_skills": list(jd_set),
    }

# 风险标签系统：6个核心维度
RISK_DIMENSIONS = {
    "WLB": [
        r'加班[严很]|996|大小周|强制加班|无偿加班',
        r'高强度|节奏快|push|高压',
        r'通宵|凌晨|周末[加值]',
        r'不加班|双休|准时下班|弹性',  # 正面信号（用于冲突检测）
    ],
    "管理风险": [
        r'PUA|精神控制|打压|贬低|否定',
        r'管理混乱|朝令夕改|目标不清',
        r'看[组部]|组[长导]决定|运气成分',
        r'leader|主管|领导',
    ],
    "成长性": [
        r'晋升[慢难]|天花板|晋升无望|晋升周期长',
        r'没有成长|学不到东西|技术[落后旧]',
        r'维护老代码|没有技术含量|CRUD',
        r'增长[强劲快]|高速发展|晋升[快空间]',  # 正面信号
    ],
    "稳定性": [
        r'裁员|优化|毕业|人员调整|缩编',
        r'HC[冻停]|暂停招聘|无HC|没有HC',
        r'倒闭|欠薪|拖欠|爆雷|收缩',
        r'不裁员|稳定|上市|国企',  # 正面信号
    ],
    "薪资": [
        r'拖欠工资|欠薪|延迟发放|薪资低',
        r'薪资[少低]|工资[少低]|待遇差',
        r'薪资[高有竞]|工资[高]|待遇好',  # 正面信号
    ],
    "面试难度": [
        r'面试[难很]|笔试[难很]|hard|手撕',
        r'面试[简单]|笔试[简单]|免笔试|不考算法',
    ],
}

# 风险标签中文名
RISK_LABELS = {
    "WLB": "WLB风险",
    "管理风险": "管理风险",
    "成长性": "成长风险",
    "稳定性": "稳定风险",
    "薪资": "薪资风险",
    "面试难度": "面试难度",
}

def extract_risk_tags(text: str) -> list[dict]:
    """从文本中提取风险标签，返回带证据数量的风险列表"""
    text_lower = text.lower()
    risk_results = []
    
    for dimension, patterns in RISK_DIMENSIONS.items():
        # 分离正面和负面模式（最后一个通常是正面）
        negative_patterns = patterns[:-1] if len(patterns) > 1 else patterns
        positive_patterns = [patterns[-1]] if len(patterns) > 1 else []
        
        # 统计负面命中
        negative_hits = 0
        for pat in negative_patterns:
            negative_hits += len(re.findall(pat, text_lower))
        
        # 统计正面命中
        positive_hits = 0
        for pat in positive_patterns:
            positive_hits += len(re.findall(pat, text_lower))
        
        # 如果有负面命中，加入风险列表
        if negative_hits > 0:
            risk_results.append({
                "dimension": dimension,
                "label": RISK_LABELS.get(dimension, dimension),
                "evidence_count": negative_hits,
                "positive_count": positive_hits,
                "controversial": negative_hits > 0 and positive_hits > 0,
            })
    
    return risk_results

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

def generate_summary(company: str, department: str, research: dict, scoring: dict) -> str:
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

    dept_info = f" {department}" if department else ""
    return f"{company}{dept_info} {rating}，总分{total}/10，{wlb_desc}{risk_hint}{conf_hint}"

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

    # 提取风险标签（带证据数量和冲突检测）
    risk_results = extract_risk_tags(all_text)
    result["risk_tags"] = [r["label"] for r in risk_results]
    result["risk_details"] = risk_results
    
    # 冲突检测：如果有多个维度存在正反评价，标记为 controversial
    controversial_dims = [r["dimension"] for r in risk_results if r.get("controversial")]
    if len(controversial_dims) >= 2:
        result["controversial"] = True
        result["controversial_dimensions"] = controversial_dims
    else:
        result["controversial"] = False

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

async def research_company(page, company: str, department: str = "", position: str = "", avoid_exam: bool = False) -> dict:
    # 基础查询（公司级）
    queries = [
        f"{company} 工作 体验 评价",
        f"{company} 加班 福利 薪资",
        f"{company} 996 WLB",
    ]

    # 部门级查询（如果指定了部门）
    if department:
        queries.extend([
            f"{company} {department} 工作 体验",
            f"{company} {department} 加班 评价",
            f"{company} {department} 团队 氛围",
        ])

    # JD 搜索（如果指定了岗位）
    if position:
        queries.append(f"{company} {position} 招聘 JD")
    
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

    # JD 分析
    jd_analysis = None
    jd_text = ""
    for r in all_results:
        if r.get("source_type") == "jd" and r.get("snippet"):
            jd_text += r["snippet"] + " "
    if jd_text.strip():
        jd_analysis = analyze_jd(jd_text)

    return {
        "wlb": round(sentiment["wlb"], 1),
        "stability": round(sentiment["stability"], 1),
        "growth": round(sentiment["growth"], 1),
        "perks": round(sentiment["perks"], 1),
        "tags": sentiment["tags"],
        "risk_tags": sentiment.get("risk_tags", []),
        "risk_details": sentiment.get("risk_details", []),
        "controversial": sentiment.get("controversial", False),
        "controversial_dimensions": sentiment.get("controversial_dimensions", []),
        "pros": sentiment["pros"][:3],
        "cons": sentiment["cons"][:3],
        "exam": exam,
        "jd_analysis": jd_analysis,
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
        print(json.dumps({"error":"Usage: python search_jobs.py <resume> <company> [department] [--avoid-exam]"}))
        sys.exit(1)

    resume_path, company = args[0], args[1]
    department = ""
    position = ""
    avoid_exam = "--avoid-exam" in args

    # 解析部门和岗位参数
    non_flag_args = [a for a in args[2:] if not a.startswith("--")]
    if len(non_flag_args) >= 2:
        department = non_flag_args[0]
        position = non_flag_args[1]
    elif len(non_flag_args) == 1:
        # 如果只有一个参数，判断是部门还是岗位
        # 简单启发：包含"部"字的是部门，否则是岗位
        if "部" in non_flag_args[0] or "组" in non_flag_args[0] or "团队" in non_flag_args[0]:
            department = non_flag_args[0]
        else:
            position = non_flag_args[0]

    resume_text = load_resume(resume_path)
    skills = extract_skills_from_resume(resume_text)
    dept_info = f" | 部门: {department}" if department else ""
    print(f"[Analysis] {company}{dept_info} | Skills: {skills['languages']}", file=sys.stderr)

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36", locale="zh-CN")
        page = await ctx.new_page()

        print(f"[Research] Searching {company}{' ' + department if department else ''}...", file=sys.stderr)
        research = await research_company(page, company, department, position, avoid_exam)
        scoring = score_company(skills, research, avoid_exam)

        await browser.close()

    # 简历匹配度
    resume_match = None
    jd_analysis = research.get("jd_analysis")
    if jd_analysis and jd_analysis.get("tech_stack"):
        resume_match = calculate_resume_match(skills, jd_analysis["tech_stack"])

    # 生成摘要
    summary = generate_summary(company, department, research, scoring)

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
        "risk_details": research.get("risk_details", []),
        "controversial": research.get("controversial", False),
        "controversial_dimensions": research.get("controversial_dimensions", []),
        "tags": research.get("tags", []),
        # JD 分析
        "jd_analysis": research.get("jd_analysis"),
        "resume_match": resume_match,
        # 摘要
        "summary": summary,
        "confidence": research.get("confidence", 0.1),
        # 详细信息
        "company": company,
        "department": department,
        "position": position,
        "skills_found": skills,
        "avoid_exam": avoid_exam,
        "exam": research.get("exam", "未评估"),
        "pros": research.get("pros", []),
        "cons": research.get("cons", []),
        "source_distribution": research.get("source_distribution", {}),
        "snippets_count": research.get("snippets_count", 0),
        "timestamp": datetime.now().isoformat(),
    }

    # 保存到 reports 目录
    reports_dir = r"D:\GoProject\src\superAgent\reports"
    os.makedirs(reports_dir, exist_ok=True)
def generate_markdown_report(output: dict, skills: dict) -> str:
    """生成 Markdown 格式的分析报告"""
    company = output.get("company", "")
    department = output.get("department", "")
    position = output.get("position", "")
    overall_score = output.get("overall_score", 0)
    summary = output.get("summary", "")
    confidence = output.get("confidence", 0.1)
    
    # 技术栈信息
    tech_match = output.get("tech_match_score", 0)
    matched = output.get("resume_match", {}).get("matched_skills", [])
    missing = output.get("resume_match", {}).get("missing_skills", [])
    
    # 风险信息
    risk_tags = output.get("risk_tags", [])
    risk_details = output.get("risk_details", [])
    controversial = output.get("controversial", False)
    
    # 评分
    wlb = output.get("wlb_score", 5)
    growth = output.get("growth_score", 5)
    stability = output.get("stability_score", 5)
    perks = output.get("perks_score", 0)
    
    # JD 分析
    jd_analysis = output.get("jd_analysis")
    jd_tech = jd_analysis.get("tech_stack", []) if jd_analysis else []
    job_dirtiness = jd_analysis.get("job_dirtiness", {}) if jd_analysis else {}
    
    # 生成报告
    lines = []
    
    # 标题
    dept_info = f" {department}" if department else ""
    lines.append(f"# 📊 {company}{dept_info} {position} 求职分析报告")
    lines.append("")
    
    # 摘要
    lines.append("## 一、综合评估")
    lines.append("")
    lines.append(f"**{summary}**")
    lines.append("")
    lines.append(f"- 置信度：{confidence*100:.0f}%")
    lines.append(f"- 综合评分：{overall_score}/10")
    lines.append("")
    
    # 评分表
    lines.append("### 评分详情")
    lines.append("")
    lines.append("| 维度 | 评分 | 说明 |")
    lines.append("|------|:--:|------|")
    lines.append(f"| 技术匹配 | {tech_match}/10 | 简历技能与JD匹配度 |")
    lines.append(f"| WLB | {wlb}/10 | 工作生活平衡 |")
    lines.append(f"| 成长性 | {growth}/10 | 晋升空间与技术成长 |")
    lines.append(f"| 稳定性 | {stability}/10 | 公司稳定性 |")
    lines.append(f"| 福利 | {perks}/10 | 生活福利 |")
    lines.append("")
    
    # 风险标签
    if risk_tags:
        lines.append("## 二、风险提示")
        lines.append("")
        for detail in risk_details:
            dim = detail.get("label", "")
            evidence = detail.get("evidence_count", 0)
            controversial_flag = "⚠️ 争议" if detail.get("controversial") else ""
            lines.append(f"- **{dim}**：{evidence}条证据 {controversial_flag}")
        if controversial:
            lines.append("")
            lines.append("> ⚠️ 该岗位存在争议信息，建议面试时重点确认")
        lines.append("")
    
    # 技术匹配
    lines.append("## 三、技术匹配分析")
    lines.append("")
    lines.append("### 你的技能栈")
    lines.append("")
    lines.append(f"- **语言**：{', '.join(skills.get('languages', []))}")
    lines.append(f"- **框架**：{', '.join(skills.get('frameworks', []))}")
    lines.append(f"- **数据库**：{', '.join(skills.get('databases', []))}")
    lines.append(f"- **DevOps**：{', '.join(skills.get('devops', []))}")
    lines.append("")
    
    if jd_tech:
        lines.append("### JD 要求的技术栈")
        lines.append("")
        lines.append(f"- {', '.join(jd_tech)}")
        lines.append("")
    
    if matched or missing:
        lines.append("### 匹配度分析")
        lines.append("")
        if matched:
            lines.append(f"- ✅ **已匹配**：{', '.join(matched)}")
        if missing:
            lines.append(f"- ❌ **缺失**：{', '.join(missing)}")
        match_score = output.get("resume_match", {}).get("match_score", 0)
        lines.append(f"- **匹配度**：{match_score:.1f}%")
        lines.append("")
    
    # 岗位脏度
    if job_dirtiness:
        job_type = job_dirtiness.get("job_type", "")
        workload_risk = job_dirtiness.get("workload_risk", "")
        lines.append("### 岗位类型")
        lines.append("")
        lines.append(f"- **岗位类型**：{job_type}")
        lines.append(f"- **工作负荷风险**：{workload_risk}")
        lines.append("")
    
    # 信源分布
    source_dist = output.get("source_distribution", {})
    if source_dist:
        lines.append("## 四、数据来源")
        lines.append("")
        lines.append("| 来源类型 | 数量 |")
        lines.append("|----------|:--:|")
        source_names = {
            "jd": "招聘信息",
            "official": "官方网站",
            "interview": "面经网站",
            "employee": "员工评价",
            "anonymous": "匿名论坛",
            "news": "新闻媒体",
            "unknown": "其他",
        }
        for src, count in source_dist.items():
            name = source_names.get(src, src)
            lines.append(f"| {name} | {count} |")
        lines.append(f"| **总计** | **{sum(source_dist.values())}** |")
        lines.append("")
    
    # JD 风险
    if jd_analysis and jd_analysis.get("risks"):
        lines.append("## 五、JD 风险分析")
        lines.append("")
        for risk in jd_analysis["risks"]:
            risk_type = risk.get("type", "")
            evidence = risk.get("evidence", [])
            lines.append(f"- **{risk_type}**：{', '.join(evidence)}")
        lines.append("")
    
    # 总结
    lines.append("## 六、综合建议")
    lines.append("")
    if overall_score >= 7:
        lines.append("**强烈推荐面试**")
    elif overall_score >= 5:
        lines.append("**推荐面试，但需关注风险点**")
    else:
        lines.append("**谨慎考虑，建议面试时重点确认风险点**")
    lines.append("")
    lines.append(f"- 技术栈匹配度：{tech_match}/10")
    lines.append(f"- 综合评分：{overall_score}/10")
    lines.append(f"- 置信度：{confidence*100:.0f}%")
    lines.append("")
    
    if risk_tags:
        lines.append("**需要确认的问题**：")
        for tag in risk_tags:
            lines.append(f"- {tag}")
        lines.append("")
    
    lines.append("---")
    lines.append(f"*报告生成时间：{output.get('timestamp', '')}*")
    lines.append(f"*数据来源：实时搜索（{output.get('snippets_count', 0)}条摘要）*")
    
    return "\n".join(lines)
    pos_part = f"-{position}" if position else ""
    base_name = f"{company}{dept_part}{pos_part}-分析报告"
    
    # 保存 JSON（给程序用）
    json_path = os.path.join(reports_dir, f"{base_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[Saved] {json_path}", file=sys.stderr)
    
    # 保存 Markdown（给人看）
    md_path = os.path.join(reports_dir, f"{base_name}.md")
    md_content = generate_markdown_report(output, skills)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[Saved] {md_path}", file=sys.stderr)

    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
