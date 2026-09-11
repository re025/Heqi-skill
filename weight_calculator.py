#!/usr/bin/env python3
"""权重计算引擎 - 基于用户自定义权重对学校和城市各维度进行加权评分
v2.0: 修复Unicode编码问题，使用标准Python Unicode转义
"""

import json, argparse, sys
from typing import Dict, Any, Optional
import os

DEFAULT_WEIGHTS = {
    "school": {"academic": 0.20, "campus_env": 0.15, "career": 0.20, "student_life": 0.04},
    "city": {"living_cost": 0.15, "transport": 0.12, "lifestyle": 0.08, "climate": 0.03, "development": 0.03},
    "school_vs_city_ratio": 0.60,
}

PRESET_TEMPLATES = {
    "research_focus": {
        "name": "🔬 科研学霸",
        "school": {"academic": 0.40, "campus_env": 0.10, "career": 0.25, "student_life": 0.03},
        "city": {"living_cost": 0.10, "transport": 0.05, "lifestyle": 0.05, "climate": 0.01, "development": 0.01},
        "school_vs_city_ratio": 0.78,
    },
    "career_focus": {
        "name": "💼 就业导向",
        "school": {"academic": 0.15, "campus_env": 0.05, "career": 0.35, "student_life": 0.03},
        "city": {"living_cost": 0.20, "transport": 0.10, "lifestyle": 0.10, "climate": 0.01, "development": 0.01},
        "school_vs_city_ratio": 0.58,
    },
    "city_explorer": {
        "name": "🏙️ 城市探索家",
        "school": {"academic": 0.10, "campus_env": 0.10, "career": 0.15, "student_life": 0.03},
        "city": {"living_cost": 0.20, "transport": 0.15, "lifestyle": 0.25, "climate": 0.01, "development": 0.01},
        "school_vs_city_ratio": 0.38,
    },
    "comfort_seeker": {
        "name": "🌸 温室花朵",
        "school": {"academic": 0.20, "campus_env": 0.25, "career": 0.10, "student_life": 0.03},
        "city": {"living_cost": 0.25, "transport": 0.05, "lifestyle": 0.10, "climate": 0.01, "development": 0.01},
        "school_vs_city_ratio": 0.58,
    },
    "balanced": {
        "name": "⚖️ 均衡发展",
        "school": {"academic": 0.20, "campus_env": 0.15, "career": 0.20, "student_life": 0.04},
        "city": {"living_cost": 0.15, "transport": 0.12, "lifestyle": 0.08, "climate": 0.03, "development": 0.03},
        "school_vs_city_ratio": 0.60,
    },
}

# v2.0新增：问卷回答到权重的映射
QUESTIONNAIRE_MAPPING = {
    "Q1": {
        "A": {"academic": 0.15, "career": 0.05},   # 学术优先
        "B": {"career": 0.15, "academic": 0.05},   # 就业优先
        "C": {"academic": 0.075, "career": 0.075}, # 都重要
    },
    "Q2": {
        "A": {"campus_env": 0.15},                 # 舒适优先
        "B": {"campus_env": 0.05},                 # 过得去
        "C": {},                                   # 不在意
    },
    "Q3": {
        "A": {"living_cost": 0.15},                # 越低越好
        "B": {"living_cost": 0.08},                # 可以接受
        "C": {"living_cost": 0.03},                # 不太在意
    },
    "Q4": {
        "A": {"transport": 0.12},                  # 交通便利
        "B": {"lifestyle": 0.12},                  # 生活品质
        "C": {"transport": 0.06, "lifestyle": 0.06}, # 都在意
    },
    "Q5": {
        "A": {"climate": 0.05},                    # 很敏感
        "B": {"climate": 0.02},                    # 一般般
        "C": {"climate": 0.01},                    # 不太在意
    }
}

