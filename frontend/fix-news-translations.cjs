const fs = require("fs");

const translations = {
  en: {
    news_heading: "Important Dates & Updates",
    news_subtitle: "Upcoming deadlines from official sources",
    news_more: "View all updates",
    news_less: "Show less",
    news_exam: "EXAM",
    news_scholarship: "SCHOLARSHIP",
    news_scheme: "SCHEME",
    news_jee: "JEE Main 2027 — Registration",
    news_yasasvi: "PM YASASVI — School Scholarship",
    news_pragati: "AICTE Pragati Scholarship",
    news_jee_correction: "JEE Main 2027 — Correction Window",
    news_pmkisan: "PM-KISAN — eKYC Update",
    news_ongoing: "Check portal",
    news_source: "Official source",
    news_new_tab: "Opens in a new tab",
    news_checked: "Last checked",
    news_disclaimer: "Independent helper. Not an official government website. Dates may change.",
    news_empty: "No upcoming deadlines listed. Check official portals."
  },

  hi: {
    news_heading: "महत्वपूर्ण तारीखें और अपडेट",
    news_subtitle: "आधिकारिक स्रोतों से आगामी अंतिम तारीखें",
    news_more: "सभी अपडेट देखें",
    news_less: "कम दिखाएँ",
    news_exam: "परीक्षा",
    news_scholarship: "छात्रवृत्ति",
    news_scheme: "योजना",
    news_jee: "जेईई मेन 2027 — पंजीकरण",
    news_yasasvi: "पीएम यशस्वी — स्कूली छात्रवृत्ति",
    news_pragati: "एआईसीटीई प्रगति छात्रवृत्ति",
    news_jee_correction: "जेईई मेन 2027 — आवेदन सुधार",
    news_pmkisan: "पीएम-किसान — ई-केवाईसी अपडेट",
    news_ongoing: "पोर्टल देखें",
    news_source: "आधिकारिक स्रोत",
    news_new_tab: "नए टैब में खुलेगा",
    news_checked: "अंतिम जाँच",
    news_disclaimer: "स्वतंत्र सहायक। यह आधिकारिक सरकारी वेबसाइट नहीं है। तारीखें बदल सकती हैं।",
    news_empty: "कोई आगामी अंतिम तारीख उपलब्ध नहीं है। आधिकारिक पोर्टल देखें।"
  },

  mr: {
    news_heading: "महत्त्वाच्या तारखा आणि अपडेट्स",
    news_subtitle: "अधिकृत स्रोतांवरील आगामी अंतिम तारखा",
    news_more: "सर्व अपडेट्स पाहा",
    news_less: "कमी दाखवा",
    news_exam: "परीक्षा",
    news_scholarship: "शिष्यवृत्ती",
    news_scheme: "योजना",
    news_jee: "जेईई मेन 2027 — नोंदणी",
    news_yasasvi: "पीएम यशस्वी — शालेय शिष्यवृत्ती",
    news_pragati: "एआयसीटीई प्रगती शिष्यवृत्ती",
    news_jee_correction: "जेईई मेन 2027 — अर्ज दुरुस्ती",
    news_pmkisan: "पीएम-किसान — ई-केवायसी अपडेट",
    news_ongoing: "पोर्टल पाहा",
    news_source: "अधिकृत स्रोत",
    news_new_tab: "नवीन टॅबमध्ये उघडेल",
    news_checked: "शेवटची तपासणी",
    news_disclaimer: "स्वतंत्र सहाय्यक. ही अधिकृत सरकारी वेबसाइट नाही. तारखा बदलू शकतात.",
    news_empty: "आगामी अंतिम तारखा उपलब्ध नाहीत. अधिकृत पोर्टल पाहा."
  }
};

for (const lang of ["en", "hi", "mr"]) {
  const path = `src/locales/${lang}.json`;
  const current = JSON.parse(fs.readFileSync(path, "utf8"));

  Object.assign(current, translations[lang]);

  fs.writeFileSync(
    path,
    JSON.stringify(current, null, 2) + "\n",
    "utf8"
  );

  console.log(`Updated ${path}`);
}
