const { spawnSync } = require('child_process');
const path = require('path');

const tests = [
  'test_unit.js',
  'test_popup.js',
  'test_gov_form.js',
  'test_integration.js',
  'test_direct_sync.js'
];

let failed = false;

for (const t of tests) {
  console.log(`\n========================================`);
  console.log(`Running ${t}...`);
  console.log(`========================================\n`);
  const res = spawnSync(process.execPath, [path.join(__dirname, t)], {
    stdio: 'inherit'
  });
  if (res.status !== 0) {
    console.error(`\n❌ ${t} FAILED with status ${res.status}`);
    failed = true;
    break;
  }
}

if (failed) {
  process.exit(1);
} else {
  console.log(`\n🎉 ALL AUTOMATED TEST SUITES PASSED!\n`);
  process.exit(0);
}
