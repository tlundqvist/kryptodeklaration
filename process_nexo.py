#!/usr/bin/env python3
#
# Tolka loggfil med transaktioner från Nexo.
#
# Nexo tolkas som en låneplattform. Dvs, all insättning och uttag är realisering.
# Interna transkationer (låsning) ger ingen realisering.
# Räntor och utdelningar blir ränta.
#
# Exempel: nexo_transactions.csv
#
# Transaction,Type,Currency,Amount,USD Equivalent,Details,Outstanding Loan,Date / Time
# NXTIISMjM2KCJ,Interest,NEXONEXO,0.17381980,$0.38,approved / 0.0042342262 AVAX,$0.00,2022-02-08 07:00:06
# NXTiucm8Fwbub,FixedTermInterest,NEXONEXO,1.99298599,$1.344756180701,approved / Term Deposit Interest,$0.00,2022-01-29 07:01:17
# NXT6atyFs1z2Q,UnlockingTermDeposit,AVAX,4.04993264,$63.63259997825,approved / Transfer from Term Wallet to Savings Wallet,$0.00,2022-01-29 07:01:17
# NXToTtEZ9Mutj,LockingTermDeposit,AVAX,-4.04993264,$516.4234202672,approved / Transfer from Savings Wallet to Term Wallet,$0.00,2021-12-29 08:39:33

# Olika Transaction Type:

POLICY_IGNORE = [
    'Locking Term Deposit',
    'Unlocking Term Deposit',
    'Exchange Deposited On'      # Extra onödig?
]

# Tolkas som skattefria gåvor, kortköpsåterbäring, typ coop-poäng

POLICY_GIFT = [
    'Exchange Cashback'        # Gåva, köp för 0 kr
]

# Ränta

POLICY_INTEREST = [
    'Interest',
    'Fixed Term Interest',
    'Dividend'
]

POLICY_OTHER = [    
    'Deposit',                   # Utlåning
    'Top up Crypto',             # samma som Deposit
    'Withdrawal',                # Retur
    'Transfer To Pro Wallet',    # Samma som retur/withdrawal
    'Transfer From Pro Wallet',  # Samma som utlåning/deposit
    'Exchange',                  # Krypto till krypto, OBS: loggfil brister, hanteras manuellt
    'Deposit To Exchange',       # Köp krypto för fiat
]

import sys, valuta

UTFIL = "resultat_nexo.csv"

def main():
    if len(sys.argv) < 2:
        print("Ange csv-filens namn som indata (crypto.com transaktionslogg)!")
        print("Utdata hamnar alltid i resultat_nexo.csv")
        exit(1)
    loggfil = sys.argv[1]
    processfile(loggfil, UTFIL)

def processfile(loggfil, utfil):
    infil = open(loggfil)
    infil.readline() # skip header line
    lines = infil.readlines()
    infil.close()
    f = open(utfil, "w")
    print("Nexo", file=f)
    print("Datum,Var,Händelse,Antal,Valuta,Belopp", file=f)
    for line in reversed(lines):
        splitted = line.rstrip().split(",")
        _, kind, currency1, amount1, currency2, amount2, amountUSD, desc, date_time = splitted
        if kind in POLICY_IGNORE:
            continue
        date = date_time.split(" ")[0]
        if currency1 == "NEXONEXO":
            currency1 = "NEXO"

        amount1, amount2, amountUSD = (float(amount1), float(amount2), float(amountUSD[1:]))

        usdkurs = valuta.lookup(date, "usd")
        amountSEK = amountUSD*usdkurs
        
        if kind in POLICY_GIFT:
            # Skattefritt köp till aktuell kurs, utgå från USD och omvandla till SEK
            print(f"{date},{kind},köp,{amount1},nexo{currency1},{amountSEK}", file=f)
        elif kind in POLICY_INTEREST:
            # Ska bli ränta i redovisningen, räntan kommer på nexo-skuldvalutan
            print(f"{date},{kind},ränta," +
                  f"{amount1},nexo{currency1},{amountSEK},,{desc}", file=f)
        elif kind in POLICY_OTHER:
            # Deposit, växling till konstgjord valuta
            if kind == 'Deposit' or kind == 'Top up Crypto' or kind == 'Transfer From Pro Wallet':
                amount1 = -amount1
                currency2 = "nexo" + currency1
                amount2 = -amount1
                amountUSD = amountUSD
                print(f"{date},{kind},sälj,{amount1},{currency1},{amountSEK}" +
                      f",,{desc}", file=f)
                print(f",,köp,{amount2},{currency2},{amountSEK}", file=f)
            elif kind == 'Withdrawal' or kind == 'Transfer To Pro Wallet':
                currency2, amount2 = currency1, -amount1
                currency1 = "nexo" + currency2
                print(f"{date},{kind},sälj,{amount1},{currency1},{amountSEK}" +
                      f",,{desc}", file=f)
                print(f",,köp,{amount2},{currency2},{amountSEK}", file=f)
            elif kind == 'Deposit To Exchange':
                # Om EUR så ska det nog inte hanteras som krypto men enklast att
                # hantera det som allt annat
                print(f"{date},{kind},köp,{amount2},nexo{currency2},{amountSEK}" +
                      f",,{desc}", file=f)
            elif kind == 'Exchange':
                # Växling
                print(f"{date},{kind},sälj,{amount1},nexo{currency1},{amountSEK}", file=f)
                print(f",,köp,{amount2},nexo{currency2},{amountSEK}", file=f)
            else:
                raise Exception("Okänd POLICY_OTHER:", kind)
        else:
            raise Exception("Okänd typ (kind) i loggen:", kind)
    f.close()

if __name__ == "__main__":
    main()
