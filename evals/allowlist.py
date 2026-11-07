"""LangSmith Sandbox adapter with Harbor hostname policy support (Harbor 0.18.0)."""

from __future__ import annotations

import asyncio
from typing import override

from harbor.environments.capabilities import EnvironmentCapabilities
from harbor.environments.langsmith import LangSmithEnvironment
from harbor.models.task.config import NetworkMode, NetworkPolicy
from langsmith._openapi_client import Langsmith


class AllowlistedLangSmithEnvironment(LangSmithEnvironment):
    @property
    @override
    def capabilities(self) -> EnvironmentCapabilities:
        return EnvironmentCapabilities(
            disable_internet=True,
            network_allowlist=True,
            network_allowlist_hostnames=True,
            network_allowlist_wildcard_hostnames=True,
            network_allowlist_ipv4_addresses=True,
            network_allowlist_ipv6_addresses=True,
            network_allowlist_ipv4_cidrs=True,
            network_allowlist_ipv6_cidrs=True,
            dynamic_network_policy=True,
            docker_compose=True,
        )

    @staticmethod
    def _proxy_config_for_policy(policy: NetworkPolicy) -> dict[str, object]:
        match policy.network_mode:
            case NetworkMode.PUBLIC:
                access_control = {"deny_list": []}
            case NetworkMode.NO_NETWORK:
                access_control = {"deny_list": ["*"]}
            case NetworkMode.ALLOWLIST:
                access_control = {"allow_list": list(policy.allowed_hosts)}
        return {"rules": [], "no_proxy": [], "access_control": access_control}

    @override
    def _create_sandbox_payload(self, snapshot_name: str | None) -> dict[str, object]:
        payload = super()._create_sandbox_payload(snapshot_name)
        payload["proxy_config"] = self._proxy_config_for_policy(self._network_policy)
        return payload

    @override
    async def _apply_network_policy(self, policy: NetworkPolicy) -> None:
        await asyncio.to_thread(self._update_proxy_config, self._proxy_config_for_policy(policy))

    def _update_proxy_config(self, config: dict[str, object]) -> None:
        client = Langsmith(
            api_key=self._api_key,
            base_url=self._langsmith_endpoint,
            default_headers=self._langsmith_client_headers() or None,
        )
        try:
            client.sandboxes.boxes.update(path_name=self._sandbox_name, proxy_config=config)
        finally:
            client.close()
