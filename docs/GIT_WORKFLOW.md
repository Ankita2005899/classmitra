# Git workflow

## Branches
`main` always works. Do each piece of work on its own branch and merge it with a pull request, even when you work alone. This gives you history and review practice.

Branch names: `feature/phase-1-database`, `fix/cors-error`, `docs/design-note`.

## Daily commands
```
git checkout main
git pull
git checkout -b feature/phase-1-database
# ...work...
git status                     # look at what changed BEFORE adding
git add backend/app/models.py  # add specific files, avoid blind "git add ."
git commit -m "feat: add Department and Class tables"
git push -u origin feature/phase-1-database
```
Then open a pull request on GitHub, check that CI is green, and merge. After merging: `git checkout main` and `git pull`.

## Commit messages
`type: short summary in present tense`

Types: `feat` (new thing), `fix` (bug), `docs`, `test`, `refactor`, `chore`.
Examples: `feat: add health endpoint`, `fix: allow GitHub Pages origin in CORS`.

## Tags per phase
After finishing a phase: `git tag phase-0-done` then `git push --tags`.

## Secrets rules
1. API keys live only in `backend/.env`, which `.gitignore` excludes.
2. Check before every commit: `git status` must NOT list any `.env` file.
3. Prove it is ignored: `git check-ignore -v backend/.env` should print a rule.
4. If a key was ever committed or pasted somewhere public, **revoke it at the provider and create a new one right away**. Deleting the commit is not enough, because the key may already have been copied.
