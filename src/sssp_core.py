"""Compatibility facade for the SSSP v0.1 core package."""
from sssp import SSSPError, SSSPStore, node_checksum, validate_document_obj, utc_now

__all__ = ["SSSPError", "SSSPStore", "node_checksum", "validate_document_obj", "utc_now"]
