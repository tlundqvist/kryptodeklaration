#!/usr/bin/env python3
#
# Tolka loggfil med transaktioner från Gnosis Wallet (token transfer export)
#
# Kolumner i CSV:
# "Transaction Hash","Blockno","UnixTimestamp","DateTime (UTC)","From","To",
# "TokenValue","USDValueDayOfTx","ContractAddress","TokenName","TokenSymbol"
#
# Exporteras från: https://gnosisscan.io/address/<addr>#tokentxns
#
# Min plånboksadress (sätts i process_gnosiswallet_config.py):
from process_gnosiswallet_config import MY_ADDRESS

import sys, csv, os
import valuta
from collections import defaultdict

UTFIL = "resultat_gnosiswallet.csv"


CRC_VARIANTER = {"CRC", "gCRC", "s-gCRC", "s-METESTSUP"}

def normalisera_symbol(sym):
    return "CRC" if sym in CRC_VARIANTER else sym


def token_till_sek(date, sym, usd_från_csv, antal):
    """Beräkna SEK-värde för en token.
    Använder USD-värde från CSV om tillgängligt, annars prisuppslag via valuta."""
    if usd_från_csv > 0:
        return round(usd_från_csv * valuta.lookup(date, "usd"), 2)
    elif antal > 0:
        usd_per_token = valuta.lookup(date, valuta.translate(sym))
        sek_per_usd = valuta.lookup(date, "usd")
        return round(antal * usd_per_token * sek_per_usd, 2)
    return 0


def parse_amount(s):
    """Hantera tusentalsavgränsare (kommatecken) i tokenbelopp."""
    return float(s.replace(",", ""))


def parse_usd(s):
    """Tolka USD-belopp ('$X.XX' eller 'N/A'), returnera None om ej tillgängligt."""
    if not s or s == "N/A":
        return None
    return float(s.lstrip("$").replace(",", ""))


def main():
    if len(sys.argv) < 2:
        print("Ange csv-filens namn som indata (Gnosis Wallet token export)!")
        print("Utdata hamnar alltid i", UTFIL)
        exit(1)
    processfile(sys.argv[1], UTFIL)


def processfile(loggfil, utfil):
    # Läs in alla rader med csv-modulen (hanterar citattecken och kommatecken i fält)
    with open(loggfil, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    # Gruppera rader per transaction hash, bevara filordningen
    transactions = defaultdict(list)
    tx_order = []
    for row in all_rows:
        txhash = row["Transaction Hash"]
        if txhash not in transactions:
            tx_order.append(txhash)
        transactions[txhash].append(row)

    my_addr = MY_ADDRESS.lower()

    with open(utfil, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Datum", "Var", "Händelse", "Antal", "Valuta", "Belopp SEK", "Hash"])

        for txhash in tx_order:
            tx_rows = transactions[txhash]
            date = tx_rows[0]["DateTime (UTC)"].split(" ")[0]
            short_hash = txhash[:16] + "..."

            # Beräkna nettoflöde per token för min adress
            # Positivt = jag fick tokens, negativt = jag skickade tokens
            net = defaultdict(float)
            usd_in = defaultdict(float)   # USD-värde för mottagna tokens (när tillgängligt)
            for row in tx_rows:
                from_addr = row["From"].lower()
                to_addr = row["To"].lower()
                symbol = normalisera_symbol(row["TokenSymbol"])
                amount = parse_amount(row["TokenValue"])
                usd = parse_usd(row["USDValueDayOfTx"])

                if to_addr == my_addr:
                    net[symbol] += amount
                    if usd is not None:
                        usd_in[symbol] += usd
                if from_addr == my_addr:
                    net[symbol] -= amount

            significant = {sym: amt for sym, amt in net.items() if abs(amt) > 1e-10}
            incoming = {sym: amt for sym, amt in significant.items() if amt > 0}
            outgoing = {sym: -amt for sym, amt in significant.items() if amt < 0}

            if not (incoming and outgoing):
                print(f"Info: tx {short_hash} ({date}) - ej swap, hoppas över (in={dict(incoming)}, ut={dict(outgoing)})")
                continue

            # Beräkna swap-värdet i SEK från inkommande tokens med känt marknadspris
            swap_sek = sum(
                token_till_sek(date, sym, usd_in.get(sym, 0), amt)
                for sym, amt in incoming.items()
            )
            # Utgående (sälj) först: första raden får swap_sek, resten 0
            rows_to_write = []
            for i, sym in enumerate(sorted(outgoing)):
                rows_to_write.append((-round(outgoing[sym], 8), sym, swap_sek if i == 0 else 0, "sälj"))
            # Inkommande (köp): alla rader får swap_sek (samma totala handelsvärde)
            for sym in sorted(incoming):
                rows_to_write.append((round(incoming[sym], 8), sym, swap_sek, "köp"))
            var_label = "Gnosis wallet, swap"

            for i, (antal, sym, sek, händelse) in enumerate(rows_to_write):
                writer.writerow([
                    date if i == 0 else "",
                    var_label if i == 0 else "",
                    händelse,
                    antal,
                    sym,
                    sek,
                    short_hash if i == 0 else ""
                ])


if __name__ == "__main__":
    main()
