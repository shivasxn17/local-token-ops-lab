# Observability Implementation Plan

## Goal

Add local, vendor-neutral observability to the LangGraph/Ollama workflow and the
vLLM concurrency benchmark. Start with traces that explain workflow and model
call latency, then add useful metrics. Keep telemetry local and avoid collecting
prompt or generated content.

## Current surfaces

- `agents/langgraph_team.py` runs an async LangGraph workflow with sequential
  architect/developer nodes and parallel reviewer/QA nodes. It calls a local
  Ollama endpoint.
- `benchmarks/benchmark_concurrency.py` sends concurrent streaming requests to
  a local vLLM OpenAI-compatible endpoint and reports latency and throughput.
- The repository does not currently have a dependency manifest or a telemetry
  backend configuration.

## Proposed architecture

- Instrument the Python processes with the OpenTelemetry API and SDK.
- Export OTLP telemetry to a local collector/backend; do not require a hosted
  observability account.
- Use a local Jaeger OTLP endpoint for the first trace-viewing experience.
  Add a Prometheus-compatible metrics path and Grafana dashboards in a later
  phase if metrics need a persistent UI.
- Configure service names separately (for example, `token-ops-agent` and
  `token-ops-benchmark`) and read exporter endpoints from environment
  variables. Do not hard-code machine-specific URLs.
- Keep observability optional for local runs: the application should still run
  when no backend is configured, while exporter errors should be visible in
  logs rather than silently discarded.

## Implementation phases

### 1. Add telemetry foundations

- Add a project dependency manifest for runtime and development dependencies,
  including the required OpenTelemetry API, SDK, and OTLP exporter packages.
- Add a small shared telemetry setup module for resource attributes, provider
  lifecycle, OTLP configuration, and graceful shutdown.
- Configure service name and exporter endpoint through environment variables;
  document local defaults and how to disable export.
- Add a local backend setup guide. Start with Jaeger for traces; keep backend
  setup independent from application code.

### 2. Trace the agent workflow

- Create a workflow span around `graph.ainvoke`.
- Create spans for `architect`, `developer`, `reviewer`, and `qa_engineer`,
  including their model invocations. Preserve parent/child context across the
  parallel reviewer and QA branches.
- Record safe attributes such as workflow name, node name, model name, provider
  (`ollama`), and outcome. Record exceptions and mark failed spans as errors.
- Do not attach prompts, generated code, specs, reviews, tests, credentials,
  or `.env` values to spans, events, or exception messages.
- Shut down the provider after the run so buffered spans are exported.

### 3. Add workflow metrics

- Record workflow and node duration, workflow/node outcomes, and model-call
  duration and failures.
- Record input/output token usage only when the model response provides reliable
  usage metadata. Do not estimate tokens from character counts.
- Use bounded-cardinality labels: avoid task text, request IDs, exception
  messages, or other unbounded values as metric attributes.
- Add a minimal dashboard or documented queries for workflow duration, node
  duration, failures, and model-call latency.

### 4. Instrument and correct the benchmark

- Record request count, failures, concurrency, time to first byte/token (as
  defined by the stream), total duration, and throughput.
- Parse the server's streaming response and usage metadata where available.
  The current benchmark counts SSE data events as generated tokens, which is
  not necessarily accurate; do not publish that value as token count or TPS
  without correcting it. If only events can be measured, label the metric
  explicitly as event/chunk throughput.
- Use a request span per benchmark request, with endpoint/model and outcome
  attributes only; do not record prompt or response bodies.
- Keep benchmark and agent telemetry identifiable as separate services.

### 5. Add privacy, reliability, and regression checks

- Add tests using an in-memory span exporter to verify span names, parent/child
  relationships, parallel node coverage, and error recording without requiring
  Ollama, vLLM, or a running collector.
- Test that telemetry setup works when export is disabled and that shutdown
  flushes spans.
- Verify that prompt and response content do not appear in exported span
  attributes or events.
- Document expected local resource usage, troubleshooting, and how to inspect
  traces and metrics.

## Initial configuration

Use environment variables for at least:

- `OTEL_SERVICE_NAME`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `OTEL_TRACES_EXPORTER` and `OTEL_METRICS_EXPORTER` (or an equivalent
  documented enable/disable setting)

Do not put secrets in these values or commit local `.env` files.

## Completion criteria

- A local run of the agent produces a trace with the workflow, each graph node,
  model calls, and both parallel branches visible.
- A failed model call is visible as an error with useful context, but without
  prompt/response content.
- The workflow still completes when telemetry is disabled or no collector is
  running; exporter failures are surfaced clearly.
- Metrics use bounded attributes and represent measured quantities accurately.
- The benchmark distinguishes first-byte/token timing and does not report SSE
  event counts as token counts.
- Automated tests validate tracing behavior without external services.
