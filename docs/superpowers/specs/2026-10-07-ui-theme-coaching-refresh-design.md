# UI Theme and Coaching Refresh Design

## Intent and scope

Replace the first screen with a lightweight coaching home, restyle the existing coaching recording/transcription states, and add a persistent light/dark preference. Preserve all coaching APIs, media handling, session data, and history behavior. The supplied screenshots are visual references only.

## Chosen approach

Use semantic CSS tokens controlled by `html[data-theme]`, with a small React theme provider. This avoids a second stylesheet tree and allows the existing CSS-heavy application to migrate screen by screen. A new home route/view delegates only to existing navigation callbacks. Recording and transcription gain presentation components/assets while preserving state machines.

## Components and data flow

```text
ThemeProvider -> html[data-theme] -> CSS tokens -> application screens
AppHeader -> ThemeToggle -> local preference (best effort)
Home screen -> existing navigate(practice | history)
Existing recording/transcription state -> state-specific visual asset + existing controls
```

- `ThemeProvider`: resolve OS preference, read/write a UI-only browser preference, set `data-theme`.
- `ThemeToggle`: circular control beside account UI; tooltips and accessible label name the *next* action.
- `Home`: product-oriented start screen; sends users to existing practice/history destinations only.
- `Recording`/`Transcription` visuals: use separate, transparent mascot assets; retain existing status messaging as the non-image source of truth.

## Safety and rollback

- No backend, database, migration, API contract, or production environment configuration change.
- All behavior changes remain isolated to a single frontend feature branch and PR.
- A deployment regression is reverted with `git revert`; the Vercel owner redeploys the previous known-good commit.
- Vercel/GCP credentials are never needed by the frontend implementation itself.

## Verification plan

- Unit tests: theme default, toggle, persisted preference, accessible label/tooltip, home navigation, recording/transcription asset selection.
- Regression tests: existing practice, microphone/recording, transcription, history navigation and history API-mocked flows.
- Build: TypeScript/Vite production build.
- Manual: desktop and small viewport; light/dark contrast; keyboard focus; image-load fallback.
