#!/bin/bash
# install.sh

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 init c2z environment...${NC}"

OS_TYPE=$(uname -s)
ARCH=$(uname -m)

# 0. Python Virtual Environment Setup (New Requirement)
setup_venv() {
    echo -e "${GREEN}� Setting up Python Virtual Environment (.venv)...${NC}"
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ python3 is required but not found.${NC}"
        exit 1
    fi

    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        echo "   Created .venv"
    else
        echo "   .venv already exists"
    fi

    # Activate and Install Requirements
    source .venv/bin/activate
    
    if [ -f "requirements.txt" ]; then
        echo "   Installing dependencies..."
        pip install -r requirements.txt | grep -v 'already satisfied' || true
    else
        echo -e "${RED}⚠️  requirements.txt not found.${NC}"
    fi
    
    echo "✅ Virtual Environment Ready"
}

# 1. Prerequisites Check
check_requirements() {
    echo -e "${GREEN}📋 Checking system requirements...${NC}"

    # RAM Check
    if [[ "$OS_TYPE" == "Darwin" ]]; then
         total_ram=$(sysctl -n hw.memsize | awk '{print int($1/1073741824)}')
    elif command -v free &> /dev/null; then
        total_ram=$(free -g | awk '/^Mem:/{print $2}')
    else
        total_ram=16 # Fallback
    fi

    if [ "$total_ram" -lt 16 ]; then
        echo -e "${RED}⚠️  Warning: Less than 16GB RAM detected ($total_ram GB). Performance may be affected.${NC}"
    fi

    # Docker Check (Required for Mac/k3d, Recommended for others)
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        if ! command -v docker &> /dev/null; then
            echo -e "${RED}❌ Docker is required on macOS for k3d.${NC}"
            exit 1
        fi
        if ! docker info &> /dev/null; then
            echo -e "${RED}❌ Docker daemon is not running.${NC}"
            exit 1
        fi
    fi

    echo "✅ Requirements Met"
}

# 2. Kubernetes Cluster Setup (Multi-platform)
install_k8s() {
    echo -e "${GREEN}🔧 Setting up Kubernetes Cluster...${NC}"
    
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        # macOS -> k3d
        if ! command -v k3d &> /dev/null; then
            echo "   Installing k3d..."
            curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
        fi

        if k3d cluster list | grep -q "c2z"; then
            echo "   Cluster 'c2z' already exists."
        else
            echo "   Creating k3d cluster 'c2z'..."
            # Create cluster with port forwarding via load balancer
            k3d cluster create c2z \
                --api-port 6443 \
                --port "80:80@loadbalancer" \
                --port "443:443@loadbalancer" \
                --port "3000-3005:3000-3005@loadbalancer" \
                --agents 1 \
                --k3s-arg "--disable=traefik@server:*" \
                --wait
        fi

        # Force merge to default config and set context
        echo "   Merging kubeconfig..."
        mkdir -p ~/.kube
        k3d kubeconfig merge c2z --output ~/.kube/config --kubeconfig-switch-context
        
        echo "   Setting context..."
        kubectl config use-context k3d-c2z || echo "   ⚠️ Could not set context to k3d-c2z"

        # Wait for cluster to be responsive
        echo "   Waiting for cluster API..."
        for i in {1..10}; do
            if kubectl cluster-info &> /dev/null; then
                break
            fi
            echo "   ... waiting for API server ($i/10)"
            sleep 3
        done
        
    elif [[ "$OS_TYPE" == "Linux" ]]; then
        # Linux -> k3s (Native)
        if command -v k3s &> /dev/null; then
            echo "   K3s already installed."
        else
            echo "   Installing K3s..."
            curl -sfL https://get.k3s.io | sh -s - \
                --write-kubeconfig-mode 644 \
                --disable traefik \
                --disable servicelb
        fi
        
        # Setup kubeconfig for user
        mkdir -p ~/.kube
        if [ -f /etc/rancher/k3s/k3s.yaml ] && [ ! -f ~/.kube/config ]; then
            sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
            sudo chown $USER:$USER ~/.kube/config
        fi
    else
        echo -e "${RED}❌ Unsupported OS: $OS_TYPE${NC}"
        exit 1
    fi
    
    echo "✅ Kubernetes Cluster Ready"
}

# 3. Helm Setup
install_helm() {
    echo -e "${GREEN}📦 Checking Helm...${NC}"
    if ! command -v helm &> /dev/null; then
        echo "   Installing Helm..."
        curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    fi
    echo "✅ Helm Ready"
}

