#!/usr/bin/env node
/**
 * Validate docs/tasks DONE tickets.
 * - DONE tickets must have Report: path
 * - Report path must exist
 * - DoD section must be present
 */
const fs = require("fs");
const path = require("path");

const root = process.cwd();
const tasksDir = path.join(root, "docs", "tasks");

function read(filePath) {
  return fs.readFileSync(filePath, "utf8");
}

function getLine(content, key) {
  const m = content.match(new RegExp(`^${key}:\\s*(.+)$`, "im"));
  return m ? m[1].trim() : "";
}

function main() {
  if (!fs.existsSync(tasksDir)) {
    console.error(`[check-task-reports] tasks dir not found: ${tasksDir}`);
    process.exit(1);
  }

  const files = fs.readdirSync(tasksDir).filter((f) => /^TASK_.*\.md$/i.test(f));
  const errors = [];
  let checked = 0;

  for (const file of files) {
    const fullPath = path.join(tasksDir, file);
    const content = read(fullPath);
    const status = getLine(content, "Status").toUpperCase();
    if (status !== "DONE") continue;
    checked += 1;

    const report = getLine(content, "Report");
    if (!report) {
      errors.push(`${file}: Report がありません`);
      continue;
    }

    const reportPath = path.resolve(root, report.replace(/`/g, ""));
    if (!fs.existsSync(reportPath)) {
      errors.push(`${file}: Report 参照先が存在しません -> ${report}`);
    }

    if (!/^##\s*DoD\s*$/im.test(content)) {
      errors.push(`${file}: DoD セクションがありません`);
    }
  }

  console.log(`[check-task-reports] checked DONE tasks: ${checked}`);
  if (errors.length > 0) {
    console.error("[check-task-reports] errors:");
    for (const e of errors) console.error(`- ${e}`);
    process.exit(2);
  }

  console.log("[check-task-reports] OK");
}

main();
