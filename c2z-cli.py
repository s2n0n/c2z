#!/usr/bin/env python3
# c2z-cli

import click
import subprocess
import yaml
import sys
from tabulate import tabulate


@click.group()
def cli():
    """c2z CLI - Kubernetes 기반 침투 테스트 환경 관리"""
    pass


@cli.command()
def list():
    """사용 가능한 시나리오 목록 표시"""
    scenarios = [
        ["web-vuln", "Web Application 취약점", "초급", "✅ 사용 가능"],
        ["container-escape", "Container Escape", "중급", "✅ 사용 가능"],
        ["network-attack", "Network Attack", "중급", "✅ 사용 가능"],
        ["api-security", "API Security", "중급", "🚧 개발 중"],
    ]

    headers = ["ID", "시나리오", "난이도", "상태"]
    print(tabulate(scenarios, headers=headers, tablefmt="grid"))


@cli.command()
@click.argument('scenario_id')
def deploy(scenario_id):
    """시나리오 배포"""
    click.echo(f"🚀 시나리오 배포 중: {scenario_id}")

    # Checking if scenario exists in charts (basic validation)
    # Ideally should check logic availability, but for MVP assuming 'c2z' chart covers all
    # The plan says: helm upgrade --install scenario-X c2z/scenario-X ...
    # BUT, the structure created in charts/c2z seems to be a SINGLE chart "c2z" with sub-templates if I look at my previous steps.
    # Wait, the plan section 3.2.2 shows:
    # charts/c2z/templates/scenarios/web-vuln/
    # The manifests I created are inside the templates folder of a SINGLE chart 'c2z'.
    # HOWEVER, the CLI command in the plan says: `helm upgrade ... c2z/scenario-{id} ...`
    # This implies there are SEPARATE charts for each scenario, OR the `c2z` chart is a repository name and `scenario-{id}` is the chart name.
    # In 2.4.2 it says "Helm Repo: pentestlab ... install pentestlab/pentestlab".
    #
    # Let's re-read the Plan 3.2.1:
    # `helm install c2z c2z/c2z` (Installs EVERYTHING?? or just base?)
    #
    # Plan 3.2.3 (CLI):
    # `helm upgrade --install scenario-{id} c2z/scenario-{id}`
    # This strongly suggests each scenario is its OWN chart.
    #
    # BUT I implemented the manifests as templates inside ONE `c2z` chart in the previous step (Step 35-61).
    # `charts/c2z/templates/scenarios/web-vuln/...`
    # If I run `helm install c2z charts/c2z`, it will install ALL templates in that folder unless conditional logic is used.
    #
    # I see `values.yaml` has:
    # scenarios:
    #   webVuln:
    #     enabled: true
    #
    # So the 'c2z' chart is a Monolith chart that installs everything based on flags.
    #
    # IF the CLI uses `c2z/scenario-{id}`, then my current structure (Monolith) conflicts with the CLI command logic in the plan.
    # OR the CLI command in the plan describes a different architecture (Micro-charts) than what I partially implemented or inferred (Monolith).
    #
    # Let's look at `values.yaml` I created:
    # scenarios:
    #   webVuln: {enabled: true}
    #
    # If I deploy the 'c2z' chart, it deploys webVuln by default.
    #
    # If the user wants `c2z-cli deploy web-vuln` to ONLY deploy web-vuln,
    # with a Monolith chart, the command should be:
    # `helm install c2z charts/c2z --set scenarios.webVuln.enabled=true --set scenarios.other.enabled=false ...`
    #
    # But the plan CLI code specifically says `c2z/scenario-{id}`.
    #
    # CONTRADICTION CHECK:
    # Plan 3.2.2 "Helm Chart 구조":
    # c2z/
    #   templates/
    #     scenarios/
    #       web-vuln/
    #       container-escape/
    # This textual tree structure implies a SINGLE chart named `c2z`.
    #
    # Plan 3.2.3 "CLI":
    # `helm upgrade ... c2z/scenario-{id}`
    # This implies multiple charts.
    #
    # Resolution:
    # The file structure in 3.2.2 (Monolith) is likely the "Source of Truth" for the chart structure I built.
    # The CLI code in 3.2.3 might be inconsistent or assumes a repo structure where subcharts are packaged separately?
    #
    # Given I ALREADY built the Monolith structure in `charts/c2z`, I should adapt the CLI to work with THIS structure.
    # The CLI should install the ONE chart but maybe with flags to enable/disable specific scenarios?
    # OR, maybe the intention is that `c2z-cli deploy web-vuln` installs the global stack?
    #
    # Wait, the CLI has `deploy(scenario_id)`.
    # If I deploy `web-vuln`, I probably shouldn't deploy `container-escape` at the same time if they are heavy.
    #
    # I will modify the CLI code to adapt to the Monolith chart structure.
    # Instead of `helm install ... c2z/scenario-{id}`, I will use:
    # `helm upgrade --install scenario-{id} ./charts/c2z --set scenarios.webVuln.enabled=true --set global.enabled=...`?
    #
    # Actually, looking at values.yaml again:
    # `scenarios.webVuln.enabled: true`
    #
    # To support granular deployment with the Monolith chart:
    # `c2z-cli deploy web-vuln`:
    #   -> helm install scenario-web-vuln ./charts/c2z --set scenarios.webVuln.enabled=true --set scenarios.containerEscape.enabled=false ...
    #
    # However, `install.sh` ALREADY installed `c2z` release into `c2z-system` namespace.
    # `helm install c2z c2z/c2z --namespace c2z-system`
    #
    # If `c2z` is already installed, then `web-vuln` is likely already running if enabled=true.
    #
    # Perhaps the `c2z` chart is the "Infrastructure" and Scenarios are separate?
    # But 3.2.2 puts `scenarios/` INSIDE `c2z/templates/`.
    # So `c2z` chart contains EVERYTHING.
    #
    # Implication: `install.sh` deploys EVERYTHING by default (since enabled=true in values).
    # Then `c2z-cli deploy` might be redundant or just a way to "enable" a scenario that was disabled?
    #
    # Let's look at `install.sh` again. It runs `start c2z`.
    # If I assume the user just wants the CLI to *work* with what I built:
    # I will implement the CLI to map `web-vuln` to the relevant Helm values or just assume the plan's CLI command was hypothetical and fix it to point to the local chart if needed.
    #
    # BUT, the plan's CLI assumes `c2z/scenario-{id}` exists in a repo.
    # If I want to stick to the plan's *intent* of modularity, maybe I should have created separate charts?
    # But 3.2.2 structure is very clear about being one folder.
    #
    # Compromise:
    # I will stick to the Monolith chart.
    # I will modify the CLI `deploy` command to:
    # 1. Check if we are using local chart or repo.
    # 2. If Monolith, maybe `c2z-cli deploy` is just "Ensure it's enabled"?
    #
    # Actually, `namespaces.yaml` creates `scenario-web-vuln` namespace.
    # The CLI command installs into `--namespace scenario-{id}`.
    #
    # If `c2z` chart creates namespaces, and we install `c2z` chart multiple times (once for infra, once for scenario?), that will conflict (Cluster-wide resources like Namespaces/ClusterRoles).
    #
    # Okay, this is a design flaw in the plan vs my implementation interpretation.
    # Plan says:
    # `deploy_c2z` in `install.sh` -> installs `c2z` chart.
    # `c2z-cli deploy` -> installs `scenario-{id}` chart.
    #
    # This strongly suggests **Scenarios should be separate charts**.
    #
    # But 3.2.2 shows them in `templates/scenarios/...`.
    #
    # If they are in templates, they are part of the `c2z` chart.
    #
    # Maybe the `c2z` chart is ONLY for infrastructure (Monitoring, Kali)?
    # And scenarios are separate?
    #
    # Let's check `values.yaml` in plan again.
    # It has `scenarios: webVuln: enabled: true`.
    # This confirms Monolith.
    #
    # If it is a Monolith, `install.sh` deploys everything.
    # So `c2z-cli deploy web-vuln` might just be a no-op or "Check if running"?
    #
    # OR, maybe I should implement the CLI to just print "Scenario already deployed as part of c2z stack"?
    #
    # Let's assume the user wants to *toggle* scenarios.
    # `c2z-cli deploy web-vuln` -> `helm upgrade c2z ./charts/c2z --set scenarios.webVuln.enabled=true`
    # `c2z-cli delete web-vuln` -> `helm upgrade c2z ./charts/c2z --set scenarios.webVuln.enabled=false`
    #
    # This makes sense for a Monolith chart.
    #
    # However, I need to look at the `deploy` command in provided code strictly.
    # It does: `helm upgrade --install scenario-web-vuln ... --namespace scenario-web-vuln`.
    # It creates a NEW release named `scenario-web-vuln`.
    #
    # If I use the Monolith chart for this, it will try to create ALREADY EXISTING namespaces/resources if they are defined in the monolithic chart.
    #
    # To fix this properly:
    # 1.  I should wrap the templates in `if` blocks in the chart. (I haven't done that yet! I just pasted the yaml).
    # 2.  I need to start using those `enabled` values in the templates.
    #
    # Action:
    # I need to update the templates I created to wrap them in `{{ if .Values.scenarios.webVuln.enabled }}` etc.
    # AND I need to update the CLI to manage the MAIN release (`c2z`) instead of installing separate releases.
    #
    # OR
    #
    # I can try to split the chart. But 3.2.2 structure is monolithic.
    #
    # I will proceed with:
    # 1.  **Refactor Templates**: Wrap scenario resources in `{{ if ... }}` blocks.
    # 2.  **Refactor CLI**: Change `deploy` to update the `c2z` release values instead of installing a new release.
    #
    # Wait, if I change the CLI significantly, I deviate from the plan code.
    # The Plan Code for CLI is:
    # ```python
    #     cmd = [
    #         "helm", "upgrade", "--install",
    #         f"scenario-{scenario_id}",
    #         f"c2z/scenario-{scenario_id}", ...
    # ```
    #
    # If I follow this code strictly, it will fail because `c2z/scenario-web-vuln` chart doesn't exist.
    #
    # I will modify the CLI to match the Architecture I built (which follows 3.2.2).
    # The CLI will:
    # - `deploy`: Enable the scenario in the `c2z` release.
    # - `delete`: Disable the scenario in the `c2z` release.
    #
    # This seems like the most robust path that respects the "Monolithic Chart" structure of 3.2.2.
    #
    # NOTE: I need to handle `helm upgrade` arguments carefully to preserve other values. `helm get values` + merge? Or just `--set`?
    # `helm upgrade --reuse-values --set scenarios.webVuln.enabled=true` is the standard way.
    #
    # Let's write the CLI with this logic.

    # Helm Chart path:
    CHART_PATH = "./charts/c2z"  # Assuming running continuously from root

    cmd = [
        "helm", "upgrade", "c2z", CHART_PATH,
        "--namespace", "c2z-system",
        "--reuse-values",
        "--set", f"scenarios.{to_camel_case(scenario_id)}.enabled=true",
        "--wait"
    ]

    # Need a helper to convert 'web-vuln' to 'webVuln'.

    # ... Wait. `install.sh` deploys to `c2z-system`.
    # The plan's CLI command deployed to `scenario-{id}` namespace.
    #
    # If I deploy via `c2z` release, everything goes to `c2z-system`?
    # No, the templates have `namespace: scenario-web-vuln` HARDCODED or templated?
    # My templates have `namespace: scenario-web-vuln` HARDCODED.
    # So even if Helm release is in `c2z-system`, the resources will go to `scenario-web-vuln`.
    # This works.

    # So, Plan change for CLI:
    # Instead of installing new releases, we update the main release 'c2z'.
    #
    # Refactoring the templates is PRE-REQUISITE.
    # I will do that in the NEXT step or THIS step.
    #
    # I will write the CLI first, assuming I will fix templates right after.

    # Helper function for camelCase
    def to_camel_case(text):
        if text == 'web-vuln': return 'webVuln'
        if text == 'container-escape': return 'containerEscape'
        if text == 'network-attack': return 'networkAttack'
        return text

    # But wait, looking at `c2z-cli` code in plan.
    # It has specific `deploy` logic.
    # I should try to preserve the user experience.

    # Updated plan:
    # 1. Write `c2z-cli` (Modified `deploy`/`delete` logic).
    # 2. Modify `templates` to add `{{ if .Values... }}`.

    # Let's write `c2z-cli` now.

    # Converting plan's `deploy` to:
    # helm upgrade c2z ./charts/c2z -n c2z-system --reuse-values --set scenarios.{id}.enabled=true

    # Converting plan's `delete` to:
    # helm upgrade c2z ./charts/c2z -n c2z-system --reuse-values --set scenarios.{id}.enabled=false

    try:
        if scenario_id == 'web-vuln':
            key = 'scenarios.webVuln.enabled'
        elif scenario_id == 'container-escape':
            key = 'scenarios.containerEscape.enabled'
        elif scenario_id == 'network-attack':
            key = 'scenarios.networkAttack.enabled'
        else:
            click.echo("Unknown scenario")
            return

        cmd = [
            "helm", "upgrade", "c2z", "./charts/c2z",
            "--namespace", "c2z-system",
            "--reuse-values",
            "--set", f"{key}=true",
            "--wait"
        ]

        subprocess.run(cmd, check=True)
        click.echo(f"✅ 시나리오 배포 완료: {scenario_id}")
        get_access_info(scenario_id)

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ 배포 실패: {e}", err=True)

    # ... similar for delete ...

    pass


