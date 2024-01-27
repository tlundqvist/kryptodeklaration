#!/usr/bin/env python3
#
# Tolka loggfil med transaktioner från crypto.com
#
# Exempel: crypto_transactions_record_20220204_213010.csv
#
# Timestamp (UTC),Transaction Description,Currency,Amount,To Currency,To Amount,Native Currency,Native Amount,Native Amount (in USD),Transaction Kind
# 2021-12-29 20:18:17,Card Cashback,CRO,0.19694596,,,USD,0.11,0.11,referral_card_cashback
# 2021-07-20 00:11:30,Crypto Earn,TGBP,11.11249041,,,USD,15.04,15.04,crypto_earn_interest_paid
# 2021-07-11 10:47:49,BTC -> EUR,BTC,-0.1,,,USD,-3307.67,-3307.67,card_top_up

# Olika Transaction Kind:

POLICY_IGNORE = [
    'crypto_deposit',
    'crypto_to_exchange_transfer',
    'exchange_to_crypto_transfer',
    'crypto_transfer',
    'crypto_withdrawal',
    'dust_conversion_credited',
    'dust_conversion_debited',
    'lockup_upgrade'                # tolkas som ej utlåning, ingen skattehändelse
]

# Tolkas som skattefria gåvor, kortköpsåterbäring, typ coop-poäng

POLICY_GIFT = [
    'card_cashback_reverted',
    'referral_bonus',
    'referral_card_cashback',
    'reimbursement',
    'reimbursement_reverted',
    'rewards_platform_deposit_credited'  # osäker på denna, airdrop?
]

# Ränta

POLICY_INTEREST = [
    'crypto_earn_interest_paid',
    'mco_stake_reward'
]

POLICY_OTHER = [    
    'crypto_earn_program_created',    # Utlåning
    'crypto_earn_program_withdrawn',  # Retur
    'crypto_exchange',                # Krypto till krypto
    'recurring_buy_order',            # Samma som viban_purchase, köp krypto
    'crypto_viban_exchange',          # Sälj krypto till fiat
    'card_top_up',                    # Sälj krypto till fiat
    'crypto_payment',                 # Betala med krypto (sälj krypto)
    'crypto_payment_refund',          # Återbetala krypto (köp krypto)
    'viban_purchase',                 # Köp krypto för fiat
    'nft_payout_credited',            # Köp krypto (men egentligen deposit kanske)
    'card_top_up'                     # Samma som viban_exchange till FIAT
]

import sys, valuta

UTFIL = "resultat_crypto_com.csv"

def main():
    if len(sys.argv) < 2:
        print("Ange csv-filens namn som indata (crypto.com transaktionslogg)!")
        print("Utdata hamnar alltid i resultat_crypto_com.csv")
        exit(1)
    loggfil = sys.argv[1]
    processfile(loggfil, UTFIL)

def processfile(loggfil, utfil):
    infil = open(loggfil)
    infil.readline() # skip header line
    lines = infil.readlines()
    infil.close()
    f = open(utfil, "w")
    print("Crypto.com", file=f)
    print("Datum,Var,Händelse,Antal,Valuta,Belopp", file=f)
    for line in reversed(lines):
        splitted = line.rstrip().split(",")
        date_time, desc, currency1, amount1, currency2, amount2, _, _, amountUSD, kind, hash = splitted
        if kind in POLICY_IGNORE:
            continue
        date = date_time.split(" ")[0]
        if amount2 == '':
            amount2 = '0'
        amount1, amount2, amountUSD = [float(amount1), float(amount2), float(amountUSD)]

        if kind in POLICY_GIFT:
            # Skattefritt köp till aktuell kurs, utgå från USD och omvandla till SEK
            usdkurs = valuta.lookup(date, "usd")
            if amount1 >= 0:
                print(f"{date},{desc},köp,{amount1},{currency1},{amountUSD*usdkurs}", file=f)
            else:
                # Egentligen en korrigering av tidigare "Köp", men köp får ej vara negativt
                # Hantera som sälj (försummbara belopp ändå)
                print(f"{date},{desc},sälj,{amount1},{currency1},{amountUSD*usdkurs}", file=f)

        elif kind in POLICY_INTEREST:
            # Ska bli ränta i redovisningen
            usdkurs = valuta.lookup(date, "usd")
            print(f"{date},{desc},ränta,{amount1},{currency1},{amountUSD*usdkurs}", file=f)
            
        elif kind in POLICY_OTHER:
            # Utlåning till earn, växling till konstgjord valuta
            usdkurs = valuta.lookup(date, "usd")
            if kind == 'crypto_earn_program_created':
                currency2 = "crypto" + currency1
                amount2 = -amount1
                amountUSD = amountUSD
                kind = 'crypto_exchange'
            if kind == 'crypto_earn_program_withdrawn':
                currency2, amount2 = currency1, amount1
                currency1 = "crypto" + currency2
                amount1 = -amount1
                kind = 'crypto_exchange'
                
            if kind == 'crypto_exchange':
                print(f"{date},{desc},sälj,{amount1},{currency1},{amountUSD*usdkurs}", file=f)
                print(f",,köp,{amount2},{currency2},{amountUSD*usdkurs}", file=f)
            elif kind == 'viban_purchase' or kind == 'recurring_buy_order':
                print(f"{date},{desc},köp,{amount2},{currency2},{amountUSD*usdkurs}", file=f)
            elif kind == 'crypto_payment_refund':
                print(f"{date},{desc},köp,{amount1},{currency1},{amountUSD*usdkurs}", file=f)
            elif kind == 'nft_payout_credited':
                print(f"{date},{desc},köp,{amount1},{currency1},{amountUSD*usdkurs}", file=f)
            elif kind == 'crypto_viban_exchange':
                print(f"{date},{desc},sälj,{amount1},{currency1},{amountUSD*usdkurs}", file=f)
            elif kind == 'crypto_payment':
                print(f"{date},{desc},sälj,{amount1},{currency1},{amountUSD*usdkurs}", file=f)
            elif kind == 'card_top_up':
                print(f"{date},{desc},sälj,{amount1},{currency1},{-amountUSD*usdkurs}", file=f)
            else:
                raise Exception("Okänd POLICY_OTHER:", kind)
        else:
            raise Exception("Okänd typ (kind) i loggen:", kind)
                
        # print(date_time, desc, currency1, amount1, currency2, amount2, amountUSD, kind)
    f.close()

if __name__ == "__main__":
    main()
