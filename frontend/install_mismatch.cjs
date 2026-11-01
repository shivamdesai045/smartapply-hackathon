/*
 Run from SmartApply-frontend/SmartApply-frontend:
 node install_mismatch.cjs
 Applies narrow, verified edits with backups. Does not replace Checklist.jsx or app.py wholesale.
 */
const fs = require('fs');
const path = require('path');
const root = process.cwd();
const front = path.join(root, 'src');
const backend = path.resolve(root, '..', '..', 'SmartApply-backend', 'SmartApply-backend');
const read = (p) => fs.readFileSync(p, 'utf8').replace(/\r\n/g, '\n');
const updates = new Map();
const add = (p, value) => updates.set(p, value);
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const changeOnce = (s, oldText, newText, description) => {
  const parts = s.split(oldText);
  assert(parts.length === 2, `${description}: expected exactly one location; found ${parts.length - 1}. No files saved.`);
  return parts.join(newText);
};
const backendPath = path.join(backend, 'app.py');
const checklistPath = path.join(front, 'pages', 'Checklist.jsx');
const apiPath = path.join(front, 'lib', 'api.js');
const newCardPath = path.join(front, 'components', 'MismatchResolutionCard.jsx');
for (const p of [backendPath, checklistPath, apiPath]) {
  assert(fs.existsSync(p), `Missing ${p}; run this from the Vite frontend project.`);
}
assert(fs.existsSync(path.join(__dirname, 'MismatchResolutionCard.jsx')),
  'Put MismatchResolutionCard.jsx beside install_mismatch.cjs before running.');

let app = read(backendPath);
assert(!app.includes('def unpack_mismatch_decision('), 'Mismatch workflow is already installed in app.py.');
app = changeOnce(app,
  'import os',
  'import os\nimport json\nimport hmac\nimport hashlib', 'Hash helper imports');
app = changeOnce(app,
  '@app.route("/api/checklist/<service_name>/mismatches", methods=["GET"])',
  `def mismatch_signature(issue):
    """Bind a decision to the exact comparison values without storing their plaintext."""
    payload = json.dumps([
        issue.get("field"), issue.get("documents"),
        issue.get("valA"), issue.get("valB"),
    ], sort_keys=True, default=str)
    return hmac.new(str(app.secret_key).encode(), payload.encode(), hashlib.sha256).hexdigest()[:24]


def unpack_mismatch_decision(stored, issue=None):
    """Decode a decision and discard it when the extracted comparison has changed."""
    if not stored:
        return None, None
    parts = stored.split("::", 2)
    if len(parts) == 3 and parts[0] in ("confirmed", "ignored", "ocr_error", "pending"):
        if issue is not None and parts[1] != mismatch_signature(issue):
            return None, None
        return parts[0], parts[2] or None
    # Legacy decisions cannot safely identify which document is incorrect.
    if stored in ("ignored", "ocr_error"):
        return stored, None
    return None, None


@app.route("/api/checklist/<service_name>/mismatches", methods=["GET"])`,
  'Insert decoder');
app = changeOnce(app,
`        decision = decisions.get(key)
        if decision is None:
            pending_count += 1
        issues_with_decisions.append({**issue, "issueKey": key, "decision": decision})`,
`        decision, incorrect_doc = unpack_mismatch_decision(decisions.get(key), issue)
        if decision is None or decision == "pending":
            pending_count += 1
        chosen_guidance = (
            get_guidance(incorrect_doc, issue["field"])
            if decision == "confirmed" and incorrect_doc in issue["documents"]
            else None
        )
        issues_with_decisions.append({
            **issue, "issueKey": key, "decision": decision,
            "incorrectDocument": incorrect_doc, "guidance": chosen_guidance,
        })`, 'Mismatch GET enrich');
