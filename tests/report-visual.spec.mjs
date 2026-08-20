import { expect, test } from "@playwright/test";
import { execFile as execFileCallback } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { promisify } from "node:util";
import path from "node:path";

const execFile = promisify(execFileCallback);
const REPOSITORY_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPORT_URL = pathToFileURL(process.env.PUNCHLIST_REPORT_HTML || path.join(REPOSITORY_ROOT, "examples", "synthetic", "report.html")).href;
const COMMITTED_PDF = path.join(REPOSITORY_ROOT, "examples", "synthetic", "report.pdf");
const PDF_INSPECTOR = path.join(REPOSITORY_ROOT, "scripts", "inspect_pdf.py");
const SECONDARY_TEXT_SELECTOR = ".eyebrow, .metadata, .finding-id, .count-list, .journey-step, .recommendation-label, .evidence-label, .evidence-meta";

test.use({ browserName: "chromium", viewport: { width: 1224, height: 1584 } });

async function openSyntheticReport(page) {
  await page.goto(REPORT_URL, { waitUntil: "load" });
  await expect(page.getByRole("main", { name: "Experience review report" })).toBeVisible();
}

async function supportedLinks(page) {
  return page.locator("a[href]").evaluateAll((links) => {
    const current = new URL(location.href);
    return links.flatMap((link) => {
      const rawHref = link.getAttribute("href") ?? "";
      let destination;
      try { destination = new URL(rawHref, location.href); } catch { return []; }
      const sameFile = destination.protocol === current.protocol && destination.pathname === current.pathname && destination.search === current.search;
      if (!sameFile) {
        return destination.protocol === "https:" ? [{ href: rawHref, target: destination.href, kind: "external", found: true }] : [{ href: rawHref, target: rawHref, kind: "unsafe", found: false }];
      }
      if (destination.hash.length < 2) return [];
      try {
        const target = decodeURIComponent(destination.hash.slice(1));
        return [{ href: rawHref, target, kind: "fragment", found: Boolean(document.getElementById(target)) }];
      } catch {
        return [{ href: rawHref, target: "", kind: "fragment", found: false }];
      }
    });
  });
}

async function expectSupportedLinksToResolve(page) {
  const links = await supportedLinks(page);
  for (const link of links) {
    expect(link.found, `link ${link.href} must be a safe external URL or resolve to its decoded target`).toBe(true);
  }
  return links;
}

async function clippingState(page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const body = document.body;
    const isVisible = (element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && Number.parseFloat(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
    };
    const pageStates = [...document.querySelectorAll("article.report-page")].map((section) => {
      const sectionRect = section.getBoundingClientRect();
      const descendants = [...section.querySelectorAll("*")].filter(isVisible);
      const outsideArticle = descendants.filter((element) => {
        const rect = element.getBoundingClientRect();
        return rect.left < sectionRect.left - 0.5 || rect.right > sectionRect.right + 0.5 || rect.top < sectionRect.top - 0.5 || rect.bottom > sectionRect.bottom + 0.5;
      }).map((element) => element.tagName.toLowerCase());
      const clippedOverflow = [section, ...descendants].filter((element) => {
        const style = getComputedStyle(element);
        const clipsX = ["hidden", "clip"].includes(style.overflowX) && element.scrollWidth > element.clientWidth + 1;
        const clipsY = ["hidden", "clip"].includes(style.overflowY) && element.scrollHeight > element.clientHeight + 1;
        return clipsX || clipsY;
      }).map((element) => element.tagName.toLowerCase());
      return {
        insideViewport: sectionRect.left >= -0.5 && sectionRect.right <= root.clientWidth + 0.5,
        scrollsHorizontally: section.scrollWidth > section.clientWidth + 1,
        outsideArticle,
        clippedOverflow,
      };
    });
    return { documentOverflowsX: root.scrollWidth > root.clientWidth + 1 || body.scrollWidth > root.clientWidth + 1, pageStates };
  });
}

