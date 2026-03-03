"""HTTP client for the Bitwise Cloud API."""

import hashlib
from pathlib import Path
from typing import Any

import httpx

from .config import get_api_key, get_api_url


class BitwiseClient:
    def __init__(self) -> None:
        self._api_url = get_api_url()
        self._api_key = get_api_key()

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key}

    async def list_documents(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._api_url}/api/v1/documents",
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

    async def upload_document(
        self, path: Path, title: str | None = None
    ) -> dict[str, Any]:
        params = {}
        if title:
            params["title"] = title

        async with httpx.AsyncClient() as client:
            with open(path, "rb") as f:
                resp = await client.post(
                    f"{self._api_url}/api/v1/documents/upload",
                    headers=self._headers(),
                    files={"file": (path.name, f, "application/pdf")},
                    params=params,
                    timeout=120,
                )
            resp.raise_for_status()
            return resp.json()

    async def get_progress(self, doc_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._api_url}/api/v1/documents/{doc_id}/progress",
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

    async def search(
        self,
        query: str,
        top_k: int = 5,
        doc_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"query": query, "top_k": top_k}
        if doc_ids:
            body["doc_ids"] = doc_ids

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._api_url}/api/v1/search",
                headers=self._headers(),
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

    async def find_register(
        self,
        name: str,
        doc_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name}
        if doc_ids:
            body["doc_ids"] = doc_ids

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._api_url}/api/v1/register",
                headers=self._headers(),
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def hash_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
