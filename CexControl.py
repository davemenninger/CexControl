#-------------------------------------------------------------------------------
# Name:       CexControl
# Purpose:    Automatically add mined coins on Cex.IO to GHS pool
#
# Author:     Eloque
#
# Created:    19-11-2013
# Copyright:  (c) Eloque 2013
# Licence:    Free to use, copy and distribute as long as I'm credited
#             Provided as is, use at your own risk and for your own benefit
# Donate BTC: 1Lehv8uMSMyYyY7ZFTN1NiRj8X24E56rvV
#-------------------------------------------------------------------------------

from __future__ import print_function

import cexapi
import re
import time
import json
import sys

## just place till P3
import urllib2

version = "0.6.6"

class Settings:

    def __init__(self):

        self.NMCThreshold = 0.0
        self.BTCThreshold = 0.0
        self.EfficiencyThreshold = 1.0

        self.username    = ""
        self.api_key     = ""
        self.api_secret  = ""

        self.HoldCoins = False

    def LoadSettings(self):

        print ("Attempting to load Settings")

        try:

            fp = open("CexControlSettings.conf")
            LoadedFromFile = json.load(fp)

            self.username    = str(LoadedFromFile['username'])
            self.api_key     = str(LoadedFromFile['key'])
            self.api_secret  = str(LoadedFromFile['secret'])

            try:
                self.NMCThreshold = float(LoadedFromFile['NMCThreshold'])
            except:
                print ("NMC Threshold Setting not present, using default")

            try:
                self.BTCThreshold = float(LoadedFromFile['BTCThreshold'])
            except:
                print ("BTC Threshold Setting not present, using default")

            try:
                self.EfficiencyThreshold = float(LoadedFromFile['EfficiencyThreshold'])
            except:
                print ("Efficiency Threshold Setting not present, using default")
                
            try:
                self.HoldCoins = bool(LoadedFromFile['HoldCoins'])
            except:
                print ("Hold Coins Setting not present, using default")
                


            if ( LoadedFromFile ):
                print ("File found, loaded")

        except IOError:
            print ("Could not open file, attempting to create new one")
            self.CreateSettings()
            self.LoadSettings()

        ## sself.WriteSettings()

    def CreateSettings(self):

        print ("")
        print ("Please enter your credentials")
        print ("")
        self.username     = raw_input("Username: ")
        self.api_key      = raw_input("API Key: ")
        self.api_secret   = raw_input("API Secret: ")

        self.CreateTresholds()

        self.WriteSettings()

    def WriteSettings(self):

        ToFile = { "username"               :str(self.username),
                   "key"                    :str(self.api_key),
                   "secret"                 :str(self.api_secret),
                   "BTCThreshold"           :str(self.BTCThreshold),
                   "NMCThreshold"           :str(self.NMCThreshold),
                   "EfficiencyThreshold"    :str(self.EfficiencyThreshold),
                   "HoldCoins"              :bool(self.HoldCoins),
                 }

        try:
            print ("")
            print ("Configuration created, attempting save")
            json.dump(ToFile, open("CexControlSettings.conf", 'w'))
            print ("Save successfull, attempting reload")
        except:
            print (sys.exc_info())
            print ("Failed to write configuration file, giving up")
            exit()

    def CreateTresholds(self):

        print ("")
        print ("Please enter your thresholds")
        print ("")
        self.BTCThreshold   = raw_input("Threshold to trade BTC: ")
        self.NMCThreshold   = raw_input("Threshold to trade NMC: ")
        self.EfficiencyThreshold   = raw_input("Efficiency at which to arbitrate: ")
        self.HoldCoins = raw_input("Hold Coins at low efficiency (Yes/No): ")
        
        if (self.HoldCoins == "Yes" ):
            self.HoldCoins = True
        else:
            self.HoldCoins = False

        self.WriteSettings()

    ## Simply return the context, based on user name, key and secret
    def GetContext(self):

        return cexapi.api(self.username, self.api_key, self.api_secret)

def main():

    print ("======= CexControl version %s =======" % version)

    ## First, try to get the configuration settings in the settings object
    settings = Settings()
    settings.LoadSettings()


    ParseArguments(settings)

