// Demo: collects the corrected details, builds the Sahayak details file and downloads it.
// In the real website, replace readProfile() with the corrected values from the mismatch checker.
function readProfile() {
  const p = {};
  document.querySelectorAll('#f [data-k]').forEach((el) => { p[el.dataset.k] = el.value; });
  return p;
}
function download(name, text) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
  a.download = name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function say(text, cls) { const p = document.createElement('p'); p.textContent = text; p.className = cls || ''; document.getElementById('msg').appendChild(p); }
document.getElementById('go').addEventListener('click', async () => {
  document.getElementById('msg').replaceChildren();
  const pw = document.getElementById('pw').value;
  if (pw && pw.length < 8) return say('Use at least 8 characters for the file passphrase, or leave it empty.', 'err');
  try {
    const { text, warnings } = await SahayakProfileIO.buildExport(readProfile(), pw || null);
    download('sahayak-details.json', text);
    say(pw ? 'Downloaded sahayak-details.json (encrypted). Import it in the extension with the same passphrase.' : 'Downloaded sahayak-details.json. It is not encrypted: import it, then delete the file.', 'ok');
    warnings.forEach((w) => say(w, 'warn'));
  } catch (e) { say(e.code === 'EMPTY' ? 'Nothing to export: fill in at least one detail.' : 'Could not create the file.', 'err'); }
});
