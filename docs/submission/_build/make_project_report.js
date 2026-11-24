const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  ImageRun, Header, Footer, PageNumber, PageBreak, PageOrientation,
  VerticalAlign, TabStopType, TabStopPosition,
} = require("docx");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const SCREENSHOTS = path.join(ROOT, "docs", "screenshots", "submission");
const ASSETS = path.join(__dirname, "assets");
const OUT = path.join(__dirname, "..", "ExpenseFlow_AI_Project_Report.docx");

// ── Brand palette (matches pdf_service.py / frontend index.css) ─────────
const GREEN = "255C45";
const GREEN_DARK = "194831";
const GREEN_LIGHT = "E8F1E9";
const INK = "192720";
const MUTED = "55645D";
const BORDER = "DDE4DC";
const ROW_ALT = "F9FAF7";
const WHITE = "FFFFFF";

const FONT = "Calibri";

function img(file, widthIn) {
  const p = path.join(ASSETS, file);
  const buf = fs.readFileSync(p);
  const { width, height } = sizeOf(buf);
  const w = Math.round(widthIn * 96);
  const h = Math.round(w * (height / width));
  return { data: buf, w, h };
}

function screenshotImg(file, widthIn) {
  const p = path.join(SCREENSHOTS, file);
  const buf = fs.readFileSync(p);
  const w = Math.round(widthIn * 96);
  const h = Math.round(w * (500 / 800));
  return { data: buf, w, h };
}

// Minimal PNG/JPEG size reader (avoids an extra npm dependency)
function sizeOf(buf) {
  if (buf[0] === 0x89 && buf[1] === 0x50) {
    // PNG: width/height are big-endian uint32 at offset 16/20
    return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
  }
  // JPEG: scan markers for SOF0/SOF2
  let offset = 2;
  while (offset < buf.length) {
    if (buf[offset] !== 0xff) { offset++; continue; }
    const marker = buf[offset + 1];
    if (marker === 0xc0 || marker === 0xc2) {
      const height = buf.readUInt16BE(offset + 5);
      const width = buf.readUInt16BE(offset + 7);
      return { width, height };
    }
    const length = buf.readUInt16BE(offset + 2);
    offset += 2 + length;
  }
  throw new Error("Could not determine image size: " + buf.slice(0, 16));
}

function heading1(text, num) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text: `${num}. ${text}`, bold: true, color: GREEN_DARK, size: 30 })],
    border: { bottom: { color: GREEN, space: 4, style: BorderStyle.SINGLE, size: 10 } },
    spacing: { before: 120, after: 200 },
  });
}

function heading2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, bold: true, color: GREEN_DARK, size: 24 })],
    spacing: { before: 200, after: 100 },
  });
}

function body(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, size: 21, color: INK, ...opts })],
    spacing: { after: 140, line: 288 },
    alignment: AlignmentType.JUSTIFIED,
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    bullet: { level },
    children: [new TextRun({ text, size: 21, color: INK })],
    spacing: { after: 90, line: 276 },
  });
}

function numbered(text, boldLead, ref = "main-numbering") {
  const runs = [];
  if (boldLead) {
    runs.push(new TextRun({ text: boldLead, bold: true, size: 21, color: INK }));
    runs.push(new TextRun({ text: " " + text, size: 21, color: INK }));
  } else {
    runs.push(new TextRun({ text, size: 21, color: INK }));
  }
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    children: runs,
    spacing: { after: 120, line: 288 },
  });
}

function caption(text) {
  return new Paragraph({
    children: [new TextRun({ text, italics: true, size: 19, color: MUTED })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 160 },
  });
}

function centerImage(image) {
  return new Paragraph({
    children: [new ImageRun({ data: image.data, transformation: { width: image.w, height: image.h }, type: imgType(image) })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 40 },
  });
}

function imgType(image) {
  return image.data[0] === 0x89 ? "png" : "jpg";
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

function cell(text, opts = {}) {
  const { bold = false, shade = null, color = INK, width, align = AlignmentType.LEFT } = opts;
  return new TableCell({
    width: width ? { size: width, type: WidthType.DXA } : undefined,
    shading: shade ? { type: ShadingType.CLEAR, fill: shade } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 90, bottom: 90, left: 110, right: 110 },
    children: [new Paragraph({
      alignment: align,
      children: [new TextRun({ text, bold, size: 19, color })],
    })],
  });
}

function dataTable(headerRow, rows, colWidths) {
  const total = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headerRow.map((t, i) => cell(t, { bold: true, shade: GREEN, color: "FFFFFF", width: colWidths[i] })),
      }),
      ...rows.map((r, idx) => new TableRow({
        children: r.map((t, i) => cell(t, { shade: idx % 2 ? ROW_ALT : null, width: colWidths[i] })),
      })),
    ],
  });
}

