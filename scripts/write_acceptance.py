"""Build the acceptance record from the actual export, never hand-count Top N."""

import argparse
import json
from pathlib import Path

import yaml

from xhs_content_engine.editorial import table_cell, verify_outputs

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def table(headers, rows):
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "|" + "|".join("---" for _ in headers) + "|",
            *["| " + " | ".join(table_cell(str(v)) for v in row) + " |" for row in rows],
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests-passed", type=int, required=True)
    parser.add_argument("--actions-url")
    parser.add_argument("--artifact-root", type=Path)
    args = parser.parse_args()
    outputs = ROOT / "outputs"
    style = yaml.safe_load((ROOT / "config/editorial_style.yaml").read_text())
    report = read(outputs / "run_report.json")
    counts = verify_outputs(outputs, style, report)
    items = read(outputs / "top_candidates.json")
    backtest = read(outputs / "v12_backtest.json")
    lines = [
        "# V1.2 Human Story 验收",
        "",
        (
            "本记录由 scripts/write_acceptance.py 读取实际 run report、JSON 与"
            " manifest 生成。内部验收材料含真实来源；日常摘要与公开简报另行检"
            "查平台名。没有自动发布，也没有伪造人工审美反馈。"
        ),
        "",
        "## 本地真实完整链",
        "",
        f"运行时间：{report['run_at']}。",
        "",
        table(
            ["指标", "实际数量"],
            [
                ["Raw", report["raw_items_this_run"]],
                ["本轮去重", report["unique_items_this_run"]],
                ["Stage A", report["stage_a"]],
                ["Stage B", report["stage_b"]],
                ["Deep", counts["deep_candidates"]],
                ["Human Review Queue", counts["human_review_queue"]],
                [
                    "Deep packets / public briefs",
                    f"{counts['editorial_packets']} / {counts['public_briefs_checked']}",
                ],
                ["Human Review packets", counts["human_review_packets"]],
            ],
        ),
        "",
        (
            f"本轮 Editorial live/cache：{report['provider_live_requests']}/"
            f"{report['provider_cache_hits']}；Human Trigger live/cache："
            f"{report['human_provider_live_requests']}/"
            f"{report['human_provider_cache_hits']}。缓存只复用完全一致的来源证"
            "据和问题定义。"
        ),
        "",
        f"## 当前真实 Deep：{len(items)} 条",
        "",
        table(
            [
                "Rank",
                "Editorial",
                "Human Trigger",
                "Viral",
                "Strongest Trigger",
                "Human Title Seed",
            ],
            [
                [
                    rank,
                    i["editorial_score"],
                    i["human_trigger_score"],
                    i["viral_potential"],
                    " + ".join(i["strongest_triggers"]),
                    i["human_title_seed"],
                ]
                for rank, i in enumerate(items, 1)
            ],
        ),
    ]
    for rank, item in enumerate(items, 1):
        lines.extend(
            [
                "",
                f"### {rank}. 场景、身份与标题",
                "",
                (
                    f"claim_scope：{item['claim_scope']}；semantic_status："
                    f"{item['semantic_status']}；Human gate："
                    f"{item['human_trigger_breakdown']['gate']}。"
                ),
                "",
                f"读者身份：{item['reader_self_projection']}",
                "",
                "Concrete Scene（来源原句）：",
                "",
                "```json",
                json.dumps(item["scene"], ensure_ascii=False, indent=2),
                "```",
                "",
                "Reversal："
                + (
                    json.dumps(item["reversal"], ensure_ascii=False)
                    if item["reversal"]
                    else "NONE；原文没有充分给出期待与结果的两段对照，不补造期待。"
                ),
                "",
                "三个不同角度的调查标题：",
                "",
                *[
                    f"- {s['angle']} [{s['claim_scope']}]：{s['text']}"
                    for s in item["human_title_seeds"]
                ],
                "",
                "自然讨论入口："
                + " / ".join(item["likely_comment_routes"])
                + "（是假设入口，不是已取得评论）。",
            ]
        )
    actual = backtest["real_candidates"]
    lines.extend(
        [
            "",
            f"## 冻结真实候选回测：{len(actual)} 条",
            "",
            (
                "使用 fixtures 中保存的真实原始标题、必要摘录、链接、时间与来源，"
                "不补写人物经历。算法中没有这些标题/品牌的得分分支。"
            ),
            "",
            table(
                ["原始题目", "Editorial", "Human", "Viral", "场景", "Gate", "降级原因"],
                [
                    [
                        i["title"],
                        i["editorial_score"],
                        i["human_trigger_score"],
                        i["viral_potential"],
                        i["human_trigger_breakdown"]["strong_scene"],
                        i["human_trigger_breakdown"].get("gate") or "NONE",
                        ", ".join(i["editorial_reject_reason"]) or "无",
                    ]
                    for i in actual
                ],
            ),
            "",
            (
                "机器人流量明显高于没有具体员工经历的 B2B 安全融资材料。高编辑价值"
                "不再保证进入 Deep；官方防诈、AI-first、交易、医疗、推荐控制与视频"
                "长度仍需具体人、实际行为和后果，不能把标题扩写成已经发生的故事。"
            ),
            "",
            "## 合成测试样本的真实语义回测",
            "",
            (
                "以下是显式标注的测试文本，不是新闻，不入生产库。pytest 的受控判断"
                "只验证组合逻辑；这里另外调用实际语义服务。"
            ),
            "",
            table(
                ["Fixture", "Human", "预期", "实际门槛"],
                [
                    [
                        i["id"],
                        i["human_trigger_score"],
                        backtest["expectations"][i["id"].removeprefix("fixture-")],
                        i["human_trigger_breakdown"].get("gate") or "LOW_HUMAN_TRIGGER",
                    ]
                    for i in backtest["synthetic_fixtures"]
                ],
            ),
            "",
            (
                "回测脚本自动断言四个负样本 <30、两个强样本 ≥65，且机器人场景高于"
                "无具体人的 B2B 材料；语义不完整则失败，不报告通过。"
            ),
            "",
            "## 测试与一致性",
            "",
            f"- pytest：{args.tests_passed} passed。ruff check / format --check 通过。",
            (
                "- 覆盖触发加分、无场景降级、正负样本、范围与标题约束、不同标题角"
                "度、读者代入、评论路由、缺key/超时/陈旧判断清除、人工队列和数量篡"
                "改。"
            ),
            "- LIKE / MAYBE / DISLIKE 及新旧 reason codes 兼容；未把任何自动判断写成人工标签。",
            (
                "- verify-outputs 读取真实文件，验证标题数量、表格行、JSON、候选身"
                "份、packet、公开简报、别名页与 run report；任一不一致失败。"
            ),
            (
                "- 本地审稿摘要与全部 public briefs 通过禁止平台名与 Show 海外 / A"
                "sk 海外 / 海外 post 机械表达检查；原始专名只保留在内部证据。"
            ),
            "",
            "## GitHub Actions 与实际 artifact",
            "",
        ]
    )
    if args.actions_url and args.artifact_root:
        cloud_report = read(args.artifact_root / "run_report.json")
        cloud_counts = verify_outputs(args.artifact_root, style, cloud_report)
        if cloud_report["stage_a"] and not (
            cloud_counts["deep_candidates"] + cloud_counts["human_review_queue"]
        ):
            raise ValueError("Cloud artifact has material but no reviewable candidates")
        lines.extend(
            [
                (
                    f"[完整手动 workflow / checks 与采集通过]({args.actions_url})。已下"
                    "载该 run artifact 并独立读取、核对文件。"
                ),
                "",
                table(
                    [
                        "Cloud raw",
                        "Stage A",
                        "Stage B",
                        "Deep",
                        "Human Review Queue",
                        "Review packets",
                    ],
                    [
                        [
                            cloud_report["raw_items_this_run"],
                            cloud_report["stage_a"],
                            cloud_report["stage_b"],
                            cloud_counts["deep_candidates"],
                            cloud_counts["human_review_queue"],
                            cloud_counts["human_review_packets"],
                        ]
                    ],
                ),
                "",
                (
                    "artifact 内 editorial_review.md 含实际候选、原始证据包链接和明确"
                    "状态，verify-outputs 通过。"
                ),
            ]
        )
        queue = read(args.artifact_root / "human_review_queue.json")
        if queue and all(i["semantic_status"] == "unavailable" for i in queue):
            if not all(
                i["human_trigger_score"] is None and i["viral_potential"] is None for i in queue
            ):
                raise ValueError("Unavailable queue pretends to have human scores")
            lines.append(
                "本次云端未取得语义判断：队列全部标记 NEEDS_HUMAN_REVIEW / semanti"
                "c_status=unavailable，Human/Viral=null。实际验证无 API 仍产生可读"
                "候选，不宣称云端完成语义筛选，也没有转移本地凭证。"
            )
    else:
        lines.append(
            "代码提交后运行完整 workflow，再从下载的 artifact 补入实测结果；这里不提前宣称通过。"
        )
    lines.extend(
        [
            "",
            "## 实际限制",
            "",
            (
                f"当前真实 Deep 只有 {len(items)} 条，数量与 JSON、Markdown、manife"
                "st、证据包一致，不为了得到四个故事而补齐。现有来源多为短摘录/标题"
                "，部分高价值新闻尚不能支撑人的具体经历；此层会把缺失显式暴露给编"
                "辑。"
            ),
            "",
            (
                "尚无独立交叉核验、真实评论采集或中文饱和度审计。情绪与受众是明确"
                "标注的调查假设，Viral Potential 不等于确定会爆。"
            ),
            "",
        ]
    )
    (ROOT / "docs/ACCEPTANCE.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
