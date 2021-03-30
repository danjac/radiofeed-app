from locust import HttpUser, between, task

# https://docs.locust.io/en/stable/quickstart.html


class Quickstart(HttpUser):
    wait_time = between(1, 2.5)

    @task
    def front_pages(self):
        self.client.get("/")
        self.client.get("/podcasts/")
        self.client.get("/discover/")
