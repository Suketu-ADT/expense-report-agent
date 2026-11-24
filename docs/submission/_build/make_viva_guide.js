const {
  fs, path, Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  GREEN, GREEN_DARK, GREEN_LIGHT, INK, MUTED, BORDER,
  heading1, heading2, body, bullet, dataTable, pageBreak,
  brandedHeader, brandedFooter, blankHeader, blankFooter, coverPage,
} = require("./report_common");
const { Table, TableRow, TableCell, WidthType, ShadingType, VerticalAlign, FONT } = require("docx");

const OUT = path.join(__dirname, "..", "ExpenseFlow_AI_Viva_Preparation_Guide.docx");

const cover = coverPage({
  title: "ExpenseFlow AI",
  subtitle: "Viva Preparation Guide",
  kicker: "Agentic AI (23CSE4018) — Questions, answers, and numbers to have ready",
  authors: "Rakshit Girase · Anuska Kumari · Suketu Mishra",
  affiliation: "L.Y. B.Tech (AIA-08)",
  date: "November 2026",
});

function qa(q, a) {
  return [
    new Paragraph({
      children: [new TextRun({ text: "Q: ", bold: true, color: GREEN_DARK, size: 22 }),
                 new TextRun({ text: q, bold: true, color: INK, size: 22 })],
      spacing: { before: 180, after: 80 },
      keepNext: true,
    }),
    body(a),
  ];
}

const howToUse = [
  heading1("How to Use This Guide", 1),
  body("Read the pitch and the numbers table the night before. Skim the Q&A bank once, out loud if you can — the goal isn't memorised phrasing, it's being able to point at the specific file or test that backs each claim. The “Likely Pushback” section is the part most worth rehearsing: those are the questions that actually separate a pass from a strong pass."),
];

const pitch = [
  heading1("The 30-Second Pitch", 2),
  body("Say this if asked “what does your project do” cold, before anything else:"),
  new Paragraph({
    children: [new TextRun({
      text: "“ExpenseFlow AI turns a raw expense CSV and a plain-English request into a validated, policy-grounded report with a human approving before anything is sent. It started as a Unit III/IV mini-project — memory and multi-agent review. For the sem-end submission we added Unit II dynamic planning, a real retrieval-augmented tool, an evaluation harness, and guardrails — while keeping two guarantees non-negotiable everywhere: financial arithmetic is always deterministic Python, and email dispatch always needs explicit human approval.”",
      italics: true, size: 22, color: INK,
    })],
    spacing: { after: 160 },
    shading: { type: ShadingType.CLEAR, fill: GREEN_LIGHT },
  }),
  body("Two sentences after that, if there's room: “We verified this with an 88-test suite, a 500-claim synthetic regression at 100% accuracy, and ten sample reports driven end-to-end through the real running system — not mocked.”"),
  pageBreak(),
];

const numbers = [
  heading1("Numbers to Have Ready", 3),
  dataTable(
    ["Metric", "Result"],
    [
      ["Backend automated test suite", "88 / 88 passing"],
      ["500-claim large-dataset reimbursement regression", "500 / 500 = 100%"],
      ["Categorization accuracy — rule tier (deterministic, offline)", "16 / 16 = 100%"],
      ["Categorization accuracy — LLM fallback tier", "10 / 10 = 100%"],
      ["Review Agent false-positive rate (30 synthetic trials)", "0%"],
      ["Review Agent true-positive rate (injected discrepancy caught)", "100%"],
      ["Retry-loop resolution rate (Correction fixes it in one pass)", "100%"],
      ["Correction retry ceiling", "3 (default / co_pilot)"],
      ["Autonomy levels and their retry ceilings", "cautious = 0, co_pilot = 3, trusting = 5"],
      ["Pipeline stages", "13, over one shared blackboard state"],
    ],
    [6300, 3100],
  ),
  pageBreak(),
];

const unit2qa = [
  heading1("Unit II — Planning & Reasoning", 4),
  ...qa(
    "The Orchestrator used to run a fixed sequence. How does it plan now, and why not let an LLM choose the whole graph dynamically?",
    "A Planner (planner_service.py) parses the request into a structured RequestIntent — an anomaly threshold and a comparison flag — via a deterministic regex pass that always runs, optionally refined by an LLM call. The Orchestrator then inserts Anomaly Detection and/or Period Comparison into execution_plan only when that intent was detected; both always report COMPLETED or SKIPPED, so the plan is visible either way. We deliberately did not let an LLM choose the whole LangGraph topology: a financial pipeline needs a fixed, auditable set of nodes, so planning here means reasoning over the request to pick from a bounded, pre-declared set of optional stages — not open-ended graph construction."
  ),
  ...qa(
    "Why is memory required in an autonomous agent system at all?",
    "Standard LLM or workflow executions are stateless — once a run finishes, all internal state is lost. Memory provides historical context (has June already been filed?), supports policy compliance across runs, enables audit without re-running the pipeline, and prevents duplicate disbursements or redundant email sends."
  ),
];

