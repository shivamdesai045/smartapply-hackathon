export function slugify(text) {
  if (!text) return "";
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "-")           // Replace spaces with -
    .replace(/[^\w\-]+/g, "")       // Remove all non-word chars
    .replace(/\-\-+/g, "-");        // Replace multiple - with single -
}

import { categories } from "../data/servicesData";

export function getServiceNameFromSlug(slug) {
  if (!slug) return null;
  for (const cat of categories) {
    for (const service of cat.services) {
      if (slugify(service.name) === slug) {
        return service.name;
      }
    }
  }
  return null;
}
