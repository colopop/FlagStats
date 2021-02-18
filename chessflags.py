import requests as rq
import PySimpleGUI as sg
#import flag
import sys
from collections import defaultdict

loss_codes = {"whitecheckmated", "whiteresigned", "whitetimeout", "blackcheckmated", "blackresigned", "blacktimeout"}
draw_codes = {"whiteagreed", "whiterepetition", "whiteinsufficient", "white50move", "whitetimevsinsufficient",
              "blackagreed", "blackrepetition", "blackinsufficient", "black50move", "blacktimevsinsufficient"}

def GetArchiveURL(player):
    return "https://api.chess.com/pub/player/" + player + "/games/archives"

def GetProfileURL(player):
    return "https://api.chess.com/pub/player/" + player

def ProcessCountries(countries):
    global loss_codes
    global draw_codes
    new_layout = []
    for country in countries:
        new_country = []
        new_country.append(country)
        #new_country.append(countries[country]["flag"])
        wins = sum(countries[country][result] for result in countries[country] if "win" in result)
        losses = sum(countries[country][result] for result in countries[country] if result in loss_codes)
        draws = sum(countries[country][result] for result in countries[country] if result in draw_codes)
        total = wins + losses + draws 
        if total > 0:
            winp = str('{w:.2f}%').format(w = 100*wins/total)
            lossp = str('{l:.2f}%').format(l = 100*losses/total)
            drawp = str('{d:.2f}%').format(d = 100*draws/total)
            new_country.append(total)
            new_country.append(lossp)
            new_country.append(winp)
            new_country.append(drawp)
            new_layout.append(new_country)
    new_layout.sort(key = lambda x : (x[1], x[2]), reverse = True)
    return new_layout


layout = [
            [sg.Text("Username"), sg.In(size=(30,1), key="-USERNAME-"), 
             sg.Button("Get Stats", bind_return_key=True)], 
            [sg.Button("Done")],
            [sg.Table(values=[['' for _ in range(4)] for _ in range(4)], 
                headings=["Country", "Games", "Win%", "Lose%", "Draw%"], justification='left',
                max_col_width=60, auto_size_columns=False,
                enable_events=True, key="-COUNTRIES-")]
         ]

# Create the window
window = sg.Window("Flag Stats", layout)

# Create an event loop
while True:
    event, values = window.read()
    # End program if user closes window or
    # presses the OK button
    if event == "Done" or event == sg.WIN_CLOSED:
        break

    if event == "Get Stats":
        user = values["-USERNAME-"]
        countries = defaultdict(lambda: defaultdict(int))

        #collect stats
        #try:
        archives = rq.get(GetArchiveURL(user)).json()["archives"]
        for month in archives:
            games = rq.get(month).json()["games"]
            for game in games:
                if game["white"]["username"] != user:
                    color = "white"
                    opponent = game["white"]["username"]
                else:
                    color = "black"
                    opponent = game["black"]["username"]
                country_url = rq.get(GetProfileURL(opponent)).json()['country']
                country = rq.get(country_url).json()
                country_name = country["name"]
                country_code = country["code"]
                result = game[color]["result"]
                countries[country_name][color+result] += 1
                #countries[country_name]["flag"] = flag.flag(country_code)
                print("finished processing game")
            print("finished processing month")
        print("finished processing archives")
        print(countries)
        processed_countries = ProcessCountries(countries)
        print(processed_countries)
        window["-COUNTRIES-"].update(values=processed_countries)

        #except:
        #    e = sys.exc_info()[0]
        #    print(sys.stderr, "Error: %s" % e )
        #    continue