// ── Header / Footer ──────────────────────────────────────────────────────
const brandedHeader = new Header({
  children: [
    new Paragraph({
      tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
      border: { bottom: { color: BORDER, space: 4, style: BorderStyle.SINGLE, size: 6 } },
      children: [
        new TextRun({ text: "ExpenseFlow AI", bold: true, color: GREEN_DARK, size: 18 }),
        new TextRun({ text: "\tProject Report", color: MUTED, size: 16 }),
      ],
    }),
  ],
});

const brandedFooter = new Footer({
  children: [
    new Paragraph({
      tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
      border: { top: { color: BORDER, space: 4, style: BorderStyle.SINGLE, size: 6 } },
      children: [
        new TextRun({ text: "Agentic AI (23CSE4018) — Sem-End Submission", size: 15, color: MUTED }),
        new TextRun({ text: "\tPage ", size: 15, color: MUTED }),
        new TextRun({ children: [PageNumber.CURRENT], size: 15, color: MUTED }),
        new TextRun({ text: " of ", size: 15, color: MUTED }),
        new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 15, color: MUTED }),
      ],
    }),
  ],
});

const blankHeader = new Header({ children: [new Paragraph({ children: [] })] });
const blankFooter = new Footer({ children: [new Paragraph({ children: [] })] });

// ── Cover page ────────────────────────────────────────────────────────────
const cover = [
  new Paragraph({ spacing: { before: 1400 }, children: [] }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    border: { bottom: { color: GREEN, space: 10, style: BorderStyle.SINGLE, size: 24 } },
    children: [new TextRun({ text: "ExpenseFlow AI", bold: true, size: 72, color: GREEN_DARK })],
    spacing: { after: 200 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Autonomous Multi-Agent Expense Reporting System", size: 30, color: INK })],
    spacing: { after: 100 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Project Report", italics: true, size: 26, color: MUTED })],
    spacing: { before: 100, after: 900 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Agentic AI (23CSE4018) — Sem-End Mini Project", size: 22, color: INK, bold: true })],
    spacing: { after: 400 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Rakshit Girase · Anuska Kumari · Suketu Mishra", size: 22, color: INK })],
    spacing: { after: 80 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "L.Y. B.Tech (AIA-08)", size: 20, color: MUTED })],
    spacing: { after: 700 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "November 2026", size: 20, color: MUTED })],
  }),
  new Paragraph({ children: [new PageBreak()] }),
];

// ── 2. Objective & Design Principles ─────────────────────────────────────
const objectiveAndPrinciples = [
  heading1("Objective", 1),
  body("ExpenseFlow AI automates the full lifecycle of a corporate travel-expense report — from a raw CSV and a plain-English request, to a validated, independently reviewed, policy-grounded PDF report, to an approved email — replacing a slow, manual, error-prone process with an autonomous multi-agent pipeline. The specific objectives of this project are:"),
  numbered("end-to-end lifecycle of a travel-expense report, from ingestion to dispatch, with zero manual aggregation of totals.", "Automate the"),
  numbered("an execution plan is derived from the user's actual wording — an anomaly threshold, a period-comparison request, or neither — instead of always running an identical fixed sequence regardless of intent.", "Replace fixed processing with request-driven planning:"),
  numbered("across runs: short-term working state while a run is in flight, and long-term report history and a retrieval-grounded policy knowledge base that both survive a server restart.", "Give the system memory"),
  numbered("independent of any single agent: every total is computed deterministically and re-verified by a separate Review agent before a report is finalised.", "Guarantee mathematical correctness"),
  numbered("via structured inter-agent messages, a bounded self-correction loop, and recovery from injected discrepancies — without ever bypassing a human approval gate before anything money-adjacent leaves the system.", "Demonstrate multi-agent collaboration"),
  numbered("every LLM call non-financial, guarded against prompt injection, and backed by a fully offline deterministic fallback, so the system's core correctness guarantees hold with or without network access.", "Keep"),

  heading1("Design Principles", 2),
  body("Five principles run through every design decision in this project, and each one is enforced in code rather than left as a convention:"),
  numbered("Totals are computed once in deterministic Python, then independently re-computed by a separate Review agent using its own pass over the data. The LLM is deliberately kept out of financial arithmetic entirely.", "Never trust a single agent's arithmetic.", "principles-numbering"),
  numbered("No matter how cleanly a report's internal checks pass, email dispatch is gated behind an explicit human approve/reject step — this gate is not configurable at any autonomy level.", "Never send irreversibly without a human.", "principles-numbering"),
  numbered("Every one of the three LLM call sites — categorisation fallback, planner intent refinement, and the receipt-match debate — has a fully deterministic, offline-safe fallback. Removing the API key changes the quality of a few edge-case guesses; it changes nothing about correctness.", "Never degrade below an offline baseline.", "principles-numbering"),
  numbered("Ambiguous receipt matches, unclassifiable merchants, and unresolved review findings are routed to a human reviewer rather than silently resolved by whichever agent happened to touch them last.", "Make uncertainty visible, not guessed away.", "principles-numbering"),
  numbered("The Planner decides which pre-declared optional stages run on a given request, but it can never construct or reorder the underlying LangGraph topology itself — a deliberate constraint so the pipeline stays auditable for financial use.", "Keep the topology fixed; let only the reasoning be dynamic.", "principles-numbering"),
];

