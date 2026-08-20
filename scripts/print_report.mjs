import { chromium } from "playwright";
import { execFile as execFileCallback } from "node:child_process";
import { access, lstat, mkdir, mkdtemp, realpath, rename, rm, stat } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { promisify } from "node:util";

class SafeError extends Error {}

const execFile = promisify(execFileCallback);
const REPOSITORY_ROOT = await realpath(path.resolve(path.dirname(fileURLToPath(import.meta.url)), ".."));
const SYNTHETIC_ROOT = await realpath(path.join(REPOSITORY_ROOT, "examples", "synthetic"));
const CANONICAL_INPUT = await realpath(path.join(SYNTHETIC_ROOT, "report.html"));
const RENDERER = path.join(REPOSITORY_ROOT, "scripts", "render_report.py");
const TEMP_ROOT = path.join(REPOSITORY_ROOT, "tmp");

function isWithin(parent, candidate) {
  const relative = path.relative(parent, candidate);
  return relative !== "" && !relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative);
}

function parseArguments(argumentsList) {
  const allowed = new Set(["--input", "--audit", "--report", "--theme", "--output"]);
  const values = new Map();
  if (argumentsList.length % 2 !== 0) throw new SafeError("arguments: invalid command");
  for (let index = 0; index < argumentsList.length; index += 2) {
    const option = argumentsList[index];
    const value = argumentsList[index + 1];
    if (!allowed.has(option) || !value || values.has(option)) throw new SafeError("arguments: invalid command");
    values.set(option, value);
  }
  const keys = new Set(values.keys());
  const canonicalMode = keys.size === 2 && keys.has("--input") && keys.has("--output");
  const dataMode = (keys.size === 3 || keys.size === 4)
    && keys.has("--audit") && keys.has("--report") && keys.has("--output")
    && (keys.size === 3 || keys.has("--theme"));
  if (!canonicalMode && !dataMode) throw new SafeError("arguments: invalid command");
  if (canonicalMode) return { mode: "canonical", input: values.get("--input"), output: values.get("--output") };
  return {
    mode: "data",
    audit: values.get("--audit"),
    report: values.get("--report"),
    theme: values.get("--theme"),
    output: values.get("--output"),
  };
}

async function resolveInput(input) {
  const supplied = path.resolve(input);
  if (supplied !== CANONICAL_INPUT) throw new SafeError("input: must be canonical synthetic HTML");
  let candidate;
  try {
    candidate = await realpath(path.resolve(input));
    await access(candidate);
  } catch {
    throw new SafeError("input: could not read synthetic HTML");
  }
  if (candidate !== CANONICAL_INPUT) throw new SafeError("input: must be canonical synthetic HTML");
  try {
    if ((await lstat(supplied)).isSymbolicLink()) throw new SafeError("input: aliases are not allowed");
  } catch (error) {
    if (error instanceof SafeError) throw error;
    throw new SafeError("input: could not read synthetic HTML");
  }
  return candidate;
}

