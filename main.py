import logging
from typing import Any, Dict, List, Optional, Union

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.dynamic.client import DynamicClient
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("kubediag", stateless_http=True)


# Pydantic models for tool requests with descriptions
class KubernetesListRequest(BaseModel):
    """Request model for listing Kubernetes resources"""

    namespace: Optional[str] = Field(
        default="default", description="Target namespace for listing resources"
    )
    resource_type: Optional[str] = Field(
        default="pods",
        description="Kubernetes resource type to list (e.g., pods, services, deployments, configmaps, secrets, jobs, cronjobs, daemonsets, statefulsets, ingresses)",
    )


class KubernetesGetRequest(BaseModel):
    """Request model for getting details of a specific Kubernetes resource"""

    namespace: Optional[str] = Field(
        default="default", description="Target namespace where the resource is located"
    )
    resource_type: Optional[str] = Field(
        default="pods",
        description="Kubernetes resource type (e.g., pods, services, deployments, configmaps, secrets, jobs, cronjobs, daemonsets, statefulsets, ingresses)",
    )
    name: str = Field(description="Name of the specific resource to get details for")


# Initialize Kubernetes client with in-cluster auto configuration
def init_kubernetes_client() -> None:
    """Initialize Kubernetes client with automatic configuration"""
    try:
        # Try in-cluster config first (when running inside a pod)
        config.load_incluster_config()
        logger.info("Using in-cluster Kubernetes configuration")
    except config.ConfigException:
        try:
            # Fall back to kubeconfig file
            config.load_kube_config()
            logger.info("Using kubeconfig file for Kubernetes configuration")
        except config.ConfigException as e:
            logger.error("Failed to load Kubernetes configuration: %s", e)
            raise Exception("Could not load Kubernetes configuration") from e


# Initialize the Kubernetes client
init_kubernetes_client()

# Create dynamic client for automatic resource discovery
dynamic_client = DynamicClient(client.ApiClient())

# Cache for resource APIs to avoid repeated expensive discovery operations
_resource_api_cache: Dict[str, Optional[Any]] = {}


def get_resource_api(resource_type: str) -> Optional[Any]:
    """Dynamically get the appropriate API for a resource type with caching"""
    # Check cache first
    if resource_type in _resource_api_cache:
        logger.debug("Using cached resource API for %s", resource_type)
        return _resource_api_cache[resource_type]

    try:
        # Get all available resources - search() takes no arguments, returns all resources
        all_resources = dynamic_client.resources.search()

        # Find resources matching the type (case insensitive)
        matching_resources = [
            resource
            for resource in all_resources
            if resource_type.lower()
            in [resource.name.lower(), resource.name.lower() + "s"]
        ]

        if not matching_resources:
            logger.warning("No matching resources found for type: %s", resource_type)
            _resource_api_cache[resource_type] = None
            return None

        # Prefer namespaced resources, fallback to cluster-scoped
        for resource in matching_resources:
            if hasattr(resource, "namespaced") and resource.namespaced:
                logger.debug("Found namespaced resource API for %s", resource_type)
                _resource_api_cache[resource_type] = resource
                return resource

        # Return first available resource if no namespaced version found
        resource = matching_resources[0]
        logger.debug("Using cluster-scoped resource API for %s", resource_type)
        _resource_api_cache[resource_type] = resource
        return resource

    except Exception as e:
        logger.error("Error discovering resource API for %s: %s", resource_type, e)
        _resource_api_cache[resource_type] = None
        return None


def _truncate_deep(obj: Any, max_length: int = 256) -> Any:
    """Efficiently truncate values in a nested data structure"""
    obj_type = type(obj)

    if obj_type is str:
        if len(obj) > max_length:
            return f"{obj[:max_length]}... [truncated, original length: {len(obj)}]"
        return obj
    elif obj_type is dict:
        return {k: _truncate_deep(v, max_length) for k, v in obj.items()}
    elif obj_type is list:
        return [_truncate_deep(item, max_length) for item in obj]
    elif obj_type in (int, float, bool, type(None)):
        return obj
    else:
        # For other types, convert to string and truncate if needed
        str_val = str(obj)
        if len(str_val) > max_length:
            return f"{str_val[:max_length]}... [truncated, original length: {len(str_val)}]"
        return str_val


def clean_resource_object(obj: Any, resource_type: str) -> Dict[str, Any]:
    """Clean the original resource object according to the specified rules"""
    if not obj:
        return {}

    # Convert to dict if it's a Kubernetes object
    if hasattr(obj, "to_dict"):
        result = obj.to_dict()
    elif hasattr(obj, "__dict__"):
        result = obj.__dict__.copy()
    else:
        result = dict(obj) if hasattr(obj, "__iter__") else {}

    # Rule 1: Clean metadata - keep only namespace, name, labels, annotations
    if "metadata" in result and result["metadata"]:
        original_metadata = result["metadata"]
        cleaned_metadata = {}

        # Keep only essential metadata fields
        for field in ("name", "namespace", "labels"):
            if field in original_metadata:
                cleaned_metadata[field] = original_metadata[field]

        # Clean annotations - remove internal Kubernetes fields
        if "annotations" in original_metadata and original_metadata["annotations"]:
            cleaned_annotations = {
                key: value
                for key, value in original_metadata["annotations"].items()
                if not (
                    key.startswith("kubectl.kubernetes.io/")
                    or key.startswith("kubernetes.io/")
                )
            }
            if cleaned_annotations:  # Only add if not empty
                cleaned_metadata["annotations"] = cleaned_annotations

        result["metadata"] = cleaned_metadata

    # Rule 2: If it's a secret, redact data field values
    if resource_type == "secrets" and "data" in result and result["data"]:
        result["data"] = {key: "REDACTED" for key in result["data"]}

    # Rule 3: Truncate values longer than 256 characters
    return _truncate_deep(result)


