const fs = require("fs");

const labels = {
  en: {
    news_checked: "Last checked",
    news_disclaimer: "Independent helper. Not an official government website. Dates may change."
  },
  hi: {
    news_checked: "अंतिम जाँच",
    news_disclaimer: "स्वतंत्र सहायक। यह आधिकारिक सरकारी वेबसाइट नहीं है। तारीखें बदल सकती हैं।"
  },
  mr: {
    news_checked: "शेवटची तपासणी",
    news_disclaimer: "स्वतंत्र सहाय्यक. ही अधिकृत सरकारी वेबसाइट नाही. तारखा बदलू शकतात."
  }
};

for (const lang of Object.keys(labels)) {
  const path = `src/locales/${lang}.json`;
  const data = JSON.parse(fs.readFileSync(path, "utf8"));

  Object.assign(data, labels[lang]);

  fs.writeFileSync(
    path,
    JSON.stringify(data, null, 2) + "\n",
    "utf8"
  );

  console.log(`Fixed ${lang} translations`);
}