# 4. Deploy c2z with Helm
deploy_c2z() {
    echo -e "${GREEN}🎯 Deploying c2z stack...${NC}"
    
    # Check if cluster is reachable
    if ! kubectl cluster-info &> /dev/null; then
        echo -e "${RED}❌ Kubernetes cluster is not reachable. Check kubeconfig.${NC}"
        exit 1
    fi

    if [ -d "./charts/c2z" ]; then
        helm upgrade --install c2z ./charts/c2z \
            --namespace c2z-system \
            --create-namespace \
            --wait \
            --timeout 10m
    else
        helm repo add c2z https://c2z.github.io/charts
        helm repo update
        helm upgrade --install c2z c2z/c2z \
            --namespace c2z-system \
            --create-namespace \
            --wait \
            --timeout 10m
    fi
    
    echo "✅ c2z Deployed"
}

# 5. Create c2z Wrapper Script
create_wrapper() {
    echo -e "${GREEN}📝 Creating c2z wrapper script...${NC}"
    cat > c2z <<EOF
#!/bin/bash
source \$(dirname "\$0")/.venv/bin/activate
python3 \$(dirname "\$0")/c2z-cli.py "\$@"
EOF
    chmod +x c2z
    echo "✅ Wrapper 'c2z' created. Usage: ./c2z list"
}

# Execution Flow
setup_venv
check_requirements
install_k8s
install_helm

# 4.5 Setup Registry Secret (Interactive)
setup_registry_secret() {
    echo -e "${GREEN}🔑 Checking Registry Credentials...${NC}"

    # Load from .env or .env.local if present
    if [ -f .env.local ]; then source .env.local; fi
    if [ -f .env ]; then source .env; fi

    # Support uppercase variable names from env file
    [ -n "$GH_USER" ] && gh_user="$GH_USER"
    [ -n "$GH_TOKEN" ] && gh_token="$GH_TOKEN"
    
    # Ensure namespace exists
    kubectl create namespace c2z-system --dry-run=client -o yaml | kubectl apply -f -
    
    if kubectl get secret ghcr-secret -n c2z-system &> /dev/null; then
        echo "   Secret 'ghcr-secret' found."
    else
        echo -e "${RED}⚠️  Secret 'ghcr-secret' not found in c2z-system.${NC}"
        echo "   This is required for private GHCR images."

        # If credentials are provided via env, auto-confirm
        if [ -n "$gh_user" ] && [ -n "$gh_token" ]; then
            echo "   ✅ Credentials found in environment/variables."
            answer="y"
        else
            read -p "   Do you want to create it now? (y/n): " answer < /dev/tty
        fi

        if [[ "$answer" =~ ^[Yy]$ ]]; then
            if [ -z "$gh_user" ]; then
                read -p "   GitHub Username: " gh_user < /dev/tty
            fi
            if [ -z "$gh_token" ]; then
                read -sp "   GitHub PAT Token: " gh_token < /dev/tty
                echo ""
            fi

            kubectl create secret docker-registry ghcr-secret \
                --docker-server=ghcr.io \
                --docker-username="$gh_user" \
                --docker-password="$gh_token" \
                --namespace=c2z-system
            echo "   ✅ Secret created."
        else
            echo "   Skipping secret creation. Deployments may fail if images are private."
        fi
    fi

}

# 6. Replicate Secret to Simulation Namespace (After Helm Deployment)
replicate_secret_to_simulation() {
    echo -e "${GREEN}🔑 Replicating secrets to simulation namespace...${NC}"
    
    # Check if simulation namespace exists (created by Helm)
    if kubectl get namespace simulation &> /dev/null; then
        if ! kubectl get secret ghcr-secret -n simulation &> /dev/null; then
            echo "   Copying 'ghcr-secret' to 'simulation' namespace..."
            kubectl get secret ghcr-secret -n c2z-system -o yaml | \
                sed 's/namespace: c2z-system/namespace: simulation/' | \
                kubectl apply -f - > /dev/null
            echo "   ✅ Secret replicated to simulation namespace"
        else
            echo "   Secret already exists in simulation namespace"
        fi
    else
        echo "   ⚠️  Simulation namespace not found (will be created on first scenario deploy)"
    fi
}

setup_registry_secret
deploy_c2z
replicate_secret_to_simulation
create_wrapper

echo ""
echo -e "${GREEN}🎉 Installation Complete!${NC}"
echo ""
echo "Use the wrapper script to manage the lab:"
echo "  ./c2z list"
echo "  ./c2z deploy web-vuln"
echo ""

