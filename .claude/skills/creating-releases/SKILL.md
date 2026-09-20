---
name: creating-releases
description: Prepare and verify a signed native Noisy Studio release.
---

# Native releases

Publication, tags and public pushes require explicit user authorization.

1. Run appropriate Python, dashboard and desktop checks. Update release notes
   for user-visible changes and compatibility requirements.
2. Run `scripts/bump_version.py` with the intended version. Review every version
   file it changes and commit a coherent release increment.
3. When authorized, push the release commit and tag. The release workflow
   creates a draft and builds the macOS app with its bundled engine.
4. Require engine version validation, frozen integration smoke checks, app
   launch smoke checks, signatures and notarization before publishing. The
   canonical repository must produce signed assets; fork builds are explicitly
   marked unsigned. Never display signing secrets or local credentials.
5. Write useful release notes; generated commit lists are not sufficient.
   Publish the draft only with authorization.
6. Follow `../after-production-release/SKILL.md`: update app and plugin together,
   then verify the running version and a spoken round trip.

Do not treat a successful workflow as proof that an installed copy was updated.
See `docs/desktop-app.md` for bundle structure and release gates.
