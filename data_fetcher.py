#!/usr/bin/env python3
"""多源数据抓取器 - 从公开数据源采集学校和城市原始数据
v6.0: 示例数据库扩充至10所高校；UGC_SOURCES更正命名为UGC_SOURCES；对齐线上v6.0元数据
v2.0: 扩充UGC社区数据源（校园墙/知乎/豆瓣/贴吧/小红书/B站/微博）
"""

import json, argparse, sys, os
from typing import Dict, Any, List, Optional
from datetime import datetime

SAMPLE_DB = {
    "清华大学": {"city": "北京", "school":
        {"a_plus_disciplines":28,"national_key_labs":12,"research_funding":280,"student_faculty_ratio":10,"library_books":550,
         "four_person_dorm_pct":60,"ac_pct":100,"canteen_count":15,"campus_area_mu":4420,"sports_facilities":20,
         "employment_rate":98,"avg_starting_salary":22,"corp_partnerships":300,"famous_alumni_count":150,"postgrad_recommendation_rate":58,
         "club_count":250,"exchange_programs":180},
        "city_data":{"monthly_rent":3500,"monthly_food":1800,"monthly_transport":300,"subway_lines":27,"airport_distance_km":25,
                "railway_station_distance_km":8,"bus_density_score":9,"tier3_hospitals":35,"large_malls":80,"parks_and_museums":120,
                "safety_index":8.5,"annual_aqi":75,"avg_temperature":13,"avg_humidity":52,"extreme_weather_days":15,
                "gdp_growth_rate":5.2,"tertiary_industry_pct":84,"talent_policy_score":9.5,"price_income_ratio":18}},
    "北京大学": {"city": "北京", "school":
        {"a_plus_disciplines":27,"national_key_labs":11,"research_funding":250,"student_faculty_ratio":11,"library_books":800,
         "four_person_dorm_pct":55,"ac_pct":100,"canteen_count":12,"campus_area_mu":4300,"sports_facilities":18,
         "employment_rate":97.5,"avg_starting_salary":21,"corp_partnerships":280,"famous_alumni_count":160,"postgrad_recommendation_rate":54,
         "club_count":280,"exchange_programs":200},
        "city_data":{"monthly_rent":3500,"monthly_food":1800,"monthly_transport":300,"subway_lines":27,"airport_distance_km":30,
                "railway_station_distance_km":10,"bus_density_score":9,"tier3_hospitals":35,"large_malls":80,"parks_and_museums":120,
                "safety_index":8.5,"annual_aqi":75,"avg_temperature":13,"avg_humidity":52,"extreme_weather_days":15,
                "gdp_growth_rate":5.2,"tertiary_industry_pct":84,"talent_policy_score":9.5,"price_income_ratio":18}},
    "浙江大学": {"city": "杭州", "school":
        {"a_plus_disciplines":19,"national_key_labs":8,"research_funding":180,"student_faculty_ratio":14,"library_books":720,
         "four_person_dorm_pct":45,"ac_pct":98,"canteen_count":10,"campus_area_mu":9330,"sports_facilities":15,
         "employment_rate":96.5,"avg_starting_salary":18,"corp_partnerships":200,"famous_alumni_count":80,"postgrad_recommendation_rate":34,
         "club_count":220,"exchange_programs":150},
        "city_data":{"monthly_rent":2200,"monthly_food":1500,"monthly_transport":200,"subway_lines":12,"airport_distance_km":28,
                "railway_station_distance_km":6,"bus_density_score":8,"tier3_hospitals":15,"large_malls":40,"parks_and_museums":60,
                "safety_index":9,"annual_aqi":55,"avg_temperature":17.2,"avg_humidity":70,"extreme_weather_days":10,
                "gdp_growth_rate":5.8,"tertiary_industry_pct":68,"talent_policy_score":9,"price_income_ratio":13}},
    "复旦大学": {"city": "上海", "school":
        {"a_plus_disciplines":18,"national_key_labs":6,"research_funding":150,"student_faculty_ratio":13,"library_books":520,
         "four_person_dorm_pct":40,"ac_pct":95,"canteen_count":8,"campus_area_mu":3200,"sports_facilities":12,
         "employment_rate":96,"avg_starting_salary":19,"corp_partnerships":220,"famous_alumni_count":90,"postgrad_recommendation_rate":32,
         "club_count":200,"exchange_programs":170},
        "city_data":{"monthly_rent":3800,"monthly_food":1900,"monthly_transport":300,"subway_lines":20,"airport_distance_km":35,
                "railway_station_distance_km":5,"bus_density_score":9.5,"tier3_hospitals":38,"large_malls":90,"parks_and_museums":100,
                "safety_index":9.2,"annual_aqi":65,"avg_temperature":17.3,"avg_humidity":72,"extreme_weather_days":8,
                "gdp_growth_rate":5,"tertiary_industry_pct":74,"talent_policy_score":9,"price_income_ratio":17}},
    "武汉大学": {"city": "武汉", "school":
        {"a_plus_disciplines":12,"national_key_labs":5,"research_funding":100,"student_faculty_ratio":16,"library_books":700,
         "four_person_dorm_pct":50,"ac_pct":90,"canteen_count":12,"campus_area_mu":5195,"sports_facilities":14,
         "employment_rate":94,"avg_starting_salary":14,"corp_partnerships":120,"famous_alumni_count":60,"postgrad_recommendation_rate":28,
         "club_count":180,"exchange_programs":100},
        "city_data":{"monthly_rent":1500,"monthly_food":1200,"monthly_transport":180,"subway_lines":12,"airport_distance_km":22,
                "railway_station_distance_km":8,"bus_density_score":7.5,"tier3_hospitals":20,"large_malls":35,"parks_and_museums":45,
                "safety_index":8,"annual_aqi":68,"avg_temperature":17.1,"avg_humidity":76,"extreme_weather_days":18,
                "gdp_growth_rate":5.5,"tertiary_industry_pct":60,"talent_policy_score":8,"price_income_ratio":11}},
    "中山大学": {"city": "广州", "school":
        {"a_plus_disciplines":14,"national_key_labs":5,"research_funding":110,"student_faculty_ratio":15,"library_books":680,
         "four_person_dorm_pct":35,"ac_pct":99,"canteen_count":10,"campus_area_mu":7140,"sports_facilities":13,
         "employment_rate":94.5,"avg_starting_salary":16,"corp_partnerships":140,"famous_alumni_count":55,"postgrad_recommendation_rate":27,
         "club_count":190,"exchange_programs":130},
        "city_data":{"monthly_rent":2000,"monthly_food":1600,"monthly_transport":250,"subway_lines":16,"airport_distance_km":35,
                "railway_station_distance_km":8,"bus_density_score":8.5,"tier3_hospitals":25,"large_malls":55,"parks_and_museums":50,
                "safety_index":8.5,"annual_aqi":50,"avg_temperature":22.5,"avg_humidity":78,"extreme_weather_days":8,
                "gdp_growth_rate":4.8,"tertiary_industry_pct":72,"talent_policy_score":8.5,"price_income_ratio":14}},
    "上海交通大学": {"city": "上海", "school":
        {"a_plus_disciplines":20,"national_key_labs":8,"research_funding":200,"student_faculty_ratio":12,"library_books":600,
         "four_person_dorm_pct":55,"ac_pct":100,"canteen_count":12,"campus_area_mu":4900,"sports_facilities":18,
         "employment_rate":97,"avg_starting_salary":20,"corp_partnerships":260,"famous_alumni_count":120,"postgrad_recommendation_rate":36,
         "club_count":230,"exchange_programs":190},
        "city_data":{"monthly_rent":3800,"monthly_food":1900,"monthly_transport":300,"subway_lines":20,"airport_distance_km":35,
                "railway_station_distance_km":5,"bus_density_score":9.5,"tier3_hospitals":38,"large_malls":90,"parks_and_museums":100,
                "safety_index":9.2,"annual_aqi":65,"avg_temperature":17.3,"avg_humidity":72,"extreme_weather_days":8,
                "gdp_growth_rate":5,"tertiary_industry_pct":74,"talent_policy_score":9,"price_income_ratio":17}},
    "南京大学": {"city": "南京", "school":
        {"a_plus_disciplines":16,"national_key_labs":7,"research_funding":130,"student_faculty_ratio":13,"library_books":650,
         "four_person_dorm_pct":50,"ac_pct":98,"canteen_count":10,"campus_area_mu":3600,"sports_facilities":14,
         "employment_rate":96,"avg_starting_salary":17,"corp_partnerships":180,"famous_alumni_count":85,"postgrad_recommendation_rate":33,
         "club_count":210,"exchange_programs":160},
        "city_data":{"monthly_rent":1800,"monthly_food":1400,"monthly_transport":200,"subway_lines":11,"airport_distance_km":35,
                "railway_station_distance_km":12,"bus_density_score":8,"tier3_hospitals":22,"large_malls":45,"parks_and_museums":70,
                "safety_index":8.8,"annual_aqi":60,"avg_temperature":16.0,"avg_humidity":72,"extreme_weather_days":12,
                "gdp_growth_rate":5.6,"tertiary_industry_pct":63,"talent_policy_score":8.5,"price_income_ratio":12}},
    "华中科技大学": {"city": "武汉", "school":
        {"a_plus_disciplines":14,"national_key_labs":6,"research_funding":140,"student_faculty_ratio":15,"library_books":640,
         "four_person_dorm_pct":48,"ac_pct":95,"canteen_count":14,"campus_area_mu":7000,"sports_facilities":16,
         "employment_rate":95.5,"avg_starting_salary":15,"corp_partnerships":160,"famous_alumni_count":70,"postgrad_recommendation_rate":28,
         "club_count":200,"exchange_programs":120},
        "city_data":{"monthly_rent":1500,"monthly_food":1200,"monthly_transport":180,"subway_lines":12,"airport_distance_km":22,
                "railway_station_distance_km":8,"bus_density_score":7.5,"tier3_hospitals":20,"large_malls":35,"parks_and_museums":45,
                "safety_index":8,"annual_aqi":68,"avg_temperature":17.1,"avg_humidity":76,"extreme_weather_days":18,
                "gdp_growth_rate":5.5,"tertiary_industry_pct":60,"talent_policy_score":8,"price_income_ratio":11}},
    "西安交通大学": {"city": "西安", "school":
        {"a_plus_disciplines":10,"national_key_labs":5,"research_funding":120,"student_faculty_ratio":14,"library_books":580,
         "four_person_dorm_pct":52,"ac_pct":92,"canteen_count":9,"campus_area_mu":4400,"sports_facilities":12,
         "employment_rate":95,"avg_starting_salary":14,"corp_partnerships":130,"famous_alumni_count":65,"postgrad_recommendation_rate":30,
         "club_count":170,"exchange_programs":100},
        "city_data":{"monthly_rent":1200,"monthly_food":1100,"monthly_transport":150,"subway_lines":9,"airport_distance_km":40,
                "railway_station_distance_km":10,"bus_density_score":7,"tier3_hospitals":18,"large_malls":30,"parks_and_museums":55,
                "safety_index":8.2,"annual_aqi":85,"avg_temperature":14.3,"avg_humidity":60,"extreme_weather_days":14,
                "gdp_growth_rate":5.9,"tertiary_industry_pct":61,"talent_policy_score":8,"price_income_ratio":9}},
}

