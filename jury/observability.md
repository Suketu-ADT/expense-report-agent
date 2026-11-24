# Observability & Tracing

Two independent layers, so tracing works whether or not the LLM is
configured — consistent with the project's "never degrade below the
offline baseline" design.

## 1. Per-stage latency trace (always on, built in)

`main.execute_run` consumes `expense_graph.stream(..., stream_mode="values")`,
which yields the full state once each node finishes. The gap in wall-clock
time between two consecutive yields is exactly that node's latency — so the
trace is computed centrally, in one place, with **no change to any
individual agent file**:

```python
now = time.perf_counter()
if last_agent is not None:
    trace.append({"agent": last_agent, "duration_ms": round((now - last_tick) * 1000, 1)})
last_agent, last_tick = state.current_agent, now
```

The finished trace is attached to `state.trace` and returned from
`GET /api/run/{run_id}` as `trace: [{agent, duration_ms}, ...]` — enough to
answer "which stage is slow" for any run, including ones that never touch
an LLM at all (the deterministic categorization/validation/calculation
path).

## 2. LLM-call tracing (opt-in, via LangSmith)

Every LLM call in this project already goes through LangChain
(`langchain_groq.ChatGroq`, composed with `PromptTemplate | llm`) in
`llm_service.py` and `planner_service.py`. LangChain auto-instruments every
such call when these two environment variables are set — **no code change
required**:

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<your LangSmith key>
```

With those set, every categorization fallback call, every reflection
critique pass, and every planner LLM refinement is traced to LangSmith with
its full prompt, response, token counts, latency and cost — giving the
jury a complete per-call audit trail for the LLM side specifically, on top
of the always-on per-stage trace above.

We did not make this mandatory: a jury laptop with no LangSmith account
and no internet still gets the full per-stage latency trace from layer 1,
and the pipeline's deterministic paths are entirely unaffected either way.

## What this does not cover

This is latency and (optionally) LLM-call observability, not a general
APM — it doesn't trace database queries, HTTP handler time, or memory
usage. For a pipeline this size, stage-level latency plus LLM-call tracing
covers the two places time and cost actually go.
