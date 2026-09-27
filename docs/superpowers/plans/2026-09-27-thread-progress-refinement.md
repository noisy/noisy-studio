# Thread Progress Refinement Plan

**Goal:** Apply the user's approved prototype corrections: concise noun-phrase task names, stable single-line titles, and elapsed time / progress bar / percentage.

**Scope:** Lab Next only, plus task-reporting skill guidance. No production UI or backend changes.

1. Update `skills/task-progress/SKILL.md` with the supplied naming examples; keep identifiers stable across reports.
2. Replace `BoundedTitle.vue` expansion with plain ellipsized text and a native title hint. Suppress the old global review flyouts inside this lab only.
3. Shorten fixture names. Supply explicit fixture start timestamps separate from report updates. Render a ticking elapsed duration, flexible bar and percentage; omit model labels.
4. Keep a long-title stress story; verify hover/click cannot resize rows or produce overflow. Run dashboard type/build and inspect narrow rails visually.
5. Commit the skill and prototype as focused increments. Keep the live dashboard unchanged pending design review.