// ── 3. Technical Model Detail ─────────────────────────────────────────────
const stageRows = [
  ["1", "Orchestrator", "Resolves the reporting period, parses intent (Planner), builds the execution plan, recalls prior reports", "Fallback only"],
  ["2", "Data Retrieval", "Loads and parses the active expenses CSV", "No"],
  ["3", "Filter & Validation", "Filters to the period; flags missing/invalid fields; excludes duplicates", "No"],
  ["4", "Categorization", "Keyword rules first; LLM fallback (with reflection) for unrecognised merchants", "Fallback only"],
  ["5", "Calculation", "Exact decimal confirmed / provisional / per-category totals", "No"],
  ["6", "Anomaly Detection", "Flags expenses above a requested threshold — runs only if asked", "No"],
  ["7", "Period Comparison", "Recalls the previous period's total from memory and reports the delta — runs only if asked", "No"],
  ["8", "Currency Conversion", "Converts foreign-currency claims to INR for display (live rate + offline fallback)", "No"],
  ["9", "Expense Review", "Independently re-checks totals, duplicates, missing fields, subtotals, report consistency", "No"],
  ["10", "Correction", "Fixes critical findings and recalculates; bounded to 3 retries", "No"],
  ["11", "Report Generation", "Builds the branded PDF (ReportLab) — reimbursement decisions cite the retrieved policy clause", "No"],
  ["12", "Memory Persistence", "Saves the report summary to SQLite", "No"],
  ["13", "Email Dispatch", "Sends the report email — only after explicit human approval", "No"],
];