const postStart = app.indexOf('@app.route("/api/checklist/<service_name>/mismatch-decision", methods=["POST"])');
const postEnd = app.indexOf('@app.route("/api/correction-guidance-pair", methods=["GET"])', postStart);
assert(postStart >= 0 && postEnd > postStart, 'Mismatch POST route not found.');
const newPost = `@app.route("/api/checklist/<service_name>/mismatch-decision", methods=["POST"])
@login_required
def post_mismatch_decision(service_name):
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    variant = data.get("variant", "adult")
    field = data.get("field")
    documents = data.get("documents")
    decision = data.get("decision")
    incorrect_document = data.get("incorrect_document")

    if (not session_id or not isinstance(field, str) or not isinstance(documents, list)
            or len(documents) != 2 or not all(isinstance(d, str) and d for d in documents)
            or documents[0] == documents[1]
            or decision not in ("confirmed", "ignored", "ocr_error", "pending")):
        return jsonify({"error": "Valid session_id, field, 2 documents and decision are required"}), 400
    if decision == "confirmed" and incorrect_document not in documents:
        return jsonify({"error": "Select the document that needs correction"}), 400

    user_id = session.get("user_id")
    current_docs = db.get_documents_with_data(session_id, service_name, variant, user_id=user_id)
    current_issues = check_mismatches(current_docs).get("issues", []) if len(current_docs) >= 2 else []
    key = build_issue_key(field, documents[0], documents[1])
    matched = next(
        (i for i in current_issues if build_issue_key(i["field"], *i["documents"]) == key),
        None,
    )
    if matched is None:
        return jsonify({"error": "This mismatch is no longer present. Recheck your documents."}), 409

    # Bound to compared field values; changed uploads/OCR require a fresh review.
    # The existing decision TEXT column stores the choice; no migration required.
    selected = incorrect_document if decision == "confirmed" else ""
    stored = f"{decision}::{mismatch_signature(matched)}::{selected}"
    db.save_decision(session_id, service_name, variant, key, stored, user_id=user_id)
    return jsonify({
        "message": "Decision saved", "issueKey": key, "decision": decision,
        "incorrectDocument": incorrect_document if decision == "confirmed" else None,
    })


`;
app = app.slice(0,postStart) + newPost + app.slice(postEnd);
app = changeOnce(app,
`        guidance = [get_guidance(issue["documents"][0], issue["field"]), get_guidance(issue["documents"][1], issue["field"])]
        completed_step_indices = correction_steps.get(key, [])
        issues_with_decisions.append({
            **issue,
            "issueKey": key,
            "decision": decisions.get(key),
            "guidance": guidance,
            "completedSteps": completed_step_indices
        })`,
`        decision, incorrect_doc = unpack_mismatch_decision(decisions.get(key), issue)
        chosen_guidance = (
            get_guidance(incorrect_doc, issue["field"])
            if decision == "confirmed" and incorrect_doc in issue["documents"]
            else None
        )
        completed_step_indices = correction_steps.get(key, [])
        issues_with_decisions.append({
            **issue,
            "issueKey": key, "decision": decision,
            "incorrectDocument": incorrect_doc,
            "guidance": [chosen_guidance] if chosen_guidance else [],
            "completedSteps": completed_step_indices,
        })`, 'Report guidance');
app = changeOnce(app,
`    has_unresolved_mismatches = any(i["decision"] != "confirmed" for i in issues_with_decisions)`,
`    # A confirmed real discrepancy remains unresolved until corrected and rechecked.
    has_unresolved_mismatches = any(i["decision"] not in ("ignored", "ocr_error") for i in issues_with_decisions)`,
'Report readiness');
app = changeOnce(app,
`            has_issue = any(doc_opt in i.get("documents", []) for i in issues_with_decisions if i["decision"] != "confirmed")`,
`            has_issue = any(doc_opt in i.get("documents", []) for i in issues_with_decisions if i["decision"] not in ("ignored", "ocr_error"))`, 'Report doc status');
add(backendPath, app);

let api = read(apiPath);
api = changeOnce(api,
`  documents,
  decision
) {
  const url =`,
`  documents,
  decision,
  incorrectDocument = null
) {
  const url =`, 'API decision function');
api = changeOnce(api,
'body: JSON.stringify({ session_id: sessionId, variant, field, documents, decision }),',
'body: JSON.stringify({ session_id: sessionId, variant, field, documents, decision, incorrect_document: incorrectDocument }),',
'API decision payload');
add(apiPath,api);