def _create_empty_response(
    resource_type: str, namespace: str
) -> Dict[str, Union[str, List[str]]]:
    """Create an empty response structure for list operations"""
    return {
        "api_group": "",
        "api_version": "",
        "resource_name": resource_type,
        "names": [],
        "namespace": namespace,
    }


def _extract_resource_info(
    resource_api: Any, resource_type: str
) -> tuple[str, str, str]:
    """Extract API group, version, and resource name from resource API"""
    api_group = getattr(resource_api, "group", "") or ""
    api_version = getattr(resource_api, "api_version", "") or ""
    resource_name = getattr(resource_api, "name", resource_type) or resource_type
    return api_group, api_version, resource_name


def _extract_resource_names(result: Any) -> List[str]:
    """Extract resource names from API response"""
    if hasattr(result, "items"):
        return [item.metadata.name for item in result.items]
    else:
        return [result.metadata.name] if hasattr(result, "metadata") else []


@mcp.tool()
def kubernetes_list(request: KubernetesListRequest) -> Dict[str, Union[str, List[str]]]:
    """List Kubernetes resources of specified type in a namespace

    Returns detailed information about the resolved resource type along with
    the list of resource names in the specified namespace.
    Supports any Kubernetes resource type with automatic discovery.

    Args:
        request: Request containing namespace and resource_type

    Returns:
        Dictionary containing api_group, api_version, resource_name, names list, and namespace
    """
    resource_type = (request.resource_type or "pods").lower()
    namespace = request.namespace or "default"

    try:
        # Get the appropriate API resource
        resource_api = get_resource_api(resource_type)

        if not resource_api:
            # Return response with empty names list if resource not found
            logger.warning("Resource type '%s' not found in cluster", resource_type)
            return _create_empty_response(resource_type, namespace)

        # Extract resource information
        api_group, api_version, resource_name = _extract_resource_info(
            resource_api, resource_type
        )

        # List resources
        if hasattr(resource_api, "namespaced") and resource_api.namespaced:
            result = resource_api.get(namespace=namespace)
        else:
            result = resource_api.get()

        # Extract resource names
        names = _extract_resource_names(result)

        logger.info(
            "Listed %d %s resources in namespace %s",
            len(names),
            resource_type,
            namespace,
        )
        return {
            "api_group": api_group,
            "api_version": api_version,
            "resource_name": resource_name,
            "names": names,
            "namespace": namespace,
        }

    except ApiException as e:
        logger.error(
            "API error listing %s in namespace %s: %s",
            resource_type,
            namespace,
            e.reason,
        )
        return _create_empty_response(resource_type, namespace)
    except Exception as e:
        logger.error(
            "Unexpected error listing %s in namespace %s: %s",
            resource_type,
            namespace,
            e,
        )
        return _create_empty_response(resource_type, namespace)


@mcp.tool()
def kubernetes_get(request: KubernetesGetRequest) -> Dict[str, Any]:
    """Get details of a specific Kubernetes resource with data cleaning

    Returns cleaned resource details with:
    - Metadata filtered to essential fields only
    - Secret values redacted (replaced with "REDACTED")
    - Long values truncated to 256 characters with length info
    - Internal Kubernetes annotations removed

    Supports any Kubernetes resource type with automatic discovery.

    Args:
        request: Request containing namespace, resource_type, and name

    Returns:
        Dictionary containing cleaned resource data or error information
    """
    resource_type = (request.resource_type or "pods").lower()

    try:
        # Get the appropriate API resource
        resource_api = get_resource_api(resource_type)

        if not resource_api:
            error_msg = f"Resource type '{resource_type}' not found in cluster"
            logger.error(error_msg)
            return {"error": error_msg}

        # Get the specific resource
        if hasattr(resource_api, "namespaced") and resource_api.namespaced:
            result = resource_api.get(name=request.name, namespace=request.namespace)
        else:
            result = resource_api.get(name=request.name)

        # Clean the original resource object according to the rules
        cleaned_result = clean_resource_object(result, resource_type)

        # Ensure we return a proper dict, handle edge cases
        if isinstance(cleaned_result, dict):
            logger.info(
                "Retrieved %s '%s' from namespace %s",
                resource_type,
                request.name,
                request.namespace,
            )
            return cleaned_result
        elif cleaned_result is None:
            return {"error": "No data returned from resource"}
        else:
            return {"data": str(cleaned_result)}

    except ApiException as e:
        error_msg = f"Error getting {resource_type} '{request.name}': {e.reason}"
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Error getting {resource_type} '{request.name}': {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