const technicalModel = [
  heading1("Technical Model Detail", 3),
  heading2("3.1 Architecture Overview"),
  body("All agents read from and write to one shared, mutable Pydantic object — the blackboard (ExpenseReportState) — and LangGraph connects them with conditional edges that route on the state it carries. FastAPI exposes the pipeline over a REST API; a React dashboard drives it and renders live per-stage status, the run log, category breakdowns, reimbursement decisions and the approval gate. SQLite persists report history, inter-agent messages and user preferences across restarts. The table below lists all 13 pipeline stages in execution order."),
  dataTable(["#", "Stage", "What it does", "LLM?"], stageRows, [500, 1800, 5800, 1500]),

  heading2("3.2 Technology Stack"),
  dataTable(
    ["Layer", "Technology"],
    [
      ["Agent orchestration", "LangGraph"],
      ["Backend API", "FastAPI, Uvicorn, Pydantic"],
      ["Persistence", "SQLite via SQLAlchemy"],
      ["LLM (optional)", "Groq-hosted model (openai/gpt-oss-20b) via LangChain"],
      ["PDF / email", "ReportLab, SMTP (simulated in development mode)"],
      ["Frontend", "React 19, Vite, Recharts, lucide-react, Axios"],
      ["Testing", "pytest (88 tests)"],
    ],
    [3000, 6600],
  ),

  heading2("3.3 Unit II — Planning & Reasoning"),
  body("A Planner (app/services/planner_service.py) replaces the fixed sequence with reasoning over the request: a deterministic regex pass always runs first (fully offline), extracting an anomaly threshold and a comparison request; an optional LLM pass refines phrasing the regex can't anticipate, but can only override a field it actually extracted a value for — a failed or unparseable LLM call leaves the deterministic result untouched. The resulting RequestIntent decides the execution plan itself, inserting Anomaly Detection and Period Comparison only when requested; both stages always report COMPLETED or SKIPPED, so the dashboard shows why a stage did or didn't run."),

  heading2("3.4 Unit III — Memory & Tool Use"),
  body("Short-term working memory is the blackboard state, alive for one run. Long-term memory is a SQLite-backed report history (recalled proactively by the Orchestrator and the Period Comparison stage) sitting behind a write-through cache, so the frequent reads a live run triggers never go stale and never hit the database unnecessarily. Tool use is demonstrated two ways: a currency-conversion tool call (a live exchange-rate API with a 3-second timeout and an offline fallback table) and a retrieval-augmented policy tool — reimbursement decisions cite the actual clause retrieved from the travel-policy document by a local term-overlap retriever, instead of a hardcoded string, with no embeddings or network call required."),

  heading2("3.5 Unit IV — Multi-Agent Collaboration & Fault Recovery"),
  body("An Expense Review agent independently recomputes every figure using deterministic Python — never an LLM — and performs five integrity checks (total reconciliation, duplicate exclusion, missing-field detection, category subtotal cross-footing, report-artifact consistency). Discrepancies are sent as structured AgentMessage objects to a Correction agent, which applies a deterministic fix and replies; the loop is capped at 3 retries, after which the report is held and needs_human_review is set. Four further extensions build on this loop without ever being allowed to change a reconciled total: a reflection pass that critiques the categorisation LLM's own proposal; a configurable autonomy level (cautious / co-pilot / trusting) that only changes how many retries are trusted before escalating; a strictly advisory two-advocate LLM debate for ambiguous receipt matches; and guardrails (prompt-injection sanitisation, whitelist-validated LLM output, PII redaction) around every LLM call."),

  heading2("3.6 Agent Taxonomy (Russell & Norvig)"),
  body("Every agent in the pipeline classifies cleanly against the standard taxonomy, and the classification is not decorative — it maps directly onto why each agent is built the way it is. Every simple-reflex agent (Validation, Calculation, Anomaly Detection) is also the set that stays fully deterministic; every model-based agent (Period Comparison, Exception Resolution) is the set that reads memory or reasons under uncertainty — and surfaces that uncertainty rather than resolving it silently; every utility-based agent (Expense Review, Correction) weighs several possible outcomes by explicit, auditable severity logic. The Orchestrator is the only goal-based agent, matching its role as the one component that decides what the rest of the run is for."),
  dataTable(
    ["Agent", "Type", "Why"],
    [
      ["Orchestrator", "Goal-based", "Maintains a goal, checks memory for whether it's already satisfied, plans before acting"],
      ["Filter & Validation", "Simple reflex", "Fixed condition-action rules per record, no memory, no lookahead"],
      ["Period Comparison", "Model-based", "Builds a model of “what happened last period” from memory before comparing"],
      ["Expense Review", "Utility-based", "Weighs multiple possible findings by severity to decide the overall outcome"],
      ["Exception Resolution", "Model-based", "Models which receipts could plausibly match which claims; routes uncertainty to a human"],
    ],
    [2800, 2000, 4800],
  ),

  heading2("3.7 Evaluation Summary"),
  body("An automated evaluation harness (app/services/evaluation_service.py) scores the pipeline against labelled fixtures, separately from the live demos:"),
  dataTable(
    ["Metric", "Result"],
    [
      ["Categorization accuracy — rule tier (deterministic, offline)", "16 / 16 = 100%"],
      ["Categorization accuracy — LLM fallback tier", "10 / 10 = 100%"],
      ["Review Agent false-positive rate (clean run wrongly flagged)", "0%"],
      ["Review Agent true-positive rate (injected discrepancy caught)", "100%"],
      ["Retry-loop resolution rate (Correction fixes it in one pass)", "100%"],
      ["500-claim large-dataset reimbursement regression", "500 / 500 = 100%"],
      ["Backend automated test suite", "88 / 88 passing"],
    ],
    [6300, 3100],
  ),
  pageBreak(),
];

// ── 5 & 6. Diagrams ───────────────────────────────────────────────────────
const diagrams = [
  heading1("Block Diagram", 4),
  body("The system block diagram below shows every pipeline stage as a module and the direction of control flow between them. All thirteen stages read from and write to one shared blackboard object rather than passing messages point-to-point, which is what lets any stage recall what an earlier stage decided without a separate message bus. The only cycle in the diagram is the bounded Expense Review → Correction retry loop (capped at 3 attempts); every other edge is a strict, one-directional, auditable sequence — a deliberate constraint for a financial pipeline (Design Principle 5)."),
  centerImage(img("block_diagram.png", 6.4)),
  caption("Figure 1. ExpenseFlow AI system block diagram — 13 pipeline stages over the shared blackboard state."),

  heading1("Flowchart", 5),
  body("Where the block diagram shows modules, the flowchart below shows the decision logic that actually governs whether a report reaches a human's inbox. Every financial-arithmetic finding is binary and deterministic (critical vs. not); every escalation path (retries exhausted, or a human explicitly rejects) still ends the same way — report generation proceeds, memory is still persisted, but email dispatch is withheld until a person acts. This is Design Principle 2 (“never send irreversibly without a human”) expressed as control flow rather than prose."),
  centerImage(img("flowchart.png", 5.6)),
  caption("Figure 2. Review, correction and human-approval decision flow."),
  pageBreak(),
];

