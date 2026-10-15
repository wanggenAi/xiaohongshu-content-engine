# Content selection and publication

This project finds overseas AI, technology and internet topics that ordinary Chinese Xiaohongshu readers would want to open. Story Mining is one of six lanes, not the global ranking criterion.

Before any publication:

1. Read latest remote main, the real publication ledger, current editorial feedback and latest available Actions artifact. Do not equate a successful checks job with a freshly scored candidate artifact.
2. Run the active Live Hot Scan and cross-lane competition. Compare at least 20 distinct, actually assessed topics; merge repeated coverage of the same event. Keep source facts, discovery snippets and engagement evidence separate. A complete first-person story gives no global priority.
3. Read `outputs/publish_candidates.md/json` and `outputs/viral_reference_report.md`. Prepare 20 grounded headlines for the final candidate, run the pairwise Title Tournament and the separate homepage Blind Top 5. Keep topic strength, headline strength and claim support separate. Never restore the old one-shot soft booleans as publication vetoes.
4. Run `uv run python -m xhs_content_engine check-publish-gate CANDIDATE_ID` immediately before drafting/publishing. Only AUTO_PUBLISH_ELIGIBLE passes. Research Deep, rank 1, a content quota, or a public-wording check does not override this command.

No best-of-bad-batch. Missing credentials, unknown scores, missing evidence, stale scans, programmer-only interest or user DISLIKE must not become reasons to fill a daily publishing quota. NO_PUBLISH_TODAY is valid. Scores are editorial estimates, not measured audience behavior.

The October 14 correction and V1.5 refinement runs are candidate review only; no second publication. Preserve the already published website-traffic post. The user's exact DISLIKE and reasons are recorded in `data/editorial_feedback.jsonl`; do not relabel them MAYBE, add this event to positive references, or delete the post without a later explicit user request.

Public Telegram collection uses `config/telegram_channels.yaml`, no-login public channel/post pages and the manual inbox. Do not bypass login, CAPTCHA, private groups or account privacy. Public posts and views are discovery evidence, not automatic proof of their claims.

Keep original sources and measured engagement internally. Public Xiaohongshu content must not name Reddit, X, Twitter, Hacker News or Telegram as its source. Claims of overseas virality need actual heat evidence. Event-level discussion metrics are not a demonstration video's view count. Preserve research, availability, geography, pricing and attribution limits.

V1.6 ordinary-consumer attention is the final ranking criterion. Read `outputs/consumer_candidates.md`: title, cover, why a normal Chinese user clicks, human trigger, stripped-tech test and three-second STOP/MAYBE/SCROLL. Ordinary appeal + card stop strength carry 54%; source heat only 3%; evidence fitness, brand names, technical importance and reference similarity carry no attraction weight. Evidence, scope, fabrication, safety and the actual title/cover remain hard gates. Never place SCROLL, stripped-tech FAIL, missing click reasons or unsupported facts in the qualified Top 5. Fewer than five qualified cards is an explicit shortage, never fill with weak cards. Diversity resolves at most a 3-point gap, after quality gates. Three-second judgments see only the actual title and cover; rerun when the tournament changes a card. Model simulations are not measured human click rates. This round also has no Xiaohongshu publication.