##    try:
        ## settings = LoadSettings()
##    except:
##        print ("Could not load settings, exiting")
##        exit()

##    username    = str(settings['username'])
 ##   api_key     = str(settings['key'])
  ##  api_secret  = str(settings['secret'])

    try:
        context = settings.GetContext()
        balance = context.balance()

        print ("========================================")

        print ("Account       : %s" % settings.username )
        print ("GHS balance   : %s" % balance['GHS']['available'])

        print ("========================================")

        print ("BTC Threshold: %0.8f" % settings.BTCThreshold)
        print ("NMC Threshold: %0.8f" % settings.NMCThreshold)
        print ("Efficiency Threshold: %s" % settings.EfficiencyThreshold)
        print ("Hold coins below efficiency threshold: %s" % settings.HoldCoins)

    except:
        print ("== !! ============================ !! ==")
        print ("Error:")

        try:
            ErrorMessage = balance['error']
        except:
            ErrorMessage = ("Unkown")

        print(ErrorMessage)

        print ("")

        print ("Could not connect Cex.IO, exiting")
        print ("== !! ============================ !! ==")
        exit()

    while True:
        try:
            now = time.asctime( time.localtime(time.time()) )

            print ("")
            print ("Start cycle at %s" % now)

            CancelOrder(context)

            ##balance = context.balance()
            GHSBalance = GetBalance(context, 'GHS')
            print ("GHS balance: %s" % GHSBalance)
            print ("")

            TargetCoin = GetTargetCoin(context)

            print ("Target Coin set to: %s" % TargetCoin[0])
            print ("")

            print ( "Efficiency threshold: %s" % settings.EfficiencyThreshold )
            print ( "Efficiency possible: %0.2f" % TargetCoin[1] )

            if (TargetCoin[1] >= settings.EfficiencyThreshold ):
                arbitrate = True
                print ("Arbitration desired, trade coins for target coin")
            else:
                arbitrate = False
                if ( settings.HoldCoins == True ):
                    print ("Arbitration not desired, hold non target coins this cycle")
                else:
                    print ("Arbitration not desired, reinvest all coins this cycle")

            print ("")
            PrintBalance( context, "BTC")
            PrintBalance( context, "NMC")

            if (TargetCoin[0] == "BTC"):
                if ( arbitrate ):
                    ReinvestCoin(context, "NMC", settings.NMCThreshold, TargetCoin[0] )
                else:
                    if ( settings.HoldCoins == False ):
                        ReinvestCoin(context, "NMC", settings.NMCThreshold, "GHS" )

                ReinvestCoin(context, "BTC", settings.BTCThreshold, "GHS" )

            if (TargetCoin[0] == "NMC"):
                if ( arbitrate ):
                    ReinvestCoin(context, "BTC", settings.BTCThreshold, TargetCoin[0] )
                else:
                    if ( settings.HoldCoins == False ):
                        ReinvestCoin(context, "BTC", settings.BTCThreshold, "GHS" )


                ReinvestCoin(context, "NMC", settings.NMCThreshold, "GHS" )

        except urllib2.HTTPError, err:
            print ("HTTPError :%s" % err)

        except:
            print ("Unexpected error:")
            print ( sys.exc_info()[0] )
            print ("An error occurred, skipping cycle")

        print("")

        cycle = 150
        print("Cycle completed, idle for %s seconds" % cycle)

        while cycle > 0:
            time.sleep(10)
            cycle = cycle - 10

    pass

## Convert a unicode based float to a real float for us in calculations
def ConvertUnicodeFloatToFloat( UnicodeFloat ):

    ## I need to use a regular expression
    ## get all the character from after the dot
    position = re.search( '\.', UnicodeFloat)
    if ( position ):
        first = position.regs
        place = first[0]
        p = place[0]
        p = p + 1

        MostSignificant  = float(UnicodeFloat[:p-1])
        LeastSignificant = float(UnicodeFloat[p:])

        Factor = len(UnicodeFloat[p:])
        Divider = 10 ** Factor

        LeastSignificant = LeastSignificant / Divider

        NewFloat = MostSignificant + LeastSignificant
    else:
        NewFloat = float(UnicodeFloat)

    return NewFloat

