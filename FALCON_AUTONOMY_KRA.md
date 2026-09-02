# FALCON Production Autonomy KRA Gates

Status: **LOCKED AS PRODUCTION AUTONOMY SCORECARD**

These KRAs are not optional features. They are the acceptance gates Falcon must pass before it is treated as a production autonomous operator for revenue-linked ownership.

## KRA-1 — Real Execution / GitHub Write

Target: Falcon can diagnose a repository issue, make the smallest safe code/config change, commit it, observe CI, diagnose failure, and repair the next blocker without hand-holding.

Pass evidence:
- authenticated governed `github.write` enabled only through explicit Founder-approved configuration;
- create/update action succeeds against a controlled repository target;
- resulting commit is verified;
- CI result is observed;
- at least one controlled failure is diagnosed and repaired automatically;
- no unrelated files are modified.

## KRA-2 — Durable Memory

Target: mission state, evidence, decisions, lessons, and resumable context survive process/runtime restarts.

Pass evidence:
- active mission state persists outside ephemeral execution;
- restart occurs;
- Falcon restores the same mission and relevant context;
- duplicate execution is prevented;
- prior evidence and lessons are available after recovery.

## KRA-3 — Autonomous Scheduler / Heartbeat

Target: Falcon continues unfinished and scheduled work without requiring the Founder to repeatedly prompt it.

Pass evidence:
- scheduled mission fires automatically;
- unfinished mission is resumed automatically;
- heartbeat detects actionable work;
- Falcon advances discover -> plan -> act -> verify -> adapt loops autonomously;
- escalation occurs only for unavailable authority, credentials, resources, or material high-risk decisions.

## KRA-4 — Browser + MCP Real-World Execution

Target: Falcon can work outside GitHub through replaceable, governed adapters.

Pass evidence:
- browser or MCP adapter is separately bounded from Brain;
- Falcon can discover/read a real external resource;
- an approved interaction can be executed;
- action and outcome are independently verified;
- secrets remain external and scoped;
- adapter failure cannot corrupt unrelated organs.

## KRA-5 — General Execution Adapter

Target: controlled command/tool execution for tasks that cannot be completed through GitHub or browser APIs alone.

Pass evidence:
- allowlisted execution operations only;
- bounded timeout/resource controls;
- stdout/stderr/result captured as evidence;
- cancellation works;
- destructive/high-risk operations remain explicitly gated;
- execution sandbox cannot silently expand its own authority.

## KRA-6 — Live Control & Observability

Target: Founder can understand what Falcon is doing, why it is doing it, what failed, and what evidence supports the outcome.

Pass evidence:
- live mission state visible;
- current plan/action/provider visible without exposing secrets;
- action/evidence/failure timeline visible;
- BLOCKED/FAILED states contain an actionable reason;
- cancellation/pause/resume state is visible;
- verified-success reporting is distinct from planned or attempted work.

## KRA-7 — Project Ownership Autonomy

Target: Falcon can accept an unfamiliar project with only a high-level Founder mission and take operational ownership without project-specific hardcoding.

Canonical acceptance prompt:

> This project is now yours. Take ownership and run it.

Pass evidence:
- discovers the target system/repository;
- infers objective and current state from available evidence;
- identifies blockers and priorities;
- creates a bounded execution plan;
- acts through governed capabilities;
- tests and verifies outcomes;
- diagnoses failures and adapts;
- continues to the next highest-value action without repeatedly asking the Founder what to do;
- escalates only genuinely unavailable authority/credential/resource/high-risk blockers;
- produces a final evidence-grounded outcome report.

## Revenue Readiness Gate

Passing the seven KRAs does **not guarantee revenue**. It establishes that Falcon is technically capable of taking accountable operational ownership of a revenue-linked mission.

A revenue mission is considered ready to assign only when:
- the business objective and measurable KPI are defined;
- required commercial data/resources are accessible;
- required real-world adapters and credentials are available;
- spending, publishing, outreach, purchasing, or other material external actions have explicit governance boundaries;
- attribution is measurable so Falcon activity can be separated from verified business outcomes.

Revenue-linked success must be measured by business evidence such as qualified leads, conversion, sales, margin, retained revenue, or another Founder-approved KPI — not by number of AI actions, commits, messages, or plans.

## Execution Priority

1. KRA-1 Real Execution / GitHub Write
2. KRA-2 Durable Memory
3. KRA-3 Autonomous Scheduler / Heartbeat
4. KRA-4 Browser + MCP
5. KRA-5 General Execution Adapter
6. KRA-6 Live Control & Observability
7. KRA-7 Project Ownership Autonomy stress test

Falcon is not to be called fully production-autonomous until all seven gates have fresh passing evidence.
