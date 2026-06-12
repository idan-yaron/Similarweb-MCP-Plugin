# § error-rendering, full pattern text (sw-foundation-render reference)

Seven canonical patterns. Apply consistently:

1. **Tool returned null or empty payload:** render `n/a` in the affected
   cell. NEVER fabricate. NEVER infer from training data. The cell stays
   `n/a` and gets a one-line entry in the Caveats block:
   "no data for `<tool>` on `<target>` (window=<window>, country=<country>)".

2. **Tool returned non-2xx (5xx, timeout, validation error):** retry once
   with a 2-second pause. On second failure, render
   "unavailable this run" in the affected cell, add to Caveats:
   "`<tool>` was unavailable this run; rerun to retry."

3. **Tool skipped due to capability gate (per § capability-gating):**
   render "not accessible on this plan" in the affected cell, add to
   Caveats: "`<tool>` not in your plan; this row is best-effort without it."

4. **Tool returned a structural-zero (classifier limitation, not actual zero):**
   render `n/a` in the affected cell with a footnote `[1]` linking to the
   Caveats block where the classifier limitation is explained. Apply to any
   cell where the API returns exactly `0.0` AND the corresponding metric is
   known to suffer from a classifier-rollup limitation (e.g., Paid Social
   often rolls into Display Ads in Similarweb's `get-traffic-channels-share`).
   The Caveats entry explains the rollup: "Paid Social returned `0.0%` from
   `get-traffic-channels-share`; Similarweb's classifier often rolls paid
   social into Display Ads. Treat as structural-zero, not measured-zero."

5. **Systemic auth failure.** Trigger: when the FIRST 2 required tools called
   (drawn from the PRESENT subset per sw-foundation-core § tool-surface
   presence) both return 403 with "missing the required claims" wording on
   the FIRST domain attempted. This indicates an account-level claims
   problem, not a per-domain restriction or transient error. When fewer than
   2 REQUIRED tools are present-and-accessible in the first place (absences
   and 403s counted together), this pattern's escalation fires via Pattern
   7's aggregate-insufficiency clause instead.

   **Action:**
   1. Stop the recipe immediately. Do NOT continue with subsequent required tools.
   2. Optional tools may be attempted ONCE each to detect partial access (e.g.,
      a PPC-spend tool can succeed while rank, traffic, and channels all fail).
      Cap at 1 attempt per optional tool.
   3. Render INSUFFICIENT SIGNAL verdict in the Executive read.
   4. The FIRST NEXT MOVE bullet MUST be a natural-language question that
      triggers a capability refresh, phrased as: `"Can you check which
      Similarweb tools I currently have access to and refresh the capability
      map?"` followed by one sentence explaining that the recipe could not
      proceed because the user's account appears to be missing claims for the
      required tools.
   5. The SECOND NEXT MOVE is optional and should be derived from any data
      that DID come back (e.g., if PPC spend succeeded for one domain, suggest
      extending that single-domain analysis).
   6. Caveats block lists EVERY tool that returned 403, distinguishing
      required vs optional.
   7. Sources block reflects the actual call count (only the calls that were
      actually issued before the short-circuit took effect, not the full
      pre-planned call count).

6. **Tool returned country-coverage gap (HTTP 400 client_error, OR HTTP 200 with empty data, carrying a country-coverage message per sw-foundation-core § Country-coverage gap detection):** evaluated BEFORE Pattern 2 (a 400 carrying the country-coverage message is Pattern 6, not Pattern 2). Detect once per (tool, country) pair on the FIRST domain attempted. Render `n/a` in the affected country cells. Mark country-unavailable_this_run for this tool per § capability-gating. Pivot the recipe's country to ww for subsequent calls. Add ONE consolidated Caveats line: "Country `<X>` not on this plan; rendered worldwide. Affected tools: `<comma-separated list>`."

   If 2 or more required tools report country-coverage gap for the same country in this turn, ALSO add a higher-level header-line modifier: the recipe's header line context drops the country to `worldwide` instead of the user-supplied country, and the Executive read opens with a one-sentence acknowledgment that the country requested is not on this plan ("US data is not on your plan for the websites tools; this read is worldwide; reach out to your CSM if a country-specific view matters for the decision.").

7. **Tool not exposed on this connector (planning-time absence per
   sw-foundation-core § tool-surface presence, OR a call-time client-level
   "No such tool available" / server-level "Unknown tool" error, message-gated
   per `unknown-tool-error-shape`):** evaluated BEFORE Pattern 2, exactly as
   Pattern 6 is (a client-level unknown-tool error is Pattern 7, never a
   retryable Pattern 2 failure). Render "not exposed on this connector" in
   the affected cell. Zero calls when detected at planning time; zero retries
   when detected at call time; collapse sibling failures from the same batch
   into ONE consolidated Caveats line: "Not exposed on this connector:
   `<tool-1>`, `<tool-2>`. This can be a connector tool setting in your AI
   client OR a plan module: check the connector's tool settings first; if the
   tool is enabled there and still absent, ask your Similarweb account
   contact about the module." Distinct from Pattern 3: a 403 denial means the
   tool exists and the plan lacks claims (CSM remedy); absence is NOT proof
   of a plan limitation, so the CSM line alone is the wrong remedy here. On
   platforms where the unknown-tool wording is not yet grounded (per
   `unknown-tool-error-shape-other-platforms`), call-time failures render the
   hedged wording "could not reach `<tool>` in this session" under Pattern 2
   handling with no absence claim; planning-time absence from a qualifying
   enumeration still renders the full Pattern 7 text. Aggregate insufficiency:
   when fewer than 2 of a recipe's REQUIRED tools are both present and
   accessible (absences and 403s counted together), escalate per Pattern 5
   semantics with the caveat naming BOTH causes instead of shipping a
   multi-section-dropped report.

A `## Caveats` block appears at the bottom of the recipe output if and only
if any of these fired. If no errors, no Caveats block.
