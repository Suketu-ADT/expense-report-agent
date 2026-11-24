const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  ImageRun, Header, Footer, PageNumber, PageBreak,
  VerticalAlign, TabStopType, TabStopPosition,
} = require("docx");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const SCREENSHOTS = path.join(ROOT, "docs", "screenshots", "submission");
const ASSETS = path.join(__dirname, "assets");

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

function sizeOf(buf) {
  if (buf[0] === 0x89 && buf[1] === 0x50) {
    return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
  }
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

function heading1(text, num) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text: num !== undefined ? `${num}. ${text}` : text, bold: true, color: GREEN_DARK, size: 30 })],
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

function imgType(image) {
  return image.data[0] === 0x89 ? "png" : "jpg";
}

function centerImage(image) {
  return new Paragraph({
    children: [new ImageRun({ data: image.data, transformation: { width: image.w, height: image.h }, type: imgType(image) })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 40 },
  });
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

function brandedHeader(subtitle) {
  return new Header({
    children: [
      new Paragraph({
        tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
        border: { bottom: { color: BORDER, space: 4, style: BorderStyle.SINGLE, size: 6 } },
        children: [
          new TextRun({ text: "ExpenseFlow AI", bold: true, color: GREEN_DARK, size: 18 }),
          new TextRun({ text: "\t" + subtitle, color: MUTED, size: 16 }),
        ],
      }),
    ],
  });
}

function brandedFooter(strapline) {
  return new Footer({
    children: [
      new Paragraph({
        tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
        border: { top: { color: BORDER, space: 4, style: BorderStyle.SINGLE, size: 6 } },
        children: [
          new TextRun({ text: strapline, size: 15, color: MUTED }),
          new TextRun({ text: "\tPage ", size: 15, color: MUTED }),
          new TextRun({ children: [PageNumber.CURRENT], size: 15, color: MUTED }),
          new TextRun({ text: " of ", size: 15, color: MUTED }),
          new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 15, color: MUTED }),
        ],
      }),
    ],
  });
}

function blankHeader() { return new Header({ children: [new Paragraph({ children: [] })] }); }
function blankFooter() { return new Footer({ children: [new Paragraph({ children: [] })] }); }

function coverPage({ title, subtitle, kicker, authors, affiliation, date }) {
  return [
    new Paragraph({ spacing: { before: 1400 }, children: [] }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      border: { bottom: { color: GREEN, space: 10, style: BorderStyle.SINGLE, size: 24 } },
      children: [new TextRun({ text: title, bold: true, size: 72, color: GREEN_DARK })],
      spacing: { after: 200 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: subtitle, size: 30, color: INK })],
      spacing: { after: 100 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: kicker, italics: true, size: 26, color: MUTED })],
      spacing: { before: 100, after: 900 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Agentic AI (23CSE4018) — Sem-End Mini Project", size: 22, color: INK, bold: true })],
      spacing: { after: 400 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: authors, size: 22, color: INK })],
      spacing: { after: 80 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: affiliation, size: 20, color: MUTED })],
      spacing: { after: 700 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: date, size: 20, color: MUTED })],
    }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

module.exports = {
  fs, path, Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, ImageRun,
  Header, Footer, PageNumber, PageBreak, VerticalAlign, TabStopType, TabStopPosition,
  ROOT, SCREENSHOTS, ASSETS,
  GREEN, GREEN_DARK, GREEN_LIGHT, INK, MUTED, BORDER, ROW_ALT, WHITE, FONT,
  img, screenshotImg, sizeOf, heading1, heading2, body, bullet, numbered,
  caption, centerImage, imgType, pageBreak, cell, dataTable,
  brandedHeader, brandedFooter, blankHeader, blankFooter, coverPage,
};