# Q1/Q2答案对school_vs_city_ratio的影响
RATIO_ADJUSTMENTS = {
    ("A", "A"): 0.72,  # 学术+舒适 → 偏学校
    ("A", "B"): 0.68,  # 学术+过得去 → 偏学校
    ("A", "C"): 0.65,  # 学术+不在意 → 中性偏校
    ("B", "A"): 0.62,  # 就业+舒适 → 中性偏校
    ("B", "B"): 0.58,  # 就业+过得去 → 中性偏城
    ("B", "C"): 0.52,  # 就业+不在意 → 偏城市
    ("C", "A"): 0.58,  # 都重要+舒适 → 中性偏城
    ("C", "B"): 0.55,  # 都重要+过得去 → 中性偏城
    ("C", "C"): 0.50,  # 都重要+不在意 → 偏城市
}


def norm_pos(v, mn, mx):
    if mx == mn: return 70.0
    return ((v - mn) / (mx - mn)) * 100

def norm_neg(v, mn, mx):
    if mx == mn: return 70.0
    return (1 - (v - mn) / (mx - mn)) * 100

def norm_opt(v, lo, hi, abs_lo, abs_hi, peak=100):
    if lo <= v <= hi: return peak
    d = (lo - v) if v < lo else (v - hi)
    rng = (lo - abs_lo) if v < lo else (abs_hi - hi)
    if rng == 0: return 70.0
    return max(peak - (d / rng) * peak * 0.8, 20)

def norm_rank(r, mx=100):
    if r <= 0: return 100.0
    return max(0, 100 - (r / mx) * 80)

def norm_pct(p): return min(100, max(0, p))

class Scorer:
    @staticmethod
    def academic(d):
        s = []
        s.append(norm_pos(d.get("a_plus_disciplines", 0), 0, 30) * .30)
        s.append(norm_pos(d.get("national_key_labs", 0), 0, 15) * .20)
        s.append(norm_pos(d.get("research_funding", 0), 0, 500) * .20)
        s.append(norm_neg(d.get("student_faculty_ratio", 18), 5, 40) * .15)
        s.append(norm_pos(d.get("library_books", 0), 0, 3000) * .15)
        return sum(s)

    @staticmethod
    def campus(d):
        s = []
        s.append(norm_pos(d.get("four_person_dorm_pct", 40), 0, 100) * .25)
        s.append(norm_pos(d.get("ac_pct", 85), 0, 100) * .20)
        s.append(norm_pos(d.get("canteen_count", 5), 1, 15) * .15)
        s.append(norm_pos(d.get("campus_area_mu", 1000), 100, 10000) * .20)
        s.append(norm_pos(d.get("sports_facilities", 8), 1, 30) * .20)
        return sum(s)

    @staticmethod
    def career(d):
        s = []
        s.append(norm_pct(d.get("employment_rate", 90)) * .25)
        s.append(norm_pos(d.get("avg_starting_salary", 12), 6, 35) * .25)
        s.append(norm_pos(d.get("corp_partnerships", 50), 0, 500) * .15)
        s.append(norm_pos(d.get("famous_alumni_count", 15), 0, 200) * .15)
        s.append(norm_pct(d.get("postgrad_recommendation_rate", 15)) * .20)
        return sum(s)

    @staticmethod
    def student_life(d):
        s = []
        s.append(norm_pos(d.get("club_count", 150), 20, 500) * .55)
        s.append(norm_pos(d.get("exchange_programs", 50), 0, 300) * .45)
        return sum(s)

    @staticmethod
    def living_cost(d):
        s = []
        s.append(norm_neg(d.get("monthly_rent", 1500), 500, 5000) * .45)
        s.append(norm_neg(d.get("monthly_food", 1200), 600, 3000) * .35)
        s.append(norm_neg(d.get("monthly_transport", 200), 50, 800) * .20)
        return sum(s)

    @staticmethod
    def transport(d):
        s = []
        s.append(norm_pos(d.get("subway_lines", 3), 0, 30) * .35)
        s.append(norm_neg(d.get("airport_distance_km", 30), 5, 100) * .20)
        s.append(norm_neg(d.get("railway_station_distance_km", 10), 1, 50) * .20)
        s.append(norm_pos(d.get("bus_density_score", 6), 1, 10) * .25)
        return sum(s)

    @staticmethod
    def lifestyle(d):
        s = []
        s.append(norm_pos(d.get("tier3_hospitals", 8), 0, 50) * .22)
        s.append(norm_pos(d.get("large_malls", 15), 0, 100) * .18)
        s.append(norm_pos(d.get("parks_and_museums", 25), 0, 200) * .18)
        s.append(norm_pos(d.get("safety_index", 7), 1, 10) * .22)
        s.append(norm_neg(d.get("annual_aqi", 75), 20, 200) * .20)
        return sum(s)

    @staticmethod
    def climate(d):
        s = []
        s.append(norm_opt(d.get("avg_temperature", 16), 14, 24, -5, 42) * .45)
        s.append(norm_opt(d.get("avg_humidity", 68), 40, 70, 20, 95) * .30)
        s.append(norm_neg(d.get("extreme_weather_days", 12), 0, 60) * .25)
        return sum(s)

    @staticmethod
    def development(d):
        s = []
        s.append(norm_pos(d.get("gdp_growth_rate", 6.0), 2, 15) * .28)
        s.append(norm_pos(d.get("tertiary_industry_pct", 58), 30, 85) * .22)
        s.append(norm_pos(d.get("talent_policy_score", 5), 1, 10) * .22)
        s.append(norm_neg(d.get("price_income_ratio", 10), 3, 25) * .28)
        return sum(s)