async function resolveOutput(output) {
  if (path.extname(output).toLowerCase() !== ".pdf") throw new SafeError("output: must end in .pdf");
  const candidate = path.resolve(output);
  let canonicalParent;
  try {
    canonicalParent = await realpath(path.dirname(candidate));
  } catch {
    throw new SafeError("output: parent directory is unavailable");
  }
  const canonicalCandidate = path.join(canonicalParent, path.basename(candidate));
  if (!isWithin(REPOSITORY_ROOT, canonicalCandidate)) throw new SafeError("output: must stay inside repository");
  try {
    if ((await lstat(canonicalCandidate)).isSymbolicLink()) throw new SafeError("output: existing symlink is not allowed");
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
  return canonicalCandidate;
}

async function resolveDataInput(input) {
  const supplied = path.resolve(input);
  try {
    const details = await lstat(supplied);
    if (details.isSymbolicLink() || !details.isFile() || path.extname(supplied).toLowerCase() !== ".json") {
      throw new SafeError("data: could not read report inputs");
    }
    return await realpath(supplied);
  } catch (error) {
    if (error instanceof SafeError) throw error;
    throw new SafeError("data: could not read report inputs");
  }
}

async function assertDistinctInputs(inputPaths) {
  try {
    const details = await Promise.all(inputPaths.map(async (inputPath) => ({
      inputPath,
      resolved: await realpath(inputPath),
      stats: await stat(inputPath),
    })));
    for (let first = 0; first < details.length; first += 1) {
      for (let second = first + 1; second < details.length; second += 1) {
        if (details[first].resolved === details[second].resolved
          || (details[first].stats.dev === details[second].stats.dev && details[first].stats.ino === details[second].stats.ino)) {
          throw new SafeError("data: report inputs must not alias");
        }
      }
    }
  } catch (error) {
    if (error instanceof SafeError) throw error;
    throw new SafeError("data: could not read report inputs");
  }
}

async function assertNotInputAlias(inputPath, outputPath) {
  try {
    const [resolvedOutput, inputStat, outputStat] = await Promise.all([realpath(outputPath), stat(inputPath), stat(outputPath)]);
    if (resolvedOutput === inputPath || (inputStat.dev === outputStat.dev && inputStat.ino === outputStat.ino)) throw new SafeError("output: must not alias input");
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
}

async function renderValidatedData({ audit, report, theme }) {
  await mkdir(TEMP_ROOT, { recursive: true });
  const canonicalTempRoot = await realpath(TEMP_ROOT);
  if (!isWithin(REPOSITORY_ROOT, canonicalTempRoot)) throw new SafeError("data: could not render validated report");
  const temporaryDirectory = await mkdtemp(path.join(canonicalTempRoot, "punchlist-pdf-"));
  const temporaryHtml = path.join(temporaryDirectory, "report.html");
  const argumentsList = [RENDERER, "--audit", audit, "--report", report];
  if (theme) argumentsList.push("--theme", theme);
  argumentsList.push("--output", temporaryHtml);
  try {
    try {
      await execFile("python", argumentsList, { cwd: REPOSITORY_ROOT, windowsHide: true });
    } catch {
      throw new SafeError("data: could not render validated report");
    }
    try {
      const [resolvedHtml, details] = await Promise.all([realpath(temporaryHtml), lstat(temporaryHtml)]);
      if (resolvedHtml !== temporaryHtml || details.isSymbolicLink() || !details.isFile()) {
        throw new SafeError("data: could not render validated report");
      }
    } catch (error) {
      if (error instanceof SafeError) throw error;
      throw new SafeError("data: could not render validated report");
    }
    return { temporaryDirectory, temporaryHtml };
  } catch (error) {
    await rm(temporaryDirectory, { recursive: true, force: true }).catch(() => undefined);
    throw error;
  }
}

async function exportPdf(inputPath, outputPath) {
  const temporaryPath = path.join(path.dirname(outputPath), `.${path.basename(outputPath)}.${randomUUID()}.tmp`);
  let browser;
  try {
    try {
      browser = await chromium.launch({ headless: true });
      const context = await browser.newContext();
      const page = await context.newPage();
      const inputUrl = pathToFileURL(inputPath).href;
      await page.route("**/*", async (route) => {
        const request = route.request();
        if (request.isNavigationRequest() && request.resourceType() === "document" && request.url() === inputUrl) {
          await route.continue();
        } else {
          await route.abort("blockedbyclient");
        }
      });
      await page.goto(inputUrl, { waitUntil: "load" });
      await page.evaluate(async () => {
        if (document.fonts) await document.fonts.ready;
      });
      await page.emulateMedia({ media: "print" });
      await page.pdf({ format: "Letter", path: temporaryPath, preferCSSPageSize: true, printBackground: true });
    } catch {
      throw new SafeError("pdf: could not export report");
    } finally {
      await browser?.close();
    }

    try {
      const recheckedOutput = await resolveOutput(outputPath);
      if (recheckedOutput !== outputPath) throw new SafeError("output: must stay inside repository");
      await assertNotInputAlias(inputPath, outputPath);
      await rename(temporaryPath, outputPath);
    } catch (error) {
      if (error instanceof SafeError) throw error;
      throw new SafeError("pdf: could not export report");
    }
  } finally {
    await rm(temporaryPath, { force: true }).catch(() => undefined);
  }
}

async function main() {
  const options = parseArguments(process.argv.slice(2));
  const outputPath = await resolveOutput(options.output);
  if (options.mode === "canonical") {
    const inputPath = await resolveInput(options.input);
    await assertNotInputAlias(inputPath, outputPath);
    await exportPdf(inputPath, outputPath);
    return;
  }

  const auditPath = await resolveDataInput(options.audit);
  const reportPath = await resolveDataInput(options.report);
  const themePath = options.theme ? await resolveDataInput(options.theme) : undefined;
  const inputPaths = [auditPath, reportPath, ...(themePath ? [themePath] : [])];
  await assertDistinctInputs(inputPaths);
  for (const inputPath of inputPaths) await assertNotInputAlias(inputPath, outputPath);
  const rendered = await renderValidatedData({ audit: auditPath, report: reportPath, theme: themePath });
  try {
    await exportPdf(rendered.temporaryHtml, outputPath);
  } finally {
    await rm(rendered.temporaryDirectory, { recursive: true, force: true }).catch(() => undefined);
  }
}

main().catch((error) => {
  console.error(error instanceof SafeError ? error.message : "pdf: could not export report");
  process.exitCode = 1;
});
