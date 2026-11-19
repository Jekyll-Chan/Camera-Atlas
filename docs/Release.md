# Release

Source repository: https://github.com/Jekyll-Chan/Camera-Atlas (public). The initial repository and commit history were published with GitHub Desktop. No version tag, GitHub Release or PyPI upload has been created.

For future updates, push the local `main` branch with GitHub Desktop, or authenticate git/GitHub CLI in your shell. To reproduce the validation/build:

```bash
python -m pip install '.[terrain,repair,heic,dev,service]'
pytest --cov=camera_atlas
ruff check .
ruff format --check .
python -m build
```

Publishing follows actual supplied-photo acceptance, not only a successful test suite. Inspect the final photo and complete selected map region, subject protection, source provenance and downloadable files before proceeding. Review the staged files and source licenses; this is a **public** repository and must not contain user photography, private GPS, credentials or runtime data.

After acceptance, check that `origin` points to the intended account/repository and push the reviewed renderer commit. Wait for its GitHub CI checks. Download that exact commit's official source archive, verify it independently, and record its SHA256 and byte size in the Skill lock along with the confirmed agent/region/online capabilities. Use a second commit for the lock and release documentation: an archive cannot contain a checksum of itself. Test the locked source in a fresh isolated environment before packaging or submitting the Agensi update. A source commit or tag does not by itself update the marketplace version.

After Agensi approval, load the live Skill again through Codex and verify the returned version and actual photo-to-file workflow. Until that observation, distinguish a prepared ZIP, a submitted update, a live listing and a tested live version.

CI uses the `ci.yml` workflow; no geographic API keys are needed. Tagged `v*` releases build wheel/sdist and attach them to a GitHub Release through `release.yml`. PyPI publication is not configured and must not be implied by a GitHub release; reserve/check the package name and configure trusted publishing separately. There is no automatic tag creation or PyPI token storage in this project.
