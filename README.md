# Kubediag - Kubernetes Diagnostic MCP Server

A Model Context Protocol (MCP) server that provides Kubernetes cluster diagnostic capabilities with automatic in-cluster configuration.

## Features

- **Dynamic Resource Discovery**: Automatically discovers and works with any Kubernetes resource type without hardcoded switch cases
- **Automatic Configuration**: Automatically detects and uses in-cluster configuration when running inside a Kubernetes pod
- **Fallback Support**: Falls back to local kubeconfig for development environments
- **Universal Resource Support**: Works with any Kubernetes resource (pods, services, deployments, configmaps, secrets, jobs, cronjobs, daemonsets, statefulsets, ingresses, etc.)
- **Comprehensive Diagnostics**: Get detailed information about specific resources with automatic metadata extraction

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
# or
uv sync
```

## Usage

### Running the MCP Server

```bash
python main.py
```

### Available Tools

#### `kubernetes_list`

List Kubernetes resources in a namespace using dynamic resource discovery.

**Parameters:**

- `namespace` (optional): Target namespace (default: "default")
- `resource_type` (optional): Resource type - any valid Kubernetes resource name (plural form) like pods, services, deployments, configmaps, secrets, jobs, cronjobs, daemonsets, statefulsets, etc. (default: "pods")

**Example:**

```python
kubernetes_list(namespace="kube-system", resource_type="pods")
kubernetes_list(namespace="default", resource_type="statefulsets")
kubernetes_list(namespace="production", resource_type="cronjobs")
```

#### `kubernetes_get`

Get detailed information about a specific Kubernetes resource using dynamic resource discovery.

**Parameters:**

- `namespace` (optional): Target namespace (default: "default")
- `resource_type` (optional): Resource type - any valid Kubernetes resource name (plural form) (default: "pods")
- `name` (required): Name of the resource

**Example:**

```python
kubernetes_get(namespace="default", resource_type="deployment", name="nginx-deployment")
kubernetes_get(namespace="kube-system", resource_type="daemonset", name="kube-proxy")
kubernetes_get(namespace="default", resource_type="ingress", name="web-ingress")
```

## Kubernetes Configuration

### In-Cluster Configuration (Production)

When running inside a Kubernetes pod, the server automatically uses in-cluster configuration:

1. **Service Account**: Ensure your pod has a service account with proper RBAC permissions
2. **RBAC Setup**: Create necessary ClusterRole and ClusterRoleBinding

Example RBAC configuration:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kubediag-sa
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kubediag-role
rules:
- apiGroups: [""]
  resources: ["*"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["*"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["batch"]
  resources: ["*"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["networking.k8s.io"]
  resources: ["*"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kubediag-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kubediag-role
subjects:
- kind: ServiceAccount
  name: kubediag-sa
  namespace: default
```

### Local Development

For local development, the server will attempt to use your local kubeconfig file (`~/.kube/config`).

## Testing

Run the test script to verify the Kubernetes setup:

```bash
python3 test_kubernetes_setup.py
```

## Error Handling

The server includes comprehensive error handling:

- Graceful fallback from in-cluster to kubeconfig configuration
- Detailed error messages for API operations
- Support for missing resources and permission issues

## Dependencies

- `kubernetes>=33.1.0`: Official Kubernetes Python client
- `mcp>=1.14.1`: Model Context Protocol server implementation

## Development

The project uses `uv` for dependency management. Key files:

- `pyproject.toml`: Project configuration and dependencies
- `main.py`: Main MCP server implementation with dynamic resource discovery
- `test_kubernetes_setup.py`: Test script for Kubernetes configuration
- `test_dynamic_resources.py`: Test script for dynamic resource discovery functionality
