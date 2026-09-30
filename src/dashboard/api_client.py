"""API client for APIx backend."""

import os
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class APIClient:
    """Client for APIx backend API."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize API client.

        Args:
            base_url: Base URL for the API. Defaults to env var APIX_API_URL or localhost.
        """
        self.base_url = (
            base_url or os.getenv("APIX_API_URL", "http://127.0.0.1:8000")
        ).rstrip("/")
        self.timeout = 5
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Make an API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response JSON

        Raises:
            requests.RequestException: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise requests.RequestException(
                f"Request to {endpoint} timed out"
            )
        except requests.exceptions.ConnectionError:
            raise requests.RequestException(
                "Unable to connect to APIx backend"
            )
        except requests.exceptions.HTTPError as e:
            if response.status_code == 503:
                raise requests.RequestException(
                    "APIx backend is currently unavailable"
                )
            raise requests.RequestException(
                f"HTTP {response.status_code}: {response.reason}"
            )
        except ValueError:
            raise requests.RequestException("Invalid JSON response from API")

    def health(self) -> dict[str, Any]:
        """Get API health status."""
        return self._request("GET", "/health")

    def latest_index(self) -> dict[str, Any]:
        """Get latest APIx index."""
        return self._request("GET", "/api/v1/index/latest")

    def index_history(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get APIx index history.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Index history data
        """
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        return self._request("GET", "/api/v1/index/history", params=params)

    def route_indices(self, date: Optional[str] = None) -> dict[str, Any]:
        """Get route-level indices.

        Args:
            date: Collection date (YYYY-MM-DD)

        Returns:
            Route index data
        """
        params = {}
        if date:
            params["date"] = date

        return self._request("GET", "/api/v1/index/routes", params=params)

    def lead_time_indices(
        self, date: Optional[str] = None, fare_class: Optional[str] = None
    ) -> dict[str, Any]:
        """Get lead-time indices by fare class.

        Args:
            date: Collection date (YYYY-MM-DD)
            fare_class: Fare class (Economy, Business)

        Returns:
            Lead-time index data
        """
        params = {}
        if date:
            params["date"] = date
        if fare_class:
            params["fare_class"] = fare_class

        return self._request("GET", "/api/v1/index/lead-times", params=params)

    def quality_report(self) -> dict[str, Any]:
        """Get quality control report."""
        return self._request("GET", "/api/v1/quality")

    def summary(self) -> dict[str, Any]:
        """Get APIx summary and metadata."""
        return self._request("GET", "/api/v1/summary")