# I will write the file with `tabulate` dependency usage as in plan.
import click
import subprocess
import yaml
from tabulate import tabulate
import os


def to_config_key(scenario_id):
    mapping = {
        'web-vuln': 'webVuln',
        'container-escape': 'containerEscape',
        'network-attack': 'networkAttack'
    }
    return mapping.get(scenario_id)


@click.group()
def cli():
    """c2z CLI - Kubernetes 기반 침투 테스트 환경 관리"""
    pass


@cli.command()
def list():
    """사용 가능한 시나리오 목록 표시"""
    scenarios = [
        ["web-vuln", "Web Application 취약점", "초급", "✅ 사용 가능"],
        ["container-escape", "Container Escape", "중급", "✅ 사용 가능"],
        ["network-attack", "Network Attack", "중급", "✅ 사용 가능"],
        ["api-security", "API Security", "중급", "🚧 개발 중"],
    ]
    headers = ["ID", "시나리오", "난이도", "상태"]
    print(tabulate(scenarios, headers=headers, tablefmt="grid"))


@cli.command()
@click.argument('scenario_id')
def deploy(scenario_id):
    """시나리오 배포 (Enables scenario in c2z stack)"""
    key = to_config_key(scenario_id)
    if not key:
        click.echo(f"❌ 알 수 없는 시나리오 ID: {scenario_id}", err=True)
        return

    click.echo(f"🚀 시나리오 배포 중: {scenario_id}")

    # Assuming chart is at ./charts/c2z
    chart_path = "./charts/c2z"
    if not os.path.isdir(chart_path):
        # Fallback to repo if not local? For now assume local as per dev environment
        click.echo("⚠️  Local chart not found, utilizing helm repo logic (not implemented fully for dev)")

    cmd = [
        "helm", "upgrade", "c2z", chart_path,
        "--namespace", "c2z-system",
        "--reuse-values",
        "--set", f"scenarios.{key}.enabled=true",
        "--wait"
    ]

    try:
        subprocess.run(cmd, check=True)
        click.echo(f"✅ 시나리오 배포 완료: {scenario_id}")
        get_access_info(scenario_id)
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ 배포 실패: {e}", err=True)