let checklist = read(checklistPath);
assert(!checklist.includes('import MismatchResolutionCard from'), 'Checklist mismatch UI already installed.');
checklist = changeOnce(checklist,
'import DocumentViewerModal from "../components/DocumentViewerModal";',
'import DocumentViewerModal from "../components/DocumentViewerModal";\nimport MismatchResolutionCard from "../components/MismatchResolutionCard";',
'Checklist new card import');
const pendingStart = checklist.indexOf('        const pending = data.issues ? data.issues.filter(');
const comparisonStart = checklist.indexOf('        const comparisons = data.comparisons || [];', pendingStart);
assert(pendingStart >= 0 && comparisonStart > pendingStart, 'Checklist issue lists differ.');
checklist = checklist.slice(0,pendingStart) + '        const issues = data.issues || [];\n' + checklist.slice(comparisonStart);
const viewStart = checklist.indexOf('            {/* Discrepancy Resolution & Guidance Cards (when issues exist) */}');
const viewEnd = checklist.indexOf('            {/* Optional manual self-report tool for subtle differences */}',viewStart);
assert(viewStart >= 0 && viewEnd > viewStart, 'Checklist issue UI differs; no files saved.');
const newView = `            {/* User-led decision: confirm mismatch -> choose incorrect document -> correction guide */}
            {issues.length > 0 && (
              <section aria-labelledby="mismatch-resolution-title" className="mb-6 space-y-4">
                <div>
                  <h2 id="mismatch-resolution-title" className="text-lg font-semibold text-slate-900 dark:text-white">
                    {t("mf_section_heading")}
                  </h2>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                    {t("mf_section_intro")}
                  </p>
                </div>
                {issues.map((issue) => (
                  <MismatchResolutionCard
                    key={issue.issueKey}
                    issue={issue}
                    serviceName={serviceName}
                    sessionId={sessionId}
                    variant={variant}
                    onChanged={load}
                    onBack={onBack}
                  />
                ))}
              </section>
            )}

`;
checklist = checklist.slice(0,viewStart)+newView+checklist.slice(viewEnd);
add(checklistPath,checklist);

