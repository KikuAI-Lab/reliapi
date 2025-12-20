"""YAML configuration loader for routes-based ReliAPI."""
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from reliapi.config.schema import ReliAPIConfig


class ConfigLoader:
    """Load and parse ReliAPI routes-based configuration."""

    def __init__(self, config_path: str):
        """
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """Load and validate configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, "r") as f:
                raw_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in {self.config_path}: {e}") from e

        # Validate through Pydantic
        try:
            validated_config = ReliAPIConfig(**raw_config)
            # Convert back to dict for compatibility
            self.config = validated_config.model_dump(exclude_none=True)
        except Exception as e:
            raise ValueError(f"Configuration validation failed in {self.config_path}: {e}") from e

        return self.config

    def get_targets(self) -> Dict[str, Dict[str, Any]]:
        """Get targets configuration (new schema)."""
        return self.config.get("targets", {})

    def get_upstreams(self) -> Dict[str, Dict[str, Any]]:
        """Get upstreams configuration (legacy, maps to targets)."""
        return self.config.get("upstreams", self.get_targets())

    def get_routes(self) -> List[Dict[str, Any]]:
        """Get routes configuration."""
        return self.config.get("routes", [])

    def get_target(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific target configuration."""
        return self.get_targets().get(name)
    
    def get_tenants(self) -> Optional[Dict[str, Any]]:
        """Get tenants configuration."""
        return self.config.get("tenants")
    
    def get_tenant(self, tenant_name: str) -> Optional[Dict[str, Any]]:
        """Get specific tenant configuration."""
        tenants = self.get_tenants()
        if not tenants:
            return None
        return tenants.get(tenant_name)
    
    def find_tenant_by_api_key(self, api_key: str) -> Optional[str]:
        """Find tenant name by API key.
        
        Returns:
            Tenant name if found, None otherwise
        """
        tenants = self.get_tenants()
        if not tenants:
            return None
        
        for tenant_name, tenant_config in tenants.items():
            if tenant_config.get("api_key") == api_key:
                return tenant_name
        
        return None

    def get_provider_key_pools(self) -> Optional[Dict[str, Any]]:
        """Get provider key pools configuration."""
        return self.config.get("provider_key_pools")

    def get_client_profiles(self) -> Optional[Dict[str, Any]]:
        """Get client profiles configuration."""
        return self.config.get("client_profiles")

    def get_upstream(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific upstream configuration (legacy)."""
        return self.get_target(name) or self.get_upstreams().get(name)

    def find_route(
        self, method: str, path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find matching route for method and path.
        
        Args:
            method: HTTP method
            path: Request path
            
        Returns:
            Route configuration or None
        """
        for route in self.get_routes():
            match = route.get("match", {})
            route_path = match.get("path", "")
            route_methods = match.get("methods", [])

            # Simple path matching (supports ** wildcard)
            if self._path_matches(path, route_path) and (
                not route_methods or method.upper() in [m.upper() for m in route_methods]
            ):
                return route

        return None

    def _path_matches(self, request_path: str, route_path: str) -> bool:
        """Simple path matching with ** wildcard support."""
        if route_path == request_path:
            return True

        # Support ** wildcard
        if "**" in route_path:
            prefix = route_path.replace("**", "")
            return request_path.startswith(prefix)

        # Support * single segment wildcard
        if "*" in route_path:
            import re
            pattern = route_path.replace("*", "[^/]+")
            return bool(re.match(pattern, request_path))

        return False


