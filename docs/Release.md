# Release

The local repository is ready for review and source/wheel builds. A connected GitHub identity does not by itself provide a repository-creation or git-push credential. If `gh` and git are authenticated in your shell:

```bash
python -m pip install '.[terrain,repair,dev]'
pytest --cov=camera_atlas
ruff check .
ruff format --check .
python -m build
gh auth login
gh repo create Camera-Atlas --public --source=. --remote=origin --push
```

Run the final command from this repository only after checking that the account/name is correct. It creates a **public** repository. This checkout contains only documented public example assets, never user private photography. Review `git ls-files` and source licenses before uploading. If the repository already exists, set the intended remote and use `git push -u origin main` instead of creating another.

CI uses the `ci.yml` workflow; no geographic API keys are needed. Tagged `v*` releases build wheel/sdist and attach them to a GitHub Release through `release.yml`. PyPI publication is not configured and must not be implied by a GitHub release; reserve/check the package name and configure trusted publishing separately. There is no automatic tag creation or PyPI token storage in this project.
