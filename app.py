import csv
import io
import json
from html import escape

import streamlit as st

from generator import draft as generate_draft
from generator import mode, report as generate_report, topics as generate_topics
from storage import create_workflow, get_workflow, list_workflows, update_workflow


st.set_page_config(page_title="内容生产工作台", page_icon="✦", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif; }
.stApp { background: #f7f8f6; color: #182b25; }
[data-testid="stSidebar"] { background: #eaf0eb; border-right: 1px solid #dce6df; }
.block-container { padding-top: 2.2rem; max-width: 1180px; }
h1, h2, h3 { color: #143f32 !important; letter-spacing: -.025em; }
h1 { font-size: 2.25rem !important; }
[data-testid="stMetric"] { background: white; border: 1px solid #e3e9e4; border-radius: 14px; padding: 16px; }
div.stButton > button[kind="primary"] { background: #176b50; border-color: #176b50; border-radius: 9px; }
div.stButton > button { border-radius: 9px; }
.eyebrow { color: #477665; font-weight: 700; font-size: .78rem; letter-spacing: .14em; text-transform: uppercase; }
.subtle { color: #677c72; font-size: .95rem; }
.step { background: white; border: 1px solid #e1e9e3; border-radius: 12px; padding: 12px 15px; min-height: 74px; }
.step.active { border: 2px solid #248060; background: #f0f9f3; }
.step.done { background: #edf5ef; }
.step small { color: #648070; }
.step strong { display: block; margin-top: 3px; }
.topic-card { background: white; border: 1px solid #dfe8e1; border-radius: 14px; padding: 19px; min-height: 240px; }
.topic-card h3 { font-size: 1.1rem; margin: .4rem 0; }
.topic-card p { font-size: .88rem; color: #61776b; margin: .5rem 0; }
.topic-tag { color: #247154; font-size: .75rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


def refresh():
    st.rerun()


def advance(workflow_id, **changes):
    update_workflow(workflow_id, **changes)
    refresh()


def generation_error(exc):
    st.error(f"生成失败：{exc}")


with st.sidebar:
    st.markdown("### ✦ 内容工作台")
    st.caption("新媒体内容生产 · 可审核 Demo")
    st.divider()
    if st.button("＋ 创建新任务", type="primary", use_container_width=True):
        st.session_state.workflow_id = None
        refresh()
    workflows = list_workflows()
    if workflows:
        st.markdown("**最近任务**")
        for item in workflows:
            label = f"#{item['id']}  {item['brand']}"
            if st.button(label, key=f"history-{item['id']}", use_container_width=True):
                st.session_state.workflow_id = item["id"]
                refresh()
    st.divider()
    st.caption(f"内容生成：{mode()}")
    st.caption("演示数据仅用于流程展示；真实发布和平台数据需接入对应平台。")

st.markdown('<div class="eyebrow">CONTENT OPERATIONS / DEMO</div>', unsafe_allow_html=True)
st.title("从灵感到复盘，每一步都可控")
st.markdown('<p class="subtle">把选题、创作、审核和数据分析放进同一条工作流。</p>', unsafe_allow_html=True)

workflow_id = st.session_state.get("workflow_id")
workflow = get_workflow(workflow_id) if workflow_id else None

if workflow is None:
    st.markdown("### 创建一条内容任务")
    st.caption("填写一个场景，立即体验完整的内容生产流程。")
    with st.form("new-workflow"):
        brand = st.text_input("品牌 / 主题", value="青山咖啡", max_chars=50)
        audience = st.text_input("目标受众", value="想在家做好咖啡的上班族", max_chars=100)
        goal = st.text_input("内容目标", value="提升品牌认知和收藏量", max_chars=100)
        submitted = st.form_submit_button("创建任务 →", type="primary")
        if submitted:
            if not all(x.strip() for x in (brand, audience, goal)):
                st.warning("请填写全部信息。")
            else:
                st.session_state.workflow_id = create_workflow(brand, audience, goal)
                refresh()
    st.stop()

st.caption(f"任务 #{workflow['id']}  ·  {workflow['brand']}  ·  受众：{workflow['audience']}  ·  目标：{workflow['goal']}")

steps = ["选题分析", "内容创作", "人工审核", "数据复盘"]
status_to_step = {"created": 0, "topics_ready": 0, "topic_selected": 1, "draft_ready": 2,
                  "revision_requested": 2, "approved": 3, "reported": 3}
current = status_to_step[workflow["status"]]
cols = st.columns(4)
for i, (col, title) in enumerate(zip(cols, steps)):
    state = "done" if i < current else "active" if i == current else ""
    note = "已完成" if i < current else "进行中" if i == current else "待开始"
    col.markdown(f'<div class="step {state}"><small>0{i+1} / {note}</small><strong>{title}</strong></div>', unsafe_allow_html=True)
st.write("")

tab1, tab2, tab3, tab4 = st.tabs(steps)

with tab1:
    st.subheader("选题分析")
    st.caption("根据品牌、受众和目标形成候选角度。演示模式不使用实时热点数据。")
    if st.button("生成 3 个候选选题", disabled=workflow["status"] not in ("created", "topics_ready"), type="primary"):
        try:
            with st.spinner("正在分析选题…"):
                result = generate_topics(workflow["brand"], workflow["audience"], workflow["goal"])
            advance(workflow_id, topics=result, status="topics_ready", selected_topic=None)
        except Exception as exc:
            generation_error(exc)
    if workflow["topics"]:
        cards = st.columns(3)
        for i, (col, topic) in enumerate(zip(cards, workflow["topics"])):
            with col:
                safe = {key: escape(str(value)) for key, value in topic.items()}
                st.markdown(f'<div class="topic-card"><span class="topic-tag">方案 0{i+1} · {safe["format"]}</span>'
                            f'<h3>{safe["title"]}</h3><p><b>内容角度：</b>{safe["angle"]}</p>'
                            f'<p><b>受众需求：</b>{safe["audience_need"]}</p><p><b>策划依据：</b>{safe["reason"]}</p></div>',
                            unsafe_allow_html=True)
                if workflow["selected_topic"] == i:
                    st.success("已选定")
                elif workflow["status"] == "topics_ready" and st.button("选定此选题", key=f"topic-{i}", use_container_width=True):
                    advance(workflow_id, selected_topic=i, status="topic_selected")

with tab2:
    st.subheader("内容创作")
    if workflow["selected_topic"] is None:
        st.info("请先在“选题分析”中选定一个选题。")
    else:
        topic = workflow["topics"][workflow["selected_topic"]]
        st.info(f"已选选题：{topic['title']}")
        if workflow["status"] == "topic_selected" and st.button("生成图文稿与短视频脚本", type="primary"):
            try:
                with st.spinner("正在创作内容…"):
                    result = generate_draft(workflow["brand"], workflow["audience"], workflow["goal"], topic)
                advance(workflow_id, draft=result, status="draft_ready")
            except Exception as exc:
                generation_error(exc)
        if workflow["draft"]:
            st.markdown(f"**标题：** {workflow['draft']['title']}")
            st.markdown(f"**封面文案：** {workflow['draft']['cover_line']}")
            st.markdown("**正文预览**")
            st.text(workflow["draft"]["body"])
            with st.expander("配图建议与短视频脚本"):
                st.markdown(f"**配图建议**  \n{workflow['draft']['visual_notes']}")
                st.markdown(f"**30 秒脚本**  \n{workflow['draft']['script']}")

with tab3:
    st.subheader("人工审核")
    if not workflow["draft"]:
        st.info("内容生成后，审核人可以编辑、退回或通过。")
    else:
        if workflow["status"] == "approved" or workflow["status"] == "reported":
            st.success("审核已通过。以下是最终发布稿。")
            if workflow["review_note"]:
                st.caption(f"审核备注：{workflow['review_note']}")
            st.download_button("下载发布稿 JSON", json.dumps(workflow["draft"], ensure_ascii=False, indent=2),
                               file_name=f"content-{workflow_id}.json", mime="application/json")
        else:
            if workflow["status"] == "revision_requested":
                st.warning(f"已退回修改：{workflow['review_note']}")
            with st.form("review-form"):
                title = st.text_input("标题", value=workflow["draft"]["title"])
                cover = st.text_input("封面文案", value=workflow["draft"]["cover_line"])
                body = st.text_area("正文", value=workflow["draft"]["body"], height=260)
                visuals = st.text_area("配图建议", value=workflow["draft"]["visual_notes"])
                script = st.text_area("短视频脚本", value=workflow["draft"]["script"], height=130)
                note = st.text_input("审核意见 / 修改说明", value=workflow["review_note"])
                left, right = st.columns(2)
                approve = left.form_submit_button("通过并锁定发布稿", type="primary", use_container_width=True)
                revise = right.form_submit_button("退回继续修改", use_container_width=True)
                if approve or revise:
                    if not title.strip() or not body.strip():
                        st.warning("标题和正文不能为空。")
                    elif revise and not note.strip():
                        st.warning("退回时请填写审核意见。")
                    else:
                        edited = {"title": title, "cover_line": cover, "body": body,
                                  "visual_notes": visuals, "script": script}
                        advance(workflow_id, draft=edited, review_note=note,
                                status="approved" if approve else "revision_requested")

with tab4:
    st.subheader("数据复盘")
    if workflow["status"] not in ("approved", "reported"):
        st.info("发布稿审核通过后，可导入平台数据进行复盘。")
    else:
        st.caption("演示时可直接填写数据，也可上传 CSV。CSV 表头：impressions,likes,saves,comments。")
        uploaded = st.file_uploader("上传数据 CSV（可选）", type=["csv"], label_visibility="collapsed")
        defaults = workflow["metrics"] or {"impressions": 12800, "likes": 426, "saves": 318, "comments": 46}
        if uploaded is not None:
            try:
                row = next(csv.DictReader(io.StringIO(uploaded.getvalue().decode("utf-8-sig"))))
                defaults = {key: int(row[key]) for key in ("impressions", "likes", "saves", "comments")}
            except (ValueError, KeyError, StopIteration, UnicodeDecodeError):
                st.error("CSV 格式错误，请检查表头和第一行数据。")
        with st.form("metrics-form"):
            metric_cols = st.columns(4)
            labels = {"impressions": "曝光量", "likes": "点赞", "saves": "收藏", "comments": "评论"}
            metrics = {key: metric_cols[i].number_input(labels[key], min_value=0, value=defaults[key], step=1)
                       for i, key in enumerate(labels)}
            submitted = st.form_submit_button("保存数据并生成复盘", type="primary")
            if submitted:
                if metrics["impressions"] == 0:
                    st.warning("曝光量需要大于 0。")
                else:
                    try:
                        with st.spinner("正在分析数据…"):
                            result = generate_report(workflow["brand"], workflow["topics"][workflow["selected_topic"]], metrics)
                        advance(workflow_id, metrics=metrics, report=result, status="reported")
                    except Exception as exc:
                        generation_error(exc)
        if workflow["report"]:
            metrics = workflow["metrics"]
            rate = (metrics["likes"] + metrics["saves"] + metrics["comments"]) / metrics["impressions"] * 100
            cols = st.columns(4)
            for col, (label, value) in zip(cols, [("曝光量", metrics["impressions"]), ("点赞", metrics["likes"]),
                                             ("收藏", metrics["saves"]), ("互动率", f"{rate:.2f}%")]):
                col.metric(label, value)
            st.markdown("#### 复盘结论")
            st.write(workflow["report"]["summary"])
            for insight in workflow["report"]["insights"]:
                st.markdown(f"- {insight}")
            st.markdown("#### 下一轮选题建议")
            for next_topic in workflow["report"]["next_topics"]:
                st.markdown(f"- {next_topic}")
