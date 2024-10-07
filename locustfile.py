from locust import HttpUser, between, task


class Application(HttpUser):
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
