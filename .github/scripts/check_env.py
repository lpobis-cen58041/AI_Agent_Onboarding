"""Read-only check of the local environment and of access to GitHub and Artifactory.

Usage: python check_env.py [--repo <git url>] [--artifactory <base url>]
Prints OK / MISSING / UNREACHABLE per item. Never prints secrets.
"""
import argparse
import os
import platform
import re
import shutil
import subprocess
import urllib.error
import urllib.request

try:  # use the OS trust store (corporate CA), like the other scripts
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

DEFAULT_REPO = "https://github.com/csas-dev/georgepete-georgepete-performance-test.git"
DEFAULT_ARTIFACTORY = "https://artifactory.csin.cz/artifactory"


def run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def report(name, status, detail=""):
    print(f"{status:<12} {name}" + (f" - {detail}" if detail else ""))


def check_java():
    if not shutil.which("java"):
        return report("Java 17+", "MISSING", "install a JDK 17 (e.g. Temurin)")
    _, out = run(["java", "-version"])
    m = re.search(r'version "(\d+)', out)
    major = int(m.group(1)) if m else 0
    report("Java 17+", "OK" if major >= 17 else "MISSING", out.splitlines()[0] if out else "")


def check_tool(name, label, hint):
    if shutil.which(name):
        _, out = run([name, "--version"])
        report(label, "OK", out.splitlines()[0] if out else "")
    else:
        report(label, "MISSING", hint)


def check_ide():
    found = [n for n in ("code", "idea") if shutil.which(n)]
    if platform.system() == "Darwin":
        for app in ("IntelliJ IDEA", "IntelliJ IDEA CE", "Visual Studio Code"):
            if any(os.path.exists(os.path.join(d, f"{app}.app")) for d in ("/Applications", os.path.expanduser("~/Applications"))):
                found.append(app)
    report("IDE (IntelliJ / VS Code)", "OK" if found else "MISSING", ", ".join(found))


def check_github(repo):
    rc, out = run(["git", "ls-remote", "--heads", repo], timeout=40)
    if rc == 0:
        report("GitHub repo access", "OK", repo)
    else:
        report("GitHub repo access", "NO ACCESS",
               "no access OR git is not logged in (credential/SSO token); also check GitHub org/team membership. " + out.splitlines()[-1][:120])


def check_http(name, url, hint=""):
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            report(name, "OK", f"HTTP {r.status}")
    except urllib.error.HTTPError as exc:
        # 401/403 still proves the host is reachable through proxy/VPN
        report(name, "REACHABLE", f"HTTP {exc.code} (login needed)")
    except Exception as exc:
        report(name, "UNREACHABLE", f"{hint} {exc}".strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--artifactory", default=DEFAULT_ARTIFACTORY)
    args = ap.parse_args()
    check_java()
    check_tool("git", "Git", "install git")
    check_ide()
    check_github(args.repo)
    check_http("Artifactory", args.artifactory.rstrip("/") + "/api/system/ping", "VPN/proxy?")
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    report("Proxy env", "SET" if proxy else "NOT SET", "set HTTPS_PROXY if your network requires it")


if __name__ == "__main__":
    main()
