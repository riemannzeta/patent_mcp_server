"""
Response normalization utilities for consistent API responses.

This module provides utilities for:
- Standardizing response format across different backends
- Token budget awareness and response truncation
- Response envelope creation
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from patent_mcp_server.config import config

logger = logging.getLogger('response_util')


class ResponseEnvelope:
    """Standard response envelope for all API responses."""

    @staticmethod
    def success(
        results: Union[List[Any], Dict[str, Any], Any],
        source: str,
        count: Optional[int] = None,
        total: Optional[int] = None,
        offset: int = 0,
        limit: int = 100,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a standardized success response.

        Args:
            results: The actual results data
            source: Data source identifier (e.g., 'patentsview', 'ppubs', 'odp')
            count: Number of results in this response
            total: Total available results (for pagination)
            offset: Current offset position
            limit: Requested limit
            metadata: Optional source-specific metadata

        Returns:
            Standardized response dictionary
        """
        # Calculate count if not provided
        if count is None:
            if isinstance(results, list):
                count = len(results)
            elif isinstance(results, dict):
                count = 1
            else:
                count = 1 if results is not None else 0

        # Calculate has_more
        if total is not None:
            has_more = (offset + count) < total
        else:
            has_more = False
            total = count

        response = {
            "success": True,
            "source": source,
            "count": count,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
            "results": results,
        }

        if metadata:
            response["metadata"] = metadata

        return response

    @staticmethod
    def from_ppubs(
        raw_response: Dict[str, Any],
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Normalize a PPUBS API response.

        Args:
            raw_response: Raw response from PPUBS API
            offset: Requested offset
            limit: Requested limit

        Returns:
            Standardized response
        """
        # PPUBS format: {numFound, perPage, page, patents: [...]}
        results = raw_response.get("patents", [])
        total = raw_response.get("numFound", len(results))

        return ResponseEnvelope.success(
            results=results,
            source="ppubs",
            count=len(results),
            total=total,
            offset=offset,
            limit=limit,
            metadata={
                "per_page": raw_response.get("perPage"),
                "page": raw_response.get("page"),
                "total_pages": raw_response.get("totalPages"),
            }
        )

    @staticmethod
    def from_odp(
        raw_response: Dict[str, Any],
        offset: int = 0,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """Normalize an ODP (api.uspto.gov) API response.

        Args:
            raw_response: Raw response from ODP API
            offset: Requested offset
            limit: Requested limit

        Returns:
            Standardized response
        """
        # ODP format varies: {count, patentFileWrapperDataBag: [...]} or direct data
        if "patentFileWrapperDataBag" in raw_response:
            results = raw_response.get("patentFileWrapperDataBag", [])
            total = raw_response.get("count", len(results))
        elif "results" in raw_response:
            results = raw_response.get("results", [])
            total = raw_response.get("count", len(results))
        else:
            # Single result or direct data
            results = raw_response
            total = 1

        return ResponseEnvelope.success(
            results=results,
            source="odp",
            count=len(results) if isinstance(results, list) else 1,
            total=total,
            offset=offset,
            limit=limit,
        )

    @staticmethod
    def from_patentsview(
        raw_response: Dict[str, Any],
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Normalize a PatentsView API response.

        Args:
            raw_response: Raw response from PatentsView API
            offset: Requested offset
            limit: Requested limit

        Returns:
            Standardized response
        """
        # PatentsView format: {patents: [...], count, total_hits}
        # or {assignees: [...], count} etc.
        results = (
            raw_response.get("patents") or
            raw_response.get("assignees") or
            raw_response.get("inventors") or
            raw_response.get("claims") or
            raw_response.get("g_claim") or
            raw_response.get("g_brf_sum_text") or
            raw_response.get("g_detail_desc_text") or
            []
        )
        total = raw_response.get("total_hits") or raw_response.get("count", len(results))

        return ResponseEnvelope.success(
            results=results,
            source="patentsview",
            count=len(results) if isinstance(results, list) else 1,
            total=total,
            offset=offset,
            limit=limit,
        )

    @staticmethod
    def from_ptab(
        raw_response: Dict[str, Any],
        offset: int = 0,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """Normalize a PTAB API response.

        Args:
            raw_response: Raw response from PTAB API
            offset: Requested offset
            limit: Requested limit

        Returns:
            Standardized response
        """
        results = raw_response.get("results", raw_response.get("data", []))
        total = raw_response.get("total", raw_response.get("count", len(results) if isinstance(results, list) else 1))

        return ResponseEnvelope.success(
            results=results,
            source="ptab",
            count=len(results) if isinstance(results, list) else 1,
            total=total,
            offset=offset,
            limit=limit,
        )


def estimate_tokens(data: Any) -> int:
    """Estimate token count for a data structure.

    Uses rough approximation of 4 characters per token.

    Args:
        data: Data to estimate tokens for

    Returns:
        Estimated token count
    """
    if data is None:
        return 0

    try:
        json_str = json.dumps(data, default=str)
        return len(json_str) // 4
    except (TypeError, ValueError):
        return len(str(data)) // 4


def truncate_response(
    response: Dict[str, Any],
    max_tokens: Optional[int] = None,
    max_results: int = 20,
) -> Dict[str, Any]:
    """Truncate a response if it exceeds token budget.

    Args:
        response: Response dictionary to potentially truncate
        max_tokens: Maximum tokens allowed (default from config)
        max_results: Maximum results to keep when truncating

    Returns:
        Original or truncated response
    """
    max_tokens = max_tokens or config.MAX_RESPONSE_TOKENS

    estimated_tokens = estimate_tokens(response)

    if estimated_tokens <= max_tokens:
        return response

    # Need to truncate
    truncated = response.copy()

    # Try to truncate results array
    if "results" in truncated and isinstance(truncated["results"], list):
        original_count = len(truncated["results"])
        if original_count > max_results:
            truncated["results"] = truncated["results"][:max_results]
            truncated["_truncated"] = True
            truncated["_original_count"] = original_count
            truncated["_truncated_to"] = max_results
            truncated["_truncation_message"] = (
                f"Response truncated from {original_count} to {max_results} results "
                f"to fit within token budget. Use 'offset' parameter to paginate "
                f"through remaining results."
            )

            # Update count
            truncated["count"] = max_results

            logger.info(
                f"Truncated response from {original_count} to {max_results} results "
                f"(estimated {estimated_tokens} tokens exceeded {max_tokens} limit)"
            )

    return truncated


def check_and_truncate(
    response: Dict[str, Any],
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Check response size and truncate if necessary.

    This is the main function to call before returning responses.

    Args:
        response: Response to check
        max_tokens: Optional token limit override

    Returns:
        Original or truncated response
    """
    if not config.TRUNCATE_LARGE_RESPONSES:
        return response

    return truncate_response(response, max_tokens)