def CancelOrder(context):
    ## BTC Order cancel
    order = context.current_orders("GHS/BTC")
    for item in order:
        try:
            context.cancel_order(item['id'])
            print ("GHS/BTC Order %s canceled" % item['id'])
        except:
            print ("Cancel order failed")

    ## NMC Order cancel
    order = context.current_orders("GHS/NMC")
    for item in order:
        try:
            context.cancel_order(item['id'])
            print ("GHS/NMC Order %s canceled" % item['id'])
        except:
            print ("Cancel order failed")

    ## NMC Order cancel
    order = context.current_orders("NMC/BTC")
    for item in order:
        try:
            context.cancel_order(item['id'])
            print ("BTC/NMC Order %s canceled" % item['id'])
        except:
            print ("Cancel order failed")

## Get the balance of certain type of Coin
def GetBalance(Context, CoinName):

    balance = ("NULL")

    try:

        balance = Context.balance()

        Coin =  balance[CoinName]
        Saldo = ConvertUnicodeFloatToFloat(Coin["available"])

    except:
        print (balance)
        Saldo = 0

    return Saldo

## Return the Contex for connection
def GetContext():

    try:
        settings = LoadSettings()
    except:
        print ("Could not load settings, exiting")
        exit()

    username    = str(settings['username'])
    api_key     = str(settings['key'])
    api_secret  = str(settings['secret'])

    try:
        context = cexapi.api(username, api_key, api_secret)

    except:
        print (context)

    return context

def ParseArguments(settings):
    arguments = sys.argv
    
    if (len(arguments) > 1):
        print ("CexControl started with arguments")
        print ("")

        ## Remove the filename itself
        del arguments[0]

        for argument in arguments:

            if argument == "newconfig":
                print ("newconfig:")
                print ("  Delete settings and create new")
                settings.CreateSettings()

            if argument == "setthreshold":
                print ("setthreshold:")
                print ("  Creeate new threshold settings")
                settings.CreateTresholds()
                settings.LoadSettings()

            if argument == "version":
                print ("Version: %s" % version )
                exit()

## Print the balance of a Coin
def PrintBalance( Context, CoinName):

    Saldo = GetBalance(Context, CoinName)

    print ("%s" % CoinName, end = " ")
    print ("Balance: %.8f" % Saldo)


## Reinvest a coin
def ReinvestCoin(Context, CoinName, Threshold, TargetCoin ):

    Saldo = GetBalance(Context, CoinName)

    if ( Saldo > Threshold ):

        TradeCoin( Context, CoinName, TargetCoin )


## Trade one coin for another
def TradeCoin( Context, CoinName, TargetCoin ):

    ## Get the Price of the TargetCoin
    Price = GetPriceByCoin( Context, CoinName, TargetCoin )

    print ("----------------------------------------")

    ## Get the balance of the coin
    Saldo = GetBalance( Context, CoinName)
    print (CoinName , end = " " )
    print ("Balance %.8f" % Saldo)

    ## Caculate what to buy
    AmountToBuy = Saldo / Price
    AmountToBuy = round(AmountToBuy-0.000005,6)

    print ("Amount to buy %.08f" % AmountToBuy)

    ## This is an HACK
    Total = AmountToBuy * Price

    ## Adjusted to compensate for floating math conversion
    while ( Total > Saldo ):
        AmountToBuy = AmountToBuy - 0.0000005
        AmountToBuy = round(AmountToBuy-0.000005,6)

        print ("")
        print ("To buy adjusted to : %.8f" % AmountToBuy)
        Total = AmountToBuy * Price

    TickerName = GetTickerName( CoinName, TargetCoin )

    ## Hack, to differentiate between buy and sell
    action = ''
    if TargetCoin == "BTC":
        action = 'sell'
        AmountToBuy = Saldo ## sell the complete balance!
        print ("To sell adjusted to : %.8f NMC" % AmountToBuy)
    else:
        action = 'buy'

    result = Context.place_order(action, AmountToBuy, Price, TickerName )

    print ("")
    print ("Placed order at %s" % TickerName)
    print ("     Buy %.8f" % AmountToBuy, end = " ")
    print ("at %.8f" % Price)
    print ("   Total %.8f" % Total)
    print ("   Funds %.8f" % Saldo)

    try:
        OrderID = result['id']
        print ("Order ID %s" % OrderID)
    except:
        print (result)
        print (AmountToBuy)
        print ("%.7f" % Price)
        print (TickerName)


    print ("----------------------------------------")

