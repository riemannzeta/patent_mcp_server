"""
Google Patents integration for patent_mcp_server.

This module provides access to Google Patents Public Datasets via BigQuery.
"""

from patent_mcp_server.google.bigquery_client import GoogleBigQueryClient

__all__ = ["GoogleBigQueryClient"]
