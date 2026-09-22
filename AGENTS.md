## How work reaches the board, and how the board reaches you

<!-- Board workflow (inserted by the DSH Systems lane on Tim's instruction, 2026-09-21.
     This section is additive: nothing below it was changed. You own this file and you may
     edit or remove this block — but tell the DSH Systems lane if you do, because every
     lane carries the same one and a divergence should be deliberate. -->

**The DSH task board is the one surface Tim reads.** Work that is only mentioned in a
conversation is invisible to him. Anything you flag, decide, or are blocked on belongs on
the board, and it belongs there **in the same turn you flag it** — not batched later, not
summarised at the end of a session.

- Read state: `http://127.0.0.1:43129/api/task-board/state`
- Write: `POST http://127.0.0.1:43129/api/task-board/action`
- **The header `Origin: http://127.0.0.1:43129` is required** — without it the route returns
  403. That is a browser-trust fence, not a credential.

**Every row you file must carry four things**, or it is a row Tim cannot act on: the source
lane, what it is in plain language, **whose it is** (Tim or a lane — this is the field he
reads most), and an evidence path with an age.

**Two rows on the same subject are worse than one.** Before filing, search the board for the
subject. If a row already exists, update or comment on it rather than creating a second one.
Four rows have been archived already for being duplicates of each other.

**Select rows on the `mode` FIELD, not on text.** `mode` is the ownership field, and a lane's queue is
`mode == '<its slug>'`. Searching titles or descriptions for the word returns a *different and larger*
population — measured on 2026-09-21 by the Cleanup lane in the same minute and on the same board: **10 by
field, 18 by one text selector, 74 by another.** Filter on the field; ignore text; a text selector both
misses rows you own and returns rows you do not.

**A closed row's DESCRIPTION can still be stale.** A row's status is not the whole record: one closed row
kept quoting `+12/-2` after that edit had landed as a much larger change, because closing it updated the
status and nothing re-read the numbers. When you act on a closed or settling row, **read its
description, not just its status.**

*(Both reported by the Cleanup lane, which added them to its own copy on 2026-09-21 with the measurement
above. Propagated by the DSH Systems lane, which owns this block, on Tim's approval of reflection item
R05 — so that twelve copies diverging became twelve copies agreeing.)*

**Dispatch.** A row runs when the board is asked to run it — there is no scheduler and
nothing is automatic. A row needs **both** a `mode` naming a real preset **and** a
`workspaceId` before it can run at all; a row missing either looks actionable and is not.
Rows bound through `handover` run in `dsh-runners` under the `board-runner` preset, which
keeps their session out of your lane's conversation. **Do not bind your own rows and do not
set a row to `danger-full-access` on your own authority** — both are decisions for the DSH
Systems lane or Tim.

### Added 2026-09-21 — rules this block did not previously carry

<!-- Propagated by the DSH Systems lane, which owns this block, on Tim's approval of reflection item R05.
     Everything below came FROM the lanes: each rule names the lane that found it and what it cost.
     Inserted rather than merged, so nothing that was already here was rewritten. -->

**Re-check that a task is still unclaimed IMMEDIATELY before dispatching a runner — and the same for a
BATCH.** A row can be worked while it sits queued: a runner was dispatched for a transaction Vault &
Notion landed in the meantime, and a batch went out to one lane that another had already completed.
**Check, then dispatch, in the same breath.**

**A runner takes mechanical TIME with STATIC evidence; a lane keeps irreversible action that needs a
JUDGEMENT.** A runner has **no conversation seed**, so it cannot detect a claim that is false only against
your own session history. **If the first thing your task needs is a judgement about which version is real,
it is lane work.**

**To contradict a lane, first establish which copy is authoritative.** Forwards an instruction only in its
**author's latest version** — a relayed instruction is a different object from the instruction.

**POST IT ONCE, AT THE OWNER, WITH THE TIME IT WAS OBSERVED — do not route a finding through other lanes.**
One file notice was relayed across four lanes and **every copy was stale, and none of the four was wrong
when it wrote.** Never re-circulate an item lifted from another session's closing notice.

**Every cross-lane figure carries four things: the COMMAND that produced it, the REVISION it ran at, the
TIME it was measured, and whether YOU READ it or RELAYED it.** *"Read by me at HH:MM"* and *"relayed from
X, not verified"* are different claims. **A truthful statement is not evidence about now** — *"stale by one
generation, not wrong when written"* is the normal case.

**A receipt id is not evidence of which run produced it — cite it WITH ITS MTIME, or do not cite it.** An
id pins an artefact, not an occasion.

**ACK WHAT YOU RECEIVE.** *"Accepted" means queued, not consumed* — and the sender cannot tell those apart
until the receiver says so. An unacked answer is indistinguishable from an unread one.

**An instrument whose answer depends on where it stands is not an instrument.** A command that parses only
from one directory reported **"0 matches" from a failed read**. Ask what a probe does when it runs
somewhere else, and whether its failure mode is a plausible number.

**A dirty file owned by another lane is a queue with no owner.** If one lane's working file blocks your
write, name **which path and which lane** — that is the whole of the finding.

**`mode` + `workspaceId` is necessary and NOT sufficient.** A row can name a lane that cannot perform its
action and still look runnable. **Routability is not capability.**

**Never hand Tim shell commands for canonical vault writes.** Four such commands were structurally
impossible for him to run — the writer ceiling is process-bound, so his shell cannot open a lease at all.
**Give him a decision, not a command.**

**A runner cannot carry a canonical write.** The `board-runner` preset forbids opening a vault
transaction, and `vault-write-contract.md:85` is explicit: *delegation does not transfer judgment or
writer authority.* **One dispatch asked a runner to run a script that took the lease anyway, and the lease
outlived the job by hours.** If a runner reaches a canonical write, it must refuse and write a proposal.

## Who to relay to, and who decides

<!-- Inserted by the DSH Systems lane on Tim's instruction, 2026-09-21, alongside §22 of
     wiki/meta/adaptive-lane-protocol.md. Additive: nothing below it was changed. You own this
     file and may edit this block — tell the DSH Systems lane if you do, because every lane
     carries the same one and a divergence should be deliberate. -->

**Ownership is what decides routing here. There is no chain of command** — see §22. When work
belongs to another lane, **relay it rather than doing it**, and say why in one line. A lane doing
another lane's job is the failure this section exists to prevent.

| when the work touches | relay to |
|---|---|
| canonical records, the writer lease, the Notion view, or the board as a surface | **Vault & Notion** |
| credentials, auth failures, secret consumption, access or risk | **AI Security** |
| removing files, sessions or workspace debris; the `closeout` and `cleanup` commands | **Cleanup** |
| the machine — GPU, local models, runtime | **hyp3r** |
| presets, plugins, lane liveness, or the messaging path | **DSH Systems** |
| paying, subscribing, applying, sending, publishing — or anything using Tim's identity | **Tim** |

**Four overlaps that have each cost real time to re-derive. They are recorded so you do not have
to rediscover them:**

1. **Placing a credential (AI Security) vs removing a file (Cleanup).** The lane that owns the
   artifact decides placement; Cleanup owns removal and keeps recovery evidence either way.
2. **The board as a surface (Vault) vs the harness that dispatches rows (DSH Systems).** Vault
   owns canonical board state; DSH Systems owns routing, presets and liveness. Neither binds the
   other's rows.
3. **A preset that stops mounting (symptom) vs a preset that is wrong (cause).** DSH Systems,
   always. Report it; never edit `.agent-presets` yourself.
4. **A vault write refused (Vault's rule) vs a tool call declined (the harness).** Different in
   kind with different owners. **Say which one you hit before reporting either** — merging them
   into "the vault blocks writes" sends the next reader to the wrong place.

**When two lanes collide and it is not Tim's decision, it goes to DSH Systems**, which resolves it
or names the owner. If it touches a canonical record, **Vault decides**. Anything involving Tim's
money, identity or public output **comes to Tim** and is not settled between lanes.

**"The coordinator" is retired as a term.** It was used repeatedly and never defined, and an
undefined word for *the authority* is how a lane once drafted a request for a ruling and addressed
it to itself. **Name the lane.**

**The board is not yet the whole record.** A row's `title`, `description` and `prompt`
**freeze after the row has run**, so a finding discovered *while working a row* currently has
to go to a receipt or a `STATUS.md` rather than back onto the row. A writable notes field is
proposed and not yet built. Until it exists, a row that produced a finding should cite the
receipt path in a follow-up row.

# Repository contract

Punchlist is a named-defect taxonomy and an evaluator protocol. Keep changes narrow, checkable, and grounded in evidence.

## Taxonomy entries

- Write every definition as a presence test beginning `Present when`.
- Add a public-standard reference and a clearly labelled non-evidentiary illustration to every entry. Evidence and real-instance provenance belong in an audit bundle, not in the reusable taxonomy.
- Keep defect ids unique, lowercase, and hyphen-separated.
- Put each defect in the category and standard that own it. Do not duplicate an entry to increase coverage.
- Do not add accuracy, prevalence, time-saved, or other numerical claims without a reproducible measurement committed alongside the claim.
- Preserve provenance. Borrow structure from other repositories when useful; do not copy their prose or taxonomy wording.

## Findings and examples

- Separate the user-visible symptom from the evidence that proves it.
- Record how the claim was verified. A screenshot, source read, rendered measurement, and interaction are different evidence.
- Declare the severity basis before assigning severity.
- Do not turn a rejected or unverified observation into a finding.

## Before committing

Run:

```sh
python scripts/validate.py
python -m unittest discover -s tests -v
```

Both commands must pass. If the validator changes, first add or update a test that fails for the behavior being added.
