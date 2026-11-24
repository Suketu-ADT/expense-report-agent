const {
  fs, path, Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  GREEN_DARK, INK, MUTED, FONT,
  heading1, heading2, body, bullet, dataTable, pageBreak,
  brandedHeader, brandedFooter, blankHeader, blankFooter, coverPage,
} = require("./report_common");

const OUT = path.join(__dirname, "..", "ExpenseFlow_AI_November_Changes.docx");

const cover = coverPage({
  title: "ExpenseFlow AI",
  subtitle: "November 2026 Changes",
  kicker: "What changed, and how — a feature changelog",
  authors: "Rakshit Girase · Anuska Kumari · Suketu Mishra",
  affiliation: "L.Y. B.Tech (AIA-08)",
  date: "November 2026",
});

function featureBlock(title, lines) {
  return [
    heading2(title),
    ...lines.map((t) => bullet(t)),
  ];
}

const atAGlance = [
  heading1("At a Glance", 1),
  body("The project entered November 2026 as a working Unit III/IV mini-project (persistent memory, review/correction loop, approval gate, HTML email — committed 21 October). Everything below was added in November, extending it into the sem-end submission."),
  dataTable(
    ["Date", "Change", "Status"],
    [
      ["24 Nov", "Dynamic planning (Unit II), policy RAG, evaluation harness, guardrails, autonomy levels, reflection, currency tool, multi-agent debate, tracing", "Committed (a836c99)"],
      ["24 Nov", "Write-through report cache; 2 stale-read bugs found and fixed", "Committed (d3bc8fc)"],
      ["24–25 Nov", "Submission package: 10 end-to-end sample reports, 10 screenshots, test results, demo video script", "Built this session — not yet committed"],
      ["25 Nov", "Branded PDF letterhead redesign (pdf_service.py)", "Built this session — not yet committed"],
      ["25 Nov", "Project Report + Full Technical Report rebuilt with real diagrams, to the faculty's exact spec", "Built this session — not yet committed"],
      ["25 Nov", "PPT redesigned: brand palette, block diagram, flowchart slide, screenshot proof strip", "Published to the live deck — not a git change"],
    ],
    [1400, 6400, 1700],
  ),
  pageBreak(),
];

const section2 = [
  heading1("24 November — Dynamic Planning, Tool Use & Sem-End Extensions", 2),
  body("Committed as a836c99. Extends the Unit III/IV mini-project into the sem-end submission with eight additions, verified by 82/82 backend tests (at the time) and the 500-claim large-dataset regression still reporting “passed” after the change."),

  ...featureBlock("Unit II: Request-driven planning", [
    "A Planner (planner_service.py) parses the request text with a deterministic regex pass (always runs, fully offline), refined by an optional LLM pass that can only override a field it actually extracted — never degrades below the offline baseline.",
    "Anomaly Detection and Period Comparison are now optional pipeline stages: they run only when the parsed intent calls for them, and always report COMPLETED or SKIPPED so the plan is visible, not silent.",
  ]),
  ...featureBlock("Unit III: Retrieval-augmented policy grounding", [
    "Reimbursement decisions used to cite one hardcoded string. They now retrieve the matching clause from travel_policy.md via a local term-overlap retriever (policy_rag.py) — no embeddings, no network call — and cite its real section number.",
    "Grounds the explanation only; the approved amount is unchanged, confirmed by re-running the full 500-claim regression after the change.",
  ]),
  ...featureBlock("Automated evaluation harness", [
    "evaluation_service.py scores categorization accuracy (100% rule tier, CI-asserted), Review Agent false-positive/true-positive rates (0% / 100% over 30 synthetic trials), and retry-loop resolution — the hard-numbers counterpart to the live demos.",
  ]),
  ...featureBlock("Guardrails", [
    "sanitize_for_prompt strips injection phrasing before any untrusted field reaches an LLM prompt.",
    "validate_llm_category / PlannerIntentOutput whitelist- or schema-validate every LLM response — nothing is trusted verbatim.",
    "redact_pii scrubs emails, phone numbers and card-like digit sequences before they reach an audit log.",
  ]),
  ...featureBlock("Reflection on the categorization fallback", [
    "A second LLM pass critiques the first proposal and may revise it; the critique is logged either way, visible in the run log rather than opaque.",
  ]),
  ...featureBlock("Configurable autonomy levels", [
    "cautious / co_pilot / trusting tune how many Correction retries are trusted before escalating (0 / 3 / 5). Email dispatch still always requires explicit human approval at every level — this gate is not configurable.",
  ]),
  ...featureBlock("Multi-agent debate for ambiguous receipts — kept advisory", [
    "Two LLM advocates argue for competing receipt candidates; a judge opines. An earlier version let the judge's pick auto-resolve the claim — it silently approved a claim a human should have reviewed and broke a labelled regression test. Reverted to advisory-only: the transcript is shown to the reviewer, never the decision.",
  ]),
  ...featureBlock("Currency Conversion tool", [
    "A genuine external tool call: a live, no-auth exchange-rate API (3-second timeout) with a static offline fallback table. Informational only — never feeds into confirmed_total.",
  ]),
  ...featureBlock("Observability", [
    "Always-on per-stage latency trace, computed centrally from LangGraph's stream events — zero changes to individual agent files. Documented, opt-in LangSmith auto-instrumentation for full LLM-call tracing.",
  ]),
  ...featureBlock("New jury documentation", [
    "agent_taxonomy.md, ethics_and_compliance.md, observability.md, evaluation_report.md — plus updates to the existing problem statement, demo guide and viva prep.",
  ]),
  pageBreak(),
];

