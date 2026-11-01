# GitHub workflow

Repository: https://github.com/praveen202105/trustdesk (public).
Initial root commit preserves the original specifications. All subsequent implementation uses phase/NN-description branches and PRs.

For each phase: implement, run relevant local tests and existing regressions, inspect diff and secrets, commit, push, open PR, wait for successful CI, merge without bypassing checks, verify main CI and record evidence. Fix failures on the phase branch. Keep phase evidence in version control; do not claim nonexistent test results.

CI runs on pull_request and pushes to main. Backend checks use real PostgreSQL with vector support; frontend checks include types, lint, build and browser tests once introduced. Logs/artifacts contain no real credentials. Production releases are explicit, not automatic on every main push.
