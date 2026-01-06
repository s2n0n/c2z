import subprocess
import json
import time
import sys
import socket
import threading
import re
import signal

# Global list to track processes for cleanup
active_processes = []

def run_command(command):
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, shell=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def get_simulation_services():
    namespace = "simulation"
    services = []

    print(f"🔍 Scanning services in namespace: {namespace}...")

    cmd = f"kubectl get svc -n {namespace} -o json"
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
                            "namespace": namespace,
                            "port": p["port"],
                            "target_port": p.get("targetPort", p["port"]),
                        }
                    )
        except json.JSONDecodeError:
            print(f"[WARN] Failed to parse JSON for namespace {namespace}")

    return services

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def get_available_port(start_port, used_ports):
    port = start_port
    while port in used_ports or is_port_in_use(port):
        port += 1
    return port

def check_local_connection(port, retries=5):
    """
    Tries to connect to localhost:port to verify port-forwarding is active.
    """
    print(f"   ... Verifying local connectivity on port {port}...")
    for i in range(retries):
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                print(f"   ✅ Local connection confirmed on port {port}.")
                return True
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(1)

    print(f"   ❌ Failed to connect to localhost:{port} after {retries} retries.")
    return False

def start_kubectl_port_forward(service, local_port):
    cmd = [
        "kubectl",
        "port-forward",
        f"svc/{service['name']}",
        f"{local_port}:{service['port']}",
        "-n",
        service["namespace"],
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        active_processes.append(proc)

        # Give it a moment to stabilize
        time.sleep(2)

        if proc.poll() is not None:
            # Process died immediately
            _, stderr = proc.communicate()
            print(
                f"[ERROR] kubectl port-forward failed immediately for {service['name']}: {stderr.decode()}"
            )
            return False

        # Verify connectivity
        if not check_local_connection(local_port):
            print(
                f"[ERROR] Port-forward process is running but port {local_port} is not accessible."
            )
            proc.terminate()
            return False

        return True
    except Exception as e:
        print(
            f"[ERROR] Failed to start kubectl port-forward for {service['name']}: {e}"
        )
        return False

def start_cloudflared_tunnel(service_name, local_port):
    # Determine host address for docker to access host
    # On macOS, host.docker.internal works.
    target_url = f"http://host.docker.internal:{local_port}"

    cmd = [
        "docker",
        "run",
        "--rm",
        "cloudflare/cloudflared:latest",
        "tunnel",
        "--url",
        target_url,
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # cloudflared prints URL to stderr usually or mixed
            text=True,
            bufsize=1,
        )
        active_processes.append(proc)

        url = None
        # Read lines to find the URL
        print(f"   ... Starting tunnel for {service_name} (Local: {local_port})...")

        start_time = time.time()
        while time.time() - start_time < 30:  # 30s timeout
            line = proc.stdout.readline()
            if not line:
                break

            # Look for trycloudflare.com URL
            # Example: https://random-name.trycloudflare.com
            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if match:
                url = match.group(0)
                break

        # We found the URL (or timed out looking), but we keep the process running!
        # Create a thread to consume the rest of the output to prevent buffer blocking
        def consume_output(p):
            for _ in p.stdout:
                pass

        t = threading.Thread(target=consume_output, args=(proc,), daemon=True)
        t.start()

        if url:
            return url
        else:
            print(f"[WARN] Could not capture URL for {service_name}")
            return None

    except Exception as e:
        print(f"[ERROR] Failed to start cloudflared for {service_name}: {e}")
        return None

def cleanup(signum, frame):
    print("\n\n🛑 Stopping all tunnels and port-forwards...")
    for proc in active_processes:
        if proc.poll() is None:
            proc.terminate()
            # For docker run, terminate might not kill the container immediately if it ignores SIGTERM
            # Ideally we would track container IDs but --rm helps cleanup
    print("✅ Done.")
    sys.exit(0)

def main():
    print("🚀 c2z Simulation Exposer (Cloudflare Tunnel)")
    print("---------------------------------------------")

    # Handle Ctrl+C
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    services = get_simulation_services()
    if not services:
        print("[ERROR] No services found in 'simulation' namespace.")
        return

    print(f"✅ Found {len(services)} services in 'simulation'.")

    used_ports = set()
    mappings = []

    print("\nStarting exposure pipeline...")
    print("-" * 60)

    next_search_port = 8000

    for svc in services:
        svc_name = svc["name"]

        # Find local port
        # We ignore the service's internal port for local binding and just look for the next free one > 8000
        local_port = get_available_port(next_search_port, used_ports)

        # Update search start for next time to be efficient
        next_search_port = local_port + 1

        used_ports.add(local_port)

        # 1. Start kubectl port-forward
        if start_kubectl_port_forward(svc, local_port):
            # 2. Start cloudflared tunnel
            public_url = start_cloudflared_tunnel(svc_name, local_port)

            if public_url:
                mappings.append(
                    {
                        "service": svc_name,
                        "local": f"localhost:{local_port}",
                        "public": public_url,
                    }
                )
                print(f"✅ {svc_name:<25} -> {public_url}")
            else:
                print(f"❌ {svc_name:<25} -> Tunnel failed")
        else:
            print(f"❌ {svc_name:<25} -> Port-forward failed")

    print("\n" + "=" * 60)
    print(f"{'SERVICE':<25} | {'LOCAL ADDR':<15} | {'PUBLIC URL'}")
    print("=" * 60)

    for m in mappings:
        print(f"{m['service']:<25} | {m['local']:<15} | {m['public']}")

    print("=" * 60)
    print("📢 Press Ctrl+C to stop all services.")

    # Keep main thread alive
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
