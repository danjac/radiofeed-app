from bs4 import BeautifulSoup

from locust import HttpUser, between, task


class AnonymousUser(HttpUser):
    """Test key endpoints"""

    wait_time = between(1, 5)

    @task
    def landing_page(self):
        """Landing page tests"""
        self.client.get("/")

    @task
    def about(self):
        """About page"""
        self.client.get("/about/")


class LoggedInUser(HttpUser):
    """Authenticated user tests"""

    wait_time = between(1, 5)

    def on_start(self):
        """Log into the application"""
        # First get the login page to retrieve the CSRF token
        response = self.client.get("/account/login/")
        csrf_token = self._extract_csrf_token(response.text)
        # Post request with CSRF token included
        response = self.client.post(
            "/account/login/",
            {
                "login": self.username,
                "password": self.password,
                "csrfmiddlewaretoken": csrf_token,
            },
            headers={
                "X-CSRFToken": csrf_token,
                "Referer": f"{self.host}/account/login/",
            },
        )

    @task
    def subscriptions(self):
        """Subscriptions page."""
        self.client.get("/subscriptions/")

    @task
    def episodes(self):
        """Episodes page."""
        self.client.get("/new/")

    @task
    def discover(self):
        """Discover page."""
        self.client.get("/discover/")

    @task
    def search(self):
        """Search page."""
        self.client.get("/search/", params={"search": "python"})

    def _extract_csrf_token(self, content) -> str:
        soup = self._soup(content)
        """Extract the CSRF token from the response body"""
        # Logic to extract the CSRF token from the response body
        value = ""
        if input := soup.find("input", {"name": "csrfmiddlewaretoken"}):
            value = input.get("value", "") or ""
            if isinstance(value, list):
                value = value[0]
        return value

    def _soup(self, content: str) -> BeautifulSoup:
        return BeautifulSoup(content, "html.parser")
