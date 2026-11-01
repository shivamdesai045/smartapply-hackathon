const fs = require("fs");

const file = "src/components/HeroSearch.jsx";
let code = fs.readFileSync(file, "utf8");

const cp1252 = [
  "\u20AC", null, "\u201A", "\u0192",
  "\u201E", "\u2026", "\u2020", "\u2021",
  "\u02C6", "\u2030", "\u0160", "\u2039",
  "\u0152", null, "\u017D", null,
  null, "\u2018", "\u2019", "\u201C",
  "\u201D", "\u2022", "\u2013", "\u2014",
  "\u02DC", "\u2122", "\u0161", "\u203A",
  "\u0153", null, "\u017E", "\u0178"
];

function corrupted(value, fallback) {
  return [...Buffer.from(value, "utf8")]
    .map(byte =>
      byte >= 128 && byte < 160
        ? cp1252[byte - 128] || fallback
        : String.fromCharCode(byte)
    )
    .join("");
}

const originalTexts = [
  "\u0939\u093F\u0902\u0926\u0940",
  "\u092E\u0930\u093E\u0920\u0940",
  "\u{1F5D3}\uFE0F",
  "\u{1F319}",
  "\u2600\uFE0F",
  "\u{1F50D}",
  "\u{1F4C1}",
  "\u{1F6AA}",
  "\u25BC",
  "\u2022"
];

let fixes = 0;

for (const original of originalTexts) {
  const variants = new Set([
    corrupted(original, "\uFFFD"),
    corrupted(original, "\u0081"),
    Buffer.from(original, "utf8").toString("latin1")
  ]);

  for (const broken of variants) {
    if (broken === original) continue;

    if (code.includes(broken)) {
      code = code.split(broken).join(original);
      fixes++;
    }
  }
}

if (fixes > 0) {
  fs.copyFileSync(file, file + ".encoding-backup");
  fs.writeFileSync(file, code, "utf8");
  console.log(`Repaired ${fixes} text patterns.`);
} else {
  console.log("No matching corrupted text found.");
}
