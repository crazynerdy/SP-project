#!/usr/bin/env node
// render.js — slide-spec JSON -> .pptx via pptxgenjs
// 用法: node render.js <input.json> <output.pptx>
//
// 配置从外部加载：
//   theme.json            — 调色板 + 字体 + 布局尺寸
//   slide_spec_schema.json — layout 单一真相源（与 prompts.py 共享）
// 加新 layout：先在 slide_spec_schema.json 加定义，再在 HANDLERS 注册 handler。

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

// ---------- 加载配置 ----------
const ROOT = path.dirname(__filename);

function loadJSON(filename) {
  const p = path.join(ROOT, filename);
  if (!fs.existsSync(p)) {
    console.error(`配置文件不存在: ${p}`);
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

const THEME = loadJSON("theme.json");
const SCHEMA = loadJSON("slide_spec_schema.json");

// 语义化别名（短名让 handler 代码可读）
const C = THEME.colors;
const F = THEME.font;
const FONT = F.family;
const FONT_NUM = F.familyNumeric;
const FZ = F.sizes;
const L = THEME.layout;
const R = SCHEMA.render_rules;

function main() {
  const [, , inputPath, outputPath] = process.argv;
  if (!inputPath || !outputPath) {
    console.error("用法: node render.js <input.json> <output.pptx>");
    process.exit(1);
  }
  if (!fs.existsSync(inputPath)) {
    console.error("输入文件不存在: " + inputPath);
    process.exit(1);
  }
  const spec = JSON.parse(fs.readFileSync(inputPath, "utf-8"));

  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
  pres.title = (spec.meta && spec.meta.title) || "演示文稿";
  pres.author = (spec.meta && spec.meta.author) || "战略规划分析";
  pres.company = (spec.meta && spec.meta.company) || "";
  pres.subject = (spec.meta && spec.meta.subtitle) || "";

  pres.defineSlideMaster({
    title: "COVER_MASTER",
    background: { color: C.primary },
  });
  pres.defineSlideMaster({
    title: "CONTENT_MASTER",
    background: { color: C.white },
  });

  const slides = spec.slides || [];
  slides.forEach((s, i) => {
    const layout = s.layout || "bullets";

    // 第一道校验：schema 里有没有
    if (!SCHEMA.layouts[layout]) {
      console.warn(`[render] slide ${i + 1}: 未知 layout="${layout}"（schema 未定义）`);
    }
    // 第二道校验：handler 实现了没
    const handler = HANDLERS[layout];
    if (!handler) {
      console.warn(`[render] slide ${i + 1}: layout="${layout}" 未实现，bullets 兜底`);
      HANDLERS.bullets(pres, { ...s, title: s.title || "(未知布局)" });
      return;
    }
    try {
      handler(pres, s);
    } catch (e) {
      console.error(`[render] slide ${i + 1} (${layout}) 出错: ${e.message}，bullets 兜底`);
      HANDLERS.bullets(pres, {
        title: s.title || "（渲染失败）",
        bullets: [`原 layout: ${layout}`, `错误: ${e.message}`],
      });
    }
  });

  pres
    .writeFile({ fileName: outputPath })
    .then((fn) => console.log("OK " + fn))
    .catch((e) => {
      console.error("ERR " + (e.message || e));
      process.exit(2);
    });
}

// ---------- 通用形状 ----------

function addHeader(slide, title) {
  slide.addShape("rect", {
    x: 0, y: 0, w: L.slideW, h: L.headerH,
    fill: { color: C.primary }, line: { type: "none" },
  });
  slide.addShape("rect", {
    x: 0, y: 0, w: L.headerAccentW, h: L.headerH,
    fill: { color: C.accent }, line: { type: "none" },
  });
  slide.addText(title || "", {
    x: L.margin, y: 0.1, w: L.slideW - L.margin * 2, h: L.headerH - 0.2,
    fontSize: FZ.header, color: C.white, bold: true,
    fontFace: FONT, align: "left", valign: "middle",
  });
}

function addLeftAccentBar(slide) {
  slide.addShape("rect", {
    x: 0, y: 0, w: L.accentBarW, h: L.slideH,
    fill: { color: C.accent }, line: { type: "none" },
  });
}

function addSectionLine(slide, x, y) {
  slide.addShape("rect", {
    x, y, w: L.sectionLineW, h: L.sectionLineH,
    fill: { color: C.accent }, line: { type: "none" },
  });
}

function addEmpty(slide, msg) {
  slide.addText(msg, {
    x: L.margin, y: L.slideH / 2 - 0.5, w: L.contentW, h: 1,
    fontSize: FZ.body, color: C.textMute, align: "center", valign: "middle",
  });
}

function coverContentBox() {
  // 封面/结论页正文区（左侧色条右边）
  const x = L.accentBarW + 0.5;
  return { x, w: L.slideW - x - L.margin };
}

function localDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

// ---------- 8 种 layout ----------

function renderTitle(pres, s) {
  const slide = pres.addSlide({ masterName: "COVER_MASTER" });
  addLeftAccentBar(slide);
  const box = coverContentBox();

  slide.addText(s.title || "", {
    x: box.x, y: L.coverTitleY, w: box.w, h: 1.6,
    fontSize: FZ.cover, color: C.white, bold: true,
    fontFace: FONT, align: "left", valign: "top",
  });
  if (s.subtitle) {
    slide.addText(s.subtitle, {
      x: box.x, y: L.coverSubY, w: box.w, h: 0.7,
      fontSize: FZ.coverSub, color: C.textSoft,
      fontFace: FONT, align: "left",
    });
  }
  const company = s.company || pres.company || "";
  slide.addText(company, {
    x: box.x, y: L.footerY, w: 8, h: 0.4,
    fontSize: FZ.tiny, color: C.textMute,
    fontFace: FONT, align: "left",
  });
  slide.addText(localDate(new Date()), {
    x: L.slideW - 2.5 - L.margin, y: L.footerY, w: 2.5, h: 0.4,
    fontSize: FZ.micro, color: C.textMute,
    fontFace: FONT_NUM, align: "right",
  });
}

function renderSection(pres, s) {
  const slide = pres.addSlide({ masterName: "COVER_MASTER" });
  const box = coverContentBox();
  addSectionLine(slide, box.x, 3.4);
  slide.addText(s.title || "", {
    x: box.x, y: 1.8, w: box.w, h: 1.6,
    fontSize: FZ.section, color: C.white, bold: true,
    fontFace: FONT, align: "left", valign: "top",
  });
}

function renderBullets(pres, s) {
  const slide = pres.addSlide({ masterName: "CONTENT_MASTER" });
  addHeader(slide, s.title);
  const bullets = (s.bullets || []).slice(0, R.bullets_per_page || 6).map((b) => ({
    text: b,
    options: { bullet: { code: "25A0" }, color: C.text, paraSpaceAfter: 14 },
  }));
  slide.addText(bullets, {
    x: L.margin, y: L.contentTop + 0.2, w: L.contentW, h: L.slideH - L.contentTop - L.margin - 0.2,
    fontSize: FZ.body, color: C.text,
    fontFace: FONT, valign: "top",
  });
}

function renderTwoCol(pres, s) {
  const slide = pres.addSlide({ masterName: "CONTENT_MASTER" });
  addHeader(slide, s.title);
  const colW = (L.contentW - L.colGap) / 2;
  const leftX = L.margin;
  const rightX = leftX + colW + L.colGap;

  slide.addShape("rect", {
    x: leftX, y: L.contentTop, w: colW, h: L.colHeaderH,
    fill: { color: C.primary }, line: { type: "none" },
  });
  slide.addText(s.left_title || "", {
    x: leftX, y: L.contentTop, w: colW, h: L.colHeaderH,
    fontSize: FZ.label, color: C.white, bold: true,
    fontFace: FONT, align: "center", valign: "middle",
  });
  slide.addShape("rect", {
    x: rightX, y: L.contentTop, w: colW, h: L.colHeaderH,
    fill: { color: C.accent }, line: { type: "none" },
  });
  slide.addText(s.right_title || "", {
    x: rightX, y: L.contentTop, w: colW, h: L.colHeaderH,
    fontSize: FZ.label, color: C.white, bold: true,
    fontFace: FONT, align: "center", valign: "middle",
  });

  const left = (s.left_bullets || []).map((b) => ({
    text: b,
    options: { bullet: { code: "25A0" }, color: C.text, paraSpaceAfter: 10 },
  }));
  slide.addText(left, {
    x: leftX, y: L.colBodyTop, w: colW, h: L.colBodyH,
    fontSize: FZ.small, color: C.text, fontFace: FONT, valign: "top",
  });
  const right = (s.right_bullets || []).map((b) => ({
    text: b,
    options: { bullet: { code: "25A0" }, color: C.text, paraSpaceAfter: 10 },
  }));
  slide.addText(right, {
    x: rightX, y: L.colBodyTop, w: colW, h: L.colBodyH,
    fontSize: FZ.small, color: C.text, fontFace: FONT, valign: "top",
  });
}

function renderTable(pres, s) {
  const slide = pres.addSlide({ masterName: "CONTENT_MASTER" });
  addHeader(slide, s.title);
  const headers = (s.table && s.table.headers ? s.table.headers : []).slice(0, R.table_max_cols);
  const rows = (s.table && s.table.rows ? s.table.rows : []).slice(0, R.table_max_rows);
  if (headers.length === 0) {
    return addEmpty(slide, "（无表头）");
  }
  const headerRow = headers.map((h) => ({
    text: String(h),
    options: {
      bold: true, color: C.white, fill: { color: C.primary },
      fontFace: FONT, align: "center", valign: "middle",
    },
  }));
  const dataRows = rows.map((r, i) =>
    r.slice(0, headers.length).map((c) => ({
      text: String(c),
      options: {
        color: C.text, fill: { color: i % 2 === 0 ? C.white : C.bgLight },
        fontFace: FONT, align: "left", valign: "middle",
      },
    }))
  );
  // 动态行高：行数多时自动收窄，避免超出 contentH 溢出页底
  const _rowH = Math.min(
    L.tableRowH,
    L.contentH / (dataRows.length + 1) // +1 留给表头
  );
  slide.addTable([headerRow, ...dataRows], {
    x: L.margin, y: L.contentTop, w: L.contentW, h: L.contentH,
    colW: headers.map(() => L.contentW / headers.length),
    fontSize: FZ.tiny, rowH: _rowH,
    border: { type: "solid", color: C.border, pt: L.borderPt },
  });
}

function renderChart(pres, s) {
  const slide = pres.addSlide({ masterName: "CONTENT_MASTER" });
  addHeader(slide, s.title);
  const type = s.chart_type || "bar";
  const chartTypeMap = {
    bar: pres.ChartType.bar,
    pie: pres.ChartType.pie,
    line: pres.ChartType.line,
  };
  const labels = (s.chart_data && s.chart_data.labels) || [];
  const series = (s.chart_data && s.chart_data.series) || [];
  const data = series.map((ser) => ({
    name: ser.name || "",
    labels: labels,
    values: ser.values || [],
  }));
  if (data.length === 0 || labels.length === 0) {
    return addEmpty(slide, "（无图表数据）");
  }
  slide.addChart(chartTypeMap[type] || pres.ChartType.bar, data, {
    x: L.margin, y: L.contentTop, w: L.contentW, h: L.contentH,
    showLegend: true, legendPos: "b", legendFontSize: L.chartLegendSize, legendColor: C.text,
    catAxisLabelFontSize: L.chartAxisSize, valAxisLabelFontSize: L.chartAxisSize,
    catAxisLabelColor: C.text, valAxisLabelColor: C.text,
    showTitle: false,
    chartColors: [C.primary, C.accent, C.secondary, C.primaryLight],
  });
}

function renderBigStat(pres, s) {
  const slide = pres.addSlide({ masterName: "CONTENT_MASTER" });
  slide.addText(s.title || "", {
    x: L.margin, y: 0.5, w: L.contentW, h: 0.6,
    fontSize: FZ.label, color: C.text, bold: true,
    fontFace: FONT, align: "left",
  });
  addSectionLine(slide, L.margin, 1.2);
  slide.addText(s.stat || "", {
    x: L.margin, y: 2.0, w: L.contentW, h: 3.4,
    fontSize: FZ.hero, color: C.accent, bold: true,
    fontFace: FONT_NUM, align: "center", valign: "middle",
  });
  slide.addText(s.description || "", {
    x: 2, y: 5.6, w: 9.33, h: 1.0,
    fontSize: FZ.body, color: C.text,
    fontFace: FONT, align: "center", valign: "middle",
  });
}

function renderConclusion(pres, s) {
  const slide = pres.addSlide({ masterName: "COVER_MASTER" });
  addLeftAccentBar(slide);
  const box = coverContentBox();
  slide.addText(s.title || "结论", {
    x: box.x, y: 0.7, w: box.w, h: 1.0,
    fontSize: FZ.conclusion, color: C.white, bold: true,
    fontFace: FONT, align: "left", valign: "top",
  });
  addSectionLine(slide, box.x, 1.85);
  const takeaways = (s.takeaways || []).map((t) => ({
    text: t,
    options: { bullet: { code: "25A0" }, color: C.white, paraSpaceAfter: 14 },
  }));
  slide.addText(takeaways, {
    x: box.x, y: 2.3, w: box.w, h: 4.5,
    fontSize: FZ.body, color: C.white,
    fontFace: FONT, valign: "top",
  });
}

const HANDLERS = {
  title: renderTitle,
  section: renderSection,
  bullets: renderBullets,
  two_col: renderTwoCol,
  table: renderTable,
  chart: renderChart,
  big_stat: renderBigStat,
  conclusion: renderConclusion,
};

main();