const section3 = [
  heading1("24 November — Write-Through Report Cache", 3),
  body("Committed as d3bc8fc. Report history is read far more often than written — every run's Orchestrator recall, every Period Comparison lookup, and every dashboard poll of /api/reports/history was a fresh SQLite query. memory_service.py now keeps three in-memory caches (by report_id, by (period, user), and by user) in front of the database, mirroring the existing active_runs dict pattern already used for live run state."),
  heading2("Two real bugs found and fixed while building it"),
  bullet("Two call sites in main.py — approve_run's delivery-status flip and the PDF-regeneration path's report_file_path update — wrote to the database directly via SQLAlchemy, bypassing the cache entirely. A report approved through either path would have shown “pending” forever to a cached reader."),
  bullet("Every cache getter returned the cached dict by reference, not a copy. GET /api/reports/{id} mutates its result by adding a reimbursement key — without a copy, that mutation would have leaked into the cache and corrupted it for every later reader."),
  body("Verified live — approving a report correctly flips pending → delivered with no stale read — plus the full 88-test suite and the 500-claim regression, both re-run clean afterward."),
  pageBreak(),
];

const section4 = [
  heading1("24–25 November — Submission Package (not yet committed)", 4),
  body("Built in this session, on disk but not committed to git, so they're a deliberate decision away from landing — see the closing note."),
  ...featureBlock("10 end-to-end sample reports", [
    "docs/submission/sample-reports/ — each one driven through the real running backend (CSV import → /api/run → receipt matching → PDF export), not hand-written: RAG policy citations, anomaly detection, multi-currency conversion, period-comparison memory recall, combined dynamic planning, multi-agent debate, duplicate-receipt guarding, guardrails/data-quality, autonomy-level contrast, and one comprehensive flagship run.",
    "Each ships with the claims.csv and receipt .txt files that produced it, plus a full API status-JSON snapshot, so any of the ten is reproducible by hand in the UI.",
  ]),
  ...featureBlock("Screenshots, test results & demo script", [
    "docs/screenshots/submission/ — 10 fresh screenshots of the live dashboard.",
    "docs/TEST_RESULTS.md — consolidated test/build/regression/evaluation results.",
    "docs/DEMO_VIDEO_SCRIPT.md — an 8-shot script with narration and exact click sequences, for self-recording.",
  ]),
  pageBreak(),
];

const section5 = [
  heading1("25 November — Professional Redesign of Every Deliverable", 5),
  body("A full visual and content pass across every submission artifact, triggered by direct feedback that the original versions weren't good enough to submit."),
  ...featureBlock("Branded PDF letterhead (backend/app/services/pdf_service.py)", [
    "Every generated report now carries an “ExpenseFlow AI” letterhead band, a report metadata block, color-coded claim status badges (green/amber/red), and a numbered confidentiality footer — using the exact brand palette from the live app's own theme.",
    "Verified against the real test suite (88/88, including the two tests that check exact text inside the generated PDF) and by rendering sample pages to images.",
  ]),
  ...featureBlock("Two Word reports rebuilt from scratch", [
    "ExpenseFlow_AI_Project_Report.docx — rebuilt to the faculty's exact required structure (Title, Objective, Design Principles, Technical Model Detail, Block Diagram, Flowchart, step-by-step screenshots), replacing the earlier six-page report.",
    "ExpenseFlow_AI_Full_Technical_Report.docx — an 18-page deeper reference covering the same ground plus guardrails, observability, ethics & compliance, the full agent taxonomy, evaluation numbers, known limitations and an API/tech-stack appendix.",
    "Both embed two hand-drawn diagrams (a system block diagram and a review/approval flowchart, built with Pillow — no external diagramming tool) and all 10 screenshots, with a branded letterhead header/footer matching the PDF and the live app.",
  ]),
  ...featureBlock("PPT redesigned", [
    "Every hardcoded color across all 14 original slides realigned to the app's exact brand green.",
    "The text-only “architecture” slide replaced with the real block diagram image.",
    "A new flowchart slide added, showing the review/correction/approval decision logic as a diagram.",
    "The single screenshot slide expanded into a 3-image proof strip, each tied to a claim made earlier in the deck.",
  ]),
];

const closing = [
  heading1("Current Commit Status", 6),
  body("Two commits (a836c99, d3bc8fc) are on the branch already. Everything in Sections 4 and 5 — the submission package and the professional redesign — exists on disk and in the live PPT artifact, but has not been committed to git. That's a deliberate checkpoint, not an oversight: commit it when you're ready to lock in this state of the submission."),
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
    headers: { default: brandedHeader("November 2026 Changes"), first: blankHeader() },
    footers: { default: brandedFooter("Agentic AI (23CSE4018) — Sem-End Submission"), first: blankFooter() },
    children: [
      ...cover, ...atAGlance, ...section2, ...section3, ...section4, ...section5, ...closing,
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(OUT, buffer);
  console.log("Wrote", OUT);
});
