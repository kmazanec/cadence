# Technology Research

**Confidence summary:** High confidence on LangGraph orchestration patterns, GraphRAG retrieval architecture, Neo4j vector/graph mechanics, and embedding model comparisons; medium confidence on several benchmark-specific performance numbers and a handful of single-source claims flagged explicitly below.

---

## LangGraph: When to Use StateGraph vs. Plain Python

LangGraph's StateGraph abstraction earns its overhead at roughly two or more agents or three or more branching decisions. Below that threshold, a plain LangChain chain or Python loop is simpler and incurs less boilerplate. Once you cross the threshold, StateGraph provides explicit typed state, deterministic edges, checkpointing, and retry primitives that you would otherwise have to hand-roll. A hub routing three specialized subgraphs (coaching Q&A, workout generation, workout logging) sits clearly above this threshold. [1][2]

The main runtime costs are (a) StateGraph schema definition boilerplate and (b) checkpoint write latency. Lean state schemas under 10 KB produce checkpoint writes under 15 ms using SQLite; schemas that store full document content can push writes to 300–800 ms and become the actual bottleneck. The design rule: store IDs and findings in state, not raw documents. [3]

LangGraph also passes state deltas rather than full conversation histories between agents, keeping token overhead bounded as the subagent count grows. A 100-run benchmark of a fixed five-agent workflow showed LangGraph completing more than twice as fast as CrewAI, with CrewAI's latency attributed to propagating large histories rather than state deltas. [2]

*LOW CONFIDENCE (single source, [2]):* The 2x speed comparison versus CrewAI and the specific "passes state deltas" framing comes from one vendor blog post and has not been independently confirmed.

---

## LangGraph: Supervisor vs. Swarm Routing Patterns

A dedicated LangGraph Supervisor (hub) pattern adds one extra LLM routing call per interaction. A customer-service benchmark with three specialist agents measured:

- Supervisor: 4.2 s latency, ~2,800 tokens per single-domain request (two LLM calls)
- Swarm (direct chain-of-thought loop): 2.8 s latency, ~1,900 tokens per single-domain request (one LLM call)
- Multi-domain: 9.1 s (supervisor) vs. 5.4 s (swarm)

The supervisor's token overhead is roughly 47% higher. However, the supervisor achieves 94% routing accuracy versus 91% for the swarm and provides a centralized audit trail. The overhead pays off when routing accuracy matters more than raw speed, when domains overlap, or when you need explainable control flow. For fewer than three domains, the recommendation is to skip multi-agent orchestration entirely. [4][5]

---

## LangGraph: Known Production Bugs and Footguns

**RetryPolicy does not catch Pydantic ValidationError.** A node configured with `RetryPolicy()` still executes only once when `model_validate()` raises `ValidationError`. The retry mechanism is bypassed for validation exceptions entirely. The workaround is manual `try/except` blocks inside the node function rather than relying on the framework's `RetryPolicy`. This is documented in GitHub issue langchain-ai/langgraph #6027 (August 2025). [6][7]

**Accumulator fields double on re-invocation.** `Annotated[list, add]` fields accumulate values across LangGraph checkpoints. If a completed thread is re-invoked with initial state passed again, checkpointed messages merge with the re-passed initial messages and the list doubles. The fix: pass initial state only on first invocation, not on resumption. A workout log accumulator is particularly at risk. [3]

*LOW CONFIDENCE (single source, [3]):* This doubling behavior is documented in one practitioner blog post; not yet reproduced against a specific LangGraph version.

**Per-thread subgraphs do not support parallel tool calls.** When an LLM tool-calls the same subgraph multiple times in one step (for example, generating two workout plans simultaneously), both calls write to the same checkpoint namespace and conflict. The officially documented error is `MULTIPLE_SUBGRAPHS`. The documented fixes are: pass `checkpointer=False` when compiling the subgraph, use the `Send()` API for fan-out instead of imperative node calls, or wrap each subagent in its own `StateGraph` with a unique node name to guarantee a stable namespace. In a hub plus three subgraph architecture, the hub must be designed to route to exactly one subgraph per turn, not fan-out concurrently. [8][9]

