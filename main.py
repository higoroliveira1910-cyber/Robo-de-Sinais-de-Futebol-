import os
import requests
import time

API_KEY = os.getenv("API_FOOTBALL_KEY")

URL = "https://v3.football.api-sports.io/fixtures"

HEADERS = {
    "x-apisports-key": API_KEY
}

def buscar_jogos():
    resposta = requests.get(
        URL,
        headers=HEADERS,
        params={"next": 20}
    )

    if resposta.status_code != 200:
        print("Erro na API:", resposta.status_code)
        return

    dados = resposta.json()

    print("Jogos encontrados:", len(dados.get("response", [])))

    for jogo in dados.get("response", []):
        mandante = jogo["teams"]["home"]["name"]
        visitante = jogo["teams"]["away"]["name"]

        print(f"{mandante} x {visitante}")


while True:
    print("Robô de sinais iniciado...")
    buscar_jogos()

    print("Aguardando 30 minutos...")
    time.sleep(1800)
