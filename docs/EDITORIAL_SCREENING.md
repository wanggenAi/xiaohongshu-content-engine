# Editorial screening contract

The semantic provider is a bounded reviewer of supplied evidence. It does not browse, create facts, or write final Xiaohongshu copy. Its answers are stored with the item so ChatGPT can see the rubric, probabilities, confidence, and missing evidence.

The code keeps four things separate:

- **Observed evidence:** title, bounded excerpt, author, timestamp, measured metrics, URLs, and exact supporting spans.
- **Editorial hypothesis:** an audience bridge, a possible lens, a title seed, a core story, and questions worth investigating.
- **Unknown:** Chinese coverage, independent corroboration, real reactions, product availability, outcome size, and whether a reported effect generalizes.
- **Decision:** verdict and reject reasons from the configured rubric.

The seven dimensions are semantic questions, not keyword counts. Human relevance asks what concrete human consequence is reported or worth checking. China relevance asks whether a Chinese ordinary reader can relate to the same kind of decision or concern; it does not claim that the source event happened in China. Novelty is capped when no Chinese coverage audit is supplied. Evidence quality is where attribution, corroboration and missing excerpts are penalized, so uncertainty is not double-counted as lack of human value.

The system will output fewer than the requested limit. Source caps are coverage caps only and never fill an empty slot. A `POSSIBLE` item still needs fact checking and ChatGPT/user approval; a `STRONG` item is a stronger research candidate, not an automatic publication recommendation.
