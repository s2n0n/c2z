import subprocess
import json
import time
import socket

def run_command(command):
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, shell=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Don't print error here to avoid spamming if just checking
        return None

def get_services():
    namespaces = ["c2z-system", "simulation"]
    services = []

    print("🔍 Scanning services in namespaces: " + ", ".join(namespaces) + "...")

    for ns in namespaces:
        cmd = f"kubectl get svc -n {ns} -o json"
        output = run_command(cmd)
        if output:
            try:
                data = json.loads(output)
                for item in data.get("items", []):
                    svc_name = item["metadata"]["name"]
                    ports = item["spec"].get("ports", [])
                    for p in ports:
                        services.append(
                            {
                                "name": svc_name,
                                "namespace": ns,
                                "port": p["port"],
                                "target_port": p.get("targetPort", p["port"]),
                            }
                        )
            except json.JSONDecodeError:
                print(f"[WARN] Failed to parse JSON for namespace {ns}")
    return services

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def get_available_port(start_port, used_ports):
    port = start_port
    # Check both our internal tracking set and the actual system
    while port in used_ports or is_port_in_use(port):
        port += 1
    return port

def main():
    print("🚀 c2z Cluster Port-Forwarding Script")
    print("---------------------------------------")

    services = get_services()
    if not services:
        print(
            "[ERROR] No services found in c2z-system or simulation namespaces. Is the cluster running?"
        )
        return

    print(f"✅ Found {len(services)} services.")

    # Sort services to potentially keep stable ordering or prioritize standard ports
    # Sorting by namespace then name seems reasonable
    services.sort(key=lambda x: (x["namespace"], x["name"]))

    processes = []
    used_ports = set()  # Track ports assigned in this session

    # Ask for mode
    forward_all = (
        input("\n❓ Forward ALL services automatically? (y/n): ").lower() == "y"
    )

    print("\nStarting port assignments...")
    print("-" * 60)
    print(f"{'SERVICE':<30} | {'NAMESPACE':<15} | {'MAPPING'}")
    print("-" * 60)

    for svc in services:
        svc_name = svc["name"]
        namespace = svc["namespace"]
        svc_port = int(svc["port"])

        should_forward = False
        local_port = 0

        if forward_all:
            should_forward = True
            # Find next available port starting from the service port
            local_port = get_available_port(svc_port, used_ports)
        else:
            # Interactive mode
            user_input = input(
                f"\n❓ Forward [{namespace}] {svc_name} (Port: {svc_port})? (y/n): "
            ).lower()
            if user_input == "y":
                should_forward = True

                # Check if default port is free
                default_is_free = (svc_port not in used_ports) and (
                    not is_port_in_use(svc_port)
                )
                prompt_default = (
                    svc_port
                    if default_is_free
                    else get_available_port(svc_port, used_ports)
                )

                port_input = input(f"   🔢 Local Port (default {prompt_default}): ")
                if port_input.strip():
                    local_port = int(port_input)
                else:
                    local_port = prompt_default
            else:
                should_forward = False

        if should_forward:
            # Final check specifically for manual input collisions
            if local_port in used_ports:
                print(
                    f"   ⚠️  Warning: Port {local_port} was already assigned in this session."
                )

            # Add to used set
            used_ports.add(local_port)

            # Start kubectl port-forward
            cmd = f"kubectl port-forward svc/{svc_name} {local_port}:{svc_port} -n {namespace}"
            try:
                proc = subprocess.Popen(
                    cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
                )
                processes.append(
                    {
                        "proc": proc,
                        "name": svc_name,
                        "namespace": namespace,
                        "local": local_port,
                        "remote": svc_port,
                    }
                )
                print(
                    f"{svc_name:<30} | {namespace:<15} | http://localhost:{local_port} -> {svc_port}"
                )
            except Exception as e:
                print(f"[ERROR] Failed to start {svc_name}: {e}")

    if not processes:
        print("\n[INFO] No port-forwarding sessions started.")
        return

    print("-" * 60)
    print(f"\n🚀 {len(processes)} active sessions running.")
    print("📢 Press Ctrl+C to stop all sessions.")

    try:
        while True:
            time.sleep(1)
            # Optional: Check if processes are still alive?
            for p in processes:
                if p["proc"].poll() is not None:
                    # Process died
                    print(f"[WARN] Port-forward for {p['name']} stopped unexpectedly.")
                    processes.remove(p)
            if not processes:
                print("[INFO] All processes stopped.")
                break
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping all sessions...")
        for p in processes:
            p["proc"].terminate()
        print("✅ Done.")

if __name__ == "__main__":
    main()