@cli.command()
@click.argument('scenario_id')
def delete(scenario_id):
    """시나리오 삭제 (Disables scenario in c2z stack)"""
    key = to_config_key(scenario_id)
    if not key:
        return

    if click.confirm(f"시나리오 '{scenario_id}'를 정말 삭제하시겠습니까?"):
        click.echo(f"🗑️  시나리오 삭제 중: {scenario_id}")

        cmd = [
            "helm", "upgrade", "c2z", "./charts/c2z",
            "--namespace", "c2z-system",
            "--reuse-values",
            "--set", f"scenarios.{key}.enabled=false",
            "--wait"
        ]

        try:
            subprocess.run(cmd, check=True)
            click.echo(f"✅ 시나리오 삭제 완료: {scenario_id}")
        except subprocess.CalledProcessError as e:
            click.echo(f"❌ 삭제 실패: {e}", err=True)


@cli.command()
def status():
    """전체 시스템 상태 확인"""
    click.echo("📊 c2z 시스템 상태\n")
    # c2z-system and scenario namespaces
    cmd = ["kubectl", "get", "pods", "-A", "-l", "app.kubernetes.io/part-of=c2z"]
    # Also get pods in scenario namespaces just in case labels match
    # Or just get all pods?
    # Plan code: kubectl get pods -A -l app.kubernetes.io/part-of=pentestlab
    # I didn't add this label to my manifests yet. I should add common labels using _helpers.tpl or manually.
    # Manual check:
    subprocess.run(["kubectl", "get", "pods", "-A", "--show-labels"])


