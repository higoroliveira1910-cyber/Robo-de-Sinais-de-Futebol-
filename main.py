
import os
import time
import requests
from datetime import datetime

# =========================
# CONFIGURAÇÕES
# =========================

API_KEY = os.getenv("API_FOOTBALL_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

API_URL = "https://v3.football.api-sports.io"

# Intervalo entre verificações
CHECK_INTERVAL = 300  # 5 minutos

# Jogos já alertados
alerted_games = set()


# =========================
# TELEGRAM
# =========================

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Erro: Secrets do Telegram não encontrados.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, data=data, timeout=20)

        if response.status_code == 200:
            print("Alerta enviado para o Telegram.")
        else:
            print("Erro Telegram:", response.text)

    except Exception as e:
        print("Erro ao enviar Telegram:", e)


# =========================
# API-FOOTBALL
# =========================

def api_request(endpoint, params=None):
    if not API_KEY:
        print("Erro: API_FOOTBALL_KEY não encontrada.")
        return None

    headers = {
        "x-apisports-key": API_KEY
    }

    try:
        response = requests.get(
            f"{API_URL}/{endpoint}",
            headers=headers,
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            print("Erro API:", response.status_code, response.text)
            return None

        return response.json()

    except Exception as e:
        print("Erro na API:", e)
        return None


# =========================
# ÚLTIMOS JOGOS
# =========================

def get_last_games(team_id, venue):
    data = api_request(
        "fixtures",
        {
            "team": team_id,
            "last": 6,
            "venue": venue
        }
    )

    if not data:
        return []

    return data.get("response", [])


# =========================
# CRITÉRIOS
# =========================

def team_stats(games, team_id):

    if len(games) < 6:
        return None

    scored = 0
    btts = 0
    over15 = 0

    for game in games:

        home = game["teams"]["home"]["id"]
        away = game["teams"]["away"]["id"]

        goals_home = game["goals"]["home"]
        goals_away = game["goals"]["away"]

        if goals_home is None or goals_away is None:
            continue

        if home == team_id:
            team_goals = goals_home
            opponent_goals = goals_away
        else:
            team_goals = goals_away
            opponent_goals = goals_home

        # Critério de gols marcados
        if team_goals >= 1:
            scored += 1

        # BTTS
        if team_goals >= 1 and opponent_goals >= 1:
            btts += 1

        # Over 1.5
        if team_goals + opponent_goals >= 2:
            over15 += 1

    return {
        "scored": scored,
        "btts": btts,
        "over15": over15
    }


# =========================
# ANALISAR JOGO
# =========================

def analyze_fixture(fixture):

    home_team = fixture["teams"]["home"]
    away_team = fixture["teams"]["away"]

    home_id = home_team["id"]
    away_id = away_team["id"]

    home_name = home_team["name"]
    away_name = away_team["name"]

    print(f"Analisando: {home_name} x {away_name}")

    # Últimos 6 jogos em casa do mandante
    home_games = get_last_games(home_id, "home")

    # Últimos 6 jogos fora do visitante
    away_games = get_last_games(away_id, "away")

    home_stats = team_stats(home_games, home_id)
    away_stats = team_stats(away_games, away_id)

    if not home_stats or not away_stats:
        return None

    # =========================
    # NOSSOS 6 CRITÉRIOS
    # =========================

    criterion1 = home_stats["scored"] >= 5
    criterion2 = away_stats["scored"] >= 4
    criterion3 = home_stats["btts"] >= 3
    criterion4 = away_stats["btts"] >= 3
    criterion5 = (
        home_stats["over15"] >= 5
        and away_stats["over15"] >= 5
    )

    # Critério 6 já é garantido pela consulta
    # venue=home para o mandante
    # venue=away para o visitante
    criterion6 = True

    approved = all([
        criterion1,
        criterion2,
        criterion3,
        criterion4,
        criterion5,
        criterion6
    ])

    if not approved:
        return None

    fixture_id = fixture["fixture"]["id"]

    return {
        "id": fixture_id,
        "home": home_name,
        "away": away_name,
        "home_scored": home_stats["scored"],
        "away_scored": away_stats["scored"],
        "home_btts": home_stats["btts"],
        "away_btts": away_stats["btts"],
        "home_over15": home_stats["over15"],
        "away_over15": away_stats["over15"]
    }


# =========================
# BUSCAR JOGOS
# =========================

def get_today_fixtures():

    today = datetime.now().strftime("%Y-%m-%d")

    data = api_request(
        "fixtures",
        {
            "date": today
        }
    )

    if not data:
        return []

    return data.get("response", [])


# =========================
# MONITORAMENTO
# =========================

def monitor():

    print("===================================")
    print(" ROBÔ DE SINAIS DE FUTEBOL")
    print(" Mercado: OVER 1.5")
    print("===================================")

    send_telegram(
        "🤖 <b>Robô de Sinais de Futebol</b>\n\n"
        "✅ Robô iniciado com sucesso.\n"
        "🔎 Monitoramento de jogos ativado."
    )

    while True:

        try:

            fixtures = get_today_fixtures()

            print(
                f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                f"{len(fixtures)} jogos encontrados."
            )

            for fixture in fixtures:

                # Somente jogos ainda não iniciados
                status = fixture["fixture"]["status"]["short"]

                if status not in ["NS", "TBD"]:
                    continue

                fixture_id = fixture["fixture"]["id"]

                if fixture_id in alerted_games:
                    continue

                signal = analyze_fixture(fixture)

                if signal:

                    message = (
                        "🚨 <b>SINAL OVER 1.5</b> 🚨\n\n"
                        f"⚽ <b>{signal['home']}</b> x "
                        f"<b>{signal['away']}</b>\n\n"

                        "📊 <b>Critérios aprovados:</b>\n"
                        f"🏠 Mandante marcou em "
                        f"{signal['home_scored']}/6\n"
                        f"✈️ Visitante marcou em "
                        f"{signal['away_scored']}/6\n"
                        f"🔄 BTTS mandante: "
                        f"{signal['home_btts']}/6\n"
                        f"🔄 BTTS visitante: "
                        f"{signal['away_btts']}/6\n"
                        f"⚽ Over 1.5 mandante: "
                        f"{signal['home_over15']}/6\n"
                        f"⚽ Over 1.5 visitante: "
                        f"{signal['away_over15']}/6\n\n"

                        "✅ <b>Jogo aprovado pelos 6 critérios.</b>"
                    )

                    send_telegram(message)

                    alerted_games.add(fixture_id)

            time.sleep(CHECK_INTERVAL)

        except Exception as e:

            print("Erro no monitoramento:", e)

            time.sleep(60)


# =========================
# INICIAR
# =========================

if __name__ == "__main__":
    monitor()
