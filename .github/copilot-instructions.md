# KubeDiag Copilot Instructions

This is a Kubernetes diagnostic MCP (Model Context Protocol) server built with FastMCP and Starlette, designed for both programmatic access and web-based diagnostics with CAS authentication.

## Architecture Overview

The application is a dual-purpose service combining:
- **MCP Server** (`/mcp/`): Provides Kubernetes diagnostic tools via JWT-authenticated HTTP/MCP protocol
- **Web Interface** (`/`): Browser-based access with CAS authentication flow that issues JWT tokens

Key architectural patterns:
- **Dynamic Resource Discovery**: Uses Kubernetes dynamic client to work with ANY resource type without hardcoded switches
- **Dual Authentication**: CAS for web UI, JWT for MCP API access
- **Environment-Aware Configuration**: Auto-detects in-cluster vs local kubeconfig

## Core Components

### `/src/kubediag/main.py`
- Starlette ASGI app combining MCP and web routes
- CAS authentication flow: redirects to CAS → validates ticket → issues JWT → renders template
- Mounts MCP server at `/mcp/` with JWT auth

### `/src/kubediag/mcp.py` 
- FastMCP server with JWT verification
- Two main tools: `kubernetes_list()` and `kubernetes_get()`
- Resource type parameter accepts ANY Kubernetes resource in plural form (pods, services, deployments, configmaps, etc.)

### `/src/kubediag/kubernetes.py`
- Dynamic Kubernetes client with automatic configuration (in-cluster → kubeconfig fallback)
- Resource discovery via `dynamic_client.resources.search()` with caching
- Data cleaning rules: minimal metadata, secret redaction, value truncation
- Handles both namespaced and cluster-scoped resources automatically

### `/src/kubediag/env.py`
- Environment configuration with sensible defaults
- Required for production: `SECRET_KEY`, `PUBLIC_URL`, `CAS_URL`, `SERVER_NAME`

## Development Workflows

### Local Development
```bash
uv sync                    # Install dependencies
./dev.sh                   # Start with hot-reload (port 8000)
```

### Production Deployment
```bash
./run.sh                   # Production server with proxy headers
docker build -t kubediag . # Container build
```

### Key Environment Variables
- `SECRET_KEY`: JWT signing key (required for production)
- `PUBLIC_URL`: Full public URL for CAS callbacks
- `CAS_URL`: CAS server base URL
- `KUBERNETES_INSECURE=true`: Disable SSL verification for dev clusters

## Critical Patterns

### Resource Type Handling
Always use lowercase plural forms: `pods`, `services`, `deployments`, `configmaps`, `nodes`, `namespaces`
The dynamic client automatically resolves these to proper API groups/versions.

### Authentication Flow
1. Web access redirects to CAS with `service` parameter
2. CAS returns with `ticket` parameter
3. Validate ticket via `/p3/serviceValidate` 
4. Issue JWT with user as subject
5. MCP requests use `Authorization: Bearer <jwt>` header

### Data Cleaning Strategy
- **Metadata**: Keep only name, namespace, labels, useful annotations
- **Secrets**: Redact all data field values to "REDACTED"
- **Truncation**: Limit string values to 256 chars with truncation markers

### MCP Client Configuration
Template generates proper `mcpServers` config with `"type": "streamable-http"`:
```json
{
  "mcpServers": {
    "kubediag": {
      "type": "streamable-http",
      "url": "https://your-server.com/mcp/",
      "headers": {
        "Authorization": "Bearer <jwt-token>"
      }
    }
  }
}
```

## Container & CI/CD

- Multi-stage Dockerfile using `uv` for fast dependency management
- GitHub Actions builds multi-arch images (amd64/arm64) on main branch pushes
- Images tagged as `main-<short-sha>` and pushed to `ghcr.io/yankeguo/kubediag`
- Chinese locale support and timezone configuration for production use

## Error Handling

- Graceful configuration fallback (in-cluster → kubeconfig → error)
- MCP tools raise `ToolError` for API exceptions with descriptive messages
- Resource discovery failures are cached as `None` to prevent repeated attempts
- Malformed resources are skipped during discovery with debug logging

When modifying the Kubernetes integration, always test both in-cluster and local kubeconfig scenarios. The dynamic resource discovery should handle any Kubernetes API version automatically.