# Story Mining

Story Mining sits between discovery and semantic Human Trigger scoring. Its job is to find a source item that already contains a person, an action, a change, and a result. It does not turn a company announcement into a user story.

`config/source_priority.yaml` keeps source authority separate from story value:

- Tier S: first-person posts, personal and developer blogs, creator experiences, and independent-builder retrospectives.
- Tier A: public discussions and replies with several experiences or viewpoints.
- Tier B: official blogs, releases, documentation, and reporting used to verify a story.
- Tier C: pure news, which stays low priority without a supported human event.

`config/story_mining.yaml` contains first-person, identity, action, consequence, before/after, conflict, and query signals. The fast score is deterministic and explainable. A score below 40 is not sent through the expensive semantic pass unless it is the only item available for a reviewable outage sample.

Each `StoryCandidate` carries source item IDs and verbatim evidence spans. The extractor records `who`, `did_what`, `what_happened`, `before_state`, `after_state`, and conflict only when the source supplies them. Multiple independent items may receive a `story_cluster_id`; the cluster remains a set of cases and is never automatically labelled a trend.

`fallback_story_score` is used only for cost control and the Human Review Queue. A missing semantic provider leaves `human_trigger_score` and `viral_potential` unset. `outputs/story_candidates.json` and the Story Mining block in each internal packet make this distinction auditable.