// All newly visible UI copy is translated into every supported language.
const translated = {
  en: {
    mf_section_heading:'Review detected differences',
    mf_section_intro:'Sahayak compares extracted data. You decide whether a difference is real and which document needs correction.',
    mf_difference:'Difference detected',
    mf_compare_notice:'Compare the original documents. OCR can misread text, and a difference does not prove which document is wrong.',
    mf_sensitive:'Document number hidden for privacy',
    mf_not_detected:'Not detected',
    mf_confirm_question:'Is this a real difference in the original documents?',
    mf_yes:'Yes, this is a mismatch',
    mf_ocr_wrong:'No, OCR read something incorrectly',
    mf_acceptable:'This difference is acceptable',
    mf_which_wrong:'Which document needs correction?',
    mf_which_hint:'Use reliable supporting evidence before choosing. Sahayak does not assume one document is always correct.',
    mf_saving:'Saving...', mf_show_steps:'Confirm and show correction steps', mf_back:'Back',
    mf_guidance_heading:'Correction guidance',
    mf_confirmed_note:'Only the document you selected is shown below. Complete the official correction, upload the updated file, then recheck.',
    mf_step1:'Check the correct details against authoritative supporting records.',
    mf_step2_form:'Locate this correction form or service',
    mf_step2_generic:'Find the correction process on the issuing authority’s official website or contact its service centre.',
    mf_step3:'Prepare the required identity, date-of-birth, or address proof listed by the issuing authority.',
    mf_step4:'Submit through the official process, retain the acknowledgement, and upload the corrected document here once available.',
    mf_generic_notice:'No document-specific verified steps are available here. Check the issuing authority before submitting.',
    mf_fees_notice:'Forms, fees, supporting documents and processing times can change. Confirm the latest rules on the official portal.',
    mf_open_portal:'Open official portal', mf_change_doc:'Change incorrect document', mf_reupload:'Return to uploaded documents',
    mf_ocr_status:'OCR extraction may be wrong. Review and edit the extracted fields, or rescan the document.',
    mf_choose_again:'Choose an incorrect document to get guidance.', mf_dismissed:'Marked acceptable by you.',
    mf_edit_ocr:'Fix OCR fields', mf_reconsider:'Reconsider', mf_save_error:'Could not save your decision.'
  },
  hi: {
    mf_section_heading:'मिले हुए अंतर की जाँच करें',
    mf_section_intro:'सहायक दस्तावेज़ों से निकाली गई जानकारी की तुलना करता है। अंतर सही है या नहीं और किस दस्तावेज़ में सुधार चाहिए, यह आप चुनते हैं।',
    mf_difference:'अंतर मिला',mf_compare_notice:'मूल दस्तावेज़ जाँचें। OCR गलत पढ़ सकता है और अंतर मिलने से यह तय नहीं होता कि कौन-सा दस्तावेज़ गलत है।',
    mf_sensitive:'गोपनीयता के लिए दस्तावेज़ संख्या छिपाई गई है',mf_not_detected:'पता नहीं चला',
    mf_confirm_question:'क्या मूल दस्तावेज़ों में सचमुच यह अंतर है?',mf_yes:'हाँ, अंतर मौजूद है',
    mf_ocr_wrong:'नहीं, OCR ने गलत पढ़ा',mf_acceptable:'यह अंतर स्वीकार्य है',
    mf_which_wrong:'किस दस्तावेज़ में सुधार चाहिए?',mf_which_hint:'चुनने से पहले सही सहायक प्रमाण जाँचें। सहायक किसी एक दस्तावेज़ को हमेशा सही नहीं मानता।',
    mf_saving:'सहेजा जा रहा है...',mf_show_steps:'पुष्टि करें और सुधार के चरण देखें',mf_back:'वापस',
    mf_guidance_heading:'सुधार मार्गदर्शन',mf_confirmed_note:'नीचे केवल चुने गए दस्तावेज़ का मार्गदर्शन है। आधिकारिक सुधार के बाद नया दस्तावेज़ अपलोड करें और फिर जाँच करें।',
    mf_step1:'सही विवरण विश्वसनीय प्रमाणों से जाँचें।',mf_step2_form:'संबंधित सुधार फॉर्म या सेवा खोजें',
    mf_step2_generic:'जारी करने वाले विभाग की आधिकारिक वेबसाइट पर सुधार प्रक्रिया खोजें या सेवा केंद्र से संपर्क करें।',
    mf_step3:'संबंधित विभाग द्वारा माँगे गए पहचान, जन्मतिथि या पते के प्रमाण तैयार करें।',
    mf_step4:'आधिकारिक प्रक्रिया से आवेदन करें, रसीद रखें और सुधार के बाद नया दस्तावेज़ यहाँ अपलोड करें।',
    mf_generic_notice:'इस दस्तावेज़ के लिए सत्यापित विशेष चरण उपलब्ध नहीं हैं। आवेदन से पहले जारीकर्ता विभाग से पुष्टि करें।',
    mf_fees_notice:'फॉर्म, शुल्क, प्रमाण और समय बदल सकते हैं। आधिकारिक वेबसाइट पर नई जानकारी जाँचें।',
    mf_open_portal:'आधिकारिक पोर्टल खोलें',mf_change_doc:'गलत दस्तावेज़ बदलें',mf_reupload:'दस्तावेज़ों पर वापस जाएँ',
    mf_ocr_status:'OCR गलत हो सकता है। निकाली गई जानकारी सुधारें या फिर स्कैन करें।',mf_choose_again:'सुधार के लिए दस्तावेज़ चुनें।',
    mf_dismissed:'आपने इस अंतर को स्वीकार्य माना है।',mf_edit_ocr:'OCR की जानकारी सुधारें',mf_reconsider:'फिर से देखें',mf_save_error:'निर्णय सहेजा नहीं जा सका।'
  },
  mr: {
    mf_section_heading:'आढळलेली तफावत तपासा',mf_section_intro:'सहाय्यक कागदपत्रांतून मिळालेल्या माहितीची तुलना करतो. तफावत खरी आहे का आणि कोणते कागदपत्र दुरुस्त करायचे ते तुम्ही ठरवा.',
    mf_difference:'तफावत आढळली',mf_compare_notice:'मूळ कागदपत्रे तपासा. OCR चुकीचे वाचू शकते आणि तफावत असल्याने कोणते कागदपत्र चुकीचे आहे हे ठरत नाही.',
    mf_sensitive:'गोपनीयतेसाठी कागदपत्र क्रमांक लपवला आहे',mf_not_detected:'आढळले नाही',
    mf_confirm_question:'मूळ कागदपत्रांमध्ये खरोखर ही तफावत आहे का?',mf_yes:'होय, तफावत आहे',
    mf_ocr_wrong:'नाही, OCR चुकीचे वाचले',mf_acceptable:'ही तफावत स्वीकारण्याजोगी आहे',
    mf_which_wrong:'कोणते कागदपत्र दुरुस्त करायचे?',mf_which_hint:'निवडण्यापूर्वी योग्य पुरावे तपासा. सहाय्यक कोणतेही एक कागदपत्र नेहमी बरोबर मानत नाही.',
    mf_saving:'जतन करत आहे...',mf_show_steps:'पुष्टी करा आणि दुरुस्तीची पावले पाहा',mf_back:'मागे',
    mf_guidance_heading:'दुरुस्तीचे मार्गदर्शन',mf_confirmed_note:'खाली फक्त तुम्ही निवडलेल्या कागदपत्राचे मार्गदर्शन आहे. अधिकृत दुरुस्ती झाल्यावर नवे कागदपत्र अपलोड करून पुन्हा तपासा.',
    mf_step1:'योग्य तपशील अधिकृत पुराव्यांसोबत पडताळा.',mf_step2_form:'हा दुरुस्तीचा फॉर्म किंवा सेवा शोधा',
    mf_step2_generic:'कागदपत्र देणाऱ्या विभागाच्या अधिकृत संकेतस्थळावर दुरुस्तीची प्रक्रिया शोधा किंवा केंद्राशी संपर्क करा.',
    mf_step3:'विभागाने मागितलेले ओळख, जन्मतारीख किंवा पत्त्याचे पुरावे तयार ठेवा.',
    mf_step4:'अधिकृत प्रक्रियेद्वारे अर्ज करा, पावती जतन करा आणि दुरुस्त कागदपत्र येथे अपलोड करा.',
    mf_generic_notice:'या कागदपत्रासाठी विशेष पडताळलेली पावले उपलब्ध नाहीत. अर्जापूर्वी संबंधित विभागाकडून खात्री करा.',
    mf_fees_notice:'फॉर्म, शुल्क, पुरावे व कालावधी बदलू शकतात. अधिकृत पोर्टलवर ताजी माहिती तपासा.',
    mf_open_portal:'अधिकृत पोर्टल उघडा',mf_change_doc:'चुकीचे कागदपत्र बदला',mf_reupload:'अपलोड केलेल्या कागदपत्रांकडे जा',
    mf_ocr_status:'OCR चुकीचे असू शकते. माहिती दुरुस्त करा किंवा पुन्हा स्कॅन करा.',mf_choose_again:'दुरुस्तीसाठी कागदपत्र निवडा.',
    mf_dismissed:'तुम्ही ही तफावत स्वीकारली आहे.',mf_edit_ocr:'OCR माहिती दुरुस्त करा',mf_reconsider:'पुन्हा तपासा',mf_save_error:'निर्णय जतन करता आला नाही.'
  }
};
for(const lang of ['en','hi','mr']) {
  const p = path.join(front,'locales',lang+'.json');
  assert(fs.existsSync(p),`Missing translation file: ${p}`);
  const original = JSON.parse(read(p));
  for(const [key,value] of Object.entries(translated[lang]))original[key] = value;
  add(p,JSON.stringify(original,null,2)+'\n');
}

// The component is installed last; all required anchor checks above must succeed first.
add(newCardPath, read(path.join(__dirname,'MismatchResolutionCard.jsx')));
const backupsDir = path.join(root,'sahayak-mismatch-backups');
fs.mkdirSync(backupsDir,{recursive:true});
const stamp = new Date().toISOString().replace(/[:.]/g,'-');
for(const [target,content] of updates) {
  if(fs.existsSync(target)) {
    const targetLabel = path.relative(root,target).replace(/[^a-zA-Z0-9._-]/g,'_');
    fs.copyFileSync(target,path.join(backupsDir,`${stamp}_${targetLabel}.bak`));
  }
}
for(const [target,content] of updates) {
  fs.mkdirSync(path.dirname(target),{recursive:true});
  fs.writeFileSync(target,content,'utf8');
  console.log('Updated',path.relative(root,target));
}
console.log('Mismatch confirmation and targeted correction guidance installed.');
console.log('Backups:',backupsDir);
