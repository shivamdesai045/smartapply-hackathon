import { categories } from "./src/data/servicesData.js";

function slugify(text) {
  if (!text) return "";
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "-")           // Replace spaces with -
    .replace(/[^\w\-]+/g, "")       // Remove all non-word chars
    .replace(/\-\-+/g, "-");        // Replace multiple - with single -
}

const map = {};
let hasDuplicate = false;

for (const cat of categories) {
  for (const service of cat.services) {
    const slug = slugify(service.name);
    console.log(`"${service.name}" -> "${slug}"`);
    if (map[slug]) {
      console.error(`DUPLICATE SLUG FOUND: ${slug} (used by "${map[slug]}" and "${service.name}")`);
      hasDuplicate = true;
    }
    map[slug] = service.name;
  }
}

if (!hasDuplicate) {
  console.log("SUCCESS: All 19 services map to unique slugs.");
} else {
  process.exit(1);
}
