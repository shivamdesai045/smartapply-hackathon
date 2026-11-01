const fs = require("fs");
const file = "src/components/HeroSearch.jsx";

if (!fs.existsSync(file)) {
  throw new Error("HeroSearch.jsx not found.");
}

let code = fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");

if (code.includes("const [headerProgress, setHeaderProgress]")) {
  console.log("Scroll-controlled header is already installed.");
  process.exit(0);
}

// Add useRef
code = code.replace(
  /import \{\s*useState\s*,\s*useEffect(?:\s*,\s*useRef)?\s*\} from ["']react["'];/,
  'import { useState, useEffect, useRef } from "react";'
);

// Replace old scrolling state
if (!code.includes("const heroSearchRef = useRef(null);")) {
  code = code.replace(
    "const [scrolled, setScrolled] = useState(false);",
    "const heroSearchRef = useRef(null);\n  const [headerProgress, setHeaderProgress] = useState(0);"
  );
} else {
  code = code.replace(
    "const [scrolled, setScrolled] = useState(false);",
    "const [headerProgress, setHeaderProgress] = useState(0);"
  );
}

if (!code.includes("const [headerProgress, setHeaderProgress]")) {
  throw new Error("Scroll state not found. No changes saved.");
}

// Track main hero search bar
if (!code.includes("ref={heroSearchRef}")) {
  code = code.replace(
    '<div className="w-full max-w-3xl">',
    '<div ref={heroSearchRef} className="w-full max-w-3xl">'
  );
}

if (!code.includes("ref={heroSearchRef}")) {
  throw new Error("Hero search bar not found. No changes saved.");
}

// Replace old scroll effect
const scrollIndex = code.indexOf("const onScroll = () =>");
const effectStart = code.lastIndexOf("  useEffect(() => {", scrollIndex);
const endMarker = "  }, []);";
const effectEnd = code.indexOf(endMarker, scrollIndex);

if (scrollIndex < 0 || effectStart < 0 || effectEnd < 0) {
  throw new Error("Scroll handler not found. No changes saved.");
}

const newEffect = `  useEffect(() => {
    const searchBar = heroSearchRef.current;
    if (!searchBar) return;

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    );

    let frameId = null;

    const updateHeader = () => {
      frameId = null;

      const searchBottom =
        searchBar.getBoundingClientRect().bottom;

      const revealDistance = Math.min(
        window.innerHeight * 0.55,
        420
      );

      const progress = Math.max(
        0,
        Math.min(
          1,
          (revealDistance - searchBottom) / revealDistance
        )
      );

      setHeaderProgress(
        reduceMotion.matches
          ? (searchBottom <= 0 ? 1 : 0)
          : progress
      );
    };

    const onScroll = () => {
      if (frameId === null) {
        frameId = window.requestAnimationFrame(updateHeader);
      }
    };

    updateHeader();

    window.addEventListener("scroll", onScroll, {
      passive: true
    });

    window.addEventListener("resize", onScroll);
    reduceMotion.addEventListener("change", onScroll);

    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      reduceMotion.removeEventListener("change", onScroll);

      if (frameId !== null) {
        window.cancelAnimationFrame(frameId);
      }
    };
  }, []);`;

code =
  code.slice(0, effectStart) +
  newEffect +
  code.slice(effectEnd + endMarker.length);

// New header transform follows actual scroll progress
const headerOpen = `      <div
        aria-hidden={headerProgress < 0.99}
        inert={headerProgress < 0.99}
        className="fixed top-0 left-0 right-0 z-50 bg-white dark:bg-gray-900 shadow-lg border-b border-gray-100 dark:border-gray-700"
        style={{
          transform: \`translate3d(0, \${(headerProgress - 1) * 100}%, 0)\`,
          opacity: headerProgress,
          pointerEvents: headerProgress >= 0.99 ? "auto" : "none",
        }}
      >`;

// Handle original and previously animated versions
const oldConditional =
  /\{scrolled\s*&&\s*\(\s*<div className="fixed top-0[^"\n]*"\s*>/;

const oldAnimated =
  /<div\s+aria-hidden=\{!scrolled\}[\s\S]*?\n\s*>/;

if (oldConditional.test(code)) {
  code = code.replace(oldConditional, headerOpen);

  const closingBlock =
    "\n        </div>\n      )}\n    </div>\n  );";

  const closingAt = code.lastIndexOf(closingBlock);

  if (closingAt < 0) {
    throw new Error("Header closing tag not found. No changes saved.");
  }

  code =
    code.slice(0, closingAt) +
    closingBlock.replace("\n      )}", "") +
    code.slice(closingAt + closingBlock.length);

} else if (oldAnimated.test(code)) {
  code = code.replace(oldAnimated, headerOpen);

} else {
  throw new Error("Unknown header structure. No changes saved.");
}

if (
  code.includes("setScrolled") ||
  code.includes("{scrolled") ||
  code.includes("!scrolled")
) {
  throw new Error("Old scrolling code remains. No changes saved.");
}

// Save backup
fs.copyFileSync(file, file + ".before-scroll-reveal.bak");

// Save new code
fs.writeFileSync(file, code, "utf8");

console.log("Scroll-controlled header installed successfully!");
console.log("Backup created for HeroSearch.jsx");