const unit3qa = [
  heading1("Unit III — Memory, Tools & Environment", 5),
  ...qa(
    "What's the architectural difference between short-term and long-term memory here?",
    "Short-term working memory is the Pydantic blackboard (ExpenseReportState), alive only for one run's execution — raw records, validated lists, subtotals, flags, pending corrections. Long-term memory is SQLite via SQLAlchemy (ReportHistoryModel, UserPreferenceModel, AgentMessage), persisting on disk across restarts: finalized summaries, historical totals, and the audit trail."
  ),
  ...qa(
    "You said arithmetic avoids LLMs. Where does retrieval (RAG) actually appear, and why not embeddings or a vector database?",
    "Reimbursement decisions used to cite one hardcoded string. They now retrieve the matching clause from travel_policy.md via policy_rag.py — chunked by section, scored by a local term-overlap retriever. We used term overlap rather than embeddings deliberately: five short, topically distinct chunks don't need a heavier semantic retriever, a model download, or a network call — and the offline guarantee matters more than marginal recall on a five-chunk corpus. Retrieval only grounds the explanation; the approved amount is unchanged, confirmed by re-running the full 500-claim regression after the change."
  ),
  ...qa(
    "You added a report cache. How do you know it's never stale?",
    "Every write path — save_report_summary, plus the two spots in main.py that update a report directly via SQLAlchemy (approve_run's delivery flip, the PDF-regen path) — refreshes the cache immediately. Finding those two bypass writes was the real work: an earlier pass only refreshed from save_report_summary and missed them, which would have shown a report as pending forever after approval. Every getter also returns a shallow copy, not the cached object, since GET /api/reports/{id} mutates its result — without the copy that mutation would have corrupted the cache for every later reader. Verified live and against the full test suite plus the 500-claim regression."
  ),
  ...qa(
    "Why SQLite over PostgreSQL or a cloud database?",
    "Zero-configuration, embedded, ACID-compliant, bundled with Python — no server, daemon or network needed. A university jury often runs on a laptop with restricted Wi-Fi, so this guarantees a 100% reliable local demo. SQLAlchemy ORM means swapping to Postgres later is a connection-string change, not a rewrite."
  ),
];

const unit4qa = [
  heading1("Unit IV — Multi-Agent Collaboration & Fault Recovery", 6),
  ...qa(
    "Why didn't you use an LLM for the Review Agent?",
    "The Expense Review Agent uses 100% deterministic Python (Decimal arithmetic), never an LLM. LLMs are probabilistic and prone to arithmetic drift and rounding error; financial auditing needs absolute precision and reproducibility. It independently recomputes confirmed/provisional totals and category subtotals from categorized_expenses, filtering out flagged IDs, and compares against the reported totals."
  ),
  ...qa(
    "How do the agents communicate?",
    "Two patterns: the blackboard (every agent reads/writes the shared ExpenseReportState, reducing point-to-point coupling), and direct structured messaging — the Review Agent builds a typed AgentMessage (sender, recipient, message_type, findings with severity, requested_action) for targeted correction requests, forming an auditable trail."
  ),
  ...qa(
    "Walk me through autonomous failure recovery end to end.",
    "Expense Review detects a discrepancy and sets overall_status to needs_correction, attaching an AgentMessage. The conditional edge check_review sees retry_count < max_retries and routes to Correction, which applies a deterministic fix, strips invalid records, and increments retry_count. Flow returns to Re-Review; if it now passes, execution proceeds to Report Generation. If retries are exhausted or the finding can't be auto-fixed, needs_human_review is set — email stays held, the report still gets generated."
  ),
  ...qa(
    "How is human approval actually enforced at the code level, not just the UI?",
    "The conditional edge check_after_persist runs before Email Dispatch in expense_graph.py: if needs_human_review is true or approval_status is “rejected”, it returns END and the graph never reaches email_node. The UI's Approve/Reject buttons just call /api/run/{run_id}/approve or /reject — the actual gate is structural, in the graph, not a UI-only check."
  ),
  ...qa(
    "You added autonomy levels and a multi-agent debate. Why does neither let money move without a human?",
    "Autonomy levels only change how many Correction retries are trusted before escalating (0 / 3 / 5) — none of the three touch the approval gate before Email Dispatch. The receipt-matching debate (two LLM advocates, a judge) is advisory for a concrete reason, not caution for its own sake: an earlier version let the judge's pick auto-attach the receipt, and it silently approved a claim a human should have reviewed, breaking a labelled regression test. It's now a transcript the reviewer sees, never the decision."
  ),
];

const taxonomyRows = [
  ["Orchestrator + Planner", "Goal-based", "Maintains a goal, checks memory for whether it's satisfied, plans before acting"],
  ["Filter & Validation", "Simple reflex", "Fixed condition-action rules per record, no memory, no lookahead"],
  ["Categorization", "Reflex → model-based", "Keyword table first; LLM judgment under uncertainty only when no rule fires"],
  ["Calculation / Anomaly Detection", "Simple reflex", "Deterministic arithmetic / one threshold rule, no world model needed"],
  ["Period Comparison", "Model-based", "Builds a model of “last period” from memory, then compares"],
  ["Expense Review", "Utility-based", "Weighs multiple findings by severity to decide the overall outcome"],
  ["Correction", "Utility-based", "Chooses the remedy that fits the specific finding, or escalates"],
  ["Exception Resolution", "Model-based", "Models which receipts could match which claims; routes uncertainty to a human"],
  ["Evidence Reviewer", "Utility-based", "Weighs merchant/date/amount/policy checks, not a single pass/fail rule"],
];

