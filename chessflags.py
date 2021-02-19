import requests as rq
import PySimpleGUI as sg
from sys import stderr
from os import path
import jsonpickle
from collections import defaultdict

# represents a single game of chess
class Game:
    def __init__(self, raw_json):
        self.url = raw_json["url"]
        self.time_class = raw_json["time_class"]
        self.variant = raw_json["rules"]
        #self.opening = raw_json["eco"] # an idea for the future?
        self.users = (FetchProfile(raw_json["white"]["@id"]), FetchProfile(raw_json["black"]["@id"]))
        self.results = (raw_json["white"]["result"], raw_json["black"]["result"])

#represents a chess.com user      
class Profile:
    def __init__(self, raw_json):
        self.url = raw_json["@id"]
        self.username = raw_json["username"]
        self.country = FetchCountry(raw_json["country"])
        #self.rating = raw_json["rating"] #an idea for the future?

#represents a country
class Country:
    def __init__(self, raw_json):
        self.url = raw_json["@id"]
        self.name = raw_json["name"]
        self.code = raw_json["code"]
        #self.flag = ":(" #someday...

#used to sum up a country's stats vs a particular player
class CountryStats:

    # some """enums"""

    # used to switch between colors
    index = {"white" : 0,
             "black" : 1}

    #used to switch between types of loss
    loss_codes = {"checkmated" : 0, 
                  "resigned" : 1, 
                  "timeout" : 2}

    #used to switch between types of draw
    draw_codes = {"stalemate" : 0, 
                  "agreed" : 1, 
                  "repetition" : 2, 
                  "insufficient" : 3, 
                  "50move" : 4, 
                  "timevsinsufficient" : 5}

    def __init__(self):
        self.code = ""
        self._total_games = 0
        self._wins = [0, 0]
        #access particular stats with self.loss_codes[code]
        self._losses = ([0,0,0], [0,0,0])
        # access particular stats with self.draw_codes[code]
        self._draws = ([0,0,0,0,0,0], [0,0,0,0,0,0])

    def UpdateStats(self, color, result):
        self._total_games += 1
        if result == "win":
            self._wins[self.index[color]] += 1
        elif result in self.loss_codes:
            self._losses[self.index[color]][self.loss_codes[result]] += 1
        elif result in self.draw_codes:
            self._draws[self.index[color]][self.draw_codes[result]] += 1 

    def TotalGames(self):
        return self._total_games

    def TotalWins(self):
        return sum(self._wins)

    def TotalLosses(self):
        return sum(sum(x) for x in self._losses)

    def TotalDraws(self):
        return sum(sum(x) for x in self._draws)

    # this class can easily be expanded on to provide more granular detail about win/loss/color

# checks the cache for a profile. if it's not there, requests it from chess.com and creates it.
# force_update means we will always request from chess.com.
def FetchProfile(url, force_update=False):
    global PROFILES
    if url in PROFILES and not force_update:
        return PROFILES[url]
    else:
        try:
            player = Profile(rq.get(url).json())
            PROFILES[url] = player
            return player
        except:
            print("Error fetching profile {}".format(url), file=stderr)
            return None

# checks the cache for a country. if it's not there, requests it from chess.com and creates it.
# force_update means we will always request from chess.com.
def FetchCountry(url, force_update=False):
    global COUNTRIES
    if url in COUNTRIES and not force_update:
        return COUNTRIES[url]
    else:
        try:
            country = Country(rq.get(url).json())
            COUNTRIES[url] = country
            return country
        except:
            print("Error fetching country {}".format(url), file=stderr)
            return None

# checks the cache for a monthly archive. if it's not there, requests it from chess.com and creates it.
# force_update means we will always request from chess.com.
def FetchMonth(url, force_update=False):
    global MONTHS
    if url in MONTHS and not force_update:
        return MONTHS[url]
    else:
        try:
            month = [Game(g) for g in rq.get(url).json()["games"]]
            MONTHS[url] = month
            return month
        except:
            print("Error fetching monthly archive {}".format(url), file=stderr)
            return None

#the archive URL for a given player
def GetArchiveURL(player):
    return "https://api.chess.com/pub/player/" + player + "/games/archives"

