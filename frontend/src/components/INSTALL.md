# Quick Start Strip — installation

1. Copy QuickStartStrip.jsx and QuickStartStrip.css into src/components/.
2. Merge the keys from qs_en.json, qs_hi.json, qs_mr.json into their corresponding existing files in src/locales/ (do not replace existing files).
3. In src/app.jsx add: import QuickStartStrip from './components/QuickStartStrip';
4. In Home() render <QuickStartStrip staticCounter={{ value: 3, labelKey: 'qs_languages' }} /> directly after <HeroSearch /> and before <Carousel />.
5. Run npm run build and npm run dev from frontend project directory.

No API/backend/env changes. Existing useServices and slugify are reused. API supplies two dynamic counts; '3 languages' is editable third static counter. Quick picks are NOT based on popularity metrics.
