# Release

Source repository: https://github.com/Jekyll-Chan/Camera-Atlas (public). The initial repository and commit history were published with GitHub Desktop. No version tag, GitHub Release or PyPI upload has been created.

For future updates, push the local `main` branch with GitHub Desktop, or authenticate git/GitHub CLI in your shell. To reproduce the validation/build:

```bash
python -m pip install '.[terrain,repair,dev]'
pytest --cov=camera_atlas
ruff check .
ruff format --check .
python -m build
git push origin main
```

Run the push command from this repository after checking that `origin` points to the intended account/repository. This is a **public** repository. This checkout contains only documented public example assets, never user private photography. Review `git ls-files` and source licenses before uploading.

CI uses the `ci.yml` workflow; no geographic API keys are needed. Tagged `v*` releases build wheel/sdist and attach them to a GitHub Release through `release.yml`. PyPI publication is not configured and must not be implied by a GitHub release; reserve/check the package name and configure trusted publishing separately. There is no automatic tag creation or PyPI token storage in this project.
