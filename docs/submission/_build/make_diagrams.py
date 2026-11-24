"""Draws the Block Diagram and Flowchart as clean PNG images using Pillow
only (no matplotlib/graphviz dependency needed) in the ExpenseFlow AI
brand palette, for embedding in the project report / full technical report
docx files. Run with the backend's own venv, e.g. from `_build/`:

    ../../../backend/.venv/Scripts/python.exe make_diagrams.py

Output lands in _build/assets/block_diagram.png and flowchart.png.
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(OUT_DIR, exist_ok=True)

SCALE = 3  # supersample for crisp text, then downscale
FONT_DIR = r"C:\Windows\Fonts"

GREEN = (37, 92, 69)
GREEN_DARK = (25, 72, 49)
GREEN_LIGHT = (232, 241, 233)
INK = (25, 39, 32)
MUTED = (85, 100, 93)
BORDER = (221, 228, 220)
WHITE = (255, 255, 255)
AMBER = (183, 121, 31)
AMBER_LIGHT = (254, 243, 231)
RED = (196, 61, 75)
RED_LIGHT = (254, 230, 232)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size * SCALE)


F_TITLE = font("arialbd.ttf", 26)
F_BOX = font("arialbd.ttf", 15)
F_BOX_SUB = font("arial.ttf", 12)
F_LABEL = font("ariali.ttf", 12)
F_SMALL = font("arial.ttf", 11)


def new_canvas(w, h):
    img = Image.new("RGB", (w * SCALE, h * SCALE), WHITE)
    return img, ImageDraw.Draw(img)


def save(img, name, out_w):
    h = int(img.height * (out_w / img.width))
    img = img.resize((out_w, h), Image.LANCZOS)
    path = os.path.join(OUT_DIR, name)
    img.save(path, quality=95)
    print("saved", path, img.size)


def rounded_box(draw, cx, cy, w, h, fill, outline, radius=14, width=2):
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius * SCALE, fill=fill, outline=outline, width=width * SCALE)
    return x0, y0, x1, y1


def centered_text(draw, cx, cy, lines, fonts, colors):
    total_h = sum(draw.textbbox((0, 0), t, font=f)[3] for t, f in zip(lines, fonts))
    gap = 4 * SCALE
    total_h += gap * (len(lines) - 1)
    y = cy - total_h / 2
    for t, f, c in zip(lines, fonts, colors):
        bbox = draw.textbbox((0, 0), t, font=f)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw / 2, y - bbox[1]), t, font=f, fill=c)
        y += th + gap


def arrow(draw, p0, p1, color=GREEN_DARK, width=3, dashed=False):
    x0, y0 = p0
    x1, y1 = p1
    w = width * SCALE
    if dashed:
        import math
        length = math.hypot(x1 - x0, y1 - y0)
        n = max(int(length / (10 * SCALE)), 1)
        for i in range(0, n, 2):
            sx = x0 + (x1 - x0) * i / n
            sy = y0 + (y1 - y0) * i / n
            ex = x0 + (x1 - x0) * min(i + 1, n) / n
            ey = y0 + (y1 - y0) * min(i + 1, n) / n
            draw.line([sx, sy, ex, ey], fill=color, width=w)
    else:
        draw.line([x0, y0, x1, y1], fill=color, width=w)
    # arrowhead
    import math
    ang = math.atan2(y1 - y0, x1 - x0)
    head = 9 * SCALE
    for side in (ang + 2.5, ang - 2.5):
        hx = x1 - head * math.cos(side)
        hy = y1 - head * math.sin(side)
        draw.line([x1, y1, hx, hy], fill=color, width=w)


def diamond(draw, cx, cy, w, h, fill, outline, width=2):
    pts = [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)]
    draw.polygon(pts, fill=fill, outline=outline, width=width * SCALE)


def pill_label(draw, cx, cy, text, color=MUTED):
    lines = text.split("\n")
    widths, heights = [], []
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=F_LABEL)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    tw = max(widths)
    line_h = max(heights) + 3 * SCALE
    total_h = line_h * len(lines)
    draw.rectangle([cx - tw / 2 - 7 * SCALE, cy - total_h / 2 - 4 * SCALE,
                    cx + tw / 2 + 7 * SCALE, cy + total_h / 2 + 4 * SCALE], fill=WHITE)
    y = cy - total_h / 2
    for ln, w in zip(lines, widths):
        draw.text((cx - w / 2, y), ln, font=F_LABEL, fill=color)
        y += line_h


# ───────────────────────────────────────────────────────────────────────
# 1. BLOCK DIAGRAM — system architecture, module-level
# ───────────────────────────────────────────────────────────────────────
W, H = 1180, 700
img, d = new_canvas(W, H)

d.text((W * SCALE / 2, 36 * SCALE), "ExpenseFlow AI — System Block Diagram", font=F_TITLE, fill=INK, anchor="mm")

box_w, box_h = 178, 72
cols = 5
col_gap = (W - 80 - cols * box_w) / (cols - 1) + box_w
row_y = [150, 300, 450, 600]

def col_x(i):
    return 80 + box_w / 2 + i * col_gap

row1 = ["Orchestrator\n(Planner)", "Data\nRetrieval", "Filter &\nValidation", "Categorization", "Calculation"]
row2 = ["Anomaly\nDetection", "Period\nComparison", "Currency\nConversion", "Expense\nReview", "Correction"]
row3 = ["Report\nGeneration", "Memory\nPersistence", "Human\nApproval", "Email\nDispatch", ""]

def draw_row(labels, y, fills=None):
    boxes = []
    for i, label in enumerate(labels):
        if not label:
            boxes.append(None)
            continue
        cx = col_x(i)
        fill = (fills[i] if fills else GREEN_LIGHT)
        rounded_box(d, cx * SCALE, y * SCALE, box_w * SCALE, box_h * SCALE, fill=fill, outline=GREEN_DARK)
        lines = label.split("\n")
        centered_text(d, cx * SCALE, y * SCALE, lines, [F_BOX] * len(lines), [INK] * len(lines))
        boxes.append((cx, y))
    return boxes

b1 = draw_row(row1, row_y[0])
b2 = draw_row(row2, row_y[1], fills=[GREEN_LIGHT, GREEN_LIGHT, GREEN_LIGHT, (255, 255, 255), AMBER_LIGHT])
b3 = draw_row(row3, row_y[2], fills=[GREEN_LIGHT, GREEN_LIGHT, AMBER_LIGHT, GREEN_LIGHT, GREEN_LIGHT])

# inter-row flow arrows (right-to-left wrap, like reading order)
for i in range(len(b1) - 1):
    arrow(d, (b1[i][0] * SCALE + box_w / 2 * SCALE, b1[i][1] * SCALE), (b1[i + 1][0] * SCALE - box_w / 2 * SCALE, b1[i + 1][1] * SCALE))
for i in range(len(b2) - 1):
    arrow(d, (b2[i][0] * SCALE + box_w / 2 * SCALE, b2[i][1] * SCALE), (b2[i + 1][0] * SCALE - box_w / 2 * SCALE, b2[i + 1][1] * SCALE))
for i in range(3):
    arrow(d, (b3[i][0] * SCALE + box_w / 2 * SCALE, b3[i][1] * SCALE), (b3[i + 1][0] * SCALE - box_w / 2 * SCALE, b3[i + 1][1] * SCALE))

MARGIN_X = 36


def elbow_wrap(draw, from_box, to_box, gap_y, color=GREEN_DARK):
    """Routes an elbow connector through the left margin, so it never
    crosses over any box in between (from the end of one row down and
    around to the start of the next)."""
    fx, fy = from_box
    tx, ty = to_box
    p0 = (fx * SCALE, (fy + box_h / 2) * SCALE)
    p1 = (fx * SCALE, gap_y * SCALE)
    p2 = (MARGIN_X * SCALE, gap_y * SCALE)
    p3 = (MARGIN_X * SCALE, ty * SCALE)
    draw.line([p0, p1], fill=color, width=3 * SCALE)
    draw.line([p1, p2], fill=color, width=3 * SCALE)
    draw.line([p2, p3], fill=color, width=3 * SCALE)
    arrow(draw, p3, ((tx - box_w / 2) * SCALE, ty * SCALE), color=color)


elbow_wrap(d, b1[-1], b2[0], row_y[0] + box_h / 2 + 28)
elbow_wrap(d, b2[-1], b3[0], row_y[1] + box_h / 2 + 28)

# Correction -> Expense Review retry loop (curved-ish via two segments, drawn above row2)
rx0, ry0 = b2[4][0] * SCALE, b2[4][1] * SCALE - box_h / 2 * SCALE
rx1, ry1 = b2[3][0] * SCALE, b2[3][1] * SCALE - box_h / 2 * SCALE
loop_y = ry0 - 34 * SCALE
d.line([rx0, ry0, rx0, loop_y], fill=AMBER, width=3 * SCALE)
d.line([rx0, loop_y, rx1, loop_y], fill=AMBER, width=3 * SCALE)
arrow(d, (rx1, loop_y), (rx1, ry1), color=AMBER)
pill_label(d, (rx0 + rx1) / 2, loop_y, "retry (max 3)", color=AMBER)

# shared blackboard state note
bb_y = 650
d.rounded_rectangle([80 * SCALE, bb_y * SCALE, (W - 80) * SCALE, (bb_y + 46) * SCALE],
                     radius=10 * SCALE, outline=MUTED, width=2 * SCALE)
d.text((W * SCALE / 2, (bb_y + 23) * SCALE),
       "All agents read from and write to one shared Pydantic blackboard — ExpenseReportState",
       font=F_BOX_SUB, fill=MUTED, anchor="mm")

save(img, "block_diagram.png", 1600)

# ───────────────────────────────────────────────────────────────────────
# 2. FLOWCHART — review / correction / approval decision logic
# ───────────────────────────────────────────────────────────────────────
W2, H2 = 1300, 1260
img2, d2 = new_canvas(W2, H2)
d2.text((W2 * SCALE / 2, 36 * SCALE), "ExpenseFlow AI — Review & Approval Flowchart", font=F_TITLE, fill=INK, anchor="mm")

cx = 430
y = 110


def oval(draw, cx, cy, w, h, fill, outline, text, tcolor=WHITE):
    draw.ellipse([(cx - w / 2) * SCALE, (cy - h / 2) * SCALE, (cx + w / 2) * SCALE, (cy + h / 2) * SCALE],
                 fill=fill, outline=outline, width=2 * SCALE)
    centered_text(draw, cx * SCALE, cy * SCALE, [text], [F_BOX], [tcolor])


def box(draw, cx, cy, w, h, text, fill=GREEN_LIGHT, outline=GREEN_DARK, tcolor=INK):
    rounded_box(draw, cx * SCALE, cy * SCALE, w * SCALE, h * SCALE, fill=fill, outline=outline)
    lines = text.split("\n")
    centered_text(draw, cx * SCALE, cy * SCALE, lines, [F_BOX] * len(lines), [tcolor] * len(lines))


def dia(draw, cx, cy, w, h, text, fill=AMBER_LIGHT, outline=AMBER):
    diamond(draw, cx * SCALE, cy * SCALE, w * SCALE, h * SCALE, fill=fill, outline=outline)
    lines = text.split("\n")
    centered_text(draw, cx * SCALE, cy * SCALE, lines, [F_BOX_SUB] * len(lines), [INK] * len(lines))


def varrow(draw, x, y0, y1, color=GREEN_DARK, label=None):
    arrow(draw, (x * SCALE, y0 * SCALE), (x * SCALE, y1 * SCALE), color=color)
    if label:
        pill_label(draw, x * SCALE, (y0 + y1) / 2 * SCALE, label, color=color if color != GREEN_DARK else MUTED)


oval(d2, cx, y, 220, 56, GREEN, GREEN_DARK, "Calculation complete")
y2 = y + 110
varrow(d2, cx, y + 28, y2 - 40)
box(d2, cx, y2, 280, 64, "Expense Review Agent\nrecomputes all totals")

y3 = y2 + 150
varrow(d2, cx, y2 + 32, y3 - 70)
dia(d2, cx, y3, 260, 130, "Critical\nfinding?")

# No -> straight down to Report Generation
y4 = y3 + 190
varrow(d2, cx, y3 + 65, y4 - 32)
pill_label(d2, cx * SCALE, (y3 + 95) * SCALE, "no", color=MUTED)
box(d2, cx, y4, 260, 56, "Report Generation (PDF)", fill=GREEN_LIGHT)

# Yes -> right to Correction Agent
right_x = cx + 380
arrow(d2, ((cx + 130) * SCALE, y3 * SCALE), ((right_x - 115) * SCALE, y3 * SCALE))
pill_label(d2, (cx + 255) * SCALE, (y3 - 20) * SCALE, "yes", color=MUTED)
box(d2, right_x, y3, 230, 64, "Correction Agent\napplies deterministic fix")

y5 = y3 + 180
varrow(d2, right_x, y3 + 32, y5 - 70)
dia(d2, right_x, y5, 250, 140, "Retries < 3 and\nstill failing?")

# "retry (re-review)" -> loop back up into the right vertex of the
# Critical-finding? diamond (never crossing the diamond itself)
loop_x = cx + 170
d2.line([(right_x - 125) * SCALE, y5 * SCALE, loop_x * SCALE, y5 * SCALE], fill=GREEN_DARK, width=3 * SCALE)
d2.line([loop_x * SCALE, y5 * SCALE, loop_x * SCALE, y3 * SCALE], fill=GREEN_DARK, width=3 * SCALE)
arrow(d2, (loop_x * SCALE, y3 * SCALE), ((cx + 132) * SCALE, y3 * SCALE))
pill_label(d2, ((loop_x + right_x - 125) / 2) * SCALE, (y5 - 24) * SCALE, "retry (re-review)", color=MUTED)

# retries exhausted -> escalate, below the retry diamond
y6 = y5 + 170
varrow(d2, right_x, y5 + 70, y6 - 42, color=RED, label=None)
pill_label(d2, (right_x + 90) * SCALE, (y5 + 110) * SCALE, "retries exhausted", color=MUTED)
box(d2, right_x, y6, 260, 72, "Escalate for human review\n(needs_human_review = True)", fill=RED_LIGHT, outline=RED)

# escalate path rejoins the main flow at Report Generation
d2.line([right_x * SCALE, (y6 + 36) * SCALE, right_x * SCALE, y4 * SCALE], fill=RED, width=3 * SCALE)
arrow(d2, (right_x * SCALE, y4 * SCALE), ((cx + 130) * SCALE, y4 * SCALE), color=RED)

y7 = y4 + 140
varrow(d2, cx, y4 + 28, y7 - 32)
box(d2, cx, y7, 260, 56, "Memory Persistence (SQLite)")

y8 = y7 + 170
varrow(d2, cx, y7 + 28, y8 - 70)
dia(d2, cx, y8, 250, 140, "Human\napproves?")

y9 = y8 + 190
varrow(d2, cx, y8 + 70, y9 - 28)
pill_label(d2, cx * SCALE, (y8 + 100) * SCALE, "approve", color=MUTED)
oval(d2, cx, y9, 220, 56, GREEN, GREEN_DARK, "Email Dispatch")

reject_x = cx - 330
arrow(d2, ((cx - 125) * SCALE, y8 * SCALE), ((reject_x + 100) * SCALE, y8 * SCALE))
pill_label(d2, (cx - 230) * SCALE, (y8 - 24) * SCALE, "reject / held", color=MUTED)
oval(d2, reject_x, y8, 210, 64, (255, 255, 255), MUTED, "Email not sent", tcolor=INK)

save(img2, "flowchart.png", 1400)
