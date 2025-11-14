"""
Client for accessing Google Patents Public Datasets via BigQuery.

This module provides async access to Google's comprehensive patent database
containing 90M+ patent publications from 17+ countries.
"""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from google.auth import default
from google.cloud import bigquery

from patent_mcp_server.config import config
from patent_mcp_server.constants import GooglePatentsTables
from patent_mcp_server.util.errors import ApiError

logger = logging.getLogger(__name__)


class GoogleBigQueryClient:
    """Client for accessing Google Patents Public Datasets via BigQuery."""

    def __init__(self):
        """Initialize BigQuery client with authentication."""
        self.project_id = config.GOOGLE_CLOUD_PROJECT
        self.dataset_id = config.BIGQUERY_DATASET
        self.location = config.BIGQUERY_LOCATION
        self.query_timeout = config.BIGQUERY_QUERY_TIMEOUT
        self.max_results = config.BIGQUERY_MAX_RESULTS

        # BigQuery client (sync API, we'll wrap in executor)
        try:
            # Set timeout for GCE metadata server queries to prevent hanging
            # when Google Cloud credentials are not available
            if "GCE_METADATA_TIMEOUT" not in os.environ:
                os.environ["GCE_METADATA_TIMEOUT"] = "5"

            credentials, project = default()
            self.client = bigquery.Client(
                credentials=credentials,
                project=self.project_id or project,
            )
            logger.info(
                f"Initialized Google BigQuery client for project: {self.project_id or project}"
            )
        except Exception as e:
            logger.warning(
                f"Google BigQuery client not available: {str(e)}. "
                "Google Patents features will be disabled. "
                "To enable, configure GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS "
                "environment variables. See README for setup instructions."
            )
            self.client = None

        # Thread pool for async execution
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def query_async(
        self, query: str, parameters: Optional[List] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute BigQuery query asynchronously.

        Args:
            query: SQL query string
            parameters: Optional list of query parameters

        Returns:
            List of dictionaries representing query results
        """
        if not self.client:
            raise ValueError(
                "BigQuery client not initialized. Check Google Cloud credentials."
            )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor, self._execute_query, query, parameters
        )
        return result

    def _execute_query(
        self, query: str, parameters: Optional[List] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute BigQuery query (sync).

        Args:
            query: SQL query string
            parameters: Optional list of query parameters

        Returns:
            List of dictionaries representing query results
        """
        job_config = bigquery.QueryJobConfig(query_parameters=parameters or [])

        try:
            query_job = self.client.query(
                query, job_config=job_config, location=self.location
            )

            results = query_job.result(timeout=self.query_timeout)

            # Convert to list of dicts
            rows = [dict(row) for row in results]

            logger.info(
                f"Query executed successfully, returned {len(rows)} rows, "
                f"processed {query_job.total_bytes_processed} bytes"
            )

            return rows

        except Exception as e:
            logger.error(f"BigQuery query failed: {str(e)}")
            raise

    async def search_patents(
        self, query: str, country: str = "US", limit: int = 100
    ) -> Dict[str, Any]:
        """
        Search patents using full-text search.

        Args:
            query: Search query string (searches titles and abstracts)
            country: Country code (US, EP, WO, JP, CN, etc.)
            limit: Maximum number of results to return

        Returns:
            Dictionary containing search results with patent metadata
        """
        try:
            # Build SQL query
            sql = f"""
            SELECT
                publication_number,
                title_localized,
                abstract_localized,
                publication_date,
                filing_date,
                grant_date,
                inventor_harmonized,
                assignee_harmonized,
                cpc,
                ipc,
                family_id,
                country_code,
                application_number
            FROM `{self.dataset_id}.{GooglePatentsTables.PUBLICATIONS}`
            WHERE
                country_code = @country
                AND (
                    LOWER(title_localized[SAFE_OFFSET(0)].text) LIKE @query
                    OR LOWER(abstract_localized[SAFE_OFFSET(0)].text) LIKE @query
                )
            ORDER BY publication_date DESC
            LIMIT @limit
            """

            parameters = [
                bigquery.ScalarQueryParameter("country", "STRING", country),
                bigquery.ScalarQueryParameter("query", "STRING", f"%{query.lower()}%"),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ]

            results = await self.query_async(sql, parameters)

            return {"success": True, "count": len(results), "results": results}

        except Exception as e:
            logger.error(f"Error searching Google Patents: {str(e)}")
            return ApiError.create(
                message=f"Failed to search Google Patents: {str(e)}", status_code=500
            )

    async def get_patent_by_number(
        self, publication_number: str
    ) -> Dict[str, Any]:
        """
        Get patent details by publication number.

        Args:
            publication_number: Patent publication number (e.g., US-9876543-B2)

        Returns:
            Dictionary containing complete patent details
        """
        try:
            sql = f"""
            SELECT *
            FROM `{self.dataset_id}.{GooglePatentsTables.PUBLICATIONS}`
            WHERE publication_number = @publication_number
            LIMIT 1
            """

            parameters = [
                bigquery.ScalarQueryParameter(
                    "publication_number", "STRING", publication_number
                )
            ]

            results = await self.query_async(sql, parameters)

            if not results:
                return ApiError.not_found("Patent", publication_number)

            return {"success": True, "patent": results[0]}

        except Exception as e:
            logger.error(
                f"Error fetching patent {publication_number}: {str(e)}"
            )
            return ApiError.create(
                message=f"Failed to fetch patent: {str(e)}", status_code=500
            )

    async def get_patent_claims(
        self, publication_number: str
    ) -> Dict[str, Any]:
        """
        Get patent claims by publication number.

        Args:
            publication_number: Patent publication number (e.g., US-9876543-B2)

        Returns:
            Dictionary containing claim number and text for each claim
        """
        try:
            sql = f"""
            SELECT
                claim_num,
                claim_text
            FROM `{self.dataset_id}.{GooglePatentsTables.PUBLICATIONS_CLAIMS}`
            WHERE publication_number = @publication_number
            ORDER BY claim_num
            """

            parameters = [
                bigquery.ScalarQueryParameter(
                    "publication_number", "STRING", publication_number
                )
            ]

            results = await self.query_async(sql, parameters)

            return {
                "success": True,
                "publication_number": publication_number,
                "claims_count": len(results),
                "claims": results,
            }

        except Exception as e:
            logger.error(
                f"Error fetching claims for {publication_number}: {str(e)}"
            )
            return ApiError.create(
                message=f"Failed to fetch claims: {str(e)}", status_code=500
            )

    async def get_patent_description(
        self, publication_number: str
    ) -> Dict[str, Any]:
        """
        Get patent description by publication number.

        Args:
            publication_number: Patent publication number (e.g., US-9876543-B2)

        Returns:
            Dictionary containing patent description text
        """
        try:
            sql = f"""
            SELECT
                publication_number,
                description_text,
                description_length
            FROM `{self.dataset_id}.{GooglePatentsTables.PUBLICATIONS_DESCRIPTION}`
            WHERE publication_number = @publication_number
            LIMIT 1
            """

            parameters = [
                bigquery.ScalarQueryParameter(
                    "publication_number", "STRING", publication_number
                )
            ]

            results = await self.query_async(sql, parameters)

            if not results:
                return ApiError.not_found(
                    "Patent description", publication_number
                )

            return {"success": True, "description": results[0]}

        except Exception as e:
            logger.error(
                f"Error fetching description for {publication_number}: {str(e)}"
            )
            return ApiError.create(
                message=f"Failed to fetch description: {str(e)}",
                status_code=500,
            )

    async def search_by_inventor(
        self, inventor_name: str, country: str = "US", limit: int = 100
    ) -> Dict[str, Any]:
        """
        Search patents by inventor name.

        Args:
            inventor_name: Inventor name to search for
            country: Country code (US, EP, WO, JP, CN, etc.)
            limit: Maximum number of results to return

        Returns:
            Dictionary containing search results
        """
        try:
            sql = f"""
            SELECT
                publication_number,
                title_localized,
                publication_date,
                inventor_harmonized,
                assignee_harmonized,
                country_code
            FROM `{self.dataset_id}.{GooglePatentsTables.PUBLICATIONS}`
            WHERE
                country_code = @country
                AND EXISTS (
                    SELECT 1 FROM UNNEST(inventor_harmonized) AS inv
                    WHERE LOWER(inv.name) LIKE @inventor_name
                )
            ORDER BY publication_date DESC
            LIMIT @limit
            """

            parameters = [
                bigquery.ScalarQueryParameter("country", "STRING", country),
                bigquery.ScalarQueryParameter(
                    "inventor_name", "STRING", f"%{inventor_name.lower()}%"
                ),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ]

            results = await self.query_async(sql, parameters)

            return {
                "success": True,
                "count": len(results),
                "inventor": inventor_name,
                "results": results,
            }

        except Exception as e:
            logger.error(f"Error searching by inventor: {str(e)}")
            return ApiError.create(
                message=f"Failed to search by inventor: {str(e)}",
                status_code=500,
            )

    async def search_by_assignee(
        self, assignee_name: str, country: str = "US", limit: int = 100
    ) -> Dict[str, Any]:
        """
        Search patents by assignee/company name.

        Args:
            assignee_name: Assignee/company name to search for
            country: Country code (US, EP, WO, JP, CN, etc.)
            limit: Maximum number of results to return

        Returns:
            Dictionary containing search results
        """
        try:
            sql = f"""
            SELECT
                publication_number,
                title_localized,
                publication_date,
                inventor_harmonized,
                assignee_harmonized,
                country_code
            FROM `{self.dataset_id}.{GooglePatentsTables.PUBLICATIONS}`
            WHERE
                country_code = @country
                AND EXISTS (
                    SELECT 1 FROM UNNEST(assignee_harmonized) AS asn
                    WHERE LOWER(asn.name) LIKE @assignee_name
                )
            ORDER BY publication_date DESC
            LIMIT @limit
            """

            parameters = [
                bigquery.ScalarQueryParameter("country", "STRING", country),
                bigquery.ScalarQueryParameter(
                    "assignee_name", "STRING", f"%{assignee_name.lower()}%"
                ),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ]

            results = await self.query_async(sql, parameters)

            return {
                "success": True,
                "count": len(results),
                "assignee": assignee_name,
                "results": results,
            }

        except Exception as e:
            logger.error(f"Error searching by assignee: {str(e)}")
            return ApiError.create(
                message=f"Failed to search by assignee: {str(e)}",
                status_code=500,
            )

    async def search_by_cpc(
        self, cpc_code: str, country: str = "US", limit: int = 100
    ) -> Dict[str, Any]:
        """
        Search patents by CPC (Cooperative Patent Classification) code.

        Args:
            cpc_code: CPC code to search for (e.g., G06N3/08)
            country: Country code (US, EP, WO, JP, CN, etc.)
            limit: Maximum number of results to return

        Returns:
            Dictionary containing search results
        """
        try:
            sql = f"""
            SELECT
                publication_number,
                title_localized,
                publication_date,
                inventor_harmonized,
                assignee_harmonized,
                cpc,
                country_code
            FROM `{self.dataset_id}.{GooglePatentsTables.PUBLICATIONS}`
            WHERE
                country_code = @country
                AND EXISTS (
                    SELECT 1 FROM UNNEST(cpc) AS c
                    WHERE c.code LIKE @cpc_code
                )
            ORDER BY publication_date DESC
            LIMIT @limit
            """

            parameters = [
                bigquery.ScalarQueryParameter("country", "STRING", country),
                bigquery.ScalarQueryParameter("cpc_code", "STRING", f"{cpc_code}%"),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ]

            results = await self.query_async(sql, parameters)

            return {
                "success": True,
                "count": len(results),
                "cpc_code": cpc_code,
                "results": results,
            }

        except Exception as e:
            logger.error(f"Error searching by CPC code: {str(e)}")
            return ApiError.create(
                message=f"Failed to search by CPC code: {str(e)}",
                status_code=500,
            )

    async def close(self):
        """Clean up resources."""
        try:
            self.executor.shutdown(wait=True)
            if self.client:
                self.client.close()
            logger.info("Google BigQuery client closed successfully")
        except Exception as e:
            logger.error(f"Error closing BigQuery client: {str(e)}")
