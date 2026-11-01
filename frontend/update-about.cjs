const fs = require("fs");

const translations = {
  en: {
    about_new_label: "ABOUT SAHAYAK",
    about_new_heading: "Making applications simpler, one document at a time.",
    about_new_description: "Sahayak is an independent platform that helps you prepare documents for government and academic applications. Find the right checklist, review possible information mismatches, and get guidance before visiting the official application portal.",
    about_new_button: "Explore Services",
    about_new_features_heading: "What can you do with Sahayak?",
    about_new_features_subtitle: "Simple guidance to help you prepare before applying.",
    about_new_feature1_title: "Find Your Application",
    about_new_feature1_desc: "Choose a service and find the application you want to prepare for.",
    about_new_feature2_title: "Know Your Requirements",
    about_new_feature2_desc: "View the document checklist for your selected service and identify missing documents.",
    about_new_feature3_title: "Check Your Documents",
    about_new_feature3_desc: "Upload supported documents and check for possible differences in names, dates of birth, and addresses.",
    about_new_feature4_title: "Get Guidance",
    about_new_feature4_desc: "Find correction guidance and continue to the relevant official portal when you are ready.",
    about_new_disclaimer: "Sahayak is an independent helper, not an official government website. Document checks are automated consistency checks, not official identity verification or a guarantee of application approval."
  },

  hi: {
    about_new_label: "सहायक के बारे में",
    about_new_heading: "हर दस्तावेज़ के साथ आवेदन प्रक्रिया को आसान बनाएँ।",
    about_new_description: "सहायक एक स्वतंत्र प्लेटफ़ॉर्म है जो सरकारी और शैक्षणिक आवेदनों के लिए दस्तावेज़ तैयार करने में मदद करता है। आवश्यक दस्तावेज़ों की सूची देखें, जानकारी में संभावित अंतर पहचानें और आधिकारिक पोर्टल पर जाने से पहले मार्गदर्शन पाएँ।",
    about_new_button: "सेवाएँ देखें",
    about_new_features_heading: "सहायक से आप क्या कर सकते हैं?",
    about_new_features_subtitle: "आवेदन से पहले तैयारी के लिए सरल मार्गदर्शन।",
    about_new_feature1_title: "अपना आवेदन चुनें",
    about_new_feature1_desc: "वह सेवा चुनें जिसके लिए आप आवेदन करना चाहते हैं।",
    about_new_feature2_title: "आवश्यक दस्तावेज़ जानें",
    about_new_feature2_desc: "चुनी गई सेवा के दस्तावेज़ों की सूची देखें और पता करें कि क्या कमी है।",
    about_new_feature3_title: "दस्तावेज़ जाँचें",
    about_new_feature3_desc: "समर्थित दस्तावेज़ अपलोड करें और नाम, जन्मतिथि तथा पते में संभावित अंतर जाँचें।",
    about_new_feature4_title: "मार्गदर्शन प्राप्त करें",
    about_new_feature4_desc: "दस्तावेज़ सुधारने का मार्गदर्शन पाएँ और तैयार होने पर संबंधित आधिकारिक पोर्टल पर जाएँ।",
    about_new_disclaimer: "सहायक एक स्वतंत्र सहायता प्लेटफ़ॉर्म है, आधिकारिक सरकारी वेबसाइट नहीं। स्वचालित जाँच केवल दस्तावेज़ों की जानकारी की तुलना करती है। यह आधिकारिक पहचान सत्यापन या आवेदन स्वीकृति की गारंटी नहीं है।"
  },

  mr: {
    about_new_label: "सहाय्यकबद्दल",
    about_new_heading: "प्रत्येक कागदपत्रासह अर्ज प्रक्रिया अधिक सोपी करा.",
    about_new_description: "सहाय्यक हे स्वतंत्र व्यासपीठ आहे जे सरकारी आणि शैक्षणिक अर्जांसाठी कागदपत्रे तयार करण्यात मदत करते. आवश्यक कागदपत्रांची यादी पाहा, माहितीतील संभाव्य तफावत ओळखा आणि अधिकृत पोर्टलवर जाण्यापूर्वी मार्गदर्शन मिळवा.",
    about_new_button: "सेवा पाहा",
    about_new_features_heading: "सहाय्यकच्या मदतीने तुम्ही काय करू शकता?",
    about_new_features_subtitle: "अर्ज करण्यापूर्वी तयारीसाठी सोपे मार्गदर्शन.",
    about_new_feature1_title: "तुमचा अर्ज निवडा",
    about_new_feature1_desc: "ज्या सेवेसाठी अर्ज करायचा आहे ती सेवा निवडा.",
    about_new_feature2_title: "आवश्यक कागदपत्रे जाणून घ्या",
    about_new_feature2_desc: "निवडलेल्या सेवेसाठी कागदपत्रांची यादी पाहा आणि कोणती कागदपत्रे कमी आहेत ते तपासा.",
    about_new_feature3_title: "कागदपत्रे तपासा",
    about_new_feature3_desc: "समर्थित कागदपत्रे अपलोड करा आणि नाव, जन्मतारीख व पत्त्यातील संभाव्य तफावत तपासा.",
    about_new_feature4_title: "मार्गदर्शन मिळवा",
    about_new_feature4_desc: "दुरुस्तीसाठी मार्गदर्शन मिळवा आणि तयारी झाल्यावर संबंधित अधिकृत पोर्टलला भेट द्या.",
    about_new_disclaimer: "सहाय्यक हे स्वतंत्र मदत करणारे व्यासपीठ आहे, अधिकृत सरकारी वेबसाइट नाही. स्वयंचलित तपासणी केवळ कागदपत्रांतील माहितीची तुलना करते. हे अधिकृत ओळख पडताळणी किंवा अर्ज मंजुरीची हमी नाही."
  }
};

for (const language of ["en", "hi", "mr"]) {
  const path = `src/locales/${language}.json`;

  const current = JSON.parse(
    fs.readFileSync(path, "utf8")
  );

  Object.assign(current, translations[language]);

  fs.writeFileSync(
    path,
    JSON.stringify(current, null, 2) + "\n",
    "utf8"
  );

  console.log(`Updated ${language}.json`);
}
