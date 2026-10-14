# Story Mining

Story Mining sits between discovery and semantic Human Trigger scoring. Its job is to find a source item that already contains a person, an action, a change, and a result. It does not turn a company announcement into a user story.

`config/source_priority.yaml` keeps source authority separate from story value:

- Tier S: first-person posts, personal and developer blogs, creator experiences, and independent-builder retrospectives.
- Tier A: public discussions and replies with several experiences or viewpoints.
- Tier B: official blogs, releases, documentation, and reporting used to verify a story.
- Tier C: pure news, which stays low priority without a supported human event.

`config/story_mining.yaml` contains first-person, identity, action, consequence, before/after, conflict, and query signals. The fast score is deterministic and explainable. Up to 50 inputs receive a bounded, cached extraction pass; only records with a supported actor, action, reported result and Story Richness ≥40 proceed to expensive Human/Editorial scoring, capped at 20. A smaller supply is reported honestly rather than filled to a quota.

The field choices are restricted to one selected firsthand account. Separate presence judgments check that it is a personal event with an actual result, rather than corporate “we”, a planned benefit or a product feature list. Before/after and conflict need their own evidence. Public comments remain attributed excerpts, with stance labels; comment counts never become viewpoints. Failed or missing extraction sends a deterministic local queue without extra downstream API calls.

Story Search consumes all configured query combinations through the public HN search index. Original posts and bounded ranked replies are read through the [official Firebase API](https://github.com/HackerNews/API). The API has no controversy metric, so the collector does not claim to select “controversial” comments. Login-gated communities use restricted adapters and Manual Inbox. Personal publisher feeds are Tier S; official updates are evidence sources.

Each `StoryCandidate` carries source item IDs and verbatim evidence spans. The extractor records `who`, `did_what`, `what_happened`, `before_state`, `after_state`, and conflict only when the source supplies them. Related patterns receive a cluster ID, but upgrading to `multiple_cases` requires distinct known case authors and evidence URLs; submitters of external links are not assumed to be their authors. A cluster is never automatically labelled a trend.

`fallback_story_score` is used only for cost control and the Human Review Queue. A missing semantic provider leaves `human_trigger_score` and `viral_potential` unset. `outputs/story_candidates.json` and the Story Mining block in each internal packet make this distinction auditable.
