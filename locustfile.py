from locust import HttpUser, task, between

class SistemTesti(HttpUser):
    host = "http://127.0.0.1:8000"  # BOTLARIN SALDIRACAĞI ADRES
    wait_time = between(1, 3)

    @task
    def anasayfa_gezinme(self):
        self.client.get("/")

    @task
    def arama_yap(self):
        self.client.get("/arama/?q=yemek")