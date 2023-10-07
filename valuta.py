#!/usr/bin/env python3
#
# Slå upp kurser för valutor
#
# För USD/EUR: exchangerate.host
# För krypto: coingecko

import sys, json, requests
from datetime import datetime

# Måste registrera sig och få nyckel nuförtiden på exchangerate.host:
from valuta_apikeys import APIKEY_EXCHANGERATE_HOST

# Cachefilen ser t ex
CACHEFILE = "valutor.json"
COINLIST = "coinlist.json"   # list.json från coingecko, symbol -> id

FIAT = ["usd", "eur", "gbp"]

def main():
    if len(sys.argv) < 2:
        print('''Användning:
 - ange datum (ex 2021-01-01 och fiatvaluta (usd, eur) som argument
 - ange datum och kryptovaluta (coinid, t ex bitcoin) som argument
 - ange enbart kryptosymbol (t ex btc) för att söka coinid
''')
        exit(1)
    if len(sys.argv) == 2:
        valutasymbol = sys.argv[1]
        symbol_to_coinid(valutasymbol)
    else:
        datum = sys.argv[1]
        valuta = sys.argv[2]
        k = lookup(datum, valuta)
        if valuta in FIAT:
            print("Kurs:", k, "SEK")
        else:
            usd = lookup(datum, "usd")
            print("Kurs:", k, "USD,", k*usd, "SEK")
    
def symbol_to_coinid(valutasymbol):
    ''' Lista matchande coinid baserat på list.json från coingecko.
        Ex: [{"id":"01coin","symbol":"zoc","name":"01coin"},...]
    '''
    with open(COINLIST) as f:
        cl = json.load(f)
    for coin in cl:
        if coin["symbol"] == valutasymbol:
            print(coin["id"])
    
def lookup(datum, valuta):
    ''' Returnera kursen för datumet och valutan. Hämta kurs från API vid behov.
        Exempel på cachefilens utseende och valutor-dicten:
  {"usd": {"2021-01-01": 8.269289, "2022-01-01": 9.048181, "2022-01-02": 9.041555},
   "bitcoin": {"2022-01-02": 47816.07767640849, "2022-01-03": 47387.212167697246}}
        OBS: fiat ger SEK tillbaks, krypto ger USD tillbaks!
    '''
    valutor = load()
    if not valuta in valutor:
        valutor[valuta] = {}
        
    if datum in valutor[valuta]:
        return valutor[valuta][datum]
    
    nu = datetime.now().date()
    dt = datetime.fromisoformat(datum).date()
    if dt > nu:
        print("Kan ej fråga om framtiden. Avbryter!")
        exit(1)

    # Första gången för detta datum
    if valuta in FIAT:
        kurs = fetch_fiat(datum, valuta, nu == dt)    # kurs i SEK
    else:
        kurs = fetch_crypto(datum, valuta, nu == dt)  # kurs i USD
        
    # Spara enbart om historiskt datum, ej dagens datum
    if datetime.fromisoformat(datum).date() < nu:
        valutor[valuta][datum] = kurs
        save(valutor)

    return kurs
    
def fetch_fiat(datum, valuta, isToday):
    ''' Returnera kurs i SEK. Exempel: datum="2021-01-01", valuta="usd" '''
    url = f"http://api.exchangerate.host/convert?amount=1&from={valuta.upper()}&to=SEK&access_key={APIKEY_EXCHANGERATE_HOST}"
    if isToday:
        print("Hämtar senaste kurs från exchangerate.host!")
    else:
        url += f"&date={datum}"
        print("Hämtar historisk kurs från exchangerate.host!")
    response = requests.get(url)
    data = response.json()
    return data["result"]

def fetch_crypto(datum, coinid, isToday):
    ''' Returnera kurs i USD. '''
    temp = datum.split("-")
    rev_date = f"{temp[2]}-{temp[1]}-{temp[0]}"
    if isToday:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coinid}&vs_currencies=usd"
        print("Hämtar senaste kurs från coingecko.com!")
        response = requests.get(url)
        data = response.json()
        return data[coinid]["usd"]
    else:
        url = f"https://api.coingecko.com/api/v3/coins/{coinid}/history?date={rev_date}"
        print("Hämtar historisk kurs från coingecko.com!")
        response = requests.get(url)
        data = response.json()
        return data['market_data']['current_price']["usd"]

def load():
    """ Läs in redan hämtade valutor från cachefilen. """
    v = {}
    try:
        with open(CACHEFILE, "r") as f:
            v = json.load(f)
    except FileNotFoundError:
        print("Varning: hittar ej", CACHEFILE, "- skapar ny!")
    return v

def save(v):
    """ Spara hämtade valutor till nästa gång. """
    with open(CACHEFILE, "w") as f:
        json.dump(v, f)

if __name__ == "__main__":
    main()
