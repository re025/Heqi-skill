#!/usr/bin/env python3
"""校外租房网站生成器 - 根据目标学校/城市数据自动生成单文件HTML租房指南站（v6.0新增）

输入 data_fetcher / weight_calculator 输出的JSON（自动读取学校/城市/租金等字段），也可用参数直接指定。
输出自包含HTML（内联CSS、零依赖），浏览器直接打开即可查看或分享给家长。
"""
import json, argparse, os, html, urllib.parse
from datetime import datetime

SEARCH_TEMPLATES = [
    "{城市} {学校} 附近 租房",
    "{学校} 东门/南门 单间 月租",
    "{城市} 大学城 合租 找室友",
    "{学校} 转租 短租 闲鱼",
    "{城市} {学校} 租房 豆瓣小组",
]

PITFALLS = [
    ("价格异常低于市场价", "低价引流帖居多，实际看房时被告知'刚租掉'，转而推销高价房源"),
    ("未看房先交钱", "任何'定金/诚意金/看房费'都不要在线转账，坚持实地看房后再付款"),
    ("二房东/托管公司", "要求出示房产证与房东身份证，核实签约主体；托管公寓查公司工商信息"),
    ("合同条款模糊", "明确租期、押金退还条件、水电网物业费标准、维修责任、提前退租违约条款"),
    ("甲醛与安全隐患", "新装修房源要求出示检测报告或自测；检查消防通道、门窗锁具"),
    ("隔断房/群租房", "部分城市明令禁止，存在被清退风险，看房时确认户型原始结构"),
]