async function expectNoClipping(page) {
  const layout = await clippingState(page);
  expect(layout.documentOverflowsX).toBe(false);
  expect(layout.pageStates).toHaveLength(6);
  for (const state of layout.pageStates) {
    expect(state.insideViewport).toBe(true);
    expect(state.scrollsHorizontally).toBe(false);
    expect(state.outsideArticle).toEqual([]);
    expect(state.clippedOverflow).toEqual([]);
  }
  return layout;
}

async function secondaryContrasts(page) {
  return page.locator(SECONDARY_TEXT_SELECTOR).evaluateAll((elements) => {
    const parseColor = (value) => {
      const channels = value.match(/\d+(?:\.\d+)?/g)?.map(Number) ?? [];
      return [channels[0] ?? 0, channels[1] ?? 0, channels[2] ?? 0, channels[3] ?? 1];
    };
    const blend = (foreground, background) => {
      const alpha = foreground[3];
      return [foreground[0] * alpha + background[0] * (1 - alpha), foreground[1] * alpha + background[1] * (1 - alpha), foreground[2] * alpha + background[2] * (1 - alpha), 1];
    };
    const effectiveBackground = (element) => {
      let background = [255, 255, 255, 1];
      const chain = [];
      for (let current = element; current; current = current.parentElement) chain.unshift(current);
      for (const current of chain) {
        const color = parseColor(getComputedStyle(current).backgroundColor);
        if (color[3] > 0) background = blend(color, background);
      }
      return background;
    };
    const linear = (channel) => {
      const normalized = channel / 255;
      return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
    };
    const luminance = (color) => 0.2126 * linear(color[0]) + 0.7152 * linear(color[1]) + 0.0722 * linear(color[2]);
    return elements.filter((element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && Number.parseFloat(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
    }).map((element) => {
      const background = effectiveBackground(element);
      const foreground = blend(parseColor(getComputedStyle(element).color), background);
      const ratio = (Math.max(luminance(foreground), luminance(background)) + 0.05) / (Math.min(luminance(foreground), luminance(background)) + 0.05);
      return { role: element.matches(".evidence-label, .evidence-meta") ? "evidence-label" : element.className, ratio };
    });
  });
}

async function expectSecondaryContrast(page) {
  const contrasts = await secondaryContrasts(page);
  expect(contrasts).not.toHaveLength(0);
  for (const contrast of contrasts) expect(contrast.ratio, `${contrast.role} must have 4.5:1 contrast`).toBeGreaterThanOrEqual(4.5);
  return contrasts;
}

async function inspectPdf(pdfPath) {
  const { stdout } = await execFile("python", [PDF_INSPECTOR, "--input", pdfPath], { cwd: REPOSITORY_ROOT });
  return JSON.parse(stdout);
}

function expectPdfParity(generated, committed) {
  expect(generated.page_count).toBe(committed.page_count);
  expect(generated.page_text_inventory_sha256).toEqual(committed.page_text_inventory_sha256);
  expect(generated.page_dimensions).toEqual(committed.page_dimensions);
  expect(generated.page_font_sizes).toEqual(committed.page_font_sizes);
  expect(generated.page_text_colors).toEqual(committed.page_text_colors);
  expect(generated.page_image_count).toEqual(committed.page_image_count);
  expect(generated.link_annotations.map((link) => link.target)).toEqual(committed.link_annotations.map((link) => link.target));
}

test("renders six readable information sections without overflow, empty image semantics, link, or template failures", async ({ page }) => {
  await openSyntheticReport(page);
  await expect(page.locator("article.report-page")).toHaveCount(6);
  await expectNoClipping(page);
  await expect(page.locator("img, [role=img]")).toHaveCount(0);
  await expect(page.locator(".evidence-summary")).toHaveCount(2);
  for (const summary of await page.locator(".evidence-summary").all()) await expect(summary).not.toBeEmpty();
  const links = await expectSupportedLinksToResolve(page);
  expect(links).toEqual([]);
  const unresolvedMarkers = await page.content().then((html) => html.match(/{{[^{}]+}}/g) ?? []);
  expect(unresolvedMarkers).toEqual([]);
  const typography = await page.evaluate(() => ({
    body: Number.parseFloat(getComputedStyle(document.body).fontSize),
    runningMetadata: [...document.querySelectorAll(".metadata, .finding-id, .count-list, .journey-step, .recommendation-label")].map((element) => Number.parseFloat(getComputedStyle(element).fontSize)),
  }));
  expect(typography.body).toBeGreaterThanOrEqual(13.333);
  expect(typography.runningMetadata).not.toHaveLength(0);
  for (const size of typography.runningMetadata) expect(size).toBeGreaterThanOrEqual(10.667);
});

test("fragment resolution helper rejects a controlled broken same-file target", async ({ page }) => {
  await openSyntheticReport(page);
  await page.evaluate(() => {
    const link = document.createElement("a");
    link.href = "report.html#missing%20target";
    link.textContent = "Broken test fragment";
    document.body.append(link);
  });
  await expect(expectSupportedLinksToResolve(page)).rejects.toThrow("link");
});

test("clipping helper rejects controlled vertical hidden overflow", async ({ page }) => {
  await openSyntheticReport(page);
  await page.evaluate(() => {
    const clipped = document.createElement("div");
    clipped.style.cssText = "height: 1px; overflow: hidden;";
    clipped.textContent = "This controlled test content is taller than one pixel.";
    document.querySelector("article.report-page")?.append(clipped);
  });
  await expect(expectNoClipping(page)).rejects.toThrow();
});

test("contrast helper rejects a controlled low-contrast semantic role", async ({ page }) => {
  await openSyntheticReport(page);
  await page.locator(".eyebrow").first().evaluate((element) => { element.style.color = "rgb(250, 250, 250)"; });
  await expect(expectSecondaryContrast(page)).rejects.toThrow("4.5:1");
});

test("maintains every visible secondary role and emits an inspectable print PDF", async ({ page }, testInfo) => {
  await openSyntheticReport(page);
  await expectSecondaryContrast(page);
  const links = await expectSupportedLinksToResolve(page);
  await page.emulateMedia({ media: "print" });
  const pdfPath = testInfo.outputPath("synthetic-report.pdf");
  await page.pdf({ format: "Letter", path: pdfPath, preferCSSPageSize: true, printBackground: true });
  const generated = await inspectPdf(pdfPath);
  const committed = await inspectPdf(COMMITTED_PDF);
  expect(generated.page_count).toBeGreaterThanOrEqual(4);
  expect(generated.page_text_characters).toHaveLength(generated.page_count);
  for (const characters of generated.page_text_characters) expect(characters).toBeGreaterThan(80);
  expect(generated.image_count).toBe(0);
  expect(generated.link_annotations).toHaveLength(links.length);
  expect(generated.link_annotations.map((link) => link.target)).toEqual(links.map((link) => link.target));
  expect(generated.link_annotations).toEqual([]);
  expect(generated.page_layout_sha256).toHaveLength(generated.page_count);
  expect(committed.page_layout_sha256).toHaveLength(committed.page_count);
  expect(() => expectPdfParity(
    { ...generated, page_text_inventory_sha256: ["0".repeat(64), ...generated.page_text_inventory_sha256.slice(1)] },
    generated,
  )).toThrow();
  expectPdfParity(generated, committed);
});

test("stacks report grids into a readable 390px mobile layout", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openSyntheticReport(page);
  await expectNoClipping(page);
  const layout = await page.evaluate(() => {
    const cover = getComputedStyle(document.querySelector(".cover-grid"));
    const journey = getComputedStyle(document.querySelector(".journey-list"));
    const sections = [...document.querySelectorAll("article.report-page")].map((section) => section.getBoundingClientRect().width);
    const bodySize = Number.parseFloat(getComputedStyle(document.body).fontSize);
    return { coverColumns: cover.gridTemplateColumns.split(" ").length, journeyColumns: journey.gridTemplateColumns.split(" ").length, sections, bodySize };
  });
  expect(layout.coverColumns).toBe(1);
  expect(layout.journeyColumns).toBe(1);
  expect(layout.bodySize).toBeGreaterThanOrEqual(14.66);
  for (const width of layout.sections) expect(width).toBeGreaterThan(330);
});
