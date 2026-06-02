# Research — AI-Powered Fitness Coaching Platform

**Project gist:** An AI fitness coaching platform with two architectural tiers, inferred from candidate take-home assessment materials. The thinner tier is a multi-agent LangGraph system (2–3 hour scope) where a hub agent routes user intent across three paths — general coaching Q&A, workout generation, and workout logging — each handled by a specialized subgraph with Pydantic-validated tool calls. The deeper tier is a knowledge-graph coaching platform (1–2 day scope) where member context is ingested into a Neo4j graph, retrieved via a GraphRAG hybrid of graph traversal and vector search, and used to generate injury-aware, personalized, explainable recommendations. Safety is load-bearing: a contraindicated exercise must never appear in output, and every inclusion/exclusion must be traceable to graph relationships — not vague LLM rationale.

**Depth:** standard · **Domains:** domain, technology, market

---

## Research Files

| File | Covers | Confidence |
|------|--------|------------|
| [DOMAIN.md](./DOMAIN.md) | Pre-participation screening (PAR-Q+, ACSM 2015), injury assessment protocols (L-DOC-SARA, SOAP notes), exercise contraindications by region (knee angle/kinetic-chain rules, shoulder impingement, lumbar herniation vs. stenosis), NASM OPT and ACSM 2026 programming standards, scope-of-practice and FDA/FTC regulatory landscape, AI failure modes in exercise recommendation, GraphRAG and knowledge-graph fitness architectures, user adherence data | **Medium** — high confidence on screening standards, NSCA/ACSM contraindication rules, scope-of-practice, regulatory classification, and adherence predictors; medium confidence on three architectural claims (deep-squat exclusion criteria precision, AI failure-mode distribution, KG explainability citation accuracy); low confidence on the 40%/71% personalization-adherence statistics (marketing figures, not peer-reviewed) |
| [TECHNOLOGY.md](./TECHNOLOGY.md) | LangGraph StateGraph vs. plain Python thresholds, supervisor vs. swarm routing tradeoffs with latency benchmarks, six documented LangGraph production bugs (RetryPolicy/Pydantic, accumulator doubling, MULTIPLE_SUBGRAPHS, interrupt/resume looping, silent schema conflicts, streaming corruption), tool-call error recovery patterns, structured output failure modes and confidence-score limits, GraphRAG graph-traversal vs. vector-only retrieval mechanics, Neo4j vector indexes (HNSW), VectorCypherRetriever, hybrid retrieval and hard exclusion patterns, embedding model comparison (nomic-embed-text-v1 vs. text-embedding-3-small), RapidFuzz + LLM fuzzy entity matching | **High** — core LangGraph orchestration patterns, GraphRAG retrieval mechanics, and Neo4j vector/graph mechanics are well-sourced; several benchmark-specific numbers and single-source operational claims are flagged medium or low confidence inline |
| [MARKET.md](./MARKET.md) | Market size ($10–17B in 2025, ~4–5x projected growth), competitive landscape (Whoop, Future, Caliber, Tonal, Fitbod, Freeletics, B2B coach tools), consumer preference data (10% prefer AI over human coach, 40%+ want sub-$10/month), churn benchmarks (9.2% average monthly), AI safety benchmarks (90.7% LLM accuracy / 41.2% comprehensiveness; 99.92% safety for rule-based system), knowledge-graph whitespace (no shipping consumer product uses KG for injury-aware contraindication), trust/explainability pilot RCT, legal gray zone summary | **Medium** — competitive pricing, consumer preference data, AI safety benchmarks, legal landscape, and KG whitespace finding are high confidence; market-size projections and churn figures are medium confidence; 80%-in-30-days dropout statistic and 52% trainer AI-adoption figure are explicitly flagged low confidence due to undisclosed methodology or single-source provenance |

---

## Caveats

The following could not be established with high confidence. A human should verify these before betting a decision on them.

**Adherence statistics.** The specific claims that AI-guided personalized training produces 40% higher adherence and that 71% of research shows AI increases exercise frequency come from a single industry marketing source, not peer-reviewed trials. Directional support exists (personalization helps), but the numbers are not citable.

**Churn benchmarks.** The 9.2% monthly churn and 80%-in-30-days figures are widely repeated across industry blogs but trace back to sources that do not disclose their primary research methodology. They are directionally useful; they should not anchor pricing or retention models.

**LangGraph bug versions.** Several LangGraph production bugs (accumulator doubling, streaming corruption) are documented in single practitioner blog posts without confirmed version attribution. Behavior may vary or have been patched; each should be reproduced against the target version before designing around it.

**GraphRAG fitness-domain benchmarks.** The GraphRAG performance gains cited (72–83% comprehensiveness improvement, 3.4x accuracy improvement) are from enterprise pharma and legal deployments, not fitness or exercise-contraindication settings. Transfer to this domain is architecturally plausible but not empirically confirmed.

**Embedding model fitness-domain fit.** Neither nomic-embed-text-v1 nor text-embedding-3-small has been evaluated on fitness or biomedical benchmarks. MTEB scores are measured on Wikipedia-domain text. Domain fine-tuning or instruction-tuned variants may matter more than the small general-benchmark gap between the two models.

**Deep-squat exclusion criteria.** The 2024 scoping review finding that 87% of studies conclude deep squats are safe is confirmed; the precise list of excluded injury conditions in that review (specifically whether ACL injuries and patellofemoral pain were formal exclusion criteria or merely absent from samples) is flagged medium confidence. The practical design rule — deep squats are not safe for injured populations regardless of classification — holds; the exact exclusion boundary needs clinical verification.

**Regulatory classification.** The FDA wellness-app vs. SaMD boundary is described from 2023–2026 guidance documents. Marketing language is as determinative as technical function; the platform's specific copy and feature framing should be reviewed by healthcare regulatory counsel before launch.

**No project brief exists.** This entire research framing is inferred from take-home assessment spec files. The actual project scope, target user, and deployment context are unknown. All domain, technology, and market findings are relevant but their weighting and applicability should be confirmed once a real project brief is in hand.