SCORERS = {
    "academic": Scorer.academic, "campus_env": Scorer.campus,
    "career": Scorer.career, "student_life": Scorer.student_life,
    "living_cost": Scorer.living_cost, "transport": Scorer.transport,
    "lifestyle": Scorer.lifestyle, "climate": Scorer.climate,
    "development": Scorer.development,
}

LABELS = {
    "academic": ("学术资源", "🎓"), "campus_env": ("校园环境", "🏫"),
    "career": ("就业前景", "💼"), "student_life": ("学生活动", "🎭"),
    "living_cost": ("生活成本", "💰"), "transport": ("交通便利", "🚇"),
    "lifestyle": ("生活品质", "🌸"), "climate": ("气候环境", "🌤️"),
    "development": ("城市发展", "📈"),
}
SCHOOL_DIMS = ["academic", "campus_env", "career", "student_life"]
CITY_DIMS = ["living_cost", "transport", "lifestyle", "climate", "development"]

class WeightCalculator:
    def validate(self, w):
        st = sum(w.get("school", {}).values())
        ct = sum(w.get("city", {}).values())
        v = {"school": {}, "city": {}, "school_vs_city_ratio": w.get("school_vs_city_ratio", 0.6)}
        if st > 0:
            for k, val in w.get("school", {}).items(): v["school"][k] = val / st
        else: v["school"] = dict(DEFAULT_WEIGHTS["school"])
        if ct > 0:
            for k, val in w.get("city", {}).items(): v["city"][k] = val / ct
        else: v["city"] = dict(DEFAULT_WEIGHTS["city"])
        return v
    
    # v2.0新增：根据问卷回答推导权重
    def derive_from_questionnaire(self, answers):
        """
        根据问卷回答自动推导权重配置
        
        Args:
            answers: 字典格式 {"Q1": "A", "Q2": "B", ...}
        
        Returns:
            权重配置字典 + 推导说明
        """
        # 1. 从默认权重开始
        school_weights = dict(DEFAULT_WEIGHTS["school"])
        city_weights = dict(DEFAULT_WEIGHTS["city"])
        
        # 2. 根据每个问题的回答累加权重增量
        top_dimensions = []  # 记录用户关注的维度（用于后续深度分析）
        
        for q_id, answer in answers.items():
            mapping = QUESTIONNAIRE_MAPPING.get(q_id, {})
            delta = mapping.get(answer, {})
            
            for dim, increment in delta.items():
                if dim in school_weights:
                    school_weights[dim] = school_weights.get(dim, 0) + increment
                    top_dimensions.append((dim, increment))
                elif dim in city_weights:
                    city_weights[dim] = city_weights.get(dim, 0) + increment
                    top_dimensions.append((dim, increment))
        
        # 3. 确定school_vs_city_ratio
        q1_answer = answers.get("Q1", "C")
        q2_answer = answers.get("Q2", "C")
        ratio = RATIO_ADJUSTMENTS.get((q1_answer, q2_answer), 0.60)
        
        # 4. 归一化处理
        raw_config = {
            "school": school_weights,
            "city": city_weights,
            "school_vs_city_ratio": ratio
        }
        
        validated = self.validate(raw_config)
        
        # 5. 识别top 3 关注维度
        top_dimensions.sort(key=lambda x: x[1], reverse=True)
        top_3 = [d[0] for d in top_dimensions[:3]]
        
        # 6. 生成推导说明
        explanation = self._generate_explanation(answers, validated, top_3)
        
        return {
            "weights": validated,
            "top_dimensions": top_3,
            "config_source": f"问卷推导({self._summarize_answers(answers)})",
            "explanation": explanation
        }
    
    def _summarize_answers(self, answers):
        """将问卷回答总结为可读字符串"""
        summary_map = {
            "Q1": {"A": "学术优先", "B": "就业优先", "C": "学术就业并重"},
            "Q2": {"A": "追求舒适", "B": "过得去就行", "C": "不太在意"},
            "Q3": {"A": "省钱优先", "B": "可以接受", "C": "不太在意"},
            "Q4": {"A": "交通便利优先", "B": "生活品质优先", "C": "两者都重视"},
            "Q5": {"A": "很敏感", "B": "一般般", "C": "不太在意"},
        }
        parts = []
        for q_id in sorted(answers.keys()):
            answer = answers[q_id]
            label = summary_map.get(q_id, {}).get(answer, answer)
            parts.append(label)
        return "+".join(parts)
    
    def _generate_explanation(self, answers, weights, top_dims):
        """生成权重推导说明"""
        lines = ["根据您的问卷回答，系统已自动推导出个性化权重配置：", ""]
        
        # 展示每个问题的影响
        q_descriptions = {
            "Q1": "学术vs就业偏好",
            "Q2": "校园环境期望",
            "Q3": "生活成本敏感度",
            "Q4": "交通vs品质偏好",
            "Q5": "气候敏感度",
        }
        
        for q_id in sorted(answers.keys()):
            answer = answers[q_id]
            desc = q_descriptions.get(q_id, q_id)
            lines.append(f"- Q{q_id[1]} ({desc}): 选择{answer} → 相关维度权重已调整")
        
        lines.append("")
        lines.append(f"**学校 vs 城市比例**: {weights['school_vs_city_ratio']*100:.0f}% : {(1-weights['school_vs_city_ratio'])*100:.0f}%")
        lines.append(f"**您最关注的维度**: {', '.join([LABELS.get(d, (d,''))[0] for d in top_dims])}")
        lines.append("")
        lines.append("> 💡 您可以在上述基础上继续微调，或直接使用此配置进行评分。")
        
        return "\n".join(lines)

    def calculate(self, raw, wc=None):
        if wc is None: wc = DEFAULT_WEIGHTS
        # v2.0支持：wc可以是derive_from_questionnaire返回的完整结果
        if isinstance(wc, dict) and "weights" in wc:
            w = wc["weights"]
            config_source = wc.get("config_source", "custom")
            top_dims = wc.get("top_dimensions", [])
        else:
            w = self.validate(wc)
            config_source = wc.get("config_source", "custom") if isinstance(wc, dict) else "default"
            top_dims = []
        
        sd, cd = raw.get("school", {}), raw.get("city", {})
        ds = {}
        for did, fn in SCORERS.items():
            ds[did] = round(fn(sd if did in SCHOOL_DIMS else cd), 1)
        sw = sum(ds[d] * wt for d, wt in w["school"].items())
        cw = sum(ds[d] * wt for d, wt in w["city"].items())
        ratio = w["school_vs_city_ratio"]
        total = sw * ratio + cw * (1 - ratio)
        bd = []
        for d in SCHOOL_DIMS + CITY_DIMS:
            ws = w["school"].get(d, 0); wx = w["city"].get(d, 0)
            wt = ws or wx
            bd.append({"dimension_id": d, "dimension_name": LABELS[d][0],
                       "raw_score": ds.get(d, 0), "weight": round(wt, 3),
                       "weighted_score": round(ds.get(d, 0) * wt, 1),
                       "category": "school" if d in SCHOOL_DIMS else "city"})
        bd.sort(key=lambda x: x["weight"], reverse=True)
        result = {"total_score": round(total, 1), "school_score": round(sw, 1),
                  "city_score": round(cw, 1), "dimension_scores": ds, "breakdown": bd,
                  "weights_used": w, "top_dimensions": top_dims}
        return result

