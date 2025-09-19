import logging
from typing import Any, List, Optional, Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import BaseModel

from .env import *
from .kubernetes import *

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "kubediag",
    version="1.0",
    auth=JWTVerifier(
        public_key=SECRET_KEY,
        algorithm="HS256",
    ),
)


class KubernetesListResponse(BaseModel):
    class ResourceType(BaseModel):
        group: str
        api_version: str
        name: str

    resource_type: ResourceType
    namespace: str
    names: List[str]


@mcp.tool(description="List Kubernetes resources of specified type in a namespace")
def kubernetes_list(
    resource_type: Annotated[
        str,
        "Kubernetes resource type in lowercase plural form (e.g., 'pods', 'services', 'deployments', 'configmaps', 'nodes', 'namespaces')",
    ],
    namespace: Optional[
        Annotated[
            str,
            "Kubernetes namespace (default: 'default'). Note: For cluster-scoped resources like 'nodes', 'namespaces', 'clusterroles', this parameter is ignored",
        ]
    ] = "default",
) -> KubernetesListResponse:
    resource_type = (resource_type or "pods").lower()
    namespace = namespace or "default"

    try:
        resource_api = get_resource_api(resource_type)

        if not resource_api:
            error_msg = f"Resource type '{resource_type}' not found in cluster"
            logger.error(error_msg)
            raise ToolError(error_msg)

        api_group, api_version, resource_name = extract_resource_info(
            resource_api, resource_type
        )

        if hasattr(resource_api, "namespaced") and resource_api.namespaced:
            result = resource_api.get(namespace=namespace)
        else:
            result = resource_api.get()

        names = extract_resource_names(result)

        logger.info(
            "Listed %d %s resources in namespace %s",
            len(names),
            resource_type,
            namespace,
        )
        return KubernetesListResponse(
            resource_type=KubernetesListResponse.ResourceType(
                group=api_group,
                api_version=api_version,
                name=resource_name,
            ),
            names=names,
            namespace=namespace,
        )
    except ApiException as e:
        error_msg = (
            f"API error listing {resource_type} in namespace {namespace}: {e.reason}"
        )
        logger.error(error_msg)
        raise ToolError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error listing {resource_type} in namespace {namespace}: {str(e)}"
        logger.error(error_msg)
        raise ToolError(error_msg) from e


@mcp.tool(description="Get details of a specific Kubernetes resource")
def kubernetes_get(
    resource_type: Annotated[
        str,
        "Kubernetes resource type in lowercase plural form (e.g., 'pods', 'services', 'deployments', 'configmaps', 'nodes', 'namespaces')",
    ],
    name: Annotated[str, "Name of the Kubernetes resource"],
    namespace: Optional[
        Annotated[
            str,
            "Kubernetes namespace (default: 'default'). Note: For cluster-scoped resources like 'nodes', 'namespaces', 'clusterroles', this parameter is ignored",
        ]
    ] = "default",
) -> dict:
    resource_type = (resource_type or "pods").lower()
    namespace = namespace or "default"

    try:
        # Get the appropriate API resource
        resource_api = get_resource_api(resource_type)

        if not resource_api:
            error_msg = f"Resource type '{resource_type}' not found in cluster"
            logger.error(error_msg)
            raise ToolError(error_msg)

        # Get the specific resource
        if hasattr(resource_api, "namespaced") and resource_api.namespaced:
            result = resource_api.get(name=name, namespace=namespace)
        else:
            result = resource_api.get(name=name)

        # Clean the original resource object according to the rules
        cleaned_result = clean_resource_object(result, resource_type)

        # Ensure we return a proper dict, handle edge cases
        if isinstance(cleaned_result, dict):
            logger.info(
                "Retrieved %s '%s' from namespace %s",
                resource_type,
                name,
                namespace,
            )
            return cleaned_result
        elif cleaned_result is None:
            raise ToolError("No data returned from resource")
        else:
            return {"data": str(cleaned_result)}

    except ApiException as e:
        error_msg = f"Error getting {resource_type} '{name}': {e.reason}"
        logger.error(error_msg)
        raise ToolError(error_msg) from e
    except Exception as e:
        error_msg = f"Error getting {resource_type} '{name}': {str(e)}"
        logger.error(error_msg)
        raise ToolError(error_msg) from e


__all__ = ("mcp",)