# UGC数据源配置（v2.0新增）
UGC_SOURCES = {
    "campus_wall": {
        "name": "校园墙",
        "platforms": ["微信", "QQ"],
        "keywords": ["表白墙", "万能墙", "互助墙", "失物招领", "二手交易"],
        "content_types": ["宿舍实拍", "食堂评价", "校园动态", "新生问答", "二手交易"],
        "verification_rules": {
            "recency": "30天内",
            "cross_check": "多墙交叉验证",
            "density": "日均>5条消息"
        }
    },
    "zhihu": {
        "name": "知乎",
        "platforms": ["知乎APP", "网页版"],
        "keywords": ["就读体验", "宿舍条件", "评价", "值得去吗", "就业前景"],
        "content_types": ["深度就读体验", "专业评价", "就业去向", "保研经验", "选课建议"],
        "verification_rules": {
            "min_likes": 100,
            "max_age": "1年内",
            "cross_check": "多回答交叉验证",
            "identity": "优先在校生/校友认证"
        }
    },
    "douban": {
        "name": "豆瓣小组",
        "platforms": ["豆瓣APP", "网页版"],
        "keywords": ["小组", "新生", "租房", "二手", "交友"],
        "content_types": ["租房信息", "二手交易", "新生答疑", "生活攻略"],
        "verification_rules": {
            "recency": "6个月内",
            "min_replies": 10,
            "activity": "小组活跃度"
        }
    },
    "tieba": {
        "name": "百度贴吧",
        "platforms": ["百度贴吧APP", "网页版"],
        "keywords": ["吧", "新生咨询", "2026新生", "专业选择"],
        "content_types": ["新生问答", "校园八卦", "选专业建议", "课程评价", "社团信息"],
        "verification_rules": {
            "quality": "精品帖标识",
            "min_replies": 10,
            "moderator": "吧主推荐"
        }
    },
    "xiaohongshu": {
        "name": "小红书",
        "platforms": ["小红书APP"],
        "keywords": ["新生攻略", "宿舍条件", "食堂探店", "行李准备", "一天vlog"],
        "content_types": ["宿舍实拍", "食堂测评", "新生清单", "校园穿搭", "周边攻略"],
        "verification_rules": {
            "min_collections": 500,
            "max_age": "1年内",
            "image_quality": "图片清晰真实",
            "spam_check": "排除广告嫌疑"
        }
    },
    "bilibili": {
        "name": "B站",
        "platforms": ["B站APP", "网页版"],
        "keywords": ["宿舍tour", "一天", "vlog", "食堂测评", "开学"],
        "content_types": ["宿舍tour视频", "校园一日vlog", "食堂测评", "开学记录", "弹幕反馈"],
        "verification_rules": {
            "min_views": 10000,
            "danmaku_quality": "弹幕互动质量",
            "resolution": "720p以上",
            "uploader_identity": "优先在校生/校友"
        }
    },
    "weibo": {
        "name": "微博超话",
        "platforms": ["微博APP", "网页版"],
        "keywords": ["超话", "新生", "开学"],
        "content_types": ["实时动态", "热点讨论", "官方通知", "学生活动"],
        "verification_rules": {
            "read_volume": "阅读量指标",
            "interaction": "互动量",
            "host_identity": "官方认证优先",
            "recency": "实时性"
        }
    }
}


