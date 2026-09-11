#!/usr/bin/env python3
"""报告生成器 - 将评分结果转换为Markdown决策报告或对比表格
v6.0: 修复报告显示'?'、配置方案打印为字面量等遗留错误；配套新增 scripts/rental_site_generator.py 租房网站生成
v2.0: 新增深度维度分析功能（针对用户最关注的维度展开详情）
"""

import json, argparse, sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

LABELS = {
    "academic":("学术资源","🎓"),"campus_env":("校园环境","🏫"),
    "career":("就业前景","💼"),"student_life":("学生活动","🎭"),
    "living_cost":("生活成本","💰"),"transport":("交通便利","🚇"),
    "lifestyle":("生活品质","🌸"),"climate":("气候环境","🌤️"),
    "development":("城市发展","📈"),
}

# 深度分析模板（v2.0新增）
DEEP_DIVE_TEMPLATES = {
    "academic": {
        "title": "🎓 学术资源深度分析",
        "sub_indicators": [
            ("a_plus_disciplines", "A+学科数", "个", "教育部学科评估结果"),
            ("national_key_labs", "国家重点实验室", "个", "科技部认定"),
            ("research_funding", "科研经费", "亿元", "年度到账科研经费"),
            ("student_faculty_ratio", "师生比", ":1", "生师比，越低越好"),
            ("library_books", "图书馆藏书", "万册", "纸质+电子资源总量"),
        ],
        "evidence_queries": [
            "{学校} A+学科 详细名单",
            "{学校} 国家重点实验室 研究方向",
            "{学校} 保研去向 清华 北大",
            "{学校} 考研升学率 专业",
        ],
        "suggestions": [
            "关注学校的王牌专业，优先选择A+学科相关专业",
            "了解实验室本科生参与科研的机会",
            "提前规划保研/考研路径，关注历年录取数据",
            "利用图书馆资源和学术数据库提升研究能力",
        ]
    },
    "campus_env": {
        "title": "🏫 校园环境深度分析",
        "sub_indicators": [
            ("four_person_dorm_pct", "4人间宿舍比例", "%", "住宿条件舒适度指标"),
            ("ac_pct", "空调覆盖率", "%", "宿舍/教室空调配备情况"),
            ("canteen_count", "食堂数量", "个", "校园餐饮选择丰富度"),
            ("campus_area_mu", "校园面积", "亩", "办学空间规模"),
            ("sports_facilities", "运动设施数量", "个", "体育馆/操场/游泳馆等"),
        ],
        "evidence_queries": [
            "{学校} 宿舍条件 实拍 图片",
            "{学校} 食堂 价格 菜品 推荐",
            "{学校} 表白墙 最新消息",
            "{学校} 宿舍 tour B站",
        ],
        "suggestions": [
            "提前了解所在学院/专业的宿舍分配情况（不同楼栋条件可能差异很大）",
            "关注食堂价格和菜品，制定餐饮预算",
            "了解校园周边的生活配套（超市/药店/银行）",
            "加入新生群获取学长学姐的实地经验分享",
        ]
    },
    "career": {
        "title": "💼 就业前景深度分析",
        "sub_indicators": [
            ("employment_rate", "就业率", "%", "毕业去向落实率"),
            ("avg_starting_salary", "平均起薪", "万元/年", "应届毕业生平均年薪"),
            ("corp_partnerships", "企业合作数量", "家", "校企合作/实习基地"),
            ("famous_alumni_count", "知名校友数", "人", "行业影响力指标"),
            ("postgrad_recommendation_rate", "保研率", "%", "推荐免试攻读研究生比例"),
        ],
        "evidence_queries": [
            "{学校} 就业质量报告 2025",
            "{学校} 毕业生 去向 行业",
            "{学校} 校招 企业 名单",
            "{学校} 保研率 各学院",
        ],
        "suggestions": [
            "关注目标行业的校招企业列表，提前准备实习",
            "了解校友网络分布，利用校友资源获取内推机会",
            "平衡就业和深造：如果保研率高且你有学术兴趣，可考虑读研",
            "关注学校就业指导中心的资源和活动",
        ]
    },
    "student_life": {
        "title": "🎭 学生活动深度分析",
        "sub_indicators": [
            ("club_count", "社团数量", "个", "官方注册学生社团总数"),
            ("exchange_programs", "国际交流项目", "个", "海外交换/双学位项目数"),
        ],
        "evidence_queries": [
            "{学校} 社团 招新 列表",
            "{学校} 国际交流 项目 申请",
            "{学校} 学生活动 精彩瞬间",
            "{学校} 学生会 组织",
        ],
        "suggestions": [
            "开学季关注百团大战（社团招新），选择1-2个深度参与",
            "提前了解国际交流项目的申请条件和时间节点",
            "平衡学业和课外活动，避免过度分散精力",
            "主动创建或加入感兴趣的小众社群",
        ]
    },
    "living_cost": {
        "title": "💰 生活成本深度分析",
        "sub_indicators": [
            ("monthly_rent", "月均房租", "元", "校外合租单间均价"),
            ("monthly_food", "月餐饮费", "元", "食堂+外出就餐"),
            ("monthly_transport", "月交通费", "元", "地铁/公交/共享单车"),
        ],
        "evidence_queries": [
            "{城市} 大学生 月生活费 2025",
            "{城市} 大学城 租房 价格",
            "{城市} 物价 水平 学生",
            "{城市} 大学生 花费 攻略",
        ],
        "suggestions": [
            "制定详细月度预算：建议50%餐饮+20%交通+20%娱乐购物+10%应急",
            "优先选择校内食堂就餐（性价比最高）",
            "了解城市的学生优惠（公交/景区/博物馆）",
            "考虑兼职机会但不要影响学业",
        ]
    },
    "transport": {
        "title": "🚇 交通便利深度分析",
        "sub_indicators": [
            ("subway_lines", "地铁线路数", "条", "城市轨道交通覆盖"),
            ("airport_distance_km", "距机场距离", "km", "航空出行便捷度"),
            ("railway_station_distance_km", "距火车站距离", "km", "高铁出行便捷度"),
            ("bus_density_score", "公交密度评分", "分", "公交线路覆盖度1-10分"),
        ],
        "evidence_queries": [
            "{城市} 地铁线路图 最新",
            "{学校} 地铁站 距离",
            "{城市} 共享单车 分布",
            "{学校} 到机场 交通方式",
        ],
        "suggestions": [
            "下载城市地铁App/乘车码，了解学生优惠",
            "熟悉学校到火车站/机场的交通路线（报到和假期回家用）",
            "关注共享单车/电动车停放点（校园周边最后一公里）",
            "了解城市的早晚高峰时段，合理安排出行时间",
        ]
    },
    "lifestyle": {
        "title": "🌸 生活品质深度分析",
        "sub_indicators": [
            ("tier3_hospitals", "三甲医院", "家", "城市医疗资源"),
            ("large_malls", "大型商场", "个", "商业配套"),
            ("parks_and_museums", "公园/博物馆", "个", "文化休闲场所"),
            ("safety_index", "安全指数", "分", "城市治安评分1-10分"),
            ("annual_aqi", "年均AQI", "", "空气质量指数，越低越好"),
        ],
        "evidence_queries": [
            "{城市} 三甲医院 列表 地址",
            "{城市} 商圈 推荐 大学生",
            "{城市} 博物馆 免费 开放时间",
            "{城市} 安全指数 排名 2025",
        ],
        "suggestions": [
            "了解学校附近的医疗机构（校医院+最近的三甲医院）",
            "探索城市的文化场馆（很多对学生免费）",
            "关注城市的安全热点区域，避免夜间单独前往",
            "空气质量敏感的城市可考虑购买空气净化器",
        ]
    },
    "climate": {
        "title": "🌤️ 气候环境深度分析",
        "sub_indicators": [
            ("avg_temperature", "年均温度", "℃", "全年平均气温"),
            ("avg_humidity", "年均湿度", "%", "相对湿度"),
            ("extreme_weather_days", "极端天气天数", "天/年", "高温/暴雨/台风/暴雪等"),
        ],
        "evidence_queries": [
            "{城市} 天气特点 一年四季",
            "{城市} 梅雨季节 时间",
            "{城市} 台风 影响",
            "{城市} 空气质量 AQI 月度",
        ],
        "suggestions": [
            "根据气候准备衣物：南方多雨带伞/除湿，北方干燥带保湿",
            "关注当地的特殊天气季节（如南方的梅雨、北方的沙尘）",
            "极端天气天数多的城市需特别关注天气预报",
            "空气质量差的城市可准备口罩和空气净化器",
        ]
    },
    "development": {
        "title": "📈 城市发展深度分析",
        "sub_indicators": [
            ("gdp_growth_rate", "GDP增速", "%", "经济发展速度"),
            ("tertiary_industry_pct", "第三产业占比", "%", "服务业发达程度"),
            ("talent_policy_score", "人才政策评分", "分", "落户/补贴/购房优惠1-10分"),
            ("price_income_ratio", "房价收入比", "", "房价与收入之比，越低越好"),
        ],
        "evidence_queries": [
            "{城市} GDP 2025 增速",
            "{城市} 人才政策 落户 补贴 2025",
            "{城市} 房价 收入比 2025",
            "{城市} 产业 发展 方向",
        ],
        "suggestions": [
            "关注城市的人才政策（落户补贴/购房优惠/创业扶持）",
            "了解城市的产业发展方向，与自己的专业规划匹配",
            "房价收入比高的城市可考虑先租房积累经验",
            "第三产业占比高意味着更多服务业就业机会",
        ]
    }
}


