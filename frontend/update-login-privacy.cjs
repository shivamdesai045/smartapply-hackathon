const fs = require("fs");

const translations = {
  en: {
    login_modal_close: "Close login dialog",
    login_modal_intro: "Sign in to upload, review and check your documents.",
    login_modal_privacy_title: "Privacy & Document Safety",
    login_modal_privacy_desc: "Documents may contain sensitive personal information. Sahayak processes uploaded files to extract details and identify possible differences between documents.",
    login_modal_privacy_tip: "Only upload documents you own or have permission to use. Review your files before uploading.",
    login_modal_disclaimer: "Independent helper. Not an official government website."
  },
  hi: {
    login_modal_close: "लॉगिन विंडो बंद करें",
    login_modal_intro: "दस्तावेज़ अपलोड करने, देखने और जाँचने के लिए लॉगिन करें।",
    login_modal_privacy_title: "गोपनीयता और दस्तावेज़ सुरक्षा",
    login_modal_privacy_desc: "दस्तावेज़ों में संवेदनशील व्यक्तिगत जानकारी हो सकती है। सहायक अपलोड की गई फ़ाइलों से जानकारी निकालकर दस्तावेज़ों के बीच संभावित अंतर पहचानता है।",
    login_modal_privacy_tip: "केवल अपने दस्तावेज़ या वे दस्तावेज़ अपलोड करें जिन्हें उपयोग करने की अनुमति आपके पास है। अपलोड करने से पहले फ़ाइलें जाँचें।",
    login_modal_disclaimer: "स्वतंत्र सहायक। यह आधिकारिक सरकारी वेबसाइट नहीं है।"
  },
  mr: {
    login_modal_close: "लॉगिन विंडो बंद करा",
    login_modal_intro: "कागदपत्रे अपलोड करण्यासाठी, पाहण्यासाठी आणि तपासण्यासाठी लॉगिन करा.",
    login_modal_privacy_title: "गोपनीयता आणि कागदपत्रांची सुरक्षितता",
    login_modal_privacy_desc: "कागदपत्रांमध्ये संवेदनशील वैयक्तिक माहिती असू शकते. सहाय्यक अपलोड केलेल्या फाइल्समधील माहिती काढून कागदपत्रांमधील संभाव्य तफावत ओळखतो.",
    login_modal_privacy_tip: "फक्त स्वतःची किंवा वापरण्याची परवानगी असलेली कागदपत्रे अपलोड करा. अपलोड करण्यापूर्वी फाइल्स तपासा.",
    login_modal_disclaimer: "स्वतंत्र सहाय्यक. ही अधिकृत सरकारी वेबसाइट नाही."
  }
};

for (const lang of ["en", "hi", "mr"]) {
  const path = `src/locales/${lang}.json`;

  const data = JSON.parse(fs.readFileSync(path, "utf8"));

  Object.assign(data, translations[lang]);

  fs.writeFileSync(
    path,
    JSON.stringify(data, null, 2) + "\n",
    "utf8"
  );

  console.log(`Updated ${path}`);
}
