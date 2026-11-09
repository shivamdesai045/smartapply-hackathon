# OCR latency changes

The fast path is local and uses two Tesseract segmentation modes. It is enabled with `OCR_FAST_TEXT_PASS=1`; Paddle remains the fallback. Both modes must produce complete validated name, DOB and document ID, meet page/identity-row confidence gates, and agree on all three values. Fast-path results still require user review. Confidence is a heuristic, not proof of correctness.

- Text PDFs bypass OCR page by page. Mixed PDFs rasterize only pages without sufficient usable embedded text; the four-page limit is explicitly reported.
- Clear images and scanned PDF pages can use the bounded fast path. Each segmentation attempt has a three-second subprocess timeout. Rejected results go to Paddle rather than being guessed or silently accepted.
- Paddle is loaded once in an isolated worker. `/api/ocr/health` exposes readiness without document information. The checklist shows its warmup state.
- Complete explicitly parsed core fields skip the redundant ML classifier. Optional region recovery is limited to one attempt when a retry budget is supplied; a nearly exhausted budget skips recovery and leaves missing values reviewable.
- Identical successful uploads can reuse results within the same authenticated user/session for five minutes. The cache is process-local, bounded to 16 entries and one MiB per entry, sanitized, cleared on logout/document deletion, and never stores plaintext passwords. Re-scan bypasses it.
- Responses contain stage timings. Job status separates queue wait from processing and freezes completed durations.

## Measurement limits

On six invented English CBSE X/XII, SSC/HSC and ICSE/ISC images with numeric DOB, the two-mode fast path read all 18 core fields exactly in 1.239–1.736 seconds per full extraction. Same-session repeat lookups were 0.005–0.008 seconds. These are local processing measurements, not public-network or concurrent-user guarantees.

The written-DOB fixture was rejected when Tesseract misread a word, as intended. Such pages still need Paddle. Measured Paddle-only runs were roughly 12–16 seconds warm in this session, with 48–54 second cold starts and one 70-second startup timeout. A batch of four was slower and was not retained; the smaller-detector/single-thread experiment was also not retained. Observed free RAM was approximately 900 MiB on an 8 GiB machine, but this does not establish the cause of every stall.

A universal ten-second maximum has NOT been achieved. Low-confidence scans, missing fields, multi-page documents, startup and queueing may exceed it. Do not present cached or preprocessed results as new live OCR. Keep the readiness indicator ready before demonstrations and review all fields before submission.

Integration validation: the isolated asynchronous upload returned all three expected fields in 3.351 seconds (2.3 seconds job processing); a scanned PDF took 2.418 seconds and a text PDF 0.082 seconds. 56 targeted backend tests, frontend production build, and browser upload/refresh/reconnect regressions passed. The running backend health reported ready.
