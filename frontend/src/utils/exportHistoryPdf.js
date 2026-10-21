// Client-side PDF export of the Report History list.
// Uses only the data already returned by api.getReportHistory(); nothing is
// recomputed or invented. The PDF libraries are loaded on demand so they do not
// add to the initial bundle.

const INK = [23, 25, 35];
const MUTED = [104, 112, 131];
const ACCENT = [99, 91, 255];
const HEAD_BG = [247, 248, 252];

// The standard PDF fonts cannot draw the rupee sign, so amounts use "Rs.".
const money = (v) => (v === null || v === undefined || Number.isNaN(Number(v))
  ? '—'
  : `Rs. ${new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(v))}`);

const humanize = (s) => {
  if (!s) return '—';
  const t = String(s).replace(/_/g, ' ').toLowerCase();
  return t.charAt(0).toUpperCase() + t.slice(1);
};

const when = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? String(iso)
    : d.toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
};

export async function buildReportHistoryPdf(reports) {
  const [{ jsPDF }, autoTableModule] = await Promise.all([import('jspdf'), import('jspdf-autotable')]);
  // The plugin's export shape differs between module loaders; accept all of them.
  const autoTable = [autoTableModule.autoTable, autoTableModule.default, autoTableModule.default?.default, autoTableModule]
    .find((candidate) => typeof candidate === 'function');
  if (!autoTable) throw new Error('PDF table plugin failed to load');

  const doc = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' });
  const pageW = doc.internal.pageSize.getWidth();
  const margin = 40;

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.setTextColor(...MUTED);
  doc.text('EXPENSEFLOW AI', margin, 40);
  doc.setFontSize(20);
  doc.setTextColor(...INK);
  doc.text('Report History', margin, 64);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.setTextColor(...MUTED);
  doc.text(
    `Exported ${new Date().toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}  |  ${reports.length} report${reports.length === 1 ? '' : 's'} saved in persistent memory`,
    margin,
    82,
  );

  const tableStyles = {
    styles: { font: 'helvetica', fontSize: 8.5, cellPadding: 5, textColor: INK, lineColor: [231, 233, 240], lineWidth: 0.5 },
    headStyles: { fillColor: HEAD_BG, textColor: MUTED, fontStyle: 'bold', fontSize: 8 },
    alternateRowStyles: { fillColor: [252, 252, 254] },
    margin: { left: margin, right: margin },
  };

  autoTable(doc, {
    ...tableStyles,
    startY: 100,
    head: [['Report ID', 'Period', 'Final amount', 'Provisional', 'Expenses', 'Flagged', 'Excluded', 'Review status', 'Delivery', 'Created']],
    body: reports.map((r) => [
      r.report_id,
      r.period_label || '—',
      money(r.confirmed_total),
      money(r.provisional_total),
      r.total_expenses ?? '—',
      r.flagged_count ?? '—',
      r.excluded_count ?? '—',
      humanize(r.review_status || 'pending'),
      humanize(r.delivery_status),
      when(r.created_at),
    ]),
    columnStyles: { 2: { halign: 'right', fontStyle: 'bold' }, 3: { halign: 'right' }, 4: { halign: 'right' }, 5: { halign: 'right' }, 6: { halign: 'right' } },
  });

  // Category breakdown per report (only reports that stored one)
  const catRows = [];
  reports.forEach((r) => {
    Object.entries(r.category_totals || {}).forEach(([cat, val]) => catRows.push([r.report_id, r.period_label || '—', cat, money(val)]));
  });
  if (catRows.length) {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.setTextColor(...INK);
    const y = doc.lastAutoTable.finalY + 28;
    if (y > doc.internal.pageSize.getHeight() - 80) doc.addPage();
    const titleY = y > doc.internal.pageSize.getHeight() - 80 ? 50 : y;
    doc.text('Category breakdown by report', margin, titleY);
    autoTable(doc, {
      ...tableStyles,
      startY: titleY + 10,
      head: [['Report ID', 'Period', 'Category', 'Amount']],
      body: catRows,
      columnStyles: { 3: { halign: 'right' } },
    });
  }

  // Review findings stored with each report
  const findingRows = [];
  reports.forEach((r) => {
    (r.review_findings || []).forEach((f) => findingRows.push([
      r.report_id, humanize(f.finding_type), humanize(f.severity), f.description || '—', humanize(f.resolution_status),
    ]));
  });
  if (findingRows.length) {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.setTextColor(...INK);
    let y = doc.lastAutoTable.finalY + 28;
    if (y > doc.internal.pageSize.getHeight() - 80) { doc.addPage(); y = 50; }
    doc.text('Review findings', margin, y);
    autoTable(doc, {
      ...tableStyles,
      startY: y + 10,
      head: [['Report ID', 'Finding', 'Severity', 'Description', 'Resolution']],
      body: findingRows,
      columnStyles: { 3: { cellWidth: 300 } },
    });
  }

  // Page footer
  const pages = doc.getNumberOfPages();
  for (let i = 1; i <= pages; i += 1) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(...MUTED);
    doc.text(`Page ${i} of ${pages}`, pageW - margin, doc.internal.pageSize.getHeight() - 20, { align: 'right' });
    if (i === 1) {
      doc.setDrawColor(...ACCENT);
      doc.setLineWidth(1.5);
      doc.line(margin, 94, margin + 40, 94);
    }
  }

  return doc;
}

export async function exportReportHistoryPdf(reports) {
  const doc = await buildReportHistoryPdf(reports);
  doc.save(`report-history-${new Date().toISOString().slice(0, 10)}.pdf`);
}