**Subgraph interrupt/resume can loop instead of pause.** GitHub issue #1222 documents a case where `interrupt_before` set on a subgraph node causes the nested subgraph to repeatedly execute the node instead of pausing and waiting for state insertion. The user-reported workaround is to pass the checkpointer explicitly to the subgraph compile step rather than inheriting it. When interrupts work correctly, they bubble up to `StateSnapshot.interrupts` on the parent and `Command(resume=value)` routes down to the correct subgraph namespace. Stateless subgraphs (`checkpointer=False`) cannot resume at all — they must be re-run from the beginning on crash. [8][10]

**Subgraph state schema conflicts are silent.** Keys missing from a subgraph's `input_schema` are silently dropped, not raised as errors. Additionally, if the parent and child define different reducers for the same key (for example, the parent uses `operator.add` to accumulate messages while the child treats the same key as a replacement field), the parent's reducer wins on write-back and silently corrupts state without raising an error. The fix is either to use different key names between parent and subgraph, or to wrap the subgraph in a node function that explicitly transforms state in both directions. [9][11]

**Streaming tool call arguments are corrupted under certain modes.** A LangChain forum report documents that using `subgraph=True` with `stream_mode='messages'` can produce incorrect tool call argument values. The workaround is to use `stream_mode='updates'` or `'values'` and read tool arguments from state rather than from streamed message events. [12]

*LOW CONFIDENCE (single source, forum post [12]):* This streaming defect is reported by one user and has not been confirmed against a specific LangGraph version or reproduced in official documentation.

---

## LangGraph: Tool Call Error Recovery

The production-validated pattern for recovering from invalid tool calls in LangGraph is: catch the error in `ToolNode`, format it as a `ToolMessage` containing the error text, return it to the LLM as conversation history, and loop back. This is not pre-execution validation — it is post-failure feedback. LangGraph's `ToolNode` automatically captures tool errors and reports them back to the model. A retry count should be tracked in graph state with a hard exit after a sane maximum to prevent unbounded loops. [13][14]

