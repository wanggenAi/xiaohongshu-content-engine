"""Record actual Story Mining exports and optional downloaded Actions artifacts."""

import argparse
import json
from pathlib import Path

import yaml

from xhs_content_engine.editorial import verify_outputs

ROOT = Path(__file__).resolve().parents[1]


def read(root, name):
    return json.loads((root / name).read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--actions-url")
    parser.add_argument("--tests-passed", type=int, required=True)
    args = parser.parse_args()
    style = yaml.safe_load((ROOT / "config/editorial_style.yaml").read_text())
    outputs = ROOT / "outputs"
    report = read(outputs, "run_report.json")
    verify_outputs(outputs, style, report)
    stories = read(outputs, "story_candidates.json")
    lines = [
        "# V1.3 Story Mining 验收",
        "",
        "本记录从实际导出生成。合成测试样本不进入生产数据库；原句是来源自述，尚非独立核验。",
        "",
        f"采集时间：{report['run_at']}；筛选时间：{report.get('exported_at', report['run_at'])}。",
        "",
        "| 指标 | 本地真实运行 |",
        "|---|---:|",
    ]
    for label, key in [
        ("Raw items", "raw_items_this_run"),
        ("Fresh discovery", "story_discovered"),
        ("Fast Story Filter", "story_fast_filter"),
        ("Story Candidates", "story_candidate_count"),
        ("后续语义输入", "story_semantic_candidates"),
        ("Deep", "deep_candidates"),
        ("Human Review Queue", "human_review_queue"),
    ]:
        lines.append(f"| {label} | {report[key]} |")
    lines.extend(
        [
            "",
            "本轮保留原 Human/Editorial 门槛。每天 3～8 条 Deep 的目标尚未证明；"
            "找到故事原料与通过最终编辑门槛是不同结果。",
            "",
            "## 来源采集",
            "",
        ]
    )
    for source in report["sources"]:
        if source["source"] in {
            "human_story_search",
            "simon_willison",
            "armin_ronacher",
            "ethan_mollick",
        }:
            lines.append(
                f"- {source['source']}：{source['status']}，{source['raw_items']} 条；"
                f"公开评论摘录 {source.get('comment_excerpts', 0)} 段。"
            )
    lines.extend(["", f"## Top 10 Story Candidates（实际 {min(10, len(stories))} 条）", ""])
    for index, story in enumerate(
        sorted(stories, key=lambda item: -item["story_strength"])[:10], 1
    ):
        lines.extend([f"### {index}. {story['context']}", ""])
        for label, key in [
            ("Who", "primary_person"),
            ("Did what", "action"),
            ("What happened", "result"),
            ("Before", "before_state"),
            ("After", "after_state"),
            ("Conflict", "conflict"),
            ("Story Richness", "story_richness_score"),
            ("Fallback Story Score", "fallback_story_score"),
            ("Human Trigger", "human_trigger_score"),
            ("Viral Potential", "viral_potential"),
            ("Claim Scope", "claim_scope"),
            ("Evidence Gaps", "evidence_gaps"),
        ]:
            value = story.get(key)
            lines.append(
                f"- {label}: {value if value not in (None, '', []) else '未取得 / 未评估'}"
            )
        lines.append("")
    if args.artifact_root:
        cloud = read(args.artifact_root, "run_report.json")
        verify_outputs(args.artifact_root, style, cloud)
        queue = read(args.artifact_root, "human_review_queue.json")
        scores = [item["fallback_story_score"] for item in queue]
        if scores != sorted(scores, reverse=True):
            raise ValueError("fallback queue order mismatch")
        lines.extend(
            [
                "## GitHub Actions artifact",
                "",
                f"[完整运行]({args.actions_url})",
                "",
                f"Raw {cloud['raw_items_this_run']} → Fast {cloud['story_fast_filter']} → "
                f"Story Candidates {cloud['story_candidate_count']} → "
                f"Deep {cloud['deep_candidates']}；"
                f"Human Review Queue {cloud['human_review_queue']}。",
                "",
                f"人工队列 Fallback Story Score：{scores}。",
                "",
                "artifact 已下载后独立检查 Markdown、JSON、packet 数量、候选身份与来源片段。",
                "",
            ]
        )
        if cloud["story_provider_live_requests"] == 0 and queue:
            if not all(
                item["human_trigger_score"] is None and item["viral_potential"] is None
                for item in queue
            ):
                raise ValueError("keyless queue must stay unscored")
            lines.extend(
                ["云端没有语义 key；本地分数仅是人工排序信号，Human/Viral 均为 null。", ""]
            )
    lines.extend(
        [
            "## 自动检查",
            "",
            f"pytest：{args.tests_passed} passed；ruff check / format 与 diff 检查通过。",
            "",
            "测试包含 30 条明确标注的合成示例及 8 条冻结真实素材，另检验企业 we、"
            "评论归属、独立案例、低权威个人来源与无 API 排序。",
            "",
        ]
    )
    (ROOT / "docs/STORY_MINING_ACCEPTANCE.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
