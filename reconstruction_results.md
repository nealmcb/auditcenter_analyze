Implemented the rigorous replay:
New module: src/auditcenter_analyze/validate_targeted_draws.py. It replays the SHA-256 RNG with the round seeds for every county-wide targeted contest, combines the county manifests, and compares the reconstructed ballots to what Colorado logged.
Outputs (all written to output/reconstructed/):
targeted_missing_ballots.csv – ordered list of every draw the RNG expected but the audit log never recorded (sequence, county, imprinted_id, round, status/reason). Only contests with missing cards appear here.
targeted_extra_ballots.csv – cards the state logged for a contest that our replay never selected (set aside for later investigation, as requested).
targeted_validation_summary.json – per-contest counts of expected vs actual vs missing/extras so you can see the imbalance at a glance.
First run flagged real gaps. Sample summary:
Adams County Commissioner - District 5: expected 194, actual 119, missing 92Pueblo County Commissioner - District 2: expected 378, actual 193, missing 189Routt County Commissioner - District 1: expected 175, actual 77, missing 98State Representative - District 10: expected 106, actual 11, missing 97