#takes a dict of CountryStats objects and turns them into something PySimpleGUI can understand
def ProcessCountries(countries):
    new_layout = []
    for name in countries:
        stats = countries[name]
        new_country = []
        new_country.append(name)
        if stats.TotalGames() > 0:
            new_country.append(stats.TotalGames()) # total games against user
            new_country.append( str('{l:.2f}%').format(l = 100 * (stats.TotalLosses() / stats.TotalGames())) ) # how often user beats them
            new_country.append( str('{w:.2f}%').format(w = 100 * (stats.TotalWins() / stats.TotalGames())) ) # how often user loses to them
            new_country.append( str('{d:.2f}%').format(d = 100 * (stats.TotalDraws() / stats.TotalGames())) ) # how often user draws them
            new_layout.append(new_country)
    new_layout.sort(key = lambda x : (x[1], x[2]), reverse = True)
    return new_layout

########################## MAIN #############################

# Load global files
if not path.exists("months.cache"):
    open("months.cache", "w").close()
if not path.exists("countries.cache"):
    open("countries.cache", "w").close()
if not path.exists("players.cache"):
    open("players.cache", "w").close()

with open("months.cache", "r+") as months:
    MONTHS = {}
    for line in months.readlines():
        line = line.split("~")
        MONTHS[line[0]] = [jsonpickle.decode(game) for game in line[1:]]
with open("countries.cache", "r+") as countries:
    COUNTRIES = {line.split("~")[0] : jsonpickle.decode(line.split("~")[1]) for line in countries.readlines()}
with open("players.cache", "r+") as profiles:
    PROFILES = {line.split("~")[0] : jsonpickle.decode(line.split("~")[1]) for line in profiles.readlines()}

# Set up layout of GUI
layout = [
            [sg.Text("Username"), sg.In(size=(30,1), key="-USERNAME-"), 
             sg.Button("Get Stats", bind_return_key=True)], 
            [sg.Checkbox("Check for Updates", default=False, key="-UPDATE-")],
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
    if event == sg.WIN_CLOSED:
        break

    # If the user enters a name, look up that profile
    if event == "Get Stats":
        user = values["-USERNAME-"]
        countries = defaultdict(CountryStats)

        #collect stats
        #try:
        archives = rq.get(GetArchiveURL(user)).json()["archives"]
        for idx, month in enumerate(archives):
            # for all past months, we should check against our cache. 
            # for the current month, we might want to update our cache.
            if idx < len(archives) - 1 or not values["-UPDATE-"]:
                games = FetchMonth(month)
            else:
                games = [Game(g) for g in rq.get(month).json()["games"]]

            for game in games:
                print("processing game...")
                if game.users[0].username != user:
                    color = "white"
                    result = game.results[0]
                else:
                    color = "black"
                    result = game.results[1]
                country = game.users[0 if color == "white" else 1].country
                countries[country.name].UpdateStats(color, result)
                countries[country.name].code = country.code
        processed_countries = ProcessCountries(countries)
        window["-COUNTRIES-"].update(values=processed_countries)
        #after all is done, write the information back to the cache
        with open("months.cache", "w") as months:
            for month in MONTHS:
                print(month + "~" + "~".join(jsonpickle.encode(game) for game in MONTHS[month]), file=months)
        with open("players.cache", "w") as players:
            for player in PROFILES:
                print(player + "~" + jsonpickle.encode(PROFILES[player]))
        with open("countries.cache", "w") as players:
            for player in PROFILES:
                print(player + "~" + jsonpickle.encode(PROFILES[player]))

        #except:
        #    e = sys.exc_info()[0]
        #    print( "Error: %s" % e, file=stderr )
        #    continue

#after all is done, write the information back to the cache
with open("months.cache", "w") as months:
    for month in MONTHS:
        print(month + "~" + "~".join(jsonpickle.encode(game) for game in MONTHS[month]), file=months)

with open("players.cache", "w") as players:
    for player in PROFILES:
        print(player + "~" + jsonpickle.encode(PROFILES[player]))

with open("countries.cache", "w") as players:
    for player in PROFILES:
        print(player + "~" + jsonpickle.encode(PROFILES[player]))