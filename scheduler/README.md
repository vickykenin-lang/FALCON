# Scheduler — FALCON Time & Recurrence Organ

Scheduler is a first-class, independently replaceable Falcon body part responsible only for **when work should start**.

It does not reason about missions and it does not execute tools. At a due time it emits a versioned scheduling signal/event into Falcon. Brain/Autonomic decide the mission lifecycle; Execution performs actions.

## Responsibilities

- one-time scheduled triggers;
- recurring schedules;
- persistent schedule definitions;
- restart recovery;
- missed-run policy;
- enable/disable/pause/resume schedules;
- next-run calculation;
- trigger history/evidence.

## Non-responsibilities

- mission reasoning;
- tool execution;
- memory implementation;
- governance decisions;
- user interface implementation.

## Replaceability rule

Cron, APScheduler, Temporal, cloud scheduler, database-backed scheduling, or a future scheduler engine may replace the implementation as long as the stable Falcon schedule contract remains satisfied.

Changing Scheduler MUST NOT require changes to Brain, Memory, Execution, Learning, Senses, Interface, or Governance.

Conceptual flow:

`Founder -> schedule contract -> Scheduler -> due trigger -> Nervous System -> Autonomic/Brain -> Execution -> verification`