def main():
    ap = argparse.ArgumentParser(description="权重计算引擎 v2.0")
    ap.add_argument("--data","-d",required=True,help="输入JSON数据文件")
    ap.add_argument("--weights","-w",default=None,help="权重配置JSON文件(preset名称或custom)")
    ap.add_argument("--output","-o",default=None,help="输出文件路径")
    ap.add_argument("--questionnaire","-q",nargs="+",help="问卷回答格式: Q1=A Q2=B ...")
    ap.add_argument("--list-presets",action="store_true",help="列出所有预设模板")
    args = ap.parse_args()
    
    if args.list_presets:
        print("📋 可用的预设模板:\n")
        for tid, tpl in PRESET_TEMPLATES.items():
            print(f"  [{tid}] {tpl['name']}")
            sw = sum(tpl['school'].values()); cw = sum(tpl['city'].values())
            print(f"    学校({sw*100:.0f}%): ", end="")
            for k,v in tpl['school'].items(): print(f"{LABELS[k][0]}={v:.0%} ", end="")
            print(f"\n    城市({cw*100:.0f}%): ", end="")
            for k,v in tpl['city'].items(): print(f"{LABELS[k][0]}={v:.0%} ", end="")
            print(f"\n    学校:城市 = {tpl['school_vs_city_ratio']*100:.0f}:{(1-tpl['school_vs_city_ratio'])*100:.0f}\n")
        return
    
    with open(args.data,'r',encoding='utf-8') as f: raw=json.load(f)
    wc = WeightCalculator()
    
    # v2.0支持：问卷模式
    if args.questionnaire:
        answers = {}
        for item in args.questionnaire:
            if "=" in item:
                k,v = item.split("=",1)
                answers[k.strip()] = v.strip().upper()
        result = wc.derive_from_questionnaire(answers)
        weights_result = result["weights"]
        config_source = result["config_source"]
        top_dims = result["top_dimensions"]
        print(f"\n🎯 问卷推导结果:\n{result['explanation']}\n")
    elif args.weights:
        try:
            with open(args.weights,'r',encoding='utf-8') as f: wcfg=json.load(f)
            weights_result = wc.validate(wcfg)
            config_source = wcfg.get("config_source", args.weights)
        except FileNotFoundError:
            if args.weights in PRESET_TEMPLATES:
                weights_result = wc.validate(PRESET_TEMPLATES[args.weights])
                config_source = PRESET_TEMPLATES[args.weights]["name"]
            else:
                weights_result = wc.validate(DEFAULT_WEIGHTS)
                config_source = "balanced(默认)"
        top_dims = []
    else:
        weights_result = wc.validate(DEFAULT_WEIGHTS)
        config_source = "balanced(默认)"
        top_dims = []
    
    calc_result = wc.calculate(raw, {"weights": weights_result, "config_source": config_source, "top_dimensions": top_dims})
    output = {**raw, **calc_result, "_meta": {**(raw.get("_meta",{})), "config_source": config_source, "last_updated": __import__("datetime").datetime.now().isoformat()}}
    
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output,'w',encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"✅ 评分结果已保存: {args.output}")
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__": main()