class DataFetcher:
    def __init__(self, out="./data/raw"):
        self.out = out; os.makedirs(out, exist_ok=True)

    def get_sample(self, name):
        for n, d in SAMPLE_DB.items():
            if name in n or n in name:
                return {"school_name": n, "city_name": d["city"], "school": dict(d["school"]),
                        "city": dict(d["city_data"]), "_meta": {"source":"sample_database","last_updated":"2026-09-08","reliability":"reference_only"}}
        return None

    def create_empty(self, school, city=""):
        return {"school_name": school, "city_name": city,
                "school":{"a_plus_disciplines":0,"national_key_labs":0,"research_funding":0,"student_faculty_ratio":18,"library_books":500,
                         "four_person_dorm_pct":40,"ac_pct":85,"canteen_count":5,"campus_area_mu":1000,"sports_facilities":8,
                         "employment_rate":92,"avg_starting_salary":12,"corp_partnerships":50,"famous_alumni_count":15,"postgrad_recommendation_rate":15,
                         "club_count":150,"exchange_programs":50},
                "city":{"monthly_rent":1500,"monthly_food":1200,"monthly_transport":200,"subway_lines":3,"airport_distance_km":30,
                        "railway_station_distance_km":10,"bus_density_score":6,"tier3_hospitals":8,"large_malls":15,"parks_and_museums":25,
                        "safety_index":7,"annual_aqi":70,"avg_temperature":16,"avg_humidity":68,"extreme_weather_days":12,
                        "gdp_growth_rate":6,"tertiary_industry_pct":58,"talent_policy_score":5,"price_income_ratio":10},
                "_meta":{"source":"empty_template","last_updated":datetime.now().isoformat(),"reliability":"needs_population"}}

    def get_ugc_search_queries(self, school_name, city_name=""):
        """生成UGC数据源的搜索词列表（v2.0新增）"""
        queries = []
        
        for source_id, source_config in UGC_SOURCES.items():
            for keyword_template in source_config["keywords"]:
                if "{学校}" in keyword_template or "{学校名}" in keyword_template:
                    query = keyword_template.replace("{学校}", school_name).replace("{学校名}", school_name)
                elif "{城市}" in keyword_template or "{城市名}" in keyword_template:
                    if city_name:
                        query = keyword_template.replace("{城市}", city_name).replace("{城市名}", city_name)
                    else:
                        continue
                else:
                    query = f"{school_name} {keyword_template}"
                
                queries.append({
                    "source": source_id,
                    "source_name": source_config["name"],
                    "query": query,
                    "content_types": source_config["content_types"],
                    "verification": source_config["verification_rules"]
                })
        
        return queries

    def save(self, data, fn=None):
        if fn is None: fn = data.get("school_name", "unknown").replace("/", "_") + ".json"
        fp = os.path.join(self.out, fn)
        with open(fp, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
        return fp

def main():
    ap = argparse.ArgumentParser(description="数据抓取器 v6.0")
    ap.add_argument("--school","-s",default=None); ap.add_argument("--city","-c",default=None)
    ap.add_argument("--template-only",action="store_true"); ap.add_argument("--output-dir","-o",default="./data/raw/")
    ap.add_argument("--list-ugc-sources",action="store_true",help="列出所有UGC数据源")
    ap.add_argument("--generate-ugc-queries",action="store_true",help="生成UGC搜索词列表")
    args = ap.parse_args()
    df = DataFetcher(args.output_dir)
    
    if args.list_ugc_sources:
        print("📋 可用UGC数据源:\n")
        for source_id, config in UGC_SOURCES.items():
            print(f"  [{source_id}] {config['name']}")
            print(f"    平台: {', '.join(config['platforms'])}")
            print(f"    关键词: {', '.join(config['keywords'][:3])}...")
            print(f"    内容类型: {', '.join(config['content_types'][:3])}...")
            print()
        return
    
    if not args.school: ap.error("请指定 --school")
    
    if args.template_only:
        data = df.create_empty(args.school, args.city or ""); print("\n📝 生成空白模板")
    else:
        data = df.get_sample(args.school)
        if data: print(f"\n✅ 找到: {data['school_name']}")
        else: print(f"\n⚠️ 未找到'{args.school}'，生成空白模板"); data = df.create_empty(args.school, args.city or "")
    
    if args.generate_ugc_queries:
        ugc_queries = df.get_ugc_search_queries(args.school, args.city or "")
        data["_ugc_queries"] = ugc_queries
        print(f"\n🌐 生成{len(ugc_queries)}条UGC搜索词:")
        for q in ugc_queries:
            print(f"  [{q['source_name']}] {q['query']}")
    
    path = df.save(data); print(f"\n💾 已保存: {path}")

if __name__ == "__main__": main()