VIEWING_CHECKLIST = [
    "白天+晚上各看一次：采光、噪音、治安",
    "手机信号与实测网速（上网课/游戏刚需）",
    "水电表读数拍照留证，确认民水民电还是商水商电",
    "家电家具逐一试用并拍照记录现有损坏",
    "通勤实测：步行/骑行/公交到校门口时间",
    "周边配套：超市、食堂/外卖、药店、打印店",
    "确认供暖/空调/热水器工作正常",
    "与现租客/邻居了解房东口碑与小区管理",
]

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: #eef2f7; color: #2d3748; line-height: 1.7; }
header { background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; padding: 48px 24px; text-align: center; }
header h1 { font-size: 28px; margin-bottom: 8px; }
header p { opacity: .92; font-size: 14px; }
main { max-width: 960px; margin: 0 auto; padding: 24px 16px 48px; }
section { background: #fff; border-radius: 14px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,.05); }
h2 { font-size: 20px; margin-bottom: 14px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; }
.card { border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; }
.price { font-size: 24px; font-weight: 700; color: #667eea; margin: 6px 0 2px; }
.price span { font-size: 12px; font-weight: 400; color: #718096; }
.total { font-size: 13px; color: #2f855a; font-weight: 600; margin-bottom: 8px; }
.suit { font-size: 12px; color: #718096; }
.tag { display: inline-block; font-size: 11px; background: #ebf4ff; color: #2b6cb0; border-radius: 999px; padding: 1px 10px; margin-bottom: 6px; }
.card a { display: inline-block; margin-top: 8px; font-size: 13px; color: #667eea; text-decoration: none; font-weight: 600; }
.chip { display: inline-block; background: #f7fafc; border: 1px solid #cbd5e0; border-radius: 999px; padding: 4px 14px; margin: 4px 6px 4px 0; font-size: 13px; }
.warn { border-left: 4px solid #f6ad55; }
.warn li, .check li { margin: 8px 0 8px 18px; font-size: 14px; }
.check li::marker { content: "\\2610  "; }
.note { font-size: 12px; color: #a0aec0; margin-top: 10px; }
footer { text-align: center; font-size: 12px; color: #a0aec0; padding: 0 16px 32px; }
"""

def esc(s):
    return html.escape(str(s), quote=True)

def load_input(args):
    data = {}
    if args.data:
        with open(args.data, encoding="utf-8") as f:
            data = json.load(f)
    meta = data.get("_meta", {}) or {}
    city_data = data.get("city", {}) or {}
    school = args.school or data.get("school_name") or meta.get("school_name") or "目标大学"
    city = args.city or data.get("city_name") or meta.get("city_name") or "学校所在城市"
    rent = args.rent or city_data.get("monthly_rent") or 1500
    food = args.food or city_data.get("monthly_food") or 1200
    transport = city_data.get("monthly_transport") or 200
    return school, city, int(rent), int(food), int(transport)

def platforms(city):
    douban_url = "https://www.douban.com/group/search?cat=1019&search_text=" + urllib.parse.quote(city + " 租房")
    return [
        ("贝壳找房 / 链家", "https://www.ke.com", "平台直租", "真房源率较高，支持地图找房与VR看房，中介费透明"),
        ("自如", "https://www.ziroom.com", "长租公寓", "统一装修、拎包入住，支持月付，适合怕折腾的新生"),
        ("安居客", "https://www.anjuke.com", "综合平台", "房源量大覆盖广，注意甄别低价引流帖"),
        ("58同城", "https://www.58.com", "综合平台", "个人房源多，筛选'个人房源'标签，谨防虚假信息"),
        ("闲鱼", "https://www.goofish.com", "转租/二手", "学长学姐转租、短租，二手家具家电一站解决"),
        ("豆瓣租房小组", douban_url, "社区", "已按城市预填搜索，个人转租与找室友信息多"),
        ("Wellcee 唯心所寓", "https://www.wellcee.com", "无中介", "主打无中介个人房源，支持宠物友好筛选"),
        ("学校万能墙/表白墙", "#search", "校园墙", "微信/QQ搜学校名+'万能墙'，校内转租、找室友最灵通"),
    ]

def budget_tiers(rent, food, transport):
    defs = [
        ("合租·经济型", 0.6, "与1-2名室友合租次卧/小单间", "预算有限，愿意共享公共空间"),
        ("合租·舒适型", 0.85, "合租主卧或独立大单间", "兼顾隐私与性价比的主流选择"),
        ("整租·一居室", 1.0, "独立一居室/loft", "注重独立空间与生活质量"),
        ("整租·品质型", 1.3, "品质公寓/品牌长租公寓", "预算充足，追求省心与服务"),
    ]
    return [(name, int(rent * k), desc, suit) for name, k, desc, suit in defs]

def render(school, city, rent, food, transport):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    tier_html = "\n".join(
        '<div class="card"><h3>%s</h3><div class="price">¥%d<span> /月 房租</span></div>'
        '<div class="total">月总支出约 ¥%d（含餐饮+交通）</div><p>%s</p><p class="suit">适合：%s</p></div>'
        % (esc(n), r, r + food + transport, esc(d), esc(s))
        for n, r, d, s in budget_tiers(rent, food, transport))
    plat_html = "\n".join(
        '<div class="card"><span class="tag">%s</span><h3>%s</h3><p>%s</p><a href="%s" target="_blank" rel="noopener">前往平台 →</a></div>'
        % (esc(t), esc(n), esc(d), esc(u))
        for n, u, t, d in platforms(city))
    chips = "\n".join('<span class="chip">%s</span>' % esc(t.format(学校=school, 城市=city)) for t in SEARCH_TEMPLATES)
    pit_html = "\n".join('<li><strong>%s</strong> — %s</li>' % (esc(t), esc(d)) for t, d in PITFALLS)
    check_html = "\n".join('<li>%s</li>' % esc(c) for c in VIEWING_CHECKLIST)
    tpl = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__SCHOOL__ 校外租房指南站</title>
<style>__CSS__</style>
</head>
<body>
<header>
<h1>🏠 __SCHOOL__ 校外租房指南站</h1>
<p>📍 __CITY__ · 基准租金 ¥__RENT__/月（一居室） · 生成时间 __NOW__</p>
</header>
<main>
<section>
<h2>💰 租金预算梯度</h2>
<div class="grid">
__TIERS__
</div>
<p class="note">租金为__CITY__示例均价估算（一居室 ¥__RENT__/月为基准），餐饮 ¥__FOOD__/月、交通 ¥__TRANS__/月计入月总支出；实际价格请以平台实时查询为准。</p>
</section>
<section id="search">
<h2>🔗 主流租房平台直达</h2>
<div class="grid">
__PLATS__
</div>
</section>
<section>
<h2>🔍 本地化搜索关键词</h2>
__CHIPS__
<p class="note">复制关键词到对应平台搜索；校园墙请在微信/QQ内搜索。</p>
</section>
<section class="warn">
<h2>⚠️ 防骗避坑清单</h2>
<ul>
__PITS__
</ul>
</section>
<section class="check">
<h2>✅ 看房检查表</h2>
<ul>
__CHECKS__
</ul>
</section>
</main>
<footer>本指南由「何栖」自动生成 · 数据为示例估算，请实地看房核实 · 谨防租房诈骗</footer>
</body>
</html>"""
    for k, v in [("__CSS__", CSS), ("__TIERS__", tier_html), ("__PLATS__", plat_html),
                 ("__CHIPS__", chips), ("__PITS__", pit_html), ("__CHECKS__", check_html),
                 ("__SCHOOL__", esc(school)), ("__CITY__", esc(city)),
                 ("__RENT__", str(rent)), ("__FOOD__", str(food)),
                 ("__TRANS__", str(transport)), ("__NOW__", now)]:
        tpl = tpl.replace(k, v)
    return tpl

def main():
    ap = argparse.ArgumentParser(description="校外租房网站生成器 v6.0")
    ap.add_argument("--data", help="数据JSON文件（data_fetcher 或 weight_calculator 输出）")
    ap.add_argument("--school", help="学校名称（覆盖数据文件）")
    ap.add_argument("--city", help="城市名称（覆盖数据文件）")
    ap.add_argument("--rent", type=int, help="城市一居室月均租金（覆盖数据文件）")
    ap.add_argument("--food", type=int, help="月均餐饮支出（覆盖数据文件）")
    ap.add_argument("--output", required=True, help="输出HTML文件路径")
    args = ap.parse_args()
    school, city, rent, food, transport = load_input(args)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(render(school, city, rent, food, transport))
    print(f"✅ 租房指南站已生成: {args.output}")
    print(f"   学校: {school} | 城市: {city} | 基准租金: ¥{rent}/月")
    print("   用浏览器打开即可查看，可直接分享单文件")

if __name__ == "__main__":
    main()