const taxonomy = [
  heading1("Agent Taxonomy Quick Reference (Russell & Norvig)", 7),
  body("If asked to classify any agent on the spot, the pattern to lean on: simple-reflex agents are exactly the ones that stay 100% deterministic (nothing here should ever need a world model); model-based agents are the ones reading memory or reasoning under uncertainty, and in every case the uncertainty is surfaced, not silently resolved; utility-based agents choose among several outcomes with the “utility function” written down as explicit severity logic, not learned. No agent here is a learning agent — deliberately: an agent reconciling money shouldn't quietly change how it reconciles money from inferred patterns."),
  dataTable(["Agent", "Type", "Why"], taxonomyRows, [2900, 2200, 4700]),
  pageBreak(),
];

const pushback = [
  heading1("Likely Pushback — and How to Answer It", 8),
  heading2("“Isn't this just rule-based, not really 'agentic'?”"),
  body("Push back gently: an agent doesn't have to be a single LLM to count as agentic — it has to perceive, decide and act toward a goal, which the Orchestrator does (it consults memory, plans, and the plan changes with the request). What's deliberately NOT agentic here is the arithmetic, by design — Design Principle 1 (“never trust a single agent's arithmetic”) is the whole point, not an oversight."),
  heading2("“Why no trained ML model anywhere?”"),
  body("The only model is a third-party LLM used for three optional, non-financial decisions (categorization fallback, its reflection, planner refinement) — each with a deterministic offline fallback. There's no model to train because the project's thesis is that financial decisions should be auditable logic, not a model you'd otherwise have to explain post-hoc. See the Model Files Note for the longer version."),
  heading2("“Your planning is pretty limited — just two optional stages?”"),
  body("Correct, and that's the defensible position, not a weakness to hide: bounded planning over a small, pre-declared set of stages is the only form of “dynamic” that keeps a financial pipeline auditable. An LLM freely reordering or inventing pipeline stages at runtime is exactly the non-determinism the rest of the project exists to prevent."),
  heading2("“How do you know your evaluation numbers aren't cherry-picked?”"),
  body("Name the exact sources: rule-tier categorization accuracy is asserted in CI (tests/test_evaluation.py), not just reported; the 500-claim regression checks every claim's status and amount against a hand-computed expected-claims.csv, reproducible with run_test.py; the Review Agent rates come from 30 seeded synthetic trials, reproducible offline. Say plainly what it doesn't claim too: not a universal accuracy guarantee on arbitrary real-world data — see evaluation_report.md's own “what this does and doesn't claim” section."),
  heading2("“What's the weakest part of this project?”"),
  body("Have a real answer ready, pulled from Known Limitations: run state (and therefore approve/reject) lives in server memory, so restarting the backend loses in-flight runs; agent messages aren't persisted to the database; stored user preferences aren't yet used by the pipeline's decisions. Naming these unprompted reads far better than being caught not knowing them."),
  pageBreak(),
];

const demoCheatSheet = [
  heading1("If Asked for a Live Demo", 9),
  body("Full shot-by-shot script: docs/DEMO_VIDEO_SCRIPT.md. Fastest click-path if time is short:"),
  bullet("Overview → type a request with both “flag anything over X” and “compare to last month” → Generate report — shows the Planner choosing stages live."),
  bullet("Agent pipeline → click Anomaly Detection and Period Comparison to show their log entries and the Orchestrator's parsed plan."),
  bullet("Report memory → shows persisted history surviving across runs."),
  bullet("Two-claim jury demo → Review claim decisions → point at a claim's reason line citing the actual policy section."),
  bullet("Receipt agent demo → Match sample receipts → point at the Exception Resolution / Evidence Reviewer log lines, and the ambiguous case routed to a human."),
  bullet("Review & approvals → point at Approve/Reject without necessarily clicking — explain the gate is structural, not just a UI button."),
  body("If something doesn't behave as expected live: say what you expected, open the Agent run log for that stage, and read the actual line out loud. The run log is instrumented specifically so that this is possible — treat it as a feature, not a scramble."),
];

const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 21, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, bold: true, size: 30, color: GREEN_DARK },
        paragraph: { spacing: { before: 240, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, bold: true, size: 24, color: GREEN_DARK },
        paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, bottom: 1200, left: 1300, right: 1300 } },
      titlePage: true,
    },
    headers: { default: brandedHeader("Viva Preparation Guide"), first: blankHeader() },
    footers: { default: brandedFooter("Agentic AI (23CSE4018) — Sem-End Submission"), first: blankFooter() },
    children: [
      ...cover, ...howToUse, ...pitch, ...numbers, ...unit2qa, ...unit3qa, ...unit4qa,
      ...taxonomy, ...pushback, ...demoCheatSheet,
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(OUT, buffer);
  console.log("Wrote", OUT);
});
