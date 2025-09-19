import logging
import os
from typing import Any, Dict, Optional, List

from kubernetes import client, config
from kubernetes.client import Configuration
from kubernetes.client.rest import ApiException
from kubernetes.dynamic.client import DynamicClient

logger = logging.getLogger(__name__)


def _create_configuration() -> Configuration:
    cfg = Configuration()
    try:
        config.load_incluster_config(client_configuration=cfg)
        logger.info("Using in-cluster Kubernetes configuration")
    except config.ConfigException:
        try:
            config.load_kube_config(client_configuration=cfg)
            logger.info("Using kubeconfig file for Kubernetes configuration")
        except config.ConfigException as e:
            logger.error("Failed to load Kubernetes configuration: %s", e)
            raise Exception("Could not load Kubernetes configuration") from e
    if os.getenv("KUBERNETES_INSECURE", "false").lower() == "true":
        import urllib3

        urllib3.disable_warnings()
        cfg.verify_ssl = False
    return cfg


_configuration = _create_configuration()

dynamic_client = DynamicClient(client.ApiClient(configuration=_configuration))

_resource_api_cache: Dict[str, Optional[Any]] = {}


def get_resource_api(resource_type: str) -> Optional[Any]:
    if resource_type in _resource_api_cache:
        return _resource_api_cache[resource_type]

    try:
        all_resources = dynamic_client.resources.search()

        matching_resources = []
        for resource in all_resources:
            try:
                # Safely check if the resource name matches, handling malformed resources
                if hasattr(resource, "name") and resource.name == resource_type:
                    matching_resources.append(resource)
            except Exception as e:
                # Log and skip malformed or inaccessible resources
                logger.debug("Skipping malformed resource during discovery: %s", e)
                continue

        if not matching_resources:
            _resource_api_cache[resource_type] = None
            logger.error("Resource type %s not found in the cluster", resource_type)
            return None

        # Prefer core Kubernetes resources over custom resources when there are multiple matches
        # Core resources have empty group ('') and standard API versions like 'v1', 'v1beta1'
        preferred_resource = None
        for resource in matching_resources:
            try:
                # Check if this is a core Kubernetes resource (empty group)
                if hasattr(resource, "group") and resource.group == "":
                    preferred_resource = resource
                    break
                # If no core resource found yet, use the first valid one as fallback
                elif preferred_resource is None:
                    preferred_resource = resource
            except Exception as e:
                logger.debug(
                    "Error checking resource properties for %s: %s", resource_type, e
                )
                continue

        # Use the preferred resource or fallback to the first one
        resource = preferred_resource or matching_resources[0]

        _resource_api_cache[resource_type] = resource

        return resource
    except Exception as e:
        logger.error("Error discovering resource API for %s: %s", resource_type, e)
        _resource_api_cache[resource_type] = None
        return None


def _truncate_deep(obj: Any, max_length: int = 256) -> Any:
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
        str_val = str(obj)
        if len(str_val) > max_length:
            return f"{str_val[:max_length]}... [truncated, original length: {len(str_val)}]"
        return str_val


def clean_resource_object(obj: Any, resource_type: str) -> Dict[str, Any]:
    if not obj:
        return {}

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

        # Clean annotations - remove internal Kubernetes fields and useless information
        if "annotations" in original_metadata and original_metadata["annotations"]:
            cleaned_annotations = {
                key: value
                for key, value in original_metadata["annotations"].items()
                if not (
                    key.startswith("kubectl.kubernetes.io/")
                    or key.startswith("kubernetes.io/")
                    or key == "kubectl.kubernetes.io/last-applied-configuration"
                    or key.endswith("/last-applied-configuration")
                    or key == "deployment.kubernetes.io/revision"
                    or key.startswith("deployment.kubernetes.io/")
                    or key.startswith("pod-template-generation")
                    or key.startswith("autoscaling.")
                    or key.startswith("control-plane.")
                    or key.startswith("deployment.")
                    or key.startswith("job.")
                    or key.startswith("batch.")
                    or key.startswith("meta.helm.sh/")
                    or key.startswith("helm.sh/")
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


def extract_resource_info(
    resource_api: Any, resource_type: str
) -> tuple[str, str, str]:
    api_group = getattr(resource_api, "group", "") or ""
    api_version = getattr(resource_api, "api_version", "") or ""
    resource_name = getattr(resource_api, "name", resource_type) or resource_type
    return api_group, api_version, resource_name


def extract_resource_names(result: Any) -> List[str]:
    if hasattr(result, "items"):
        return [item.metadata.name for item in result.items]
    else:
        return [result.metadata.name] if hasattr(result, "metadata") else []


__all__ = (
    "dynamic_client",
    "ApiException",
    "get_resource_api",
    "clean_resource_object",
    "extract_resource_info",
    "extract_resource_names",
)