The superior variant (used by LangChain's `ToolStrategy` and shown in the extraction retry tutorial) appends the `ToolMessage` with validation error text to state so the LLM can self-correct on the next attempt. This error-feedback-in-state pattern reduced structured output parsing errors from 40% to 2% in documented cases. [14][15]

LangChain's `create_agent` handles multiple-tool-call errors by providing error feedback in a `ToolMessage` and prompting the model to retry — this is built-in behavior activated via the `handle_errors` parameter, which accepts a Boolean, custom error string, exception type filter, or custom handler function. [16]

**Baseline pattern caveat:** In the simplest retry loop pattern (`has_errors` flag, up to 10 attempts with `model_validate()`), each retry is an independent invocation and previous failures remain invisible to the LLM unless the error feedback is explicitly appended to state. The superior error-feedback-in-state approach should be preferred. [14][15]

---

## Structured Output and Confidence Scores

`with_structured_output()` fails in three documented modes: (1) function-calling failure producing Null output, (2) JSON mode hallucinating incorrect schema structure, (3) token exhaustion before JSON closure. The `include_raw=True` parameter enables capturing raw output before Pydantic validation, making it possible to distinguish which failure mode occurred. [17]

Any `confidence_score` field in a Pydantic model used with `with_structured_output()` is generated by the LLM itself, not statistically calibrated. The CONSTRUCT paper (arXiv 2603.18014) describes a separate scoring layer for per-field trustworthiness, but it requires an additional lightweight scoring pass not included in standard LangChain. The recommended production pattern is to treat the confidence field as a routing threshold signal (typically 0.7) rather than a probability: queries below threshold are routed to a clarification node rather than proceeding with a potentially misclassified intent. [17][18]

Embedding-based (semantic router) classification achieves 92–96% precision for intent routing in production chatbots at substantially lower cost than per-request LLM classification, since it uses precomputed route embeddings matched by cosine similarity. LLM-based routing is then reserved for ambiguous or novel intents that fall below the embedding similarity threshold. [19]

*LOW CONFIDENCE (single source, gist [19]):* The 92–96% precision figure for semantic router comes from one community gist and has not been confirmed by peer-reviewed or large-scale independent benchmarks.

---

## GraphRAG: Graph Traversal vs. Vector-Only Retrieval

GraphRAG's graph traversal component achieves 87.9–90.9% evidence recall on multi-hop questions where vector-only RAG fails. However, it introduces up to 2.3x higher latency and up to 40,000 tokens of context versus roughly 900 tokens for vanilla RAG. The graph component is justified for injury-exercise contraindication because that relationship is inherently multi-hop (member → injury → joint → contraindicated exercise), but traversal depth must be bounded and the retrieved neighborhood pre-filtered before feeding context to the LLM. [20][21]

Knowledge Graphs act as a factual constraint layer: if the graph does not contain a relationship between entities, the retrieval layer cannot provide that context, structurally reducing hallucination risk. This is categorically different from pure vector search, where a semantically similar but factually incorrect exercise could be surfaced. Contraindication edges must be built at ingestion time from a vetted ontology, not inferred by the LLM. [22][20]

---

## GraphRAG: Safety-Critical Hard Exclusion

For safety-critical retrieval (injury → contraindicated exercise), soft re-ranking cannot provide hard exclusion guarantees. Neo4j's `HybridRetriever` fuses vector similarity and full-text scores by normalizing each and combining them — a soft ranking that can still surface a contraindicated exercise at rank 1 if its embedding similarity score is high enough. The correct pattern is:

1. Cypher traversal to collect the complete set of CONTRAINDICATED exercises for this member's injuries.
2. Pass that set as a `WHERE NOT IN` exclusion filter to the subsequent vector search, so no contraindicated exercise can appear in any ranked result regardless of embedding proximity.

Both the Medical GraphRAG paper (arXiv 2408.04187) and the GraphRAG-FI paper (arXiv 2503.13804) treat safety as a hard pre-filter, not a soft re-ranking signal. [23][24]

Neo4j vector indexes use HNSW (Hierarchical Navigable Small World) for approximate nearest neighbor search. The approximation means a contraindicated exercise could theoretically be omitted from the true near-neighbor set or included via approximation error — both scenarios require the Cypher exclusion filter to take precedence over any ranked output. [25]

---

## Neo4j: Vector Indexes and Graph Traversal

**Vector index creation** requires specifying embedding dimensions and similarity function: `CREATE VECTOR INDEX name FOR (n:Label) ON (n.embedding) OPTIONS {indexConfig: {vector.dimensions: 1536, vector.similarity_function: 'cosine'}}`. The dimension must exactly match the embedding model's output; mismatched-dimension queries fail clearly rather than silently. Importantly, changes within a transaction are not visible to the vector index until the transaction is committed, meaning embedding writes and vector searches cannot share a transaction. [25][26]

*LOW CONFIDENCE (not self-verified, [25][26]):* No specific latency benchmarks for small graphs (hundreds of members) are documented in Neo4j's public developer guides; the design is intended to scale to millions of nodes.

**VectorCypherRetriever** executes a two-stage pipeline: HNSW vector search identifies initial nodes, then a developer-supplied Cypher query traverses relationships from those nodes to return enriched context. The `HybridCypherRetriever` extends this by incorporating full-text (BM25) search before the traversal step. [21][27]

**Score normalization, not RRF.** Neo4j's `HybridRetriever` normalizes vector and full-text scores independently before merging them via linear combination. This is not Reciprocal Rank Fusion — the relative weight of graph vs. vector signals depends on score distribution shapes and must be tuned empirically. Raw scores from the two sources are not directly comparable and should not be combined without normalization. [23][28]

**Variable-length path performance.** Cypher variable-length path traversal for neighborhood retrieval must use bounded depth and always specify relationship types — for example, `[:AFFECTS|LOADS|CONTRAINDICATED*1..3]`. Untyped variable-length paths produce full graph scans. Neo4j 5.9 introduced Quantified Path Patterns that provide inline predicate pruning during traversal; in one benchmark on a 6M+ node/relationship database, label inference improved from ~13 ms to ~80 µs. For injury-exercise neighborhood retrieval at 2–3 hops on hundreds of members, bounded typed traversal should execute well under 100 ms. [29][30]

*LOW CONFIDENCE (not self-verified, [29][30]):* The 13 ms → 80 µs figure comes from one Neo4j developer blog benchmark on a specific large dataset; performance at the fitness platform's scale is extrapolated, not directly measured.

**TigerGraph vs. Neo4j at scale.** The TigerVector paper (arXiv:2501.11216) reports TigerGraph achieving 3.77x higher throughput and 23–26% higher recall than Neo4j on SIFT100M and Deep100M benchmarks (100 million vectors). At hundreds-of-members scale, Neo4j's absolute throughput is more than sufficient. The performance gap matters at millions of members or millions of exercise records. [31]

*LOW CONFIDENCE (single source, [31]):* The benchmark is on datasets far larger than a fitness platform exercise catalog; direct applicability to the assessment's scale is limited.

---

## Hybrid Retrieval: Reciprocal Rank Fusion

Reciprocal Rank Fusion (RRF) with constant k=60 is the standard fusion strategy for combining vector and full-text retrieval signals. The formula is: `ScoreRRF(d) = sum(1 / (k + rank_i(d)))`. RRF is robust across different score scales because it ranks by position rather than raw score, so no normalization is needed before fusion. Documents appearing near the top of both retrieval systems rank highest. The standard pipeline is: hybrid retrieval (vector + BM25/full-text) fused via RRF, then optionally a cross-encoder reranker for precision. For safety-critical use cases, hard constraint pre-filtering must precede both retrieval signals. [32][33]

---

## Embedding Models: nomic-embed-text-v1 vs. text-embedding-3-small

From Table 1 of arXiv:2402.01613 (confirmed by Nomic's release announcement):

| Metric | nomic-embed-text-v1 | text-embedding-3-small | text-embedding-ada-002 |
|---|---|---|---|
| MTEB average | 62.39 | 62.26 | 60.99 |
| MTEB retrieval sub-score | 52.8 | 51.1 | — |
| LoCo long-context | 85.53 | 82.40 | — |
| Jina long-context | 54.16 | 58.21 | — |

The two models are effectively tied on general retrieval. Nomic wins on long-document benchmarks (LoCo); text-embedding-3-small wins on a different long-context benchmark (Jina). For matching short-text exercise names and injury descriptions (typically under 20 tokens), neither model's general MTEB advantage is likely to be the deciding factor. [34][35]

nomic-embed-text-v1 is 137M parameters, Apache-2 licensed, and fully open-weight, enabling local deployment that avoids per-token API costs and keeps member health data on-premises. text-embedding-3-small requires no infrastructure, has pay-per-call pricing, and integrates directly with OpenAI's tool ecosystem — making it the practical default for a rapid prototype. For a production system where cost or data-residency is a concern, nomic-embed-text-v1.5 (with Matryoshka truncation for flexible output dimensions) becomes competitive. [35][36]

*LOW CONFIDENCE (not self-verified, [36]):* The "default choice for most AI applications" framing for text-embedding-3-small and the operational simplicity comparison come from sources that have not been independently verified.

Neither model was evaluated on biomedical or fitness-specific benchmarks; domain adaptation via fine-tuning or instruction-tuned variants may matter more than general MTEB scores for this domain. [34]

*LOW CONFIDENCE (single source, [37]):* The 1.7-point MTEB retrieval sub-score gap (52.8 vs. 51.1) is from a single paper; MTEB retrieval is measured on Wikipedia-domain text, so transfer to fitness ontologies is not confirmed.

---

## Entity Matching: RapidFuzz + LLM Hybrid

For fuzzy entity matching (user says "bench press" vs. dataset "Barbell Flat Bench Press"), a hybrid approach — RapidFuzz narrows candidates, LLM verifies on short snippets — improved accuracy by up to 50 percentage points while reducing latency by half and cost-per-correct by 87–96% compared to LLM-only approaches. [38][39]

RapidFuzz's `WRatio` scorer is the recommended default for exercise name matching because it automatically selects among `ratio`, `partial_ratio`, `token_sort_ratio`, and `token_set_ratio` based on string length and token count. It applies `partial_ratio` comparisons (scaled by 0.9) when strings differ in length by 1.5x or more, and token-based comparisons (scaled by 0.95) for token-based cases. The `score_cutoff` parameter (recommended: 80 for exercise names) filters low-confidence candidates before LLM verification. `token_set_ratio` specifically handles unordered or repetitive text, making it effective when user input contains a subset of tokens from the canonical name. [40][41]

---

## References

1. https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025
2. https://aerospike.com/blog/langgraph-production-latency-replay-scale/
3. https://www.kalviumlabs.ai/blog/langgraph-in-production-stateful-multi-step-agents/
4. https://focused.io/lab/multi-agent-orchestration-in-langgraph-supervisor-vs-swarm-tradeoffs-and-architecture
5. https://dev.to/focused_dot_io/multi-agent-orchestration-in-langgraph-supervisor-vs-swarm-tradeoffs-and-architecture-1b7e
6. https://github.com/langchain-ai/langgraph/issues/6027
7. https://github.com/langchain-ai/langchain/discussions/26619
8. https://docs.langchain.com/oss/python/langgraph/use-subgraphs
9. https://deepwiki.com/langchain-ai/langgraph/3.6-graph-composition-and-nested-graphs
10. https://github.com/langchain-ai/langgraph/issues/1222
11. https://deepwiki.com/jun-sajima/langgraph-study/8.3-tool-call-validation-and-error-handling
12. https://forum.langchain.com/t/if-i-use-subgraph-true-stream-mode-messages-when-call-stream-the-arguments-of-tool-call-become-incorrect/1611
13. https://medium.com/@gopiariv/handling-tool-calling-errors-in-langgraph-a-guide-with-examples-f391b7acb15e
14. https://deepwiki.com/jun-sajima/langgraph-study/8.3-tool-call-validation-and-error-handling
15. https://medium.com/@docherty/mastering-structured-output-in-llms-revisiting-langchain-and-json-structured-outputs-d95dfc286045
16. https://docs.langchain.com/oss/python/langchain/structured-output
17. https://medium.com/@mr.murga/enhancing-intent-classification-and-error-handling-in-agentic-llm-applications-df2917d0a3cc
18. https://arxiv.org/pdf/2603.18014
19. https://gist.github.com/mkbctrl/a35764e99fe0c8e8c00b2358f55cd7fa
20. https://arxiv.org/html/2506.05690v3
21. https://neo4j.com/blog/developer/graph-traversal-graphrag-python-package/
22. https://salfati.group/topics/graph-rag
23. https://neo4j.com/blog/developer/hybrid-retrieval-graphrag-python-package/
24. https://arxiv.org/pdf/2408.04187
25. https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/
26. https://neo4j.com/developer/genai-ecosystem/vector-search/
27. https://medium.com/neo4j/enhancing-hybrid-retrieval-with-graph-traversal-using-the-neo4j-graphrag-package-for-python-983638d0aa08
28. https://neo4j.com/docs/cypher-manual/current/indexes/
29. https://neo4j.com/blog/developer/cypher-performance-neo4j-5/
30. https://neo4j.com/docs/cypher-manual/current/patterns/variable-length-paths/
31. https://arxiv.org/html/2501.11216v1
32. https://dev.to/lucash_ribeiro_dev/graph-augmented-hybrid-retrieval-and-multi-stage-re-ranking-a-framework-for-high-fidelity-chunk-50ca
33. https://avchauzov.github.io/blog/2025/hybrid-retrieval-rrf-rank-fusion/
34. https://arxiv.org/abs/2402.01613
35. https://www.nomic.ai/news/nomic-embed-text-v1
36. https://agntdev.com/text-embedding-3-small-openai-guide-2026/
37. https://ar5iv.labs.arxiv.org/html/2402.01613
38. https://arxiv.org/html/2511.11594v1
39. https://techcommunity.microsoft.com/blog/educatordeveloperblog/what%E2%80%99s-in-a-name-fuzzy-matching-for-real-world-data/4462152
40. https://github.com/rapidfuzz/RapidFuzz
41. https://medium.com/@kasperjuunge/rapidfuzz-explained-c26e93b6012d
42. https://sparkco.ai/blog/advanced-error-handling-strategies-in-langgraph-applications
43. https://arxiv.org/html/2402.01613v2
44. https://milvus.io/blog/choose-embedding-model-rag-2026.md
45. https://langchain-ai.github.io/langgraph/troubleshooting/errors/MULTIPLE_SUBGRAPHS/
46. https://neo4j.com/labs/apoc/
47. https://mirascope.com/blog/langchain-structured-output
