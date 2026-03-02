#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const childProcess = require("child_process");

const root = process.cwd();
const validator = path.join(root, ".shared-workflows", "scripts", "report-validator.js");
const config = path.join(root, ".shared-workflows", "REPORT_CONFIG.yml");
const tasksDir = path.join(root, "docs", "tasks");
const manifestPath = path.join(root, "config", "operational_report_targets.json");

function runValidation(targetPath, extraArgs = []) {
  const args = ["node", validator, targetPath, config, root, ...extraArgs];
  const result = childProcess.spawnSync(args[0], args.slice(1), {
    cwd: root,
    encoding: "utf8",
    stdio: "pipe",
  });

  process.stdout.write(result.stdout || "");
  process.stderr.write(result.stderr || "");

  if (result.status !== 0) {
    throw new Error(`validation failed: ${targetPath}`);
  }
}

function parseKeyLine(content, key) {
  const pattern = new RegExp(`^${key}:\\s*(.+)$`, "im");
  const match = content.match(pattern);
  return match ? match[1].trim() : "";
}

function readManifestTargets() {
  if (!fs.existsSync(manifestPath)) {
    return null;
  }

  const raw = fs.readFileSync(manifestPath, "utf8");
  const manifest = JSON.parse(raw);
  if (!Array.isArray(manifest.targets)) {
    throw new Error("operational report manifest must contain a targets array");
  }

  return manifest.targets.map((target) => ({
    path: path.resolve(root, target.path),
    args: Array.isArray(target.args) ? target.args : [],
  }));
}

function collectTaskReportTargets() {
  if (!fs.existsSync(tasksDir)) {
    return [];
  }

  const allowedStatuses = new Set(["DONE", "IN_PROGRESS", "BLOCKED"]);
  const reportPaths = new Set();
  const taskFiles = fs.readdirSync(tasksDir).filter((file) => /^TASK_.*\.md$/i.test(file));

  for (const taskFile of taskFiles) {
    const taskPath = path.join(tasksDir, taskFile);
    const content = fs.readFileSync(taskPath, "utf8");
    const status = parseKeyLine(content, "Status").toUpperCase();
    const report = parseKeyLine(content, "Report").replace(/`/g, "");
    if (!allowedStatuses.has(status) || !report) {
      continue;
    }

    const reportPath = path.resolve(root, report);
    if (path.extname(reportPath).toLowerCase() === ".md") {
      reportPaths.add(reportPath);
    }
  }

  return Array.from(reportPaths).sort();
}

function main() {
  if (!fs.existsSync(validator) || !fs.existsSync(config)) {
    console.error("[validate-operational-reports] validator or config not found");
    process.exit(1);
  }

  const manifestTargets = readManifestTargets();
  const targets = manifestTargets || [
    { path: path.join(root, "docs", "HANDOVER.md"), args: ["--profile", "handover"] },
    ...collectTaskReportTargets().map((reportPath) => ({ path: reportPath, args: [] })),
  ];

  let checked = 0;
  for (const target of targets) {
    runValidation(target.path, target.args);
    checked += 1;
  }

  console.log(`[validate-operational-reports] VALIDATION_OK (${checked} files)`);
}

main();
