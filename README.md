# sim-epochs

The Mu2e simulation-epochs catalog. Derives which simulation datasets
exist, which one to use, what each was made with, and what can be
retired together — from SAM parentage, on every run. A person supplies
only what a machine cannot know: one small JSON per digitization
campaign with a name, a purpose, a standing and the root patterns.

Design: `docs/design.md`. Glossary: `CONTEXT.md`. Decisions:
`docs/adr/`. Cut from `Mu2e/prodtools` on 2026-09-05 with history.

## Running

Any Mu2e node. The only runtime dependency outside the standard
library is `samweb_client`, which is not on PyPI:

```bash
source /cvmfs/mu2e.opensciencegrid.org/setupmu2e-art.sh
muse setup ops
bin/epochs members --family Run1B --status current
```

No Musing, no `muse setup SimJob`, no production account.

## Verbs

| verb | answers |
|---|---|
| `members [--tier T] [--status S]` | which datasets exist and which one to use (`current` / `stale` / `superseded`) |
| `gaps` | a dig content with no mcs or nts yet, and every stale member; **exits 1** on a stale member of a current epoch (ADR 0006) |
| `consistency` | generation spread per tier: which musing and Offline version made the current datasets |
| `lookup DATASET` | one dataset's epoch, status, generation, children, `superseded_by` |
| `retire` | delete candidates in `purge_proposal` line format; refuses while the catalog is incomplete |
| `propose --family F` | write `data/epochs/<letters>.json` for every dig campaign that has none |
| `index-cnfs` | rebuild `data/epochs/cnf_index.json`, dataset to the cnf that produced it |
| `publish --out FILE` | the catalog document the sim-epochs MCP server reads |

`--family F` restricts the build for `members`, `gaps`, `lookup` and
`consistency` (seconds instead of minutes); `retire` and `publish`
always build every family. `--epoch` filters printed rows for
`members`, `gaps` and `retire`, and is refused elsewhere. `--json` on
any listing verb. `--quiet` drops the stderr progress.

## Epoch files

One per digitization campaign, `data/epochs/<letters>.json`:

```json
{
  "name": "Run1Ban",
  "purpose": "SimJob/Run1Ban, Offline v13_17_10",
  "status": "frozen",
  "roots": ["dig.mu2e.%.Run1Ban.art", "dig.mu2e.%.Run1Ban_%.art", "dig.mu2e.%.Run1Ban-%.art"],
  "pins": {"exclude": [], "hold": [], "not_expected": [], "order": [], "notes": []}
}
```

`status` is the epoch's standing — `current` (being worked on),
`frozen` (a hold on every member), `retired` (every member a delete
candidate). A dataset's own status is never stored; it is recomputed.

## The rule

The newest-named dataset per description is the one to run on, and
production keeps that promise: a remade parent obligates remaking every
downstream tier before the round is complete. `bin/epochs gaps` is the
round-complete check. ADR 0006.

## Tests

```bash
python3 -m unittest discover -s tests
```

No SAM, no Mu2e environment: `samweb_client` is stubbed.
