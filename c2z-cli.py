#!/usr/bin/env python3
# c2z-cli

import click
import subprocess
import yaml
import os
from tabulate import tabulate


def to_camel_case(text):
    if text == "web-vuln":
        return "webVuln"
    if text == "container-escape":
        return "containerEscape"
    if text == "network-attack":
        return "networkAttack"
    return text


def to_config_key(scenario_id):
    mapping = {
        "web-vuln": "webVuln",
        "container-escape": "containerEscape",
        "network-attack": "networkAttack",
    }
    return mapping.get(scenario_id)


def get_access_info(scenario_id):
    """시나리오 접속 정보 출력"""
    click.echo("\n📍 접속 정보:")
    ns = f"scenario-{scenario_id}"

    cmd = ["kubectl", "get", "svc", "-n", ns, "-o", "json"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        try:
            services = yaml.safe_load(result.stdout)
            items = services.get("items", [])
            if not items:
                click.echo("  (No services found)")
                return

            for svc in items:
                name = svc["metadata"]["name"]
                spec = svc.get("spec", {})
                ports = spec.get("ports", [])
                for p in ports:
                    port = p["port"]
                    link = f"http://localhost:{port} (via port-forward)"
                    click.echo(f"  - {name}: {link}")
                    click.echo(
                        f"    (Run: kubectl port-forward -n {ns} svc/{name} {port}:{port})"
                    )
        except yaml.YAMLError:
            pass
    except subprocess.CalledProcessError:
        click.echo(
            "  서비스 정보를 가져올 수 없습니다. (Namespace might not exist yet)"
        )


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
@click.argument("scenario_id")
def deploy(scenario_id):
    """시나리오 배포 (Enables scenario in c2z stack)"""
    key = to_config_key(scenario_id)
    if not key:
        click.echo(f"❌ 알 수 없는 시나리오 ID: {scenario_id}", err=True)
        return

    click.echo(f"🚀 시나리오 배포 중: {scenario_id}")

    # Assuming chart is at ./charts/c2z relative to where CLI is run
    chart_path = "./charts/c2z"
    if not os.path.exists(chart_path):
        # Try to find it relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        chart_path = os.path.join(script_dir, "charts", "c2z")

    if not os.path.exists(chart_path):
        click.echo(
            f"⚠️  Chart path not found at {chart_path}. Assuming 'c2z/c2z' from repo if adding that logic."
        )
        # For now, fail or assume current dir
        chart_path = "./charts/c2z"

    cmd = [
        "helm",
        "upgrade",
        "--install",
        "c2z",
        chart_path,
        "--namespace",
        "c2z-system",
        "--create-namespace",
        "--reuse-values",
        "--set",
        f"scenarios.{key}.enabled=true",
        "--wait",
    ]

    try:
        subprocess.run(cmd, check=True)
        click.echo(f"✅ 시나리오 배포 완료: {scenario_id}")
        get_access_info(scenario_id)
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ 배포 실패: {e}", err=True)


@cli.command()
@click.argument("scenario_id")
def delete(scenario_id):
    """시나리오 삭제 (Disables scenario in c2z stack)"""
    key = to_config_key(scenario_id)
    if not key:
        click.echo(f"❌ 알 수 없는 시나리오 ID: {scenario_id}", err=True)
        return

    if click.confirm(f"시나리오 '{scenario_id}'를 정말 삭제하시겠습니까?"):
        click.echo(f"🗑️  시나리오 삭제 중: {scenario_id}")

        # We need to find the chart path again to run upgrade
        chart_path = "./charts/c2z"
        if not os.path.exists(chart_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            chart_path = os.path.join(script_dir, "charts", "c2z")

        cmd = [
            "helm",
            "upgrade",
            "c2z",
            chart_path,
            "--namespace",
            "c2z-system",
            "--reuse-values",
            "--set",
            f"scenarios.{key}.enabled=false",
            "--wait",
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
    # Check if kubectl is available
    try:
        subprocess.run(
            ["kubectl", "version", "--client"], check=True, stdout=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        click.echo("❌ kubectl not found or not working")
        return

    click.echo("Checking pods in c2z-related namespaces...")
    # List all pods with label app.kubernetes.io/part-of=c2z OR in specific namespaces
    # Since we can't easily grep all namespaces by name pattern without scripting,
    # we'll list all and grep or just show all if label is present.
    # Assuming we added labels to our charts.
    # If not, let's just check the known namespaces.

    namespaces = [
        "c2z-system",
        "scenario-web-vuln",
        "scenario-container-escape",
        "scenario-network-attack",
    ]
    found_any = False
    for ns in namespaces:
        # check if namespace exists
        res = subprocess.run(["kubectl", "get", "ns", ns], capture_output=True)
        if res.returncode == 0:
            click.echo(f"\nNamespace: {ns}")
            subprocess.run(["kubectl", "get", "pods", "-n", ns])
            found_any = True

    if not found_any:
        click.echo("No c2z namespaces found.")


if __name__ == "__main__":
    cli()