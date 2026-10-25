#!/usr/bin/env bash
# Validate a standalone Markdown report from a file or stdin; no hook envelope.
set -euo pipefail
[[ $# -le 1 ]] || { echo 'Usage: check-report.sh [report.md]' >&2; exit 2; }
awk '
function error(message) { print message > "/dev/stderr"; bad=1 }
/^## / {
  section=$0
  if ($0 ~ /^## Verdict: (APPROVE|REQUEST_CHANGES|ESCALATE|INCOMPLETE)$/) {
    verdict=$3; verdict_count++
  }
  seen[$0]++
}
section == "## Gates" && /^- / {
  key=$2; sub(/:$/, "", key); value=$3
  if (key ~ /^(fmt|clippy|tests|doctests|deny)$/) {
    if (gate[key] != "") error("Duplicate gate: " key)
    gate[key]=value
    if (value == "NOT" && $4 == "RUN") gate[key]="NOT RUN"
    if (gate[key] !~ /^(PASS|FAIL|NOT RUN|N\/A)$/) error("Invalid gate status: " key)
    if (value == "N/A" && (key ~ /^(fmt|clippy|tests)$/ || NF < 4)) error("Invalid N/A: " key)
  }
}
section == "## Memory safety" && /^- / {
  key=$2; sub(/:$/, "", key)
  if (key ~ /^(memory-scope|miri|aliasing|memory-evidence|aliasing-evidence)$/) {
    if (memory_seen[key]++) error("Duplicate memory field: " key)
    memory[key]=$3
    if (key == "miri" && $3 == "NOT" && $4 == "RUN") memory[key]="NOT RUN"
    if (NF < 3) error("Empty memory field: " key)
  }
}
section == "## Concurrency" && /^- / {
  key=$2; sub(/:$/, "", key)
  if (key ~ /^(async-scope|deadlocks|cancellation|task-lifecycle|async-evidence|sync-scope|loom|synchronization|model-evidence)$/) {
    if (concurrency_seen[key]++) error("Duplicate concurrency field: " key)
    concurrency[key]=$3
    if ($3 == "NOT" && $4 == "RUN") concurrency[key]="NOT RUN"
    concurrency_words[key]=NF
    if (NF < 3) error("Empty concurrency field: " key)
  }
}
section == "## Spec" && /^- spec:/ {
  spec_count++; spec=$3
  if (spec == "NOT" && $4 == "RUN") spec="NOT RUN"
  if (spec !~ /^(PASS|FAIL|PARTIAL|NOT RUN)$/) error("Invalid spec status")
}
section == "## Spec" && /^- (missing|unrequested|contradictions): .+/ { spec_fields[$2]++ }
section == "## Findings" && /^- \[P[0-3]\] / {
  findings++
  if ($0 !~ /[^ ]+:[1-9][0-9]* - .+/) error("Finding missing file:line or explanation")
  if ($2 ~ /\[P[01]\]/) blocking=1
}
section == "## Findings" && /^No findings\.$/ { empty_findings++ }
END {
  if (verdict_count != 1) error("Exactly one valid Verdict required")
  required[1]="## Gates"; required[2]="## Spec"; required[3]="## Findings"; required[4]="## Residual risks"; required[5]="## Memory safety"
  required[6]="## Concurrency"
  for (i=1;i<=6;i++) if (seen[required[i]] != 1) error("Missing/duplicate section: " required[i])
  split("fmt clippy tests doctests deny", names, " ")
  for (i=1;i<=5;i++) {
    key=names[i]
    if (gate[key] == "") error("Missing gate: " key)
    if (verdict == "APPROVE" && gate[key] != "PASS" && gate[key] != "N/A") error("APPROVE requires completed gates: " key)
  }
  if (spec_count != 1) error("Exactly one spec status required")
  split("missing: unrequested: contradictions:", names, " ")
  for (i=1;i<=3;i++) if (spec_fields[names[i]] != 1) error("Missing/duplicate spec field: " names[i])
  if ((!findings && empty_findings != 1) || (findings && empty_findings)) error("Provide findings or No findings., not both")
  if (verdict == "APPROVE" && (spec != "PASS" || blocking)) error("APPROVE conflicts with spec or P0/P1 findings")
  split("memory-scope miri aliasing memory-evidence aliasing-evidence", names, " ")
  for (i=1;i<=5;i++) if (memory_seen[names[i]] != 1) error("Missing memory field: " names[i])
  if (memory["memory-scope"] !~ /^(REQUIRED|NONE)$/) error("Invalid memory scope")
  if (memory["miri"] !~ /^(PASS|FAIL|NOT RUN|N\/A)$/) error("Invalid Miri status")
  if (memory["aliasing"] !~ /^(PASS|FAIL|UNRESOLVED|N\/A)$/) error("Invalid aliasing status")
  if (memory["memory-scope"] == "NONE") {
    if (memory["miri"] != "N/A" || memory["aliasing"] != "N/A") error("NONE scope requires N/A memory checks")
  } else if (memory["memory-scope"] == "REQUIRED") {
    if (memory["miri"] == "N/A" || memory["aliasing"] == "N/A") error("Required memory checks cannot be N/A")
    if (memory["memory-evidence"] == "N/A" || memory["aliasing-evidence"] == "N/A") error("Required memory assessment needs evidence or explicit gaps")
    if ((memory["miri"] == "NOT RUN" || memory["aliasing"] == "UNRESOLVED") && verdict != "ESCALATE") error("Unresolved memory obligations require ESCALATE")
    if (verdict == "APPROVE" && (memory["miri"] != "PASS" || memory["aliasing"] != "PASS")) error("APPROVE requires targeted Miri and aliasing PASS")
    if ((memory["miri"] == "FAIL" || memory["aliasing"] == "FAIL") && verdict !~ /^(REQUEST_CHANGES|ESCALATE)$/) error("Memory failure blocks approval/completion")
  }
  split("async-scope deadlocks cancellation task-lifecycle async-evidence sync-scope loom synchronization model-evidence", names, " ")
  for (i=1;i<=9;i++) if (concurrency_seen[names[i]] != 1) error("Missing concurrency field: " names[i])
  if (concurrency["async-scope"] !~ /^(REQUIRED|NONE)$/) error("Invalid async scope")
  if (concurrency["sync-scope"] !~ /^(REQUIRED|NONE)$/) error("Invalid synchronization scope")
  split("deadlocks cancellation task-lifecycle", names, " ")
  applicable=0
  for (i=1;i<=3;i++) {
    key=names[i]; value=concurrency[key]
    if (value !~ /^(PASS|FAIL|NOT RUN|N\/A)$/) error("Invalid async status: " key)
    if (value == "N/A" && concurrency_words[key] < 4) error("N/A needs an applicability reason: " key)
    if (concurrency["async-scope"] == "NONE" && value != "N/A") error("NONE async scope requires N/A: " key)
    if (concurrency["async-scope"] == "REQUIRED") {
      if (value != "N/A") applicable++
      if (value == "NOT RUN" && verdict != "ESCALATE") error("Missing targeted async evidence requires ESCALATE: " key)
      if (value == "FAIL" && verdict !~ /^(REQUEST_CHANGES|ESCALATE)$/) error("Async failure blocks approval/completion: " key)
    }
  }
  if (concurrency["async-scope"] == "REQUIRED") {
    if (!applicable) error("Required async scope cannot mark all checks N/A")
    if (concurrency["async-evidence"] == "N/A") error("Required async assessment needs evidence or explicit gaps")
  }
  if (concurrency["loom"] !~ /^(PASS|FAIL|NOT RUN|N\/A)$/) error("Invalid Loom status")
  if (concurrency["synchronization"] !~ /^(PASS|FAIL|UNRESOLVED|N\/A)$/) error("Invalid synchronization status")
  if (concurrency["sync-scope"] == "NONE") {
    if (concurrency["loom"] != "N/A" || concurrency["synchronization"] != "N/A") error("NONE sync scope requires N/A checks")
  } else if (concurrency["sync-scope"] == "REQUIRED") {
    if (concurrency["loom"] == "N/A" || concurrency["synchronization"] == "N/A") error("Required synchronization checks cannot be N/A")
    if (concurrency["model-evidence"] == "N/A") error("Required synchronization assessment needs model evidence or explicit gaps")
    if ((concurrency["loom"] == "NOT RUN" || concurrency["synchronization"] == "UNRESOLVED") && verdict != "ESCALATE") error("Incomplete synchronization evidence requires ESCALATE")
    if ((concurrency["loom"] == "FAIL" || concurrency["synchronization"] == "FAIL") && verdict !~ /^(REQUEST_CHANGES|ESCALATE)$/) error("Synchronization failure blocks approval/completion")
  }
  exit bad ? 1 : 0
}' "${1:--}"
