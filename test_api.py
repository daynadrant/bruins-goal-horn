import requests
import time

api_url = "https://sportspage-feeds.p.rapidapi.com/games?league=NHL&team=Bruins"
headers = {"x-rapidapi-key": "24d19f0775msha5d5a718525b776p1082c9jsn44005b74762f", "x-rapidapi-host": "sportspage-feeds.p.rapidapi.com"}

print("Watching for Bruins GOALS...")

last_bruins_score = None

while True:
    try:
        response = requests.get(api_url, headers=headers)
        data = response.json()
        results = data.get("results", [])

        if not results:
            print("No Bruins game currently found.")
        else:
            game = results[0]
            status = game["status"]
            teams = game["teams"]
            home_team = teams["home"]["team"]
            away_team = teams["away"]["team"]

            # Determine which side Bruins are on
            if "Bruins" in home_team:
                direction = "home"
            else:
                direction = "away"

            if "scoreboard" in game:
                score = game["scoreboard"]["score"]
                bruins_score = score[direction]

                print(f"Current Score → Bruins: {bruins_score}")
                print("Game status:", status)

                # check for change
                if last_bruins_score is None:
                    last_bruins_score = bruins_score
                elif bruins_score > last_bruins_score:
                    print("\n🎉🎉🎉 BRUINS GOAL DETECTED!!! 🎉🎉🎉\n")
                    last_bruins_score = bruins_score

            else:
                print("Game hasn't started yet — no score data.")

    except Exception as e:
        print("Error:", e)

    time.sleep(15)