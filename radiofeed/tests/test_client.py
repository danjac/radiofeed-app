import contextlib
import json

import aiohttp
import pytest
from aioresponses import aioresponses

from radiofeed.client import Client, ClientResponse, StreamingClientResponse, get_client


class TestClient:
    url = "https://example.com/test"

    async def test_default_headers(self, settings):
        settings.USER_AGENT = "TestAgent/1.0"
        client = Client()
        assert client._session.headers["User-Agent"] == "TestAgent/1.0"
        await client.aclose()

    async def test_custom_headers(self, settings):
        settings.USER_AGENT = "TestAgent/1.0"
        client = Client(headers={"X-Custom": "value"})
        assert client._session.headers["User-Agent"] == "TestAgent/1.0"
        assert client._session.headers["X-Custom"] == "value"
        await client.aclose()

    async def test_custom_timeout(self, settings):
        settings.USER_AGENT = "TestAgent/1.0"
        client = Client(timeout=30)
        assert client._session.timeout.total == 30
        await client.aclose()

    async def test_get_ok(self):
        with aioresponses() as m:
            m.get(self.url, status=200, body=b"response body")
            client = Client()
            response = await client.get(self.url)
            await client.aclose()

        assert isinstance(response, ClientResponse)
        assert response.status == 200
        assert response.content == b"response body"
        assert response.url == self.url

    async def test_get_with_headers(self):
        with aioresponses() as m:
            m.get(self.url, status=200, body=b"ok")
            client = Client()
            response = await client.get(self.url, headers={"Accept": "text/html"})
            await client.aclose()

        assert response.status == 200

    async def test_get_json(self):
        with aioresponses() as m:
            m.get(self.url, status=200, body=json.dumps({"key": "value"}).encode())
            client = Client()
            response = await client.get(self.url)
            await client.aclose()

        assert response.json() == {"key": "value"}

    async def test_get_error(self):
        with aioresponses() as m:
            m.get(self.url, status=500)
            client = Client()
            with pytest.raises(aiohttp.ClientResponseError):
                await client.get(self.url)
            await client.aclose()

    async def test_get_client_error(self):
        with aioresponses() as m:
            m.get(self.url, exception=aiohttp.ClientError("connection failed"))
            client = Client()
            with pytest.raises(aiohttp.ClientError):
                await client.get(self.url)
            await client.aclose()

    async def test_stream_ok(self):
        with aioresponses() as m:
            m.get(self.url, status=200, body=b"streamed")
            client = Client()
            async with client.stream(self.url) as response:
                assert isinstance(response, StreamingClientResponse)
                assert response.status == 200
            await client.aclose()

    async def test_stream_with_headers(self):
        with aioresponses() as m:
            m.get(self.url, status=200, body=b"ok")
            client = Client()
            async with client.stream(
                self.url, headers={"Accept": "audio/mpeg"}
            ) as response:
                assert response.status == 200
            await client.aclose()

    async def test_stream_error(self):
        with aioresponses() as m:
            m.get(self.url, status=500)
            client = Client()
            with pytest.raises(aiohttp.ClientResponseError):
                async with client.stream(self.url):
                    pass
            await client.aclose()

    async def test_aclose(self):
        client = Client()
        assert not client._session.closed
        await client.aclose()
        assert client._session.closed


class TestGetClient:
    async def test_yields_client(self):
        async with get_client() as client:
            assert isinstance(client, Client)

    async def test_closes_on_exit(self):
        async with get_client() as client:
            session = client._session
        assert session.closed

    async def test_passes_kwargs(self, settings):
        settings.USER_AGENT = "TestAgent/1.0"
        async with get_client(timeout=30) as client:
            assert client._session.timeout.total == 30

    async def test_closes_on_exception(self):
        session = None
        with contextlib.suppress(RuntimeError):
            async with get_client() as client:
                session = client._session
                raise RuntimeError("test error")
        assert session is not None
        assert session.closed