@cli.command()
@click.argument('scenario_id')
def logs(scenario_id):
    """시나리오 로그 조회"""
    # Namespaces are hardcoded in plan: scenario-{id}
    ns = f"scenario-{scenario_id}"
    cmd = [
        "kubectl", "logs",
        "-n", ns,
        "--all-containers=true",
        "--prefix=true",
        "-l", f"scenario={scenario_id}",  # I added this label to deployments
        "--tail=100",
        "-f"
    ]
    subprocess.run(cmd)


def get_access_info(scenario_id):
    """시나리오 접속 정보 출력"""
    click.echo("\n📍 접속 정보:")
    ns = f"scenario-{scenario_id}"

    cmd = [
        "kubectl", "get", "svc",
        "-n", ns,
        "-o", "json"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        try:
            services = yaml.safe_load(result.stdout)
            for svc in services.get('items', []):
                name = svc['metadata']['name']
                ports = svc['spec']['ports']
                for p in ports:
                    port = p['port']
                    link = f"http://localhost:{port} (via port-forward)"
                    click.echo(f"  - {name}: {link}")
                    # Note: Localhost access requires port-forwarding which isn't setup automatically here.
                    # The plan implies direct access? `http://localhost:port`
                    # If using K3s (docker), ports might be mapped?
                    # Or user needs `kubectl port-forward`.
                    # I will add a hint.
                    click.echo(f"    (Run: kubectl port-forward -n {ns} svc/{name} {port}:{port})")
        except yaml.YAMLError:
            pass
    except subprocess.CalledProcessError:
        click.echo("  서비스 정보를 가져올 수 없습니다.")


if __name__ == '__main__':
    cli()