class ReportGen:
    def bar(self, score, w=20):
        f = int(score/100*w); return "█"*f+"░"*(w-f)
    def stars(self, s):
        if s>=90: return "⭐⭐⭐⭐⭐"
        elif s>=80: return "⭐⭐⭐⭐"
        elif s>=70: return "⭐⭐⭐"
        elif s>=60: return "⭐⭐"
        return "⭐"

    @staticmethod
    def _names(sd):
        """学校/城市名：优先顶层字段，回退_meta（修复此前报告显示'?'的问题）"""
        m = sd.get("_meta", {}) or {}
        return (sd.get("school_name") or m.get("school_name") or "?",
                sd.get("city_name") or m.get("city_name") or "?")

    def single(self, sd):
        m = sd.get("_meta",{}); sn,cn=self._names(sd)
        t=sd.get("total_score",0); ss=sd.get("school_score",0); cs=sd.get("city_score",0)
        ds=sd.get("dimension_scores",{}); bd=sd.get("breakdown",[])
        lines=[f"# 🎓 {sn} 入学决策分析报告","",f"\u003e **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')} | **所在城市**: {cn} | **权重方案**: {m.get('config_source','?')}",""]
        lines+=["---",""]
        lines+[f"## 📊 综合评分: **{t}/100** {self.stars(t)}",""]
        lines+=[ "| 维度类别 | 得分 | 占比 |","|----------|------|------|"]
        r=sd.get("weights_used",{}).get("school_vs_city_ratio",0.6)
        lines+=[f"| 🏫 校园维度 | **{ss}/100** | {r*100:.0f}% |",f"| 🏙️ 城市维度 | **{cs}/100** | {(1-r)*100:.0f}% |",""]
        lines+=["### 📊 各维度得分详情","```"]
        for it in bd:
            lid=it["dimension_id"]; lb,ic=LABELS.get(lid,(lid,"📊"))
            tag="🏫" if it["category"]=="school" else "🏙️"
            lines.append(f"{tag} {ic} {lb:8s} {self.bar(it['raw_score'])} {it['raw_score']:5.1f}/100  (权重{it['weight']:.1%})")
        lines+=["```", ""]
        top3=sorted(bd,key=lambda x:x["raw_score"],reverse=True)[:3]; bot3=sorted(bd,key=lambda x:x["raw_score"])[:3]
        lines+=["### ✅ 优势亮点 (Top 3)",""]
        for i,it in enumerate(top3,1):
            lb,ic=LABELS.get(it["dimension_id"],(it["dimension_name"],"📊")); sc=it["raw_score"]
            lines.append(f"{i}. **{ic} {lb}** ({sc:.1f}/100) — {self._strength(it['dimension_id'],sc,sn,cn)}")
        lines+=["","### ⚠️ 注意事项 (Top 3)",""]
        for i,it in enumerate(bot3,1):
            lb,ic=LABELS.get(it["dimension_id"],(it["dimension_name"],"📊")); sc=it["raw_score"]
            pre="" if sc>=70 else ("🔴 " if sc<50 else "⚠️ ")
            lines.append(f"{i}. {pre}**{ic} {lb}** ({sc:.1f}/100) — {self._warn(it['dimension_id'],sc,sn,cn)}")
        lines+=["","### 💡 决策建议","",f"\u003e {self._advice(sd)}",""]
        lines+=["### 📋 入学准备 Checklist",""]
        for item in self._checklist(sn,cn,ds): lines.append(f"- [ ] {item}")
        lines+=["","---",""]
        lines+=["### 🔗 数据来源与说明",""]
        lines+=[ "| 项目 | 内容 |","|------|------|"]
        for row in [f"学校名称|{sn}",f"所在城市|{cn}",f"权重方案|{m.get('config_source','?')}",
                    f"数据版本|{m.get('last_updated','N/A')}",f"报告生成时间|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]:
            lines.append(f"| {row} |")
        lines+=["","*注：本报告由何栖自动生成，评分结果仅供参考。*"]
        return "\n".join(lines)

    # v2.0新增：深度维度分析生成器
    def generate_deep_dive(self, dim_id, score, school_data, city_data, school_name, city_name, ugc_evidences=None):
        """
        针对指定维度生成深度分析报告
        
        Args:
            dim_id: 维度ID (academic/campus_env/career/student_life/living_cost/transport/lifestyle/climate/development)
            score: 该维度的归一化得分 (0-100)
            school_data: 学校原始数据字典
            city_data: 城市原始数据字典
            school_name: 学校名称
            city_name: 城市名称
            ugc_evidences: 从UGC社区采集的证据列表（可选）
        
        Returns:
            Markdown格式的深度分析字符串
        """
        template = DEEP_DIVE_TEMPLATES.get(dim_id)
        if not template:
            return f"## ❌ 未找到维度 '{dim_id}' 的深度分析模板\n\n该维度暂不支持深度分析，将在后续版本中补充。"
        
        dim_label = LABELS.get(dim_id, (dim_id, "📊"))[0]
        lines = [f"", f"## {template['title']}", f""]
        
        # 1. 得分拆解表
        lines += [f"### 📊 得分拆解", ""]
        lines += ["| 子指标 | 原始数据 | 单位 | 说明 |", "|--------|---------|------|------|"]
        
        data_source = school_data if dim_id in ["academic", "campus_env", "career", "student_life"] else city_data
        
        for field, label, unit, desc in template["sub_indicators"]:
            value = data_source.get(field, "N/A")
            # 格式化显示
            if isinstance(value, float):
                if unit == "%":
                    display_val = f"{value:.1f}"
                elif unit == "亿元" or unit == "万册" or unit == "万元/年":
                    display_val = f"{value:.1f}"
                elif unit == "":
                    display_val = f"{value:.1f}"
                else:
                    display_val = f"{value:.1f}"
            else:
                display_val = str(value)
            
            lines.append(f"| {label} | {display_val} | {unit} | {desc} |")
        
        lines += [""]
        
        # 2. 多源证据汇总
        lines += [f"### 🔍 多源证据汇总", ""]
        lines += [f"以下搜索关键词可用于进一步采集该维度的详细信息：", ""]
        for query_template in template["evidence_queries"]:
            query = query_template.replace("{学校}", school_name).replace("{城市}", city_name)
            lines.append(f"- `{query}`")
        lines += [""]
        
        # 3. UGC真实声音（如果有提供）
        if ugc_evidences and len(ugc_evidences) > 0:
            lines += [f"### 💬 来自真实在校生的声音", ""]
            for evidence in ugc_evidences[:5]:  # 最多展示5条
                source = evidence.get("source", "未知来源")
                content = evidence.get("content", "")
                author = evidence.get("author", "")
                timestamp = evidence.get("timestamp", "")
                
                if source == "知乎":
                    icon = "💬"
                    meta = f"@{author} ({timestamp})" if author else timestamp
                elif source == "小红书":
                    icon = "📸"
                    meta = f"@{author}" if author else timestamp
                elif source == "贴吧":
                    icon = "🗨️"
                    meta = f"贴吧用户 ({timestamp})" if timestamp else "贴吧用户"
                elif source == "B站":
                    icon = "🎬"
                    meta = f"UP主: @{author}" if author else "B站视频"
                elif source == "校园墙":
                    icon = "📱"
                    meta = f"校园墙 ({timestamp})" if timestamp else "校园墙"
                else:
                    icon = "💭"
                    meta = f"{source}"
                
                lines.append(f"> {icon} \"{content}\"")
                lines.append(f"> — 来源：{meta}")
                lines.append("")
        else:
            lines += [f"### 💬 来自真实在校生的声音", ""]
            lines += [f"> *提示：运行完整分析时可从知乎/小红书/贴吧/B站/校园墙自动采集该校的真实评价*", ""]
        
        # 4. 深度解读
        lines += [f"### ⚡ 维度深度解读", ""]
        interpretation = self._deep_interpret(dim_id, score, school_data, city_data, school_name, city_name)
        lines += [interpretation, ""]
        
        # 5. 个性化建议
        lines += [f"### 🎯 个性化建议", ""]
        for i, suggestion in enumerate(template["suggestions"], 1):
            lines.append(f"{i}. {suggestion}")
        lines += [""]
        
        # 6. 延伸资源
        lines += [f"### 🔗 延伸资源 & 推荐关注", ""]
        resources = self._get_resources(dim_id, school_name, city_name)
        for resource in resources:
            lines.append(f"- {resource}")
        lines += [""]
        
        return "\n".join(lines)
    
    def _deep_interpret(self, did, score, sd, cd, sn, cn):
        """生成维度深度解读"""
        interpretations = {
            "academic": lambda: self._interpret_academic(score, sd, sn),
            "campus_env": lambda: self._interpret_campus(score, sd, sn),
            "career": lambda: self._interpret_career(score, sd, sn),
            "student_life": lambda: self._interpret_student_life(score, sd, sn),
            "living_cost": lambda: self._interpret_living_cost(score, cd, cn),
            "transport": lambda: self._interpret_transport(score, cd, cn),
            "lifestyle": lambda: self._interpret_lifestyle(score, cd, cn),
            "climate": lambda: self._interpret_climate(score, cd, cn),
            "development": lambda: self._interpret_development(score, cd, cn),
        }
        fn = interpretations.get(did, lambda: f"{LABELS.get(did,(did,''))[0]}得分为{score:.1f}/100，表现{'优秀' if score>=80 else '良好' if score>=60 else '一般' if score>=40 else '较弱'}。")
        return fn()
    
    def _interpret_academic(self, score, sd, sn):
        a_plus = sd.get("a_plus_disciplines", 0)
        labs = sd.get("national_key_labs", 0)
        funding = sd.get("research_funding", 0)
        ratio = sd.get("student_faculty_ratio", 18)
        parts = []
        parts.append(f"**{sn}的学术资源综合得分为{score:.1f}/100**。")
        if a_plus > 0:
            parts.append(f"该校拥有**{a_plus}个A+学科**，这些学科在国内处于顶尖水平，是学校的'金字招牌'。")
        if labs > 0:
            parts.append(f"共有**{labs}个国家重点实验室**，为本科生参与前沿科研提供了平台。")
        if funding > 50:
            parts.append(f"年度科研经费达**{funding:.0f}亿元**，说明学校在科研投入上力度较大。")
        if ratio <= 12:
            parts.append(f"师生比为**{ratio}:1**，属于较高水平，学生能获得更多教师关注度。")
        elif ratio >= 18:
            parts.append(f"师生比为**{ratio}:1**，部分热门课程可能人数较多，需要主动争取互动机会。")
        if score >= 80:
            parts.append("整体来看，该校学术实力强劲，适合有志于学术研究或进入高端行业的学生。")
        elif score >= 60:
            parts.append("整体来看，该校学术实力处于中上水平，部分优势学科值得重点关注。")
        else:
            parts.append("整体来看，该校学术资源相对有限，建议通过自学和网络资源弥补。")
        return "\n\n".join(parts)
    
    def _interpret_campus(self, score, sd, sn):
        dorm_pct = sd.get("four_person_dorm_pct", 40)
        ac_pct = sd.get("ac_pct", 85)
        canteen = sd.get("canteen_count", 5)
        parts = []
        parts.append(f"**{sn}的校园环境综合得分为{score:.1f}/100**。")
        if dorm_pct >= 60:
            parts.append(f"**{dorm_pct}%**的宿舍为4人间或更优配置，住宿条件较好。")
        elif dorm_pct < 40:
            parts.append(f"仅约**{dorm_pct}%**的宿舍为4人间，6-8人间占比较高，可能较为拥挤。")
        if ac_pct >= 95:
            parts.append(f"空调覆盖率高达**{ac_pct}%**，夏季学习和睡眠不受炎热困扰。")
        elif ac_pct < 80:
            parts.append(f"空调覆盖率仅为**{ac_pct}%**，部分宿舍/教室可能没有空调，建议自备小风扇。")
        if canteen >= 10:
            parts.append(f"校园内有**{canteen}个食堂**，餐饮选择丰富多样。")
        parts.append("\n> ⚠️ **重要提醒**: 不同校区、不同学院的宿舍条件可能差异很大，建议提前向学长学姐确认自己所在的具体楼宇情况。")
        return "\n\n".join(parts)
    
    def _interpret_career(self, score, sd, sn):
        emp_rate = sd.get("employment_rate", 92)
        salary = sd.get("avg_starting_salary", 12)
        baoyan = sd.get("postgrad_recommendation_rate", 15)
        parts = []
        parts.append(f"**{sn}的就业前景综合得分为{score:.1f}/100**。")
        if emp_rate >= 95:
            parts.append(f"就业率高达**{emp_rate}%**，毕业生就业竞争力强。")
        elif emp_rate < 90:
            parts.append(f"就业率为**{emp_rate}%**，部分专业可能面临较大就业压力，建议提前规划。")
        if salary >= 18:
            parts.append(f"平均起薪约**{salary}万元/年**，处于较高水平。")
        elif salary < 12:
            parts.append(f"平均起薪约**{salary}万元/年**，起薪相对较低但成长空间值得关注。")
        if baoyan >= 25:
            parts.append(f"保研率**{baoyan}%**，有相当比例的学生可以免试攻读研究生。")
        parts.append("\n> 💡 **建议**: 无论学校整体就业率如何，个人发展最终取决于自身努力。建议从大一开始就关注实习机会，积累项目经验和人脉资源。")
        return "\n\n".join(parts)
    
    def _interpret_student_life(self, score, sd, sn):
        clubs = sd.get("club_count", 150)
        exchange = sd.get("exchange_programs", 50)
        parts = []
        parts.append(f"**{sn}的学生活动综合得分为{score:.1f}/100**。")
        if clubs >= 200:
            parts.append(f"拥有**{clubs}个学生社团**，涵盖文艺/体育/科技/公益等多个领域。")
        elif clubs < 100:
            parts.append(f"约有**{clubs}个学生社团**，选择相对有限，但也可以尝试发起感兴趣的社团。")
        if exchange >= 100:
            parts.append(f"提供**{exchange}个国际交流项目**，出国交换机会丰富。")
        parts.append("\n> 🎯 **提示**: 社团不在多而在精，深度参与1-2个社团比泛泛参加10个更有价值。国际交流项目通常需要提前1年申请并达到语言成绩要求。")
        return "\n\n".join(parts)
    
    def _interpret_living_cost(self, score, cd, cn):
        rent = cd.get("monthly_rent", 1500)
        food = cd.get("monthly_food", 1200)
        total_est = rent + food + 300  # +300 for transport/misc
        parts = []
        parts.append(f"**{cn}的生活成本综合得分为{score:.1f}/100**（得分越高表示成本越友好）。")
        parts.append(f"预估月生活费:")
        parts.append(f"- 房租（校外合租单间）：约**{rent:.0f}元/月**")
        parts.append(f"- 餐饮费：约**{food:.0f}元/月**")
        parts.append(f"- 交通/日用品/娱乐：约**300元/月**")
        parts.append(f"- **合计：约{total_est:.0f}元/月**（不含学费和大型采购）")
        if score >= 80:
            parts.append(f"\n{cn}的生活成本相对较低，大部分学生月生活费**1500-2000元**即可过得比较舒适。")
        elif score < 60:
            parts.append(f"\n{cn}的生活成本偏高，建议做好财务规划，月生活费预算**2500元以上**。")
        return "\n\n".join(parts)
    
    def _interpret_transport(self, score, cd, cn):
        subway = cd.get("subway_lines", 3)
        airport = cd.get("airport_distance_km", 30)
        railway = cd.get("railway_station_distance_km", 10)
        parts = []
        parts.append(f"**{cn}的交通便捷度综合得分为{score:.1f}/100**。")
        if subway >= 10:
            parts.append(f"拥有**{subway}条地铁线路**，轨道交通网络发达，出行非常方便。")
        elif subway >= 5:
            parts.append(f"拥有**{subway}条地铁线路**，基本覆盖主要区域。")
        elif subway > 0:
            parts.append(f"有**{subway}条地铁线路**，但覆盖范围有限，可能需要结合公交/打车。")
        else:
            parts.append(f"目前暂无地铁（或数据缺失），主要依赖公交和其他交通工具。")
        if airport <= 20:
            parts.append(f"距离机场仅**{airport}公里**，航空出行便捷。")
        if railway <= 5:
            parts.append(f"距离火车站**{railway}公里**，高铁出行方便。")
        return "\n\n".join(parts)
    
    def _interpret_lifestyle(self, score, cd, cn):
        hospitals = cd.get("tier3_hospitals", 8)
        malls = cd.get("large_malls", 15)
        aqi = cd.get("annual_aqi", 70)
        safety = cd.get("safety_index", 7)
        parks = cd.get("parks_and_museums", 25)
        parts = []
        parts.append(f"**{cn}的生活品质综合得分为{score:.1f}/100**。")
        parts.append(f"- 医疗资源：**{hospitals}家三甲医院**")
        parts.append(f"- 商业配套：**{malls}个大型商场**")
        parts.append(f"- 文化休闲：**{parks}个公园/博物馆**")
        parts.append(f"- 安全指数：**{safety}/10**")
        parts.append(f"- 年均AQI：**{aqi}**（{'优' if aqi<=50 else '良' if aqi<=100 else '轻度污染' if aqi<=150 else '中度以上污染'}）")
        if safety >= 8.5:
            parts.append(f"\n{cn}治安状况良好，夜间出行安全性较高。")
        if aqi > 100:
            parts.append(f"\n⚠️ 空气质量需要注意，建议关注每日AQI预报，雾霾天减少户外活动并佩戴口罩。")
        return "\n\n".join(parts)
    
    def _interpret_climate(self, score, cd, cn):
        temp = cd.get("avg_temperature", 16)
        humidity = cd.get("avg_humidity", 68)
        extreme = cd.get("extreme_weather_days", 12)
        parts = []
        parts.append(f"**{cn}的气候环境综合得分为{score:.1f}/100**。")
        parts.append(f"- 年均温度：**{temp}°C**")
        parts.append(f"- 年均湿度：**{humidity}%**")
        parts.append(f"- 极端天气天数：约**{extreme}天/年**")
        if 14 <= temp <= 24:
            parts.append(f"\n温度适宜，四季相对温和，体感舒适度高。")
        elif temp >= 26:
            parts.append(f"\n整体偏热，夏季漫长且炎热，需做好防暑降温准备。")
        elif temp < 12:
            parts.append(f"\n整体偏冷，冬季漫长且寒冷，需准备充足保暖衣物。")
        if humidity >= 75:
            parts.append(f"湿度较高（{humidity}%），体感闷热，南方城市需注意防潮除湿。")
        elif humidity < 45:
            parts.append(f"湿度较低（{humidity}%），气候干燥，注意皮肤保湿和多喝水。")
        if extreme > 20:
            parts.append(f"\n⚠️ 极端天气较多（年均{extreme}天），需特别关注当地气象预警。")
        return "\n\n".join(parts)
    
    def _interpret_development(self, score, cd, cn):
        gdp_g = cd.get("gdp_growth_rate", 6)
        tertiary = cd.get("tertiary_industry_pct", 58)
        talent = cd.get("talent_policy_score", 5)
        price_income = cd.get("price_income_ratio", 10)
        parts = []
        parts.append(f"**{cn}的城市发展综合得分为{score:.1f}/100**。")
        parts.append(f"- GDP增速：**{gdp_g}%**（{'高速增长' if gdp_g>=7 else '稳健增长' if gdp_g>=5 else '增速放缓' if gdp_g>=3 else '低速增长'}）")
        parts.append(f"- 第三产业占比：**{tertiary}%**（{'服务业主导' if tertiary>=70 else '工业与服务并重' if tertiary>=50 else '工业主导'}）")
        parts.append(f"- 人才政策评分：**{talent}/10**")
        parts.append(f"- 房价收入比：**{price_income}**（{'房价合理' if price_income<=8 else '略有压力' if price_income<=15 else '压力较大' if price_income<=20 else '压力很大'}）")
        if gdp_g >= 6 and talent >= 7:
            parts.append(f"\n{cn}经济发展活力强，人才政策优惠，适合毕业后在当地发展的学生。")
        if price_income > 15:
            parts.append(f"\n⚠️ 房价收入比较高，毕业后购房面临一定压力，可先租房积累经验。")
        return "\n\n".join(parts)
    
    def _get_resources(self, did, sn, cn):
        """获取延伸资源"""
        resource_map = {
            "academic": [
                f"教育部学科评估官网: https://www.cdgdc.edu.cn/",
                f"{sn}研究生院官网（查询招生/保研政策）",
                f"{sn}图书馆官网（访问学术数据库）",
                "知网/万方/维普（中文文献检索）",
            ],
            "campus_env": [
                f"搜索「{sn} 表白墙」获取最新校园动态",
                f"B站搜索「{sn} 宿舍 tour」查看实拍视频",
                f"小红书搜索「{sn} 新生攻略」查看图文攻略",
                f"加入{sn}新生QQ群/微信群",
            ],
            "career": [
                f"{sn}就业信息网（校招/实习信息）",
                f"{sn}就业质量年度报告（PDF）",
                "BOSS直聘/牛人网（查看岗位薪资）",
                "LinkedIn领英（建立职业档案）",
            ],
            "student_life": [
                f"{sn}团委/学生会公众号（活动通知）",
                f"{sn}社团联合会（社团列表和招新信息）",
                f"{sn}国际交流处（交换项目申请）",
            ],
            "living_cost": [
                f"贝壳找房/链家（查看{cn}房租价格）",
                f"大众点评（查看学校周边餐饮价格）",
                f"美团外卖（查看配送范围和价格）",
            ],
            "transport": [
                f"{cn}地铁官网/APP（线路图和运营时间）",
                f"高德地图/百度地图（路线规划）",
                f"12306官网（火车票预订）",
                f"携程/去哪儿（机票比价）",
            ],
            "lifestyle": [
                f"{cn}卫健委官网（三甲医院列表）",
                f"大众点评（商场/美食/娱乐推荐）",
                f"马蜂窝/穷游网（旅游攻略）",
            ],
            "climate": [
                f"中国天气网（{cn}历史天气和预报）",
                f"墨迹天气APP（实时天气和空气质量）",
            ],
            "development": [
                f"{cn}统计局官网（经济数据）",
                f"{cn}人社局官网（人才政策详情）",
                f"安居客/房天下（房价走势）",
            ],
        }
        return resource_map.get(did, ["暂无延伸资源推荐"])

    def compare(self, scores_list):
        lines=["# 🎓 多校入学决策对比报告",""]
        lines.append(f"\u003e **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')} | **对比学校数**: {len(scores_list)}")
        lines+=["---",""]
        names=[]; headers=["维度/学校"]
        for s in scores_list:
            n,c=self._names(s)
            names.append(f"{n}\n({c})"); headers.append(f"{n}\n({c})")
        # total table
        lines+=["## 📊 综合评分对比",""]
        lines.append("| "+" | ".join(headers)+" |"); lines.append("| "+" | ".join(["---"]*len(headers))+" |")
        row=["**综合分**"]
        for s in scores_list:
            t=s.get("total_score",0); row.append(f"**{t}/100** {self.stars(t)}")
        lines.append("| "+" | ".join(row)+" |")
        row=["🏫 校园"]
        for s in scores_list: row.append(f"{s.get('school_score',0):.1f}")
        lines.append("| "+" | ".join(row)+" |")
        row=["🏙️ 城市"]
        for s in scores_list: row.append(f"{s.get('city_score',0):.1f}")
        lines.append("| "+" | ".join(row)+" |")
        # dim table
        lines+="","\n## 📊 各维度详细对比",""
        dh=["维度"]
        for sn in names: dh.append(sn.replace("\n"," "))
        lines.append("| "+" | ".join(dh)+" |"); lines.append("| "+" | ".join(["---"]*len(dh))+" |")
        for did in LABELS:
            lb,ic=LABELS[did]; row=[f"{ic} {lb}"]
            for s in scores_list: row.append(f"{s.get('dimension_scores',{}).get(did,0):.1f}")
            lines.append("| "+" | ".join(row)+" |")
        # ranking
        lines+="","\n## 🏆 综合排名",""
        ranked=sorted(scores_list,key=lambda x:x.get("total_score",0),reverse=True)
        medals={1:"🥇",2:"🥈",3:"🥉"}
        for i,s in enumerate(ranked,1):
            n,c=self._names(s); t=s.get("total_score",0)
            lines.append(f"{medals.get(i,f'{i}.')} **{n}** ({c}) — {t}/100 {self.stars(t)}")
        lines+="","\n*注：以上排名基于当前权重配置。*"
        return "\n".join(lines)

    def _strength(self, did, score, sch, city):
        msgs={"academic":f"{sch}在该维度表现突出，学术资源丰富。",
               "campus_env":"校园环境优越，硬件设施完善。",
               "career":"就业前景广阔，毕业生竞争力强。",
               "student_life":"课外活动丰富，国际交流机会多。",
               "living_cost":f"{city}的生活成本相对合理。",
               "transport":"交通便利，出行便捷。",
               "lifestyle":f"{city}的生活品质优秀。",
               "climate":"气候宜人，居住舒适度高。",
               "development":f"{city}发展潜力大，未来机遇多。"}
        b=msgs.get(did,"表现良好。")
        if score>=90: b=b.replace("表现良好","表现卓越").replace("突出","极为突出")
        return b

    def _warn(self, did, score, sch, city):
        msgs={"academic":"学术资源可能不如顶尖院校丰富。",
              "campus_env":"校园硬件可能存在短板，建议提前了解宿舍和食堂。",
              "career":"就业竞争可能较激烈，建议提前规划实习。",
              "student_life":"课外活动选择相对有限。",
              "living_cost":f"{city}生活成本较高，需做好财务规划。",
              "transport":"交通可能不够便利。",
              "lifestyle":"城市配套可能不够完善。",
              "climate":"气候条件特殊，需做好适应性准备。",
              "development":"城市发展速度一般。"}
        return msgs.get(did,"该维度存在改进空间。")

    def _advice(self, sd):
        t=sd["total_score"]; ss=sd["school_score"]; cs=sd["city_score"]
        m=sd.get("_meta",{}); sn=m.get("school_name","该校")
        parts=[]
        if t>=85: parts.append(f"**高度推荐**。{sn}的综合表现非常出色")
        elif t>=75: parts.append(f"**推荐**。{sn}整体表现良好")
        elif t>=60: parts.append(f"**可以考虑**。{sn}在某些方面有特色")
        else: parts.append(f"**需谨慎考虑**。{sn}在某些关键维度存在明显短板")
        if ss>cs+10: parts.append("学校实力强于城市条件，如果更看重学术和学历背景")
        elif cs>ss+10: parts.append("城市条件优于学校平均水平，如果看重城市发展和生活体验")
        return "。".join(parts)+"。"

    def _checklist(self, sch, city, ds):
        items=[
            "📋 确认录取通知书及报到要求",
            "🆔 准备身份证/户口本复印件(多份)",
            "📸 准备证件照(一寸/二寸)",
            "💳 办理银行卡",
            "📱 了解学校WiFi/校园网接入方式",
            "🎓 购置必要的学习用品",
            "💊 准备常用药品",
            f"🔍 搜索'{sch} 新生攻略'获取更多经验",
            f"🗺️ 在地图App上收藏学校位置及周边重要地点",
        ]
        lc=ds.get("living_cost",70)
        if lc<60: items.insert(-1,"💰 制定详细月度预算(该城市生活成本较高)")
        cl=ds.get("climate",70)
        if cl<60: items.insert(-1,"👕 准备适应当地气候的特殊衣物")
        tr=ds.get("transport",70)
        if tr<70: items.insert(-1,"🗺️ 提前下载离线地图，熟悉交通路线")
        return items

def main():
    ap=argparse.ArgumentParser(description="报告生成器 v6.0")
    ap.add_argument("--scores","-s",nargs="+",required=True)
    ap.add_argument("--output","-o",default=None)
    ap.add_argument("--compare",action="store_true")
    ap.add_argument("--summary",action="store_true")
    ap.add_argument("--deep-dive",nargs="?",const="auto",help="指定要深度分析的维度ID(auto=自动识别)")
    args=ap.parse_args()
    rg=ReportGen(); sl=[]
    for p in args.scores:
        with open(p,'r',encoding='utf-8') as f: sl.append(json.load(f))
    if args.compare and len(sl)>1:
        out=rg.compare(sl); mode="多校对比报告"
    elif args.summary:
        sd=sl[0]; m=sd.get("_meta",{})
        out=f"{'='*55}\n🎓 {ReportGen._names(sd)[0]} ({ReportGen._names(sd)[1]}) — 快速摘要\n{'='*55}\n综合: {sd['total_score']}/100 {rg.stars(sd['total_score'])}\n校园: {sd['school_score']:.1f} | 城市: {sd['city_score']:.1f}"
        mode="控制台摘要"
    else:
        out=rg.single(sl[0]); mode="单校完整报告"
    
    # v2.0新增：深度分析
    if args.deep_dive and sl:
        sd = sl[0]
        m = sd.get("_meta",{})
        sn, cn = rg._names(sd)
        bd = sd.get("breakdown",[])
        ds = sd.get("dimension_scores",{})
        
        if args.deep_dive == "auto":
            # 自动选择得分最高的3个维度或权重最大的3个维度
            target_dims = sorted(bd, key=lambda x: x["weight"], reverse=True)[:3]
            target_dims = [d["dimension_id"] for d in target_dims]
        else:
            target_dims = [args.deep_dive]
        
        deep_out = []
        for dim_id in target_dims:
            score = ds.get(dim_id, 0)
            school_data = sd.get("school", {})
            city_data = sd.get("city", {})
            dive = rg.generate_deep_dive(dim_id, score, school_data, city_data, sn, cn)
            deep_out.append(dive)
        
        out = out + "\n\n" + "\n".join(deep_out)
        mode += " + 深度分析"
    
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output,'w',encoding='utf-8') as f: f.write(out)
        print(f"✅ {mode}已保存: {args.output}")
    else: print(out)

if __name__=="__main__": main()
