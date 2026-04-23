import os, glob, json, requests, subprocess, re
from datetime import datetime

today = subprocess.check_output("date +%Y-%m-%d", shell=True).decode().strip()

md_file = f"data/summaries/horizon-{today}-zh.md"
if not os.path.exists(md_file):
    files = sorted(glob.glob("data/summaries/horizon-*-zh.md"))
    md_file = files[-1] if files else None

raw_content = open(md_file).read() if md_file else ""

api_key = os.environ.get("DEEPSEEK_API_KEY", "")

prompt = f"""你是一位专业的 AI 科技日报编辑。请根据下面的原始内容，整理成 JSON 格式的日报。

原始内容：
{raw_content[:6000]}

请严格按照以下 JSON 格式输出，不要输出任何其他内容：
{{
  "date": "{today}",
  "must_know": [
    {{"rank": 1, "title": "标题", "why": "为什么重要（1-2句话，口语化）", "tags": ["标签1", "标签2"]}},
    {{"rank": 2, "title": "标题", "why": "为什么重要", "tags": ["标签1"]}},
    {{"rank": 3, "title": "标题", "why": "为什么重要", "tags": ["标签1"]}}
  ],
  "boss_says": [
    {{"name": "人名", "role": "职位/身份", "initials": "缩写两字母", "quote": "观点原文或摘要", "comment": "编辑点评（犀利一点，说出真实判断）"}},
    {{"name": "人名", "role": "职位", "initials": "缩写", "quote": "观点", "comment": "点评"}}
  ],
  "open_source": [
    {{"name": "项目名", "stars": "★ 12k", "hot": "今日 +500", "desc": "用大白话说清楚这个项目是干什么的，适合谁用", "lang": "Python", "use_case": "适合：XXX场景"}},
    {{"name": "项目名", "stars": "★ 8k", "hot": "", "desc": "描述", "lang": "TypeScript", "use_case": "适合：XXX"}}
  ],
  "landing": [
    {{"amount": "$2亿", "type": "A轮", "company": "公司名", "desc": "一句话说清楚这家公司做什么、融资有什么意义"}},
    {{"amount": "上线", "type": "新产品", "company": "产品名", "desc": "描述"}}
  ],
  "agent_news": [
    {{"badge": "框架更新", "title": "标题", "desc": "描述"}},
    {{"badge": "真实落地", "title": "标题", "desc": "描述"}}
  ],
  "insights": [
    {{"text": "趋势洞察内容，要有观点，不要废话"}},
    {{"text": "第二条洞察"}}
  ]
}}

要求：
1. 全部用中文
2. 语言口语化，适合通勤路上阅读
3. 大佬优先选：Karpathy、Altman、黄仁勋、马斯克、LeCun、Hinton、李飞飞等 AI 领域知名人物
4. 开源项目优先选今日涨星快的和 Agent 相关的，至少 10 个
5. 落地风向标至少 6 条，包含融资、产品上线、企业落地案例
6. 大佬说了啥至少 5 条，优先选有争议或有洞见的观点
7. Agent 动态至少 5 条
8. 趋势洞察至少 4 条
6. 如果原始内容中某板块信息不足，用当前 AI 领域真实的近期动态补充
7. JSON 必须合法，不要有多余的逗号或注释
8. 所有字符串值中不能包含换行符，请用空格代替"""

