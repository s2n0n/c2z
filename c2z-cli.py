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
    """c2z CLI"""


@cli.command()
def list() -> None:
    scenarios = [
        ["web-vuln", "Web Application Vulnerability", "Basic", "Active"],
        ["container-escape", "Container Escape", "Intermediate", "Active"],
        ["network-attack", "Network Attack", "Intermediate", "Active"],
        ["nextjs", "Next.js Secure Coding", "Advanced", "Active"],
        ["api-security", "API Security", "Intermediate", "Dev"],
    ]
    headers = ["ID", "Scenario", "Difficulty", "Status"]
    print(tabulate(scenarios, headers=headers, tablefmt="grid"))


@cli.command()
@click.argument("scenario_id")
def deploy(scenario_id: str) -> None:
    key = to_config_key(scenario_id)
    if not key:
        click.echo(f"Unknown scenario ID: {scenario_id}", err=True)
        return

    click.echo(f"Deploying scenario: {scenario_id}")

    chart_path = "./charts/c2z"
    if not os.path.exists(chart_path) and os.path.exists("../charts/c2z"):
        chart_path = "../charts/c2z"

    check_cmd = ["helm", "status", "c2z", "-n", "simulation"]
    is_installed = subprocess.run(check_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    cmd = [
        "helm",
        "upgrade",
        "--install",
        "c2z",
        chart_path,
        "--namespace",
        "simulation",
        "--create-namespace",
        "--wait",
    ]

    if is_installed:
        cmd.append("--reuse-values")

    cmd.append("--set")
    cmd.append(f"scenarios.{key}.enabled=true")

    try:
        subprocess.run(cmd, check=True)
        click.echo(f"Scenario deployed: {scenario_id}")
        get_access_info(scenario_id)
    except subprocess.CalledProcessError as e:
        click.echo(f"Deploy failed: {e}", err=True)


@cli.command()
@click.argument("scenario_id")
def delete(scenario_id: str) -> None:
    key = to_config_key(scenario_id)
    if not key:
        click.echo(f"Unknown scenario ID: {scenario_id}", err=True)
        return

    if click.confirm(f"Delete scenario '{scenario_id}'?"):
        click.echo(f"Deleting scenario: {scenario_id}")

        chart_path = "./charts/c2z"
        if not os.path.exists(chart_path) and os.path.exists("../charts/c2z"):
            chart_path = "../charts/c2z"

        cmd = [
            "helm",
            "upgrade",
            "c2z",
            chart_path,
            "--namespace",
            "simulation",
            "--reuse-values",
            "--set",
            f"scenarios.{key}.enabled=false",
            "--wait",
        ]

        try:
            subprocess.run(cmd, check=True)
            click.echo(f"Scenario deleted: {scenario_id}")
        except subprocess.CalledProcessError as e:
            click.echo(f"Delete failed: {e}", err=True)


@cli.command()
def status() -> None:
    click.echo("System Status\n")
    click.echo("--- Namespace: simulation ---")
    subprocess.run(["kubectl", "get", "pods", "-n", "simulation"], check=False)


@cli.command()
@click.argument("scenario_id")
def logs(scenario_id: str) -> None:
    ns = "simulation"
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
        "-f"
    ]
    try:
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        return


@cli.command()
def build() -> None:
    click.echo("Building Next.js image in Minikube environment...")
    
    src_path = "./nextjs-src"
    if not os.path.exists(src_path) and os.path.exists("../nextjs-src"):
        src_path = "../nextjs-src"
    
    if not os.path.exists(src_path):
        click.echo(f"Source path not found: {src_path}", err=True)
        return

    cmd = f"eval $(minikube docker-env) && docker build -t nextjs:16.1.1 {src_path}"
    
    try:
        subprocess.run(cmd, shell=True, check=True, executable="/bin/bash")
        click.echo("\nBuild success. Run 'deploy nextjs' to start.")
    except subprocess.CalledProcessError:
        click.echo("\nBuild failed.", err=True)


def get_access_info(scenario_id: str) -> None:
    click.echo("\nAccess Info:")
    ns = "simulation"
    
    if scenario_id == "nextjs":
        click.echo("  - App: Next.js Secure Coding")
        click.echo(f"    Local Access: kubectl port-forward -n {ns} deployment/nextjs-16-secure 8082:3000")
        return

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
                click.echo(f"    Local Access: kubectl port-forward -n {ns} svc/{name} {port}:{port}")
                found = True

        if not found:
            click.echo("  (No services found)")

    except subprocess.CalledProcessError:
        click.echo(f"  Cannot access namespace '{ns}'")
    except Exception as e:
        click.echo(f"  Error: {e}")


if __name__ == "__main__":
    cli()
