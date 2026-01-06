#!/usr/bin/env python3
import os
import subprocess
import click
import yaml
from tabulate import tabulate


def to_config_key(scenario_id):
    mapping = {
        "web-vuln": "webVuln",
        "container-escape": "containerEscape",
        "network-attack": "networkAttack",
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
@click.argument("scenario_id")
def deploy(scenario_id):
    """시나리오 배포 (Enables scenario in c2z stack)"""
    key = to_config_key(scenario_id)
    if not key:
        click.echo(f"❌ 알 수 없는 시나리오 ID: {scenario_id}", err=True)
        return

    click.echo(f"🚀 시나리오 배포 중: {scenario_id}")

    chart_path = "./charts/c2z"
    if not os.path.exists(chart_path) and os.path.exists("../charts/c2z"):
        chart_path = "../charts/c2z"

    # Monolith chart strategy: Update the main release with the scenario enabled
    cmd = [
        "helm",
        "upgrade",
        "c2z",
        chart_path,
        "--namespace",
        "c2z-system",
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

        chart_path = "./charts/c2z"
        if not os.path.exists(chart_path) and os.path.exists("../charts/c2z"):
            chart_path = "../charts/c2z"

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
    click.echo("📊 c2z 시스템 상태 (Pods in c2z-system and scenario namespaces)\n")

    click.echo("--- Namespace: c2z-system ---")
    subprocess.run(["kubectl", "get", "pods", "-n", "c2z-system"])

    scenarios = [
        "scenario-web-vuln",
        "scenario-container-escape",
        "scenario-network-attack",
    ]
    for ns in scenarios:
        # Check if namespace exists first to avoid spammy errors
        check_ns = subprocess.run(
            ["kubectl", "get", "ns", ns],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if check_ns.returncode == 0:
            click.echo(f"\n--- Namespace: {ns} ---")
            subprocess.run(["kubectl", "get", "pods", "-n", ns])

@cli.command()
@click.argument("scenario_id")
def logs(scenario_id):
    """시나리오 로그 조회"""
    ns = f"scenario-{scenario_id}"
    cmd = [
        "kubectl",
        "logs",
        "-n",
        ns,
        "--all-containers=true",
        "--prefix=true",
        "-l",
        f"scenario={scenario_id}",
        "--tail=100",
        "-f",
    ]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass

def get_access_info(scenario_id):
    """시나리오 접속 정보 출력"""
    click.echo("\n📍 접속 정보:")
    ns = f"scenario-{scenario_id}"

    try:
        result = subprocess.run(
            ["kubectl", "get", "svc", "-n", ns, "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        services = yaml.safe_load(result.stdout)

        found = False
        for svc in services.get("items", []):
            name = svc["metadata"]["name"]
            spec = svc.get("spec", {})
            ports = spec.get("ports", [])

            for p in ports:
                port = p["port"]
                click.echo(f"  - Service: {name}")
                click.echo(
                    f"    Local Access: kubectl port-forward -n {ns} svc/{name} {port}:{port}"
                )
                found = True

        if not found:
            click.echo("  (No services found)")

    except subprocess.CalledProcessError:
        click.echo(f"  Namespace '{ns}'에 접근할 수 없거나 서비스가 없습니다.")
    except Exception as e:
        click.echo(f"  정보 조회 오류: {e}")

if __name__ == "__main__":
    cli()