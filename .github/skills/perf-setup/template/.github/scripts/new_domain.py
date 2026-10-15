"""Add a new domain skeleton (requests/steps/flows/usecases/data, simulation, tests) to a perf repo.

  python .github/scripts/new_domain.py <repo-dir> <domain> [--path /orders] [--method GET|POST] [--dry-run]

<domain> is lowercase letters/digits (e.g. orders). Creates only new files, edits only
env/test.properties, env/prod.properties and ci/simulation-data.csv (append), and refuses to
overwrite anything. Afterwards run `./mvnw -q test` in the repo.
"""
import argparse
import re
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("domain")
    ap.add_argument("--path", help="endpoint path, default /<domain>")
    ap.add_argument("--method", choices=["GET", "POST"], default="GET")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    repo = a.repo.expanduser().resolve()
    if not re.fullmatch(r"[a-z][a-z0-9]*", a.domain):
        print("ERROR: domain must be lowercase letters/digits, starting with a letter (e.g. orders).", file=sys.stderr)
        return 1
    path = a.path or f"/{a.domain}"
    if not path.startswith("/"):
        print("ERROR: --path must start with '/'.", file=sys.stderr)
        return 1
    marker = next((repo / "src/main/kotlin").rglob("setup/UseCase.kt"), None)
    if marker is None:
        print("ERROR: not a perf repo from the template (setup/UseCase.kt not found).", file=sys.stderr)
        return 1
    base = marker.parents[1]                       # .../cz/example/perf
    pkg = re.search(r"^package\s+(\S+)\.setup", marker.read_text(encoding="utf-8"), re.M).group(1)
    pkg_dir = base.relative_to(repo / "src/main/kotlin")
    d, D = a.domain, a.domain.capitalize()
    key = f"{d}Endpoint"

    main_dir = repo / "src/main/kotlin" / pkg_dir
    test_dir = repo / "src/test/kotlin" / pkg_dir
    if a.method == "GET":
        req = f'http("{D} request")\n            .get(Paths.{key})'
    else:
        req = (f'http("{D} request")\n            .post(Paths.{key})\n'
               '            .header("Content-Type", "application/json")\n'
               '            .body(StringBody("{}"))')
    imports_extra = "import io.gatling.javaapi.core.CoreDsl.StringBody\n" if a.method == "POST" else ""

    files = {
        main_dir / f"domain/{d}/data/{D}Feeders.kt": f'''package {pkg}.domain.{d}.data

import io.gatling.javaapi.core.CoreDsl.csv
import io.gatling.javaapi.core.FeederBuilder

object {D}Feeders {{
    private const val basePath = "{d}"
    val users: FeederBuilder<String> = csv("$basePath/{d}.csv").random()
}}
''',
        main_dir / f"domain/{d}/requests/{D}Requests.kt": f'''package {pkg}.domain.{d}.requests

import {pkg}.config.Paths
{imports_extra}import io.gatling.javaapi.core.CoreDsl.exec
import io.gatling.javaapi.http.HttpDsl.http
import io.gatling.javaapi.http.HttpDsl.status

object {D}Requests {{
    fun call{D}() = exec(
        {req}
            .check(status().`is`(200))
    )
}}
''',
        main_dir / f"domain/{d}/steps/{D}Steps.kt": f'''package {pkg}.domain.{d}.steps

import {pkg}.auth.Auth
import {pkg}.domain.{d}.data.{D}Feeders
import io.gatling.javaapi.core.ChainBuilder
import io.gatling.javaapi.core.CoreDsl.feed

object {D}Steps {{
    fun with{D}Data(): ChainBuilder = feed({D}Feeders.users).exec(Auth.withTokenFromSession())
}}
''',
        main_dir / f"domain/{d}/flows/{D}Flows.kt": f'''package {pkg}.domain.{d}.flows

import {pkg}.domain.{d}.requests.{D}Requests
import {pkg}.domain.{d}.steps.{D}Steps
import io.gatling.javaapi.core.ChainBuilder
import io.gatling.javaapi.core.CoreDsl.exec

object {D}Flows {{
    fun basic{D}(): ChainBuilder =
        exec({D}Steps.with{D}Data())
            .exec({D}Requests.call{D}())
}}
''',
        main_dir / f"domain/{d}/usecases/{D}UseCases.kt": f'''package {pkg}.domain.{d}.usecases

import {pkg}.domain.{d}.flows.{D}Flows
import {pkg}.setup.UseCase

object {D}UseCases {{
    val basic{D} = UseCase("basic{D}", {D}Flows.basic{D}(), 100.0)

    val all = listOf(basic{D})
}}
''',
        main_dir / f"simulations/domain/{d}/{D}MixSimulation.kt": f'''package {pkg}.simulations.domain.{d}

import {pkg}.config.Protocols
import {pkg}.domain.{d}.usecases.{D}UseCases
import {pkg}.setup.MixBuilder
import {pkg}.setup.SimulationSetup
import io.gatling.javaapi.core.CoreDsl.scenario

class {D}MixSimulation : SimulationSetup() {{
    private val scn = scenario("{D} mix").exec(MixBuilder.fromDefaults({D}UseCases.all))

    init {{
        run(scn, Protocols.api)
    }}
}}
''',
        test_dir / f"domain/{d}/{D}UseCasesTest.kt": f'''package {pkg}.domain.{d}

import {pkg}.domain.{d}.usecases.{D}UseCases
import {pkg}.testutil.GatlingTestBootstrap
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class {D}UseCasesTest {{
    @Test
    fun `{d} use case weights sum to 100`() {{
        GatlingTestBootstrap.init()
        assertEquals(100.0, {D}UseCases.all.sumOf {{ it.defaultWeight }}, 0.0001)
    }}

    @Test
    fun `{d} use case names are unique`() {{
        GatlingTestBootstrap.init()
        val names = {D}UseCases.all.map {{ it.name }}
        assertEquals(names.size, names.toSet().size)
        assertTrue(names.isNotEmpty())
    }}
}}
''',
        repo / f"src/test/resources/{d}/{d}.csv": "token\nlocal-dummy-token-1\nlocal-dummy-token-2\n",
    }
    appends = {
        repo / "src/main/resources/env/test.properties": f"{key}={path}\n",
        repo / "src/main/resources/env/prod.properties": f"{key}={path}\n",
        repo / "ci/simulation-data.csv": f"{pkg}.simulations.domain.{d}.{D}MixSimulation,<ARTIFACTORY_PATH>/resources/{d}/**,src/test/resources/{d}/\n",
    }

    clash = [f for f in files if f.exists()]
    missing = [f for f in appends if not f.exists()]
    if clash or missing:
        for f in clash:
            print(f"ERROR: already exists: {f.relative_to(repo)}", file=sys.stderr)
        for f in missing:
            print(f"ERROR: expected file missing: {f.relative_to(repo)}", file=sys.stderr)
        return 1
    if key in appends[repo / "src/main/resources/env/test.properties"] and \
            re.search(rf"^{key}=", (repo / "src/main/resources/env/test.properties").read_text(encoding="utf-8"), re.M):
        print(f"ERROR: key {key} already in env properties.", file=sys.stderr)
        return 1

    for f in files:
        print(("would create " if a.dry_run else "created ") + str(f.relative_to(repo)))
    for f, line in appends.items():
        print(("would append to " if a.dry_run else "appended to ") + f"{f.relative_to(repo)}: {line.strip()}")
    if a.dry_run:
        return 0
    for f, content in files.items():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
    for f, line in appends.items():
        t = f.read_text(encoding="utf-8")
        f.write_text(t + ("" if t.endswith("\n") else "\n") + line, encoding="utf-8")
    print("\nNext: ./mvnw -q test (in the repo directory)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
