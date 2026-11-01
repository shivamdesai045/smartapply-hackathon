const fs = require("fs");

const file = "src/pages/Checklist.jsx";

let code = fs.readFileSync(file, "utf8");

// Remove all Developer OCR Diagnostics displays
const componentPattern =
  /^[ \t]*<DevDiagnosticViewer\b[\s\S]*?\/>[ \t]*\r?\n/gm;

const matches = code.match(componentPattern) || [];

if (matches.length === 0) {
  throw new Error("Diagnostic component not found. No changes made.");
}

code = code.replace(componentPattern, "");

// Remove entire diagnostic component definition
const start = code.indexOf("function DevDiagnosticViewer(");
const end = code.indexOf("function Checklist() {", start);

if (start === -1 || end === -1) {
  throw new Error("Diagnostic function not found. No changes made.");
}

code = code.slice(0, start) + code.slice(end);

// Remove unused diagnostics API import
code = code.replace(
  /^[ \t]*fetchChecklistDiagnostics,\r?\n/m,
  ""
);

// Back up original file
fs.copyFileSync(file, file + ".before-diagnostics-removal.bak");

// Save cleaned file
fs.writeFileSync(file, code, "utf8");

console.log("Developer OCR Diagnostics removed successfully.");
console.log(`Removed ${matches.length} diagnostic displays.`);
console.log("Original file backed up.");
