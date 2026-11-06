# Photo Organizer Requirements

## Purpose

A local-first desktop application that helps a person organize photos on a
local drive. It analyzes selected folders, proposes rename, move, and removal
actions, and shows those proposals for user review before changing any files.

## Product Principles

- The user remains in control: analysis never changes files, and execution
	requires an explicit approval step.
- Prefer reversible operations. Removal means moving a file to a recoverable
	holding area; permanent deletion must be a separate, clearly confirmed action.
- Be transparent: every suggestion explains what will change and why.
- Work locally. Photo contents and metadata are not uploaded.
- Handle errors per file and report partial success without hiding failures.

## Primary User And Workflow

The primary user has photos in one or more folders and wants help applying a
consistent organization scheme without losing control of the originals.

1. Select one or more source folders and configure an organization rule, such
	 as a date-based folder layout and filename pattern.
2. Scan the folders and inspect the discovered photos and available metadata.
3. Review suggested actions, including the proposed destination or new name,
	 the reason, and any warnings. Preview a photo when supported.
4. Select or exclude individual actions, then confirm the complete operation
	 plan.
5. Apply the approved plan and review a per-file result report. Undo completed
	 reversible actions where possible.

## User Stories

Each story is written as *As a \<role\>, I want \<goal\>, so that \<benefit\>*,
with acceptance criteria below it. Stories link to the Functional
Requirement(s) they elaborate so the two stay traceable; a story with no
FR-id yet is a candidate for a new requirement.

**To add or change a requirement:** add a new story here with the next
`US-` number, write its acceptance criteria, and either point it at an
existing `FR-#` or flag it `(new)` so a Functional Requirement gets written
for it later. Editing a story's acceptance criteria is the easy path for
refining an existing requirement without renumbering anything else.

- **US-1 — Scan without risk.** As a user with photos in a folder, I want to
	scan it read-only, so that I can see what the app found before anything
	about my files can change. *(FR-1, FR-2)*
	- Starting a scan never modifies file contents, timestamps, or location.
	- I can cancel an in-progress scan.
	- Files of unsupported types are counted and skipped, not silently
		dropped or treated as photos.
	- Scan errors for individual files are shown; they don't stop the rest of
		the scan.

- **US-2 — Trust the dates I'm shown.** As a user relying on photo dates to
	organize my library, I want to know whether a date came from the photo's
	metadata or just the file's filesystem timestamp, so that I don't treat a
	guess as a fact. *(FR-3)*
	- Each scanned file's date shows its source (metadata vs. filesystem
		fallback vs. unknown).
	- A missing or ambiguous date is surfaced for my review, never silently
		guessed or hidden.

- **US-3 — Understand every suggestion.** As a user reviewing proposed
	changes, I want each suggested rename/move to explain why it was proposed,
	so that I can decide whether to trust it. *(FR-4)*
	- Every suggestion shows its proposed destination/name and a plain-language
		reason.
	- Uncertainty (e.g., fallback date used) or a conflict is shown on the
		suggestion itself, not hidden until after approval.

- **US-4 — Review before anything happens.** As a user about to let the app
	touch my files, I want to preview, compare, and selectively exclude
	proposed actions, so that I stay in control of exactly what runs.
	*(FR-5)*
	- I can preview a supported image from the review list.
	- I can see current path and proposed path side by side.
	- I can include or exclude each action independently.
	- Warnings are visible before I approve, not just in the result report.

- **US-5 — Nothing moves without my say.** As a user, I want to be certain no
	file changes happen until I explicitly approve the plan, so that I never
	lose control of my originals. *(FR-6)*
	- No rename, move, or removal is attempted before an explicit approval
		action.
	- The set of actions executed exactly matches what I approved — nothing
		added or dropped afterward.

- **US-6 — Never lose a file to a silent overwrite.** As a user, I want the
	app to catch destination collisions and stale source files before it acts,
	so that I never silently lose a photo to an overwrite. *(FR-7)*
	- A destination collision (two suggestions targeting the same path, or an
		existing file already there) is flagged before I can approve it.
	- A source file that changed or disappeared after the scan is skipped and
		reported, not forced through.

- **US-7 — Apply changes and get a straight answer per file.** As a user
	who approved a plan, I want each rename/move attempted and reported
	individually, so that one bad file doesn't hide the outcome of the rest.
	*(FR-8)*
	- Every approved, included action is attempted.
	- Each action's outcome (succeeded/skipped/failed) is reported
		individually, with a reason for anything other than success.

- **US-8 — Remove photos without fear of losing them for good.** As a user
	cleaning up a library, I want "remove" to be recoverable, so that a
	mistake doesn't mean a permanently deleted photo. *(FR-9)*
	- Removing a photo moves it to a recoverable holding area, never straight
		to permanent deletion.
	- Permanent deletion, if offered at all, is a distinct, explicitly
		confirmed action.

