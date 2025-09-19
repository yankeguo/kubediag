# Kubediag - Kubernetes Diagnostic MCP Server

A Model Context Protocol (MCP) server that provides Kubernetes cluster diagnostic capabilities with automatic in-cluster configuration. The application includes both an MCP server for programmatic access and a web interface with CAS authentication for browser-based access.

## Features

- **Dynamic Resource Discovery**: Automatically discovers and works with any Kubernetes resource type without hardcoded switch cases
- **Automatic Configuration**: Automatically detects and uses in-cluster configuration when running inside a Kubernetes pod
- **Fallback Support**: Falls back to local kubeconfig for development environments
- **Universal Resource Support**: Works with any Kubernetes resource (pods, services, deployments, configmaps, secrets, jobs, cronjobs, daemonsets, statefulsets, ingresses, etc.)
- **Comprehensive Diagnostics**: Get detailed information about specific resources with automatic metadata extraction
- **Web Interface**: Browser-based access with CAS authentication
- **JWT Authentication**: Secure API access with JWT token verification
- **Container Ready**: Docker containerization with multi-architecture support
- **CI/CD Integration**: Automated container builds and publishing via GitHub Actions

## Project Structure

```
kubediag/
├── .github/
│   └── workflows/
│       └── build-image.yml       # GitHub Actions CI/CD pipeline
├── src/
│   └── kubediag/
│       ├── __init__.py
│       ├── main.py               # Main FastAPI/Starlette application
│       ├── mcp.py                # MCP server implementation
│       ├── kubernetes.py         # Kubernetes client and utilities
│       ├── env.py                # Environment configuration
│       └── view/
│           └── index.html.j2     # Web interface template
├── docs/                         # Documentation and sample files
├── Dockerfile                    # Container build configuration
├── pyproject.toml               # Python project configuration
├── uv.lock                      # Dependency lock file
├── run.sh                       # Production startup script
├── dev.sh                       # Development startup script
└── README.md                    # This file
```

## Installation and Setup

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Kubernetes cluster access (for functionality)

### Local Development

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yankeguo/kubediag.git
   cd kubediag
   ```

2. **Install dependencies:**

   ```bash
   uv sync
   ```

3. **Configure environment (optional):**

   ```bash
   cp .env.example .env  # If available
   # Edit .env with your configuration
   ```

4. **Run in development mode:**

   ```bash
   ./dev.sh
   ```

   This starts the server with hot-reload enabled at `http://localhost:8000`

### Production Deployment

#### Using Docker

1. **Build the container:**

   ```bash
   docker build -t kubediag .
   ```

2. **Run the container:**

   ```bash
   docker run -p 8000:8000 kubediag
   ```

#### Using Pre-built Images

Images are automatically built and published to GitHub Container Registry:

```bash
# Pull the latest image
docker pull ghcr.io/yankeguo/kubediag:main-<commit-sha>

# Run the container
docker run -p 8000:8000 ghcr.io/yankeguo/kubediag:main-<commit-sha>
```

#### Manual Production Run

```bash
./run.sh
```

This starts the server in production mode with proper proxy headers and network configuration.

## Usage

### Web Interface

Access the web interface at `http://localhost:8000`. The interface provides:

- CAS authentication integration
- Browser-based Kubernetes resource exploration
- JWT token-based session management

### MCP Server API

The MCP server is accessible at `http://localhost:8000/` and provides the following tools:

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

## Configuration

### Environment Variables

The application supports configuration through environment variables:

- `CAS_URL`: CAS authentication server URL
- `PUBLIC_URL`: Public URL of the application for CAS callbacks
- `SECRET_KEY`: JWT signing key for authentication

### Authentication

The application uses JWT-based authentication for MCP API access and CAS authentication for web interface access.

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

### Local Development Environment

For local development, the server will attempt to use your local kubeconfig file (`~/.kube/config`).

## Development

### Technology Stack

- **FastMCP**: Model Context Protocol server framework
- **Starlette**: ASGI web framework
- **Kubernetes Python Client**: Official Kubernetes API client
- **Jinja2**: Template engine for web interface
- **JWT**: JSON Web Token authentication
- **uvicorn**: ASGI server
- **uv**: Fast Python package manager

### Development Scripts

- `dev.sh`: Start development server with hot-reload
- `run.sh`: Start production server
- Scripts automatically activate the virtual environment and load `.env` if present

### Container Development

The project includes a multi-stage Dockerfile optimized for:

- Python 3.13 with uv package manager
- Chinese locale support (zh_CN.UTF-8)
- Multi-architecture builds (amd64/arm64)
- Proper timezone configuration (Asia/Shanghai)
- Minimal attack surface with tini init system

### CI/CD Pipeline

GitHub Actions automatically:

- Builds container images on every push to main branch
- Tags images with format: `main-{short-sha}`
- Publishes to GitHub Container Registry (`ghcr.io/yankeguo/kubediag`)
- Supports multi-architecture builds
- Uses build caching for faster builds

## Testing

Verify Kubernetes connectivity and permissions:

```bash
# Test the application in development mode
./dev.sh

# Check if Kubernetes client can connect
# (The application will log connection status on startup)
```

## Error Handling

The server includes comprehensive error handling:

- Graceful fallback from in-cluster to kubeconfig configuration
- Detailed error messages for API operations
- Support for missing resources and permission issues
- JWT authentication error handling
- CAS authentication flow error handling

## Dependencies

Key dependencies defined in `pyproject.toml`:

- `aiohttp[speedups]>=3.12.15`: Async HTTP client
- `fastmcp>=2.12.3`: Model Context Protocol server implementation
- `kubernetes>=33.1.0`: Official Kubernetes Python client
- `starlette>=0.48.0`: ASGI web framework
- `uvicorn>=0.35.0`: ASGI server
- `pyjwt>=2.10.0`: JWT authentication
- `jinja2>=3.1.6`: Template engine

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

See the [LICENSE](LICENSE) file for license information.
