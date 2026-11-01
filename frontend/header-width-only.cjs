const fs = require("fs");

const file = "src/components/HeroSearch.jsx";
const backup = file + ".before-layout-fix.bak";

let code = fs.readFileSync(file, "utf8");

// Restore original single-row layout if changed
if (code.includes("hero-sticky-layout")) {
  if (!fs.existsSync(backup)) {
    throw new Error("Original layout backup not found.");
  }
  code = fs.readFileSync(backup, "utf8");
}

// Remove search width restriction
const searchPattern = /flex-1\s+(?:(?:max-w-\S+|min-w-0|w-full)\s+)*flex items-center border border-gray-300 rounded-full/;

if (!searchPattern.test(code)) {
  throw new Error("Search bar class not found.");
}

code = code.replace(
  searchPattern,
  "flex-1 min-w-0 w-full max-w-none flex items-center border border-gray-300 rounded-full"
);

// Reduce unnecessary spacing, keeping same layout
code = code.replace(
  'className="flex items-center gap-5 px-6 py-4"',
  'className="flex items-center gap-2 px-4 py-4"'
);

code = code.replace(
  'className="flex items-center gap-4 ml-auto shrink-0"',
  'className="flex items-center gap-2 ml-auto shrink-0"'
);

fs.copyFileSync(file, file + ".before-width-only.bak");
fs.writeFileSync(file, code, "utf8");

console.log("Single-row layout preserved. Search width expanded.");