- **US-9 — Undo what I didn't mean to do.** As a user, I want to see my
	past operations and undo the reversible ones, so that mistakes are
	recoverable, not permanent. *(FR-10)*
	- I can view a history of past operations and their outcomes.
	- I can undo a completed rename, move, or removal when the current
		filesystem state still allows it.
	- When an action can't be undone, the app tells me why instead of failing
		silently.

- **US-10 — Keep my data on my machine.** As a privacy-conscious user, I
	want my photos, metadata, and history to stay local, so that nothing
	about my library leaves my device. *(FR-11)*
	- Settings and operation history are stored locally.
	- The app functions with no network access and never transmits photo
		data or metadata.

- **US-11 — Pick up where an interrupted run left off.** As a user whose
	apply step was interrupted (crash, power loss, forced close), I want to
	see exactly what state each in-progress action was left in in before I
	retry or undo anything, so that I don't double-apply or lose track of a
	half-finished batch. *(new — see Safety And Data Integrity Requirements)*
	- On the next launch, any action left `running` is shown with a
		reconciled status based on actual source/destination state.
	- The app does not automatically retry an ambiguous interrupted action.

- **US-12 — See the full filename on hover.** As a user reviewing a table
	of long or truncated filenames/paths, I want hovering over a cell to show
	its full text, so that I don't have to resize columns just to read one
	entry. *(FR-5)*
	- Hovering any truncated cell in the review table (current path,
		proposed path, reason, warnings) shows the full text in a tooltip.

- **US-13 — Resize review table columns.** As a user comparing current vs.
	proposed paths, I want to drag column borders to resize them, so that I
	can see more of the columns that matter to me. *(FR-5)*
	- Every column in the review table can be manually resized by dragging
		its header border.
	- Resized widths persist only for the current session; persisting them
		across restarts is deferred until settings storage (FR-11) exists.

- **US-14 — Configure the filename/folder pattern.** As a user who doesn't
	want the fixed year/month folder layout, I want to edit the destination
	folder and filename pattern myself, so that the app organizes photos the
	way I actually want. *(FR-4; resolves architecture.md's "Default and
	custom organization rules" open decision — Decided: yes, user-editable
	via placeholders.)*
	- A pattern is editable in the UI before scanning, using placeholders
		`{year}`, `{month}`, `{day}`, `{name}`, `{ext}`, `{seq}` (see US-15),
		and `{yy}`, `{hour}`, `{minute}`, `{second}` (see US-16).
	- An empty or invalid pattern (missing placeholders, unusable path
		characters) is rejected with a clear message before scanning runs.
	- A sensible default (today's `{year}/{month}/{year}-{month}-{day}_{name}{ext}`
		layout) is pre-filled, so this is additive, not a breaking change.
	- Pattern changes take effect on the next scan/suggestion pass, not
		retroactively on an already-reviewed plan.
	- Hovering the pattern field (or its label) shows a legend of every
		available placeholder and what it means.