## Simply reformat a float to 8 numbers behind the comma
def FormatFloat( number):

    number = unicode("%.8f" % number)
    return number

## Get TargetCoin, reveal what coin we should use to buy GHS
def GetTargetCoin(Context):
    ## Get the Price NMC/BTC

    GHS_NMCPrice = GetPrice(Context, "GHS/NMC")
    GHS_BTCPrice = GetPrice(Context, "GHS/BTC")
    NMC_BTCPrice = GetPrice(Context, "NMC/BTC")

    BTC_NMCPrice = 1/NMC_BTCPrice

    GHS_NMCPrice = 1/GHS_NMCPrice
    GHS_BTCPrice = 1/GHS_BTCPrice

    print ("1 NMC is %s GHS" % FormatFloat(GHS_NMCPrice))
    print ("1 NMC is %s BTC" % FormatFloat(NMC_BTCPrice))
    print ("1 BTC is %s GHS" % FormatFloat(GHS_BTCPrice))
    print ("1 BTC is %s NMC" % FormatFloat(BTC_NMCPrice))

    NMCviaBTC = NMC_BTCPrice * GHS_BTCPrice
    BTCviaNMC = BTC_NMCPrice * GHS_NMCPrice

    BTCviaNMCPercentage = BTCviaNMC / GHS_BTCPrice * 100
    NMCviaBTCPercentage = NMCviaBTC / GHS_NMCPrice * 100

    print ("")
    print ("1 BTC via NMC is %s GHS" % FormatFloat(BTCviaNMC), end = " " )
    print ("Efficiency : %2.2f" % BTCviaNMCPercentage)
    print ("1 NMC via BTC is %s GHS" % FormatFloat(NMCviaBTC), end = " " )
    print ("Efficiency : %2.2f" % NMCviaBTCPercentage)

    if NMCviaBTCPercentage > BTCviaNMCPercentage:
        coin = "BTC"
        efficiency = NMCviaBTCPercentage - 100
    else:
        coin = "NMC"
        efficiency = BTCviaNMCPercentage - 100

    returnvalue = (coin, efficiency)

    print ("")
    print ("Buy %s" % coin, end = " " )
    print ("then use that to buy GHS")

    return returnvalue

## Get the price of a coin for a market value
def GetPriceByCoin(Context, CoinName, TargetCoin ):

    Ticker = GetTickerName( CoinName, TargetCoin )

    return GetPrice(Context, Ticker)

## Fall back function to get TickerName
def GetTickerName( CoinName, TargetCoin ):

    Ticker = ""

    if CoinName == "NMC" :
        if TargetCoin == "GHS" :
            Ticker = "GHS/NMC"
        if TargetCoin == "BTC" :
            Ticker = "NMC/BTC"

    if CoinName == "BTC" :
        if TargetCoin == "GHS" :
            Ticker = "GHS/BTC"
        if TargetCoin == "NMC" :
            Ticker = "NMC/BTC"

    return Ticker

## Get Price by ticker
def GetPrice(Context, Ticker):

    ## Get price
    ticker = Context.ticker(Ticker)

    Ask = ConvertUnicodeFloatToFloat(ticker["ask"])
    Bid = ConvertUnicodeFloatToFloat(ticker["bid"])

    ## Get average
    Price = (Ask+Bid) / 2

    ## Change price to 7 decimals
    Price = round(Price,7)

    ##print Price
    ##Price = int(Price * INTEGERMATH)

    return Price


if __name__ == '__main__':
    main()
