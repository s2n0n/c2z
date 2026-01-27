#!/usr/bin/env python3
import os
import subprocess
import click
import yaml
from tabulate import tabulate


def to_config_key(scenario_id: str) -> str | None:
    mapping = {
        "web-vuln": "webVuln",
        "container-escape": "containerEscape",
        "network-attack": "networkAttack",
        "nextjs": "nextjs",
    }
    return mapping.get(scenario_id)


@click.group()
def cli() -> None:
    """c2z CLI - Kubernetes 기반 침투 테스트 환경 관리"""


@cli.command()
def list() -> None:  # noqa: A001
    """사용 가능한 시나리오 목록 표시"""
    scenarios = [
        ["web-vuln", "Web Application 취약점", "초급", "✅ 사용 가능"],
        ["container-escape", "Container Escape", "중급", "✅ 사용 가능"],
        ["network-attack", "Network Attack", "중급", "✅ 사용 가능"],
        ["nextjs", "Next.js Secure Coding", "고급", "✅ 사용 가능"],
        ["api-security", "API Security", "중급", "🚧 개발 중"],
    ]
    headers = ["ID", "시나리오", "난이도", "상태"]
    print(tabulate(scenarios, headers=headers, tablefmt="grid"))


@cli.command()
@click.argument("scenario_id")
def deploy(scenario_id: str) -> None:
    """시나리오 배포 (Enables scenario in c2z stack)"""
    key = to_config_key(scenario_id)
    if not key:
        click.echo(f"❌ 알 수 없는 시나리오 ID: {scenario_id}", err=True)
        return

    click.echo(f"🚀 시나리오 배포 중: {scenario_id}")

    chart_path = "./charts/c2z"
    if not os.path.exists(chart_path) and os.path.exists("../charts/c2z"):
        chart_path = "../charts/c2z"

    ns = "c2z-system"

    cmd = [
        "helm",
        "upgrade",
        "--install",
        "c2z",
        chart_path,
        "--namespace",
        ns,
        "--create-namespace",
        "--reuse-values",
        "--set",
        f"scenarios.{key}.enabled=true",
        "--wait",
    ]

    try:
        subprocess.run(cmd, check=True)
        click.echo(f"✅ 시나리오 배포 완료: {scenario_id}")
        get_access_info(scenario_id, ns)
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ 배포 실패: {e}", err=True)


@cli.command()
@click.argument("scenario_id")
def delete(scenario_id: str) -> None:
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

        ns = "c2z-system"

        cmd = [
            "helm",
            "upgrade",
            "c2z",
            chart_path,
            "--namespace",
            ns,
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
def status() -> None:
    """전체 시스템 상태 확인"""
    click.echo("📊 c2z 시스템 상태 (Pods in c2z-system and scenario namespaces)\n")

    click.echo("--- Namespace: c2z-system ---")
    subprocess.run(["kubectl", "get", "pods", "-n", "c2z-system"], check=False)

    scenarios = [
        "scenario-web-vuln",
        "scenario-container-escape",
        "scenario-network-attack",
        "scenario-nextjs",
    ]
    for ns in scenarios:
        check_ns = subprocess.run(
            ["kubectl", "get", "ns", ns],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if check_ns.returncode == 0:
            click.echo(f"\n--- Namespace: {ns} ---")
            subprocess.run(["kubectl", "get", "pods", "-n", ns], check=False)


@cli.command()
@click.argument("scenario_id")
def logs(scenario_id: str) -> None:
    """시나리오 로그 조회"""
    ns = f"scenario-{scenario_id}"

    if scenario_id == "nextjs":
        ns = "c2z-system"

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
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        return


@cli.command()
def build() -> None:
    """Next.js 이미지 빌드 (Minikube Docker Env)"""
    click.echo("🐳 Minikube Docker 환경에 연결하여 빌드를 시작합니다...")

    src_path = "./nextjs-src"
    if not os.path.exists(src_path) and os.path.exists("../nextjs-src"):
        src_path = "../nextjs-src"

    if not os.path.exists(src_path):
        click.echo(f"❌ 소스코드 폴더({src_path})를 찾을 수 없습니다.", err=True)
        return

    cmd = f"eval $(minikube docker-env) && docker build -t nextjs:16.1.1 {src_path}"

    try:
        subprocess.run(cmd, shell=True, check=True, executable="/bin/bash")
        click.echo("\n✅ 빌드 성공! 이제 'nextjs'를 실행할 수 있습니다.")
    except subprocess.CalledProcessError:
        click.echo("\n❌ 빌드 실패: 도커 연결 또는 용량을 확인하세요.", err=True)


def get_access_info(scenario_id: str, ns: str) -> None:
    if scenario_id == "nextjs":
        click.echo("\n📍 [접속 정보]")
        click.echo(f"   명령어: kubectl port-forward -n {ns} deployment/nextjs-16-1-1 8082:3000")
        click.echo(f"   주소: http://localhost:8082")


if __name__ == "__main__":
    cli()
