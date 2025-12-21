# External Access Guide

This guide explains how to expose your local `c2z` cluster services to the external internet. This is useful for sharing your simulation environment with others or accessing it from a remote location.

## Recommended: Cloudflare Tunnel

Cloudflare Tunnel (formerly Argo Tunnel) is the most secure and easiest way to expose local services without configuring firewall rules or port forwarding on your router.

### 1. Install `cloudflared`

**macOS:**

```bash
brew install cloudflared
```

**Linux:**
follows the [official instructions](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/).

### 2. Login

```bash
cloudflared tunnel login
```

### 3. Expose a Service

To expose a specific service (e.g., DVWA on port 80), run:

```bash
# Assuming DVWA is forwarded to localhost:8080 by the port_forward.py script
cloudflared tunnel --url http://localhost:8080
```

Cloudflare will provide a temporary URL (e.g., `https://random-name.trycloudflare.com`) that tunnels directly to your local service.

## Alternative: ngrok

ngrok is a popular tool for secure tunnels.

### 1. Install ngrok

**macOS:**

```bash
brew install ngrok/ngrok/ngrok
```

### 2. Expose a Service

```bash
ngrok http 8080
```

## Advanced: Router Port Forwarding

> [!WARNING]
> This method exposes your local network directly to the internet. Ensure you have strong security measures in place.

Since the `c2z` cluster defaults to disabling Traefik (Ingress Controller) on port 80/443 to avoid conflicts, you must:

1.  **Enable Ingress**: Re-install the cluster with Traefik enabled or install another Ingress Controller (like Nginx).
2.  **Configure Service**: Create an Ingress resource for the service you want to expose.
3.  **Router Config**: Log in to your router and forward external port 80 to your machine's local IP address.
