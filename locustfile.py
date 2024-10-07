from locust import HttpUser, between, task


class QuickstartUser(HttpUser):
    """Login"""

    wait_time = between(1, 5)

    @task
    def landing_page(self):
        """Landing page tests"""
        self.client.get("/")

    def on_start(self):
        """Login to the application"""
        self.client.post("/login", json={"username": "foo", "password": "bar"})
