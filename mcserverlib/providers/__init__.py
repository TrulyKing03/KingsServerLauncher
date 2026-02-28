from __future__ import annotations

from .base import LoaderProvider
from .fabric import FabricProvider
from .forge import ForgeProvider
from .neoforge import NeoForgeProvider
from .paper_family import FoliaProvider, PaperProvider
from .purpur import PurpurProvider
from .quilt import QuiltProvider
from .vanilla import VanillaProvider


def create_provider_registry() -> dict[str, LoaderProvider]:
    providers: list[LoaderProvider] = [
        VanillaProvider(),
        PaperProvider(),
        FoliaProvider(),
        PurpurProvider(),
        FabricProvider(),
        QuiltProvider(),
        ForgeProvider(),
        NeoForgeProvider(),
    ]
    return {provider.loader_id: provider for provider in providers}


__all__ = [
    "LoaderProvider",
    "create_provider_registry",
]
