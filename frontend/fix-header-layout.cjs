const fs = require("fs");

const file = "src/components/HeroSearch.jsx";
const cssFile = "src/components/HeroSearchHeader.css";

if (!fs.existsSync(file)) {
  throw new Error("HeroSearch.jsx not found.");
}

let code = fs.readFileSync(file, "utf8");

if (
  !code.includes("function HeroSearch()") ||
  (!code.includes("hero-sticky-actions") &&
   !code.includes('className="flex items-center gap-4 ml-auto shrink-0"'))
) {
  throw new Error("Header structure differs. No changes saved.");
}

// Repair Hindi and Marathi using Unicode-safe labels
const languages = String.raw`const languages = [
  { code: "en", label: "English" },
  { code: "hi", label: "\u0939\u093f\u0902\u0926\u0940" },
  { code: "mr", label: "\u092e\u0930\u093e\u0920\u0940" },
];`;

if (!/const languages = \[[\s\S]*?\n\];/.test(code)) {
  throw new Error("Language list not found.");
}

code = code.replace(
  /const languages = \[[\s\S]*?\n\];/,
  languages
);

// Use proper icons instead of corrupted emoji characters
if (!code.includes('from "lucide-react"')) {
  code =
    'import { Search, CalendarDays, Moon, Sun, Folder, LogOut, ChevronDown } from "lucide-react";\n' +
    code;
}

code = code.replace(
  /<span className="text-gray-400 mr-3 text-lg">[^<]*<\/span>/g,
  '<Search size={20} className="mr-3 shrink-0 text-gray-400" aria-hidden="true" />'
);

code = code.replace(
  /<span className="text-gray-400 pl-4 text-lg">[^<]*<\/span>/g,
  '<Search size={20} className="ml-4 shrink-0 text-gray-400" aria-hidden="true" />'
);

code = code.replace(
  /^.*\{dateStr\}.*\{timeStr\}.*$/m,
  '      <CalendarDays size={16} className="inline-block align-middle mr-1" aria-hidden="true" /> {dateStr} &nbsp; | &nbsp; {timeStr}'
);

code = code.replace(
  /\{theme === "light" \?[^\n}]*\}/g,
  '{theme === "light" ? <Moon size={18} /> : <Sun size={18} />}'
);

code = code.replace(
  /<span>[^<]*<\/span>(\s*<span>My Documents<\/span>)/g,
  '<Folder size={17} aria-hidden="true" />$1'
);

code = code.replace(
  /<span>[^<]*<\/span>(\s*<span>Logout<\/span>)/g,
  '<LogOut size={17} aria-hidden="true" />$1'
);

code = code.replace(
  /<span className="text-xs">[^<]*<\/span>/g,
  '<ChevronDown size={14} aria-hidden="true" />'
);

// Create a two-row compact header
if (!code.includes("hero-sticky-layout")) {
  const old = 'className="flex items-center gap-5 px-6 py-4"';

  if (!code.includes(old)) {
    throw new Error("Compact header layout not found.");
  }

  code = code.replace(
    old,
    'className="hero-sticky-layout flex items-center gap-5 px-6 py-4"'
  );
}

// Give logo its own grid position
const rowStart = code.indexOf("hero-sticky-layout");
const tail = code.slice(rowStart);

if (!tail.includes("hero-sticky-logo")) {
  if (!tail.includes('<Link to="/" className="shrink-0">')) {
    throw new Error("Compact header logo not found.");
  }

  code = code.slice(0, rowStart) + tail.replace(
    '<Link to="/" className="shrink-0">',
    '<Link to="/" className="hero-sticky-logo shrink-0">'
  );
}

// Expand search to the full available width
if (!code.includes("hero-sticky-search")) {
  const searchClass =
    /className="flex-1 (?:max-w-[^\s"]+\s+)?(?:min-w-0\s+)?flex items-center border border-gray-300 rounded-full overflow-hidden bg-gray-50 focus-within:border-brand-500 focus-within:bg-white transition relative"/;

  if (!searchClass.test(code)) {
    throw new Error("Compact search wrapper not found.");
  }

  code = code.replace(
    searchClass,
    'className="hero-sticky-search flex min-w-0 w-full items-center border border-gray-300 rounded-full overflow-hidden bg-gray-50 focus-within:border-brand-500 focus-within:bg-white transition relative"'
  );
}

// Move user controls into first row
if (!code.includes("hero-sticky-actions")) {
  code = code.replace(
    'className="flex items-center gap-4 ml-auto shrink-0"',
    'className="hero-sticky-actions flex items-center gap-4 ml-auto shrink-0"'
  );
}

if (!code.includes('import "./HeroSearchHeader.css";')) {
  code = 'import "./HeroSearchHeader.css";\n' + code;
}

// Styling for the new header
const css = `
.hero-sticky-layout {
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas:
    "logo actions"
    "search search";
  gap: 12px 24px;
  padding: 12px clamp(16px, 3vw, 48px);
  background: #ffffff;
}

.hero-sticky-logo {
  grid-area: logo;
  justify-self: start;
}

.hero-sticky-search {
  grid-area: search;
  width: 100%;
  max-width: none !important;
  min-width: 0;
  min-height: 48px;
}

.hero-sticky-search input {
  min-width: 0;
}

.hero-sticky-actions {
  grid-area: actions;
  justify-self: end;
  margin-left: 0;
}

.dark .hero-sticky-layout {
  background: #111827;
}

.dark .hero-sticky-search {
  background: #1f2937;
  border-color: #475569;
}

.dark .hero-sticky-search input {
  color: #ffffff;
}

@media (max-width: 720px) {
  .hero-sticky-layout {
    gap: 8px;
    padding: 10px 12px;
  }

  .hero-sticky-logo img {
    height: 32px;
  }

  .hero-sticky-actions {
    gap: 8px;
  }

  .hero-sticky-actions > :first-child {
    display: none;
  }

  .hero-sticky-search select {
    max-width: 36%;
    padding-inline: 8px;
  }

  .hero-sticky-search button {
    padding-inline: 12px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-sticky-layout,
  .hero-sticky-search {
    transition: none !important;
  }
}
`;

// Backup existing file before changes
fs.copyFileSync(
  file,
  file + ".before-layout-fix.bak"
);

fs.writeFileSync(file, code, "utf8");
fs.writeFileSync(cssFile, css, "utf8");

console.log("Header width and icons updated.");
console.log("Backup created.");
