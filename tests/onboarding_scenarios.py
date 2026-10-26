"""Finite decision-path coverage, not exhaustive natural-language paraphrases."""
from itertools import product
import re

AUTOMATIC_PREFIX = (
    r"(?:prefix|automatically|"
    r"(?:form|SAS).{0,80}(?:adds?|supplies|prepends?).{0,60}(?:application|name)|"
    r"(?:application|name).{0,60}(?:added|supplied|prepended))"
)

# These services are addressed later, not while selecting a GitHub contributor role.
CONTRIBUTOR_SCOPE = [
    r"\bART_[A-Z0-9_]+", r"\bGeorgePete_Viewer\b",
    r"\bAPIMAN_DEVELOPER\b", r"\bAlfred_[A-Z0-9_]+",
    r"\bGHB_[A-Z0-9_]+_ADM\b",
    r"\bI (?:have )?verified (?:these|your) permissions\b",
]


def build_scenarios():
    scenarios = []
    # A provisioned corporate repository requires SAS, so exclude repo-without-SAS.
    resources = ("repo-exists", "sas-only", "no-sas")
    for situation, resource, permissions in product(
        ("joining", "starting"), resources, ("granted", "missing", "pending")
    ):
        # Missing-resource paths must not contradict the known GEORGEPETE example.
        app = "GEORGEPETE" if resource == "repo-exists" else "ONBOARDING_DEMO"
        repository = ("https://github.com/csas-dev/georgepete-georgepete-performance-test"
                      if resource == "repo-exists" else
                      "https://github.com/csas-dev/onboarding-demo-pete-automation")
        write_group = f"CSIN\\GHB_DEV_{app}_WRITE"
        mapping = (f"The team confirmed the exact contributor group is {write_group}. "
                   "This is a synthetic test fixture, not a claim of real provisioning. ")
        turns = [
            {
                "prompt": "I'm new to PERF testing. Guide me through onboarding, one step at a time. "
                          "This is a guided conversation, not a request to execute commands or submit forms.",
                "must": [r"(join|existing)", r"(new|scratch|start)"],
                "must_not": [r"APIMAN_DEVELOPER", r"ART_"],
            },
            {
                "prompt": ("I'm joining an existing project." if situation == "joining" else
                           "I'm starting a new load-testing project from scratch."),
                "must": [r"(SAS|repositor|application)"],
            },
        ]
        if resource == "no-sas":
            turns += [
                {
                    "prompt": "The application has no SAS yet and there is no project repository. "
                              "What must be arranged before a corporate repository request?",
                    "must": [r"SAS", r"(ServiceNow|document|procedure)"],
                    "must_not": [r"\bSAS\s+is\s+(ready|created)\b"],
                },
                {
                    "prompt": "The SAS request is now submitted and awaiting approval. "
                              "What can we do while waiting?",
                    "must": [r"(pending|wait|approv)", r"(local|prepar|learn|sample)"],
                    "must_not": [r"(SAS|project|infrastructure) is (ready|complete)"],
                },
                {
                    "prompt": f"The team has now confirmed SAS_{app} exists in this test scenario. "
                              "There is still no test repository. Where do I request it and "
                              "how should I name it?",
                    "must": [r"ServiceNow", AUTOMATIC_PREFIX, r"SAS"],
                },
            ]
        elif resource == "sas-only":
            turns.append({
                "prompt": f"The application already has SAS_{app} in this synthetic test scenario, "
                          "but the test repository does not exist. "
                          "Where do I request it and how do I name it?",
                "must": [r"ServiceNow", AUTOMATIC_PREFIX, r"pete-automation"],
            })
        else:
            turns.append({
                "prompt": "Our team confirmed SAS_GEORGEPETE maps to "
                          "https://github.com/csas-dev/georgepete-georgepete-performance-test. "
                          "The project repository already exists. I will contribute tests.",
                "must": [re.escape(write_group)],
                "max_words": 160,
                "must_not": CONTRIBUTOR_SCOPE + [
                    r"(create|request|provision) (a |another |the new )?(new |replacement )?repository",
                ],
            })
        if resource != "repo-exists":
            turns.append({
                "prompt": f"In this test scenario, repository provisioning is complete: {repository} "
                          f"under SAS_{app}. " + mapping +
                          "I will contribute tests. What permission applies?",
                "must": [re.escape(write_group)],
                "max_words": 160,
                "must_not": CONTRIBUTOR_SCOPE,
            })
        permission_turns = {
            "granted": {
                "prompt": "I already have the required project GitHub write permission; "
                          "the existing repository and artifact repository are available to me. "
                          "The project's APIMAN application and key are already configured. "
                          "Let's continue with local preparation without running commands.",
                "must": [r"(local|Java|Git|IDE|clon)"],
                "must_not": [r"(request|apply for) .{0,25}(GitHub|write) permission"],
            },
            "missing": {
                "prompt": "I do not have the project GitHub write permission. "
                          "Which exact group should I personally request and where?",
                "must": [re.escape(write_group), r"REDiM"],
                "max_words": 160,
                "must_not": CONTRIBUTOR_SCOPE,
            },
            "pending": {
                "prompt": f"My REDiM request for {write_group} is already pending. "
                          "Can we prepare locally while waiting, without running commands?",
                "must": [r"(pending|wait|approv)", r"(local|prepar|learn|sample)"],
                "must_not": [r"(submit|file|create) (another|a new) request"],
            },
        }
        turns.append(permission_turns[permissions])
        scenarios.append({
            "id": f"onboarding-{situation}-{resource}-{permissions}",
            "max_questions": 1,
            "max_words": 240,
            "forbidden_commands": ["gh repo create"],
            "must_not": [
                r"(?:which|choose|select).{0,35}environment",
                r"(?:TEST or PROD|PROD or TEST)\s*\?",
                r"(?:paste|send|share|provide).{0,25}(?:API[- ]?key|token|password)\b",
                r"(?:I have|I've|I successfully) (?:submitted|created your|verified your permissions)",
            ],
            "turns": turns,
        })
    return scenarios