try:
    resp = requests.post(
        ""https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": "qwen3.5-plus", "messages": [{"role": "user", "content": prompt}], "max_tokens": 3000},
        timeout=120
    )
    result = resp.json()
    content = result["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
    print("=== DeepSeek 返回内容 ===")
    print(content[:3000])
    print("=== 返回内容结束 ===")
    data = json.loads(content.strip())
    print("AI 整理成功")
except Exception as e:
    print(f"AI 整理失败: {e}，使用默认数据")
    data = {
        "date": today,
        "must_know": [{"rank": 1, "title": "今日日报生成中", "why": "系统正在调试中，明天起正常推送", "tags": ["系统"]}],
        "boss_says": [],
        "open_source": [],
        "landing": [],
        "agent_news": [],
        "insights": [{"text": "系统调试中，明天起正常推送完整内容"}]
    }

def tags_html(tags):
    return "".join(f'<span class="tag">{t}</span>' for t in tags)

def must_cards(items):
    html = ""
    for item in items:
        html += f"""<div class="must-card">
<div class="must-rank">{item.get('rank','')}</div>
<div class="must-title">{item.get('title','')}</div>
<div class="must-why">{item.get('why','')}</div>
<div class="must-tags">{tags_html(item.get('tags',[]))}</div>
</div>"""
    return html

colors = ["#E6F1FB:#0C447C","#EAF3DE:#27500A","#F1EFE8:#444441","#FAEEDA:#633806","#EEEDFE:#3C3489","#FBEAF0:#72243E"]

def boss_cards(items):
    html = ""
    for i, item in enumerate(items):
        bg, fg = colors[i % len(colors)].split(":")
        html += f"""<div class="boss-card">
<div class="boss-header">
<div class="boss-avatar" style="background:{bg};color:{fg}">{item.get('initials','AI')}</div>
<div class="boss-info">
<div class="boss-name">{item.get('name','')}</div>
<div class="boss-handle">{item.get('role','')}</div>
</div>
</div>
<div class="boss-quote">{item.get('quote','')}</div>
<div class="boss-comment">{item.get('comment','')}</div>
</div>"""
    return html

def open_cards(items):
    html = ""
    for item in items:
        hot_html = f'<span class="open-hot">{item["hot"]}</span>' if item.get("hot") else ""
        html += f"""<div class="open-card">
<div class="open-header">
<div class="open-name">{item.get('name','')}</div>
<div class="open-right">{hot_html}<span class="open-stars">{item.get('stars','')}</span></div>
</div>
<div class="open-desc">{item.get('desc','')}</div>
<div class="open-meta"><span class="lang-badge">{item.get('lang','')}</span><span class="open-use">{item.get('use_case','')}</span></div>
</div>"""
    return html

def landing_cards(items):
    html = ""
    for item in items:
        html += f"""<div class="fund-card">
<div class="fund-amount">{item.get('amount','')}<span>{item.get('type','')}</span></div>
<div class="fund-content">
<div class="fund-company">{item.get('company','')}</div>
<div class="fund-desc">{item.get('desc','')}</div>
</div>
</div>"""
    return html

def agent_cards(items):
    html = ""
    for item in items:
        html += f"""<div class="agent-card">
<div class="agent-badge">{item.get('badge','')}</div>
<div class="agent-title">{item.get('title','')}</div>
<div class="agent-desc">{item.get('desc','')}</div>
</div>"""
    return html

def insight_cards(items):
    html = ""
    for item in items:
        html += f'<div class="insight-card"><div class="insight-text">{item.get("text","")}</div></div>'
    return html

weekdays = ["周一","周二","周三","周四","周五","周六","周日"]
wd = weekdays[datetime.strptime(today, "%Y-%m-%d").weekday()]

html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>AI 科技日报 {today}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Helvetica Neue',sans-serif;background:#f7f7f5;color:#222;line-height:1.6}}
.page{{max-width:680px;margin:0 auto;padding:16px;background:#fff;min-height:100vh}}
.header{{padding:20px 0 16px;border-bottom:1px solid #eee;margin-bottom:20px}}
.header-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}}
.logo{{font-size:18px;font-weight:600;color:#111}}
.date-badge{{font-size:12px;color:#888;background:#f5f5f3;padding:4px 10px;border-radius:20px;border:1px solid #e8e8e5}}
.subtitle{{font-size:13px;color:#888}}
.section{{margin-bottom:28px}}
.section-header{{display:flex;align-items:center;gap:8px;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #eee}}
.section-icon{{width:28px;height:28px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}}
.icon-must{{background:#E6F1FB}}.icon-boss{{background:#FBEAF0}}.icon-open{{background:#EAF3DE}}
.icon-fund{{background:#FAEEDA}}.icon-agent{{background:#EEEDFE}}.icon-insight{{background:#E1F5EE}}
.section-title{{font-size:15px;font-weight:600;color:#111}}
.section-count{{font-size:12px;color:#888;margin-left:auto;background:#f5f5f3;padding:2px 8px;border-radius:10px}}
.must-card{{background:#fff;border:1px solid #eee;border-radius:12px;padding:14px;margin-bottom:10px}}
.must-card:last-child{{margin-bottom:0}}
.must-rank{{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:6px;font-size:11px;font-weight:600;margin-bottom:8px;background:#E6F1FB;color:#0C447C}}
.must-title{{font-size:14px;font-weight:600;color:#111;margin-bottom:6px;line-height:1.5}}
.must-why{{font-size:13px;color:#666;line-height:1.6;margin-bottom:8px}}
.must-tags{{display:flex;gap:6px;flex-wrap:wrap}}
.tag{{font-size:11px;padding:2px 8px;border-radius:10px;border:1px solid #eee;color:#888}}
.boss-card{{background:#fff;border:1px solid #eee;border-radius:12px;padding:14px;margin-bottom:10px}}
.boss-card:last-child{{margin-bottom:0}}
.boss-header{{display:flex;align-items:center;gap:10px;margin-bottom:10px}}
.boss-avatar{{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;flex-shrink:0}}
.boss-name{{font-size:13px;font-weight:600;color:#111}}
.boss-handle{{font-size:11px;color:#888}}
.boss-quote{{font-size:13px;color:#111;line-height:1.7;margin-bottom:8px;padding-left:10px;border-left:2px solid #ddd}}
.boss-comment{{font-size:12px;color:#666;line-height:1.6;background:#f7f7f5;padding:8px 10px;border-radius:8px}}
.open-card{{background:#fff;border:1px solid #eee;border-radius:12px;padding:14px;margin-bottom:10px}}
.open-card:last-child{{margin-bottom:0}}
.open-header{{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:6px}}
.open-name{{font-size:14px;font-weight:600;color:#111}}
.open-right{{display:flex;align-items:center;gap:6px;flex-shrink:0}}
.open-stars{{font-size:12px;color:#BA7517;background:#FAEEDA;padding:2px 8px;border-radius:10px}}
.open-hot{{font-size:11px;color:#993C1D;background:#FAECE7;padding:2px 8px;border-radius:10px}}
.open-desc{{font-size:13px;color:#666;line-height:1.6;margin-bottom:8px}}
.open-meta{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.lang-badge{{font-size:11px;padding:2px 8px;border-radius:10px;background:#EAF3DE;color:#27500A;border:1px solid #C0DD97}}
.open-use{{font-size:12px;color:#888}}
.fund-card{{background:#fff;border:1px solid #eee;border-radius:12px;padding:14px;margin-bottom:10px;display:flex;gap:12px;align-items:flex-start}}
.fund-card:last-child{{margin-bottom:0}}
.fund-amount{{background:#FAEEDA;color:#633806;font-size:13px;font-weight:600;padding:6px 10px;border-radius:8px;text-align:center;min-width:56px;flex-shrink:0;line-height:1.4}}
.fund-amount span{{display:block;font-size:10px;font-weight:400;color:#854F0B;margin-top:2px}}
.fund-company{{font-size:14px;font-weight:600;color:#111;margin-bottom:4px}}
.fund-desc{{font-size:13px;color:#666;line-height:1.6}}
.agent-card{{background:#fff;border:1px solid #eee;border-radius:12px;padding:14px;margin-bottom:10px}}
.agent-card:last-child{{margin-bottom:0}}
.agent-badge{{display:inline-block;font-size:11px;padding:2px 8px;border-radius:10px;background:#EEEDFE;color:#3C3489;margin-bottom:8px}}
.agent-title{{font-size:14px;font-weight:600;color:#111;margin-bottom:6px;line-height:1.5}}
.agent-desc{{font-size:13px;color:#666;line-height:1.6}}
.insight-card{{border-left:3px solid #1D9E75;padding:12px 14px;margin-bottom:10px;background:#f7f7f5;border-radius:0 12px 12px 0}}
.insight-card:last-child{{margin-bottom:0}}
.insight-text{{font-size:14px;color:#111;line-height:1.7}}
.footer{{text-align:center;padding:20px 0 8px;border-top:1px solid #eee;margin-top:8px}}
.footer-text{{font-size:12px;color:#aaa}}
</style>
</head>
<body>
<div class="page">
<div class="header">
<div class="header-top">
<div class="logo">AI 科技日报</div>
<div class="date-badge">{today} {wd}</div>
</div>
<div class="subtitle">每天 08:00 自动更新 · DeepSeek 精选</div>
</div>
<div class="section">
<div class="section-header">
<div class="section-icon icon-must">⚡</div>
<div class="section-title">今日必知</div>
<div class="section-count">{len(data.get('must_know',[]))} 条</div>
</div>
{must_cards(data.get('must_know',[]))}
</div>
<div class="section">
<div class="section-header">
<div class="section-icon icon-boss">💬</div>
<div class="section-title">大佬说了啥</div>
<div class="section-count">{len(data.get('boss_says',[]))} 条</div>
</div>
{boss_cards(data.get('boss_says',[]))}
</div>
<div class="section">
<div class="section-header">
<div class="section-icon icon-open">🔧</div>
<div class="section-title">热门开源项目</div>
<div class="section-count">{len(data.get('open_source',[]))} 个</div>
</div>
{open_cards(data.get('open_source',[]))}
</div>
<div class="section">
<div class="section-header">
<div class="section-icon icon-fund">💰</div>
<div class="section-title">落地风向标</div>
<div class="section-count">{len(data.get('landing',[]))} 条</div>
</div>
{landing_cards(data.get('landing',[]))}
</div>
<div class="section">
<div class="section-header">
<div class="section-icon icon-agent">🤖</div>
<div class="section-title">Agent 动态</div>
<div class="section-count">{len(data.get('agent_news',[]))} 条</div>
</div>
{agent_cards(data.get('agent_news',[]))}
</div>
<div class="section">
<div class="section-header">
<div class="section-icon icon-insight">🔮</div>
<div class="section-title">趋势洞察</div>
<div class="section-count">{len(data.get('insights',[]))} 条</div>
</div>
{insight_cards(data.get('insights',[]))}
</div>
<div class="footer">
<div class="footer-text">每天 08:00 自动更新 · maxwin7373-wq.github.io/ai-daily-report</div>
</div>
</div>
</body>
</html>"""

os.makedirs("_site", exist_ok=True)
with open("_site/index.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"网页生成成功，板块：{list(data.keys())}")
