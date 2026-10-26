# General load-testing basics

Use this short overview only for general concepts. It is deliberately independent of any application or project.

- **Purpose:** evaluate performance and capacity under a defined, controlled workload; use findings to guide reliability and capacity improvements.
- **Plan before execution:** agree on the goal, workload profile, virtual users or request rate, duration, ramp-up, schedule, success criteria, monitoring, and responsible contacts.
- **Assess impact:** review each proposed operation for side effects and dependencies before using it in a load test. Prefer safe, repeatable, read-only behavior unless state-changing operations have been explicitly assessed and approved.
- **Protect data:** use the minimum necessary test data, restrict access, and avoid exposing credentials or personal data in source control, prompts, or reports.
- **Prepare capacity:** confirm the load generator has adequate capacity and that its traffic will not itself become the bottleneck.
- **Run safely:** test only in the agreed environment and approved window. Production testing requires explicit approval and coordination; never infer approval from a plan or a completed setup.
- **Evaluate:** compare measured latency, throughput, errors, and resource use with agreed thresholds. Record limitations and evidence; do not claim a system passed without measured results.
- **Automate deliberately:** automate repeatable checks after validating the workload, data handling, permissions, monitoring, and failure/stop conditions.

This overview does not define any application's endpoints, scenarios, data, schedules, thresholds, owners, or approval chain. Obtain those from an approved project-specific source when needed.