// ── 7. Screenshots of the working model, step by step ────────────────────
const screenshotSpecs = [
  ["01-overview-summary-cards.jpg", "Overview dashboard", "After Generate report, the Overview page shows confirmed and provisional totals, expense counts, and informational cards for any optional stage (anomaly, comparison, currency) that actually ran."],
  ["02-agent-pipeline-13-stages.jpg", "Agent pipeline — 13 live stages", "Every stage reports COMPLETED, SKIPPED or RUNNING in real time; clicking a stage expands its own log entries."],
  ["03-agent-run-log.jpg", "Agent run log", "A timestamped, per-agent reasoning trail — including the Orchestrator's parsed plan and any guardrail warnings."],
  ["04-review-and-approval.jpg", "Expense Review & human approval gate", "The Review agent's independent result, and the Approve / Reject controls that always sit between a passed review and a sent email."],
  ["05-expense-reports-category-breakdown.jpg", "Category breakdown", "Itemised expenses with their assigned category; flagged and excluded records are highlighted separately from confirmed totals."],
  ["06-report-history.jpg", "Report history", "Every past report, persisted in SQLite and browsable across server restarts — long-term memory in practice, not just in the architecture diagram."],
  ["07-report-memory-recall.jpg", "Memory recall", "The Orchestrator's proactive recall of prior reports for the requested period, shown to the user rather than hidden inside a log."],
  ["08-reimbursement-policy-citation.jpg", "Policy-grounded reimbursement", "A claim's approval reason citing the actual retrieved travel-policy clause and section number — not a hardcoded string."],
  ["09-exception-resolution-evidence-review.jpg", "Multi-agent receipt resolution", "The Exception Resolution Agent proposing a receipt match and the Evidence Reviewer independently verifying it before any claim is approved."],
  ["10-advanced-autonomy-level.jpg", "Configurable autonomy level", "The cautious / co-pilot / trusting selector that tunes how many correction retries are trusted before escalating — the approval gate itself never becomes configurable."],
];

const screenshots = [heading1("Screenshot of Working Model — Step by Step", 6)];
screenshotSpecs.forEach(([file, title, cap], i) => {
  screenshots.push(new Paragraph({
    children: [new TextRun({ text: `Step ${i + 1}: ${title}`, bold: true, color: GREEN_DARK, size: 22 })],
    spacing: { before: 200, after: 60 },
    keepNext: true,
  }));
  screenshots.push(centerImage(screenshotImg(file, 3.0)));
  screenshots.push(new Paragraph({
    children: [new TextRun({ text: cap, size: 19, color: MUTED })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 220 },
  }));
  if ((i + 1) % 3 === 0 && i !== screenshotSpecs.length - 1) screenshots.push(pageBreak());
});

screenshots.push(
  heading2("Conclusion"),
  body("ExpenseFlow AI demonstrates all three extended units on top of a working baseline: request-driven planning that changes what the pipeline actually does (Unit II), persistent memory and a retrieval-grounded policy tool (Unit III), and an independently verified, self-correcting, human-gated multi-agent loop (Unit IV) — backed by an 88-test suite, a 500-claim regression at 100% accuracy, and the ten screenshots above taken directly from the running system, not a mockup."),
);

// ── Document assembly ────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [
      {
        reference: "main-numbering",
        levels: [{ level: 0, format: "decimal", text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 360 } } } }],
      },
      {
        reference: "principles-numbering",
        levels: [{ level: 0, format: "decimal", text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 360 } } } }],
      },
    ],
  },
  styles: {
    default: {
      document: { run: { font: FONT, size: 21, color: INK } },
    },
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
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1300, bottom: 1200, left: 1300, right: 1300 },
      },
      titlePage: true,
    },
    headers: { default: brandedHeader, first: blankHeader },
    footers: { default: brandedFooter, first: blankFooter },
    children: [
      ...cover,
      ...objectiveAndPrinciples,
      ...technicalModel,
      ...diagrams,
      ...screenshots,
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(OUT, buffer);
  console.log("Wrote", OUT);
});
