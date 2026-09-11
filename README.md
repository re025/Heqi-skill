# 何栖

最初做这个skill的灵感，是来源于最近一次的南京旅游。南京，这座据说是龙气所钟的城市是如此使人流连忘返，所以我去过不下五次。这些经历大大小小的分散在我的成长记忆之中。而最近的一次旅途中，我发现我看这座城市的方法改变了，或者说，我打量这座城市的眼光改变了。我不自觉地以一个即将来这座城市生活的大学生来打量它，而非仅仅是一个游客。
由于高考的失利与填报大学时灰心丧气的懒惰，我被现今这所大学所录取。它有自己的优点，但它的缺点却都是我更在意的地方。所以，一个创作出一个skill来帮助像我一样的人——想知道学校如何却从未去过那个地方的人——来有一个更清晰的对学校的认知，而非依赖随机选择的中间人、学长学姐们不完整的建议，或者靠试错来解决。我希望利用这个skill将这些信息全部整合到一起，并为用户提供一个清晰、个性化且基于预算的即时推荐。

## 功能特性

- **🎯 Step 0 目标学校确认**：先询问是否有心仪大学——有则记录并衔接后续分析，无则基于问卷偏好推荐候选学校
- **🏫 学校深度画像**：学术资源、校园环境、就业前景、学生活动 4 大维度
- **🏙️ 城市生存指南**：生活成本、交通、生活品质、气候、城市发展 5 大维度
- **🎯 问答式权重推导**：5 个问题自动推导个性化权重（也可使用 5 套预设模板或完全自定义）
- **📊 深度维度分析**：针对用户最关注的 Top-3 维度展开详细报告
- **🌐 多源数据采集**：官方源 + 第三方 + 7 个 UGC 社区（校园墙/知乎/豆瓣/贴吧/小红书/B站/微博）
- **🏠 校外租房网站自动生成**：一键生成单文件 HTML 租房指南站（租金梯度、平台直达、避坑清单、看房检查表）
- **个性化决策报告**：Markdown 报告 + 多校对比（最多 5 所）
- **内置 10 所高校示例数据库**：清华、北大、上交、复旦、浙大、南大、武大、华科、中大、西交

## 使用方法

### 1. 数据采集

```bash
# 获取示例数据（10所示例高校之一）
python scripts/data_fetcher.py --school 浙江大学 --output-dir ./data/raw

# 生成 UGC 社区搜索词（7个平台）
python scripts/data_fetcher.py --school 浙江大学 --generate-ugc-queries

# 列出所有 UGC 数据源
python scripts/data_fetcher.py --list-ugc-sources
```

### 2. 权重计算

```bash
# 列出可用的预设模板
python scripts/weight_calculator.py --data data/raw/浙江大学.json --list-presets

# 使用预设模板计算（科研学霸/就业导向/城市探索家/温室花朵/均衡发展）
python scripts/weight_calculator.py --data data/raw/浙江大学.json --weights balanced --output data/scores/浙江大学.json

# 使用交互式问卷推导权重
python scripts/weight_calculator.py --data data/raw/浙江大学.json --questionnaire Q1=A Q2=A Q3=B Q4=C Q5=A --output data/scores/浙江大学.json
```

### 3. 生成报告

```bash
# 单校完整报告 + 自动深度分析
python scripts/report_generator.py --scores data/scores/浙江大学.json --output reports/浙江大学_report.md --deep-dive auto

# 控制台快速摘要
python scripts/report_generator.py --scores data/scores/浙江大学.json --summary

# 多校对比（最多5所）
python scripts/report_generator.py --scores data/scores/浙江大学.json data/scores/复旦大学.json --compare --output reports/对比报告.md
```

### 4. 生成校外租房指南站（v6.0 新增）

```bash
python scripts/rental_site_generator.py --data data/scores/浙江大学.json --output reports/浙江大学_租房指南.html
# 用浏览器打开生成的 HTML 文件即可查看/分享
```

## 文件结构

- `SKILL.md` — 技能说明文档（Step 0-A/0-B → Step 1-3 工作流、9大维度、数据源、失败处理）
- `scripts/data_fetcher.py` — 数据抓取器（10校示例库、7个UGC数据源搜索词生成）
- `scripts/weight_calculator.py` — 权重计算引擎（预设模板/问卷推导/自定义权重）
- `scripts/report_generator.py` — 报告生成器（单校/多校对比/深度分析）
- `scripts/rental_site_generator.py` — 校外租房网站生成器（单文件HTML）
- `references/` — 数据源指南、维度定义与归一化基准
- `templates/` — 报告模板、权重配置模板
- `examples/` — 示例输出

## 预设权重模板

| 模板 | 适用人群 | 校园:城市 |
|------|---------|----------|
| 科研学霸 | 走学术/科研道路 | 70:30 |
| 就业导向 | 以就业为首要目标 | 65:35 |
| 城市探索家 | 体验城市生活 | 30:70 |
| 温室花朵 | 需要舒适环境 | 70:30 |
| 均衡发展 | 全面均衡考虑 | 60:40 |

## 免责声明

本工具生成的报告与租房指南仅供参考。示例数据为演示用途，实际决策请通过官方渠道核实最新数据；租房时请实地看房、核实房源与签约主体，谨防诈骗。
