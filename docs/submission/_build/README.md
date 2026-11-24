# Report generation scripts

These scripts regenerate the two Word reports in the parent folder, plus
the diagram images they embed.

## 1. Regenerate the diagrams (optional — already committed in `assets/`)

```powershell
cd docs/submission/_build
..\..\..\backend\.venv\Scripts\python.exe make_diagrams.py
```

Writes `assets/block_diagram.png` and `assets/flowchart.png` (Pillow only,
no external diagramming tool required).

## 2. Regenerate the reports (Node.js, using the `docx` npm package)

```powershell
cd docs/submission/_build
npm install docx
node make_project_report.js          # -> ../ExpenseFlow_AI_Project_Report.docx
node make_full_technical_report.js   # -> ../ExpenseFlow_AI_Full_Technical_Report.docx
node make_november_changes.js        # -> ../ExpenseFlow_AI_November_Changes.docx
node make_viva_guide.js              # -> ../ExpenseFlow_AI_Viva_Preparation_Guide.docx
```

`report_common.js` holds the shared brand palette, styles, header/footer
and table helpers both scripts use, so the two documents stay visually
consistent with each other and with the branded PDF (`backend/app/services/
pdf_service.py`) and the live app's own theme (`frontend/src/index.css`).

`node_modules` is not committed; reinstall with the command above before
running either script. After running them, you can delete `node_modules`,
`package.json` and `package-lock.json` again to keep the repo clean — the
`.js` scripts and `assets/` are the only parts worth keeping under version
control.

## What each report is

- **ExpenseFlow_AI_Project_Report.docx** — the required 10-page submission
  report (Title, Objective, Design Principles, Technical Model Detail,
  Block Diagram, Flowchart, step-by-step screenshots), built to the
  faculty's exact section list.
- **ExpenseFlow_AI_Full_Technical_Report.docx** — a deeper reference
  document covering the same material plus guardrails, observability,
  ethics & compliance, the full agent taxonomy, evaluation numbers, known
  limitations, and an API/tech-stack appendix.
- **ExpenseFlow_AI_November_Changes.docx** — a changelog of everything
  added in November, both committed (two git commits) and built this
  session but not yet committed.
- **ExpenseFlow_AI_Viva_Preparation_Guide.docx** — a pitch, a numbers
  table, a Q&A bank organised by unit, the agent taxonomy, anticipated
  pushback with answers, and a fast click-path for a live demo.

Both are verified with Microsoft Word via PowerShell COM automation
(`$word = New-Object -ComObject Word.Application`) for an authoritative
page count and PDF export, since this environment has no pandoc/LibreOffice/
poppler installed.
