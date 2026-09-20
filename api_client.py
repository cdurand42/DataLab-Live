"""DataLab-Live Server-Side Backend API Client.

All HTTP communication with the private DataLab backend occurs exclusively
server-side within the Streamlit Python process.
The client browser NEVER directly communicates with the private backend,
and the secret DATALAB_API_TOKEN is NEVER exposed or returned to the browser.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
import httpx

from datalab_live.auth import get_config

logger = logging.getLogger("datalab_live.api_client")


def is_backend_configured() -> bool:
    """Return True if both backend URL and secret API token are configured."""
    url = get_config("DATALAB_API_URL")
    token = get_config("DATALAB_API_TOKEN")
    return bool(url and url.strip() and token and token.strip())


def make_api_request(
    endpoint: str,
    params: Optional[dict[str, Any]] = None,
    timeout: int = 15,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Execute a secure server-side GET request to the private DataLab backend.

    Returns:
        tuple (data, user_facing_error_message)
        Never leaks tokens, query details, or internal server errors.
    """
    api_url = get_config("DATALAB_API_URL").rstrip("/")
    api_token = get_config("DATALAB_API_TOKEN")

    if not api_url:
        return None, "Configuration manquante : DATALAB_API_URL n'est pas défini."
    if not api_token:
        return None, "Configuration manquante : DATALAB_API_TOKEN n'est pas défini."

    url = f"{api_url}{endpoint}"
    headers = {
        "X-DataLab-Token": api_token,
        "Accept": "application/json",
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params=params, headers=headers)

        if response.status_code == 401:
            return None, "Accès refusé (401) : le jeton DATALAB_API_TOKEN est invalide ou rejeté."
        if response.status_code == 403:
            return None, "Accès interdit (403) : permissions insuffisantes."
        if response.status_code == 404:
            return None, f"Ressource introuvable (404) sur le backend."
        if response.status_code >= 500:
            return None, "Erreur interne du serveur distant DataLab."

        response.raise_for_status()
        return response.json(), None

    except httpx.TimeoutException:
        return None, "Délai d'attente dépassé lors de la communication avec le backend DataLab."
    except httpx.ConnectError:
        return None, "Connexion impossible avec le backend DataLab privé (serveur éteint ou inaccessible)."
    except httpx.HTTPError:
        return None, "Erreur de communication réseau avec le backend DataLab."
    except Exception:
        return None, "Une erreur inattendue est survenue lors de la communication avec le backend."


def get_health(timeout: int = 5) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Query the public health check endpoint on the backend."""
    api_url = get_config("DATALAB_API_URL").rstrip("/")
    if not api_url:
        return None, "DATALAB_API_URL non configuré."
    url = f"{api_url}/health"
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.json(), None
            return None, f"Health check a répondu avec le code {resp.status_code}."
    except Exception:
        return None, "Backend DataLab inaccessible."


def get_overview() -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Retrieve overview metrics from the private backend."""
    return make_api_request("/api/overview")


def get_bench(
    year: int = 2024,
    limit: Optional[int] = None,
    search: Optional[str] = None,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Retrieve Bench commune data from the private backend."""
    params: dict[str, Any] = {"year": year}
    if limit is not None:
        params["limit"] = limit
    if search:
        params["search"] = search
    return make_api_request("/api/bench", params=params)


def get_radar(
    year: int = 2024,
    limit: Optional[int] = None,
    search: Optional[str] = None,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Retrieve Radar signals from the private backend."""
    params: dict[str, Any] = {"year": year}
    if limit is not None:
        params["limit"] = limit
    if search:
        params["search"] = search
    return make_api_request("/api/radar", params=params)


def get_watch(
    ref_year: int = 2024,
    prev_year: int = 2023,
    limit: Optional[int] = None,
    search: Optional[str] = None,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Retrieve Watch signals from the private backend."""
    params: dict[str, Any] = {
        "ref_year": ref_year,
        "prev_year": prev_year,
    }
    if limit is not None:
        params["limit"] = limit
    if search:
        params["search"] = search
    return make_api_request("/api/watch", params=params)


def get_geo() -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Retrieve commune geographic coordinates from the private backend."""
    return make_api_request("/api/geo")
