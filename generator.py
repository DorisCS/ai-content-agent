"""Content generation. Local sample mode is deterministic and needs no credentials."""

import json
import os
from urllib import request


def mode():
    return "AI API" if os.getenv("OPENAI_API_KEY") else "演示数据"


def _ask_json(instruction, payload):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    body = json.dumps({
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "instructions": instruction + " 仅返回一个有效 JSON 对象，不要 Markdown。不得编造真实统计数据或引用来源。",
        "input": json.dumps(payload, ensure_ascii=False),
    }).encode("utf-8")
    req = request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=45) as response:
        result = json.load(response)
    text = "".join(
        part.get("text", "")
        for item in result.get("output", [])
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    )
    return json.loads(text)


def topics(brand, audience, goal):
    prompt = ("你是新媒体内容策划。返回 JSON，键 topics 是恰好 3 个对象的数组；每个对象有 "
              "title、angle、audience_need、reason、format。reason 只说明选题逻辑，不声称有外部热点数据。")
    result = _ask_json(prompt, {"品牌": brand, "受众": audience, "目标": goal})
    if result is not None:
        items = result["topics"]
        if len(items) != 3 or any(not all(k in x for k in ("title", "angle", "audience_need", "reason", "format")) for x in items):
            raise ValueError("AI 返回的选题格式不完整，请重试")
        return items
    return [
        {"title": f"{audience}最常问的 5 个问题，一次说清", "angle": "问题解答", "audience_need": "快速消除选择疑虑", "reason": f"围绕“{goal}”整理高频决策问题，适合收藏和转发。", "format": "小红书图文"},
        {"title": f"第一次了解{brand}，先看这份入门指南", "angle": "新手入门", "audience_need": "用低门槛信息建立认知", "reason": "以步骤化结构降低理解成本，适合作为系列内容起点。", "format": "小红书图文"},
        {"title": f"关于{brand}，这 3 个常见误区值得避开", "angle": "误区澄清", "audience_need": "识别错误做法并获得替代方案", "reason": "用对比结构制造阅读动力，同时提供可执行建议。", "format": "小红书图文"},
    ]


def draft(brand, audience, goal, topic):
    prompt = ("你是新媒体编辑。围绕已选选题写一份可审核的小红书图文稿。返回 JSON 对象，" 
              "字段为 title、cover_line、body、visual_notes、script。script 是 30 秒口播脚本。" 
              "文案避免未经证实的效果承诺，结尾要有自然的互动引导。")
    result = _ask_json(prompt, {"品牌": brand, "受众": audience, "目标": goal, "选题": topic})
    if result is not None:
        if not all(k in result for k in ("title", "cover_line", "body", "visual_notes", "script")):
            raise ValueError("AI 返回的文案格式不完整，请重试")
        return result
    return {
        "title": topic["title"],
        "cover_line": "先收藏，再逐项检查", 
        "body": f"如果你也是{audience}，准备了解{brand}时，可以先从这 3 件事入手。\n\n"
                "① 明确自己的需求：现在最想解决的问题是什么？\n"
                "② 比较可选方案：重点看适用场景、投入和长期使用成本。\n"
                "③ 先做小范围尝试：记录体验，再决定是否继续。\n\n"
                f"这份清单希望帮你更清楚地做选择。你最在意哪一点？欢迎在评论区聊聊。\n\n#{brand} #入门指南 #实用清单",
        "visual_notes": "封面用一句问题吸引注意；内页分别呈现 3 个要点；末页放互动问题。整体保持留白和统一配色。",
        "script": f"0–5 秒：第一次了解{brand}，先别急着做决定。\n5–23 秒：先明确需求，再比较方案，最后小范围尝试。每一步都写下你的判断依据。\n23–30 秒：你最在意哪一步？评论区告诉我。",
    }


def report(brand, topic, metrics):
    impressions = metrics["impressions"]
    likes = metrics["likes"]
    saves = metrics["saves"]
    comments = metrics["comments"]
    engagement = (likes + saves + comments) / impressions * 100 if impressions else 0
    prompt = ("你是内容分析师。只根据提供的数据分析，不推断没有的数据。返回 JSON 对象，"
              "字段为 summary、insights（字符串数组，2 到 3 条）、next_topics（字符串数组，2 条）。")
    result = _ask_json(prompt, {"品牌": brand, "选题": topic, "指标": metrics, "互动率百分比": round(engagement, 2)})
    if result is not None:
        if not all(k in result for k in ("summary", "insights", "next_topics")):
            raise ValueError("AI 返回的复盘格式不完整，请重试")
        return result
    return {
        "summary": f"这条内容获得 {impressions:,} 次曝光，互动率约 {engagement:.2f}%。建议结合更多内容对比，判断选题是否稳定有效。",
        "insights": [
            f"点赞 {likes:,}、收藏 {saves:,}、评论 {comments:,}；收藏占互动的比例可用于观察内容的实用性。",
            "当前只有单条内容数据，无法确认增长由选题、封面还是发布时间带来。",
        ],
        "next_topics": [f"延伸：{topic['angle']}的进阶清单", f"对比：{brand}相关的常见选择场景"],
    }