- **US-15 — Number same-day photos with a sequence.** As a user organizing
	a burst of photos or files that otherwise wouldn't sort uniquely, I want
	a sequence-number placeholder in the pattern, so that same-day photos get
	distinct, predictably ordered filenames. *(FR-4, extends US-14.)*
	- The pattern can include `{seq}`, a 4-digit zero-padded number.
	- `{seq}` resets to `0001` for the first file on a given capture date and
		increments for each subsequent file on that same date; it does not
		reset per destination folder or run continuously across the whole
		batch.
	- A pattern must include `{name}`, `{seq}`, or the full time-of-day
		(`{hour}` + `{minute}` + `{second}`, see US-16) — otherwise it's
		rejected, since there'd be nothing to distinguish files sharing a date.
	- Files with no usable capture date still go to the fixed `unknown_date`
		folder (US-14's existing fallback) and are not numbered by this
		placeholder.

- **US-16 — Two-digit years and time-of-day in the pattern.** As a user who
	wants shorter folder names or finer-grained organization than "one
	folder per day," I want a two-digit year and the capture time (hour,
	minute, second) available as placeholders, so that I can build patterns
	like `23/07/14-05-09_IMG.jpg` instead of always writing out the full
	year and date. *(FR-4, extends US-14.)*
	- `{yy}` is the 2-digit year (e.g. `23` for 2023).
	- `{hour}`, `{minute}`, `{second}` are each 2-digit, 24-hour-clock
		components of the capture time.
	- A pattern using all three of `{hour}`, `{minute}`, `{second}` together
		is considered specific enough on its own and doesn't also require
		`{name}` or `{seq}` (see US-15's requirement); any two files that
		still collide because they share the same second are handled per
		US-17, not rejected at validation time.

- **US-17 — Never block on a collision this app itself can resolve.** As a
	user whose pattern isn't fine-grained enough to tell two files in the
	same scan apart (most often same-second photos organized by time of day
	alone, US-16), I want the app to number them automatically instead of
	stopping me, so that a coarse pattern doesn't turn into manual
	busywork for every burst of photos. *(FR-4, FR-7.)*
	- When two or more files in the same scan would move to the same
		destination, the app appends an unpadded `_2`, `_3`, ... to the
		second and later files' names to make each destination unique.
		(This numbering is independent of the zero-padded `{seq}`
		placeholder from US-15, which the user places deliberately.)
	- This automatic renumbering is visible in that row's warnings — it is
		automatic, not silent.
	- It never applies across runs: a destination that already exists on
		disk from a previous run (or an unrelated file) is still a blocking
		collision the user must resolve themselves (FR-7) — automatic
		numbering only ever disambiguates files within the current batch.

## Scope

### MVP

- Select local folders and scan supported image files without modifying them.
- Read basic filesystem information and available capture-date metadata. Fall
	back to filesystem timestamps only when clearly identified as a fallback.
- Generate configurable, rule-based rename and move suggestions.
- Present a reviewable list with thumbnail/preview where supported, old path,
	proposed path, reason, warnings, and selection controls.
- Detect name collisions, unreadable files, missing metadata, and files changed
	since the scan; prevent unsafe actions from running silently.
- Apply only the approved actions and show success, skip, and failure results.
- Provide a recoverable removal workflow and an operation history sufficient
	to undo supported rename, move, and removal actions.
- Persist user preferences and operation history locally.

### Out Of Scope For MVP

- Cloud sync, uploads, accounts, or shared libraries.
- Editing image pixels or changing embedded metadata.
- Automatic execution without review and approval.
- AI-generated classifications or facial recognition.
- Guaranteed undo after a file is externally changed, moved, or removed.

## Functional Requirements

- **FR-1 Scan:** The user can choose source folders and start, cancel, and
	repeat a read-only scan. The app reports progress and scan errors.
- **FR-2 File support:** Supported formats are listed in the UI and docs. Other
	files are skipped and counted rather than treated as photos. The initial
	format list is a product decision to confirm before implementation.
- **FR-3 Metadata:** The app uses available capture-date metadata when
	generating date-based suggestions and identifies the source of each date.
	Missing or ambiguous dates are surfaced for review, not guessed silently.
- **FR-4 Suggestions:** The app proposes new names and destinations according
	to user-selected rules. Each suggestion includes its rationale and any
	uncertainty or conflict.
- **FR-5 Review:** The user can preview a supported image, compare its current
	and proposed paths, include or exclude each action, and inspect warnings
	before approval.
- **FR-6 Approval gate:** No file-changing operation may run until the user
	approves the displayed plan. The approved plan is the exact set of actions
	the app attempts.
- **FR-7 Conflict handling:** The app never silently overwrites a destination.
	It detects collisions and stale source files before execution and asks the
	user to revise or skip affected actions.
- **FR-8 Rename and move:** The app renames and moves approved files on local
	storage. It records each result and handles failures without discarding the
	rest of the report.
- **FR-9 Removal:** “Remove” moves the approved file into a recoverable
	application-managed holding area. Permanent deletion is not part of the MVP.
- **FR-10 Undo and history:** The user can inspect prior operations and undo
	reversible actions when the original and destination state still permit it.
	The app explains when an action cannot be undone.
- **FR-11 Local state:** Settings and operation history remain on the device.
	The app does not transmit photo data or metadata.

## Safety And Data Integrity Requirements

- A scan and suggestion pass must not modify source files.
- Before applying each action, verify that the source still exists and that
	the destination is still available; skip and report changed or conflicting
	files rather than overwriting them.
- Never follow directory symlinks by default. The behavior for file symlinks
	must be explicit and consistent across supported platforms.
- Keep an operation journal with enough information to report partial
	completion and attempt undo; do not claim multi-file operations are atomic.
- Preserve file contents and embedded metadata during moves and renames.
- Handle interrupted execution so the next launch can identify incomplete work
	and show its status before retrying or undoing anything.

## Quality Requirements

- **Usability:** A first-time user can scan, review, and apply a small folder
	without needing to understand filesystem internals.
- **Performance:** Scanning and thumbnail generation provide progress and do
	not block the interface. Establish a representative library-size target
	before implementation.
- **Reliability:** One inaccessible or invalid file does not stop unrelated
	approved actions from being reported or processed.
- **Privacy:** All processing and persistent state are local by default.
- **Accessibility:** Core workflows are keyboard operable and controls have
	accessible names; preview is not the only way to distinguish files.

## MVP Acceptance Checks

- Scanning a folder leaves its files and folder structure unchanged.
- A user can exclude one suggestion, approve the rest, and verify that only
	approved actions were attempted.
- A destination collision is shown before approval and never overwrites a file.
- A source changed or removed after review is skipped with a clear result.
- Removing a photo places it in the recoverable holding area; undo restores it
	when the original location is available.
- An interrupted or partially failed batch leaves a readable history of each
	action and its status.
- The app can run with network access unavailable and does not upload data.

## Open Decisions

Tracked in one place to avoid drift: see architecture.md → Open Decisions for
the current status (decided vs. still open) of operating system/packaging,
image format support, default/custom organization rules, holding-area
retention, caching limits, library size/minimum machine, and duplicate
detection.
