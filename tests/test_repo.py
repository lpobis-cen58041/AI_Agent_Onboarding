"""Deterministic checks of the perf-setup agent repo (no model, no network, nothing is submitted)."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".github" / "scripts"
SKILL = ROOT / ".github" / "skills" / "perf-setup"
AGENT = ROOT / ".github" / "agents" / "perf-setup.agent.md"
TEMPLATE = SKILL / "template"


def run(*args, cwd=SCRIPTS, env=None):
    import os
    e = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    e.update(env or {})
    for k in ("REDIM_API_KEY", "REDIM_REQUESTOR"):
        e.pop(k, None) if not (env and k in env) else None
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, env=e, timeout=300)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---- configuration files ----------------------------------------------------------------

@pytest.mark.parametrize("name", ["access.json", "sources.json", "tickets.json"])
def test_config_is_valid_json(name):
    assert isinstance(load(SKILL / name), dict)


def test_access_groups_have_domain_and_both_envs():
    cfg = load(SKILL / "access.json")
    for env in ("prod", "test"):
        assert cfg["groups"][env], env
        assert cfg["portals"][env].startswith("https://")
        assert cfg["api"][env].startswith("https://")
        for g in cfg["groups"][env]:
            assert re.fullmatch(r"[A-Z]+\\[A-Za-z0-9_]+", g), f"bad group name: {g}"
    assert "CSIN\\GHB_DEV_GEORGEPETE_WRITE" in cfg["groups"]["prod"]


def test_sources_reference_unique_files():
    cfg = load(SKILL / "sources.json")
    files = [p["file"] for p in cfg["extra_pages"]]
    assert len(files) == len(set(files))
    assert all(isinstance(p["id"], int) for p in cfg["extra_pages"])
    assert all(isinstance(t["root_id"], int) for t in cfg["trees"])


def test_tickets_entries_complete():
    for item in load(SKILL / "tickets.json")["required"]:
        assert item["name"] and item["keywords"] and item["how"]


def test_glossary_covers_key_terms():
    text = (SKILL / "glossary.md").read_text(encoding="utf-8")
    for term in ("RPS", "PETE", "Redim", "Feeder", "Artifactory", "ServiceNow"):
        assert term in text


# ---- agent definition -------------------------------------------------------------------

def test_agent_frontmatter():
    text = AGENT.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "missing frontmatter"
    assert re.search(r"^name: perf-setup$", m.group(1), re.M)
    assert re.search(r"^description: .+", m.group(1), re.M)


def test_agent_references_existing_scripts_and_files():
    text = AGENT.read_text(encoding="utf-8")
    for script in set(re.findall(r"`?(?:python )?([a-z_]+\.py)\b", text)):
        assert (SCRIPTS / script).exists(), f"agent mentions missing script {script}"
    for f in ("access.json", "tickets.json", "sources.json", "glossary.md"):
        if f in text:
            assert (SKILL / f).exists()


def test_agent_safety_rules_present():
    text = AGENT.read_text(encoding="utf-8")
    assert "nikdy nečítaj ani nevypisuj" in text            # never read .env
    assert "Nič si nevymýšľaj" in text
    assert "NEodosiela" in text                              # no autonomous request submission
    assert "explicitného potvrdenia" in text or "explicitnom potvrdení" in text
    assert "necommituj" in text.lower()


def test_agent_has_no_embedded_secrets():
    text = AGENT.read_text(encoding="utf-8")
    assert not re.search(r"(?i)(token|password|key)\s*=\s*[A-Za-z0-9+/_-]{16,}", text)


# ---- repository hygiene -----------------------------------------------------------------

def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("not a git checkout")
    return out.stdout.splitlines()


def test_no_secrets_or_snapshots_tracked():
    files = tracked_files()
    assert ".env" not in files
    assert not any(f.startswith(".github/skills/perf-setup/wiki/") for f in files)
    assert ".github/skills/perf-setup/manifest.json" not in files
    assert not any(f.endswith("secrets.txt") for f in files)


def test_gitignore_covers_sensitive_paths():
    text = (ROOT / ".gitignore").read_text()
    for entry in (".env", ".github/skills/perf-setup/wiki/", ".github/skills/perf-setup/manifest.json"):
        assert entry in text


def test_tracked_text_has_no_token_patterns():
    pat = re.compile(r"(gh[pousr]_[A-Za-z0-9]{30,}|BEGIN (RSA |OPENSSH )?PRIVATE KEY|Bearer [A-Za-z0-9._-]{30,})")
    for f in tracked_files():
        p = ROOT / f
        if p.suffix in {".py", ".md", ".json", ".yml", ".kt", ".xml", ".example", ".csv", ".properties"} and p.is_file():
            assert not pat.search(p.read_text(encoding="utf-8", errors="ignore")), f"possible secret in {f}"


def test_env_example_has_no_values_for_secrets():
    for line in (ROOT / ".env.example").read_text().splitlines():
        if re.match(r"(?:\w*(TOKEN|KEY|PASSWORD|COOKIE)\w*)=", line):
            assert line.split("=", 1)[1].strip() == "", f"secret value in .env.example: {line}"


# ---- scripts ----------------------------------------------------------------------------

@pytest.mark.parametrize("script", sorted(p.name for p in SCRIPTS.glob("*.py")))
def test_scripts_compile(script):
    r = run("-m", "py_compile", script)
    assert r.returncode == 0, r.stderr


def test_request_access_dry_run_sends_nothing():
    r = run("request_access.py", "--env", "test", "--account", "cen00000")
    assert r.returncode == 0, r.stderr
    assert "DRY RUN" in r.stdout
    assert r.stdout.count("AddUserToPrimWinAppAccessAdGroupRequest") == len(load(SKILL / "access.json")["groups"]["test"])
    assert '"adGroupName": "GeorgePete_Viewer"' in r.stdout


def test_request_access_rejects_unknown_group_and_missing_account():
    assert run("request_access.py", "--env", "prod", "--account", "x", "--groups", "Foo").returncode != 0
    assert run("request_access.py", "--env", "test").returncode != 0


def test_request_access_submit_requires_credentials():
    r = run("request_access.py", "--env", "test", "--account", "cen00000", "--submit")
    assert r.returncode != 0
    assert "REDIM_API_KEY" in (r.stdout + r.stderr)


def test_request_access_aborts_without_yes(tmp_path):
    r = subprocess.run([sys.executable, "request_access.py", "--env", "test", "--account", "cen00000", "--submit"],
                       cwd=SCRIPTS, input="no\n", capture_output=True, text=True,
                       env={**__import__("os").environ, "REDIM_API_KEY": "x", "REDIM_REQUESTOR": "cen11111"}, timeout=60)
    assert r.returncode != 0
    assert "Aborted" in r.stdout


# ---- sample template + scaffold ---------------------------------------------------------

def test_template_env_files_have_identical_keys():
    def keys(f):
        return {l.split("=", 1)[0] for l in (TEMPLATE / "src/main/resources/env" / f).read_text().splitlines()
                if l.strip() and not l.startswith("#")}
    assert keys("test.properties") == keys("prod.properties")


def test_template_ci_rows_point_to_existing_simulations():
    rows = (TEMPLATE / "ci/simulation-data.csv").read_text().splitlines()[1:]
    assert rows
    for row in rows:
        cls = row.split(",")[0]
        path = TEMPLATE / "src/main/kotlin" / (cls.replace(".", "/") + ".kt")
        assert path.exists(), f"{cls} has no file {path}"


def test_template_follows_domain_layout():
    base = TEMPLATE / "src/main/kotlin/cz/example/perf"
    for domain in (base / "domain").iterdir():
        for layer in ("requests", "steps", "flows", "usecases", "data"):
            assert (domain / layer).is_dir(), f"{domain.name} lacks {layer}"
        assert (base / "simulations/domain" / domain.name).is_dir()


def test_template_has_no_internal_hosts():
    pat = re.compile(r"(csin\.cz|csint\.cz|csas\.cz|csast\.|artifactory\.csin)")
    for p in TEMPLATE.rglob("*"):
        if p.is_file() and p.suffix in {".kt", ".xml", ".md", ".yml", ".csv", ".properties"}:
            assert not pat.search(p.read_text(encoding="utf-8", errors="ignore")), f"internal host in {p}"


def test_scaffold_creates_repo(tmp_path):
    r = run("scaffold.py", "perf-sample-test", "--dest", str(tmp_path), "--no-test", "--no-git")
    assert r.returncode == 0, r.stderr
    out = tmp_path / "perf-sample-test"
    assert (out / "pom.xml").exists() and (out / "mvnw").exists()
    leftovers = [p for p in out.rglob("*") if p.is_file() and p.suffix in {".xml", ".md", ".yml", ".kt"}
                 and "__PROJECT_NAME__" in p.read_text(encoding="utf-8", errors="ignore")]
    assert not leftovers
    assert run("scaffold.py", "perf-sample-test", "--dest", str(tmp_path), "--no-test", "--no-git").returncode != 0
    assert run("scaffold.py", "Bad Name", "--dest", str(tmp_path)).returncode != 0
