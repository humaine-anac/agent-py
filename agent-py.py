# Imports
from flask import Flask
from flask import request
from functools import reduce
import requests
import importlib
import json
import sys
import time
import math
import random
app = Flask(__name__)

conversation = importlib.import_module('conversation')
extract_bid = importlib.import_module('extract-bid')

# Global variables / settings
appSettings = None
with open('./appSettings.json') as f:
    appSettings = json.load(f)
myPort = appSettings['defaultPort']
agentName = appSettings['name'] or "Agent007"
defaultRole = 'buyer'
defaultSpeaker = 'Jeff'
defaultEnvironmentUUID = 'abcdefg'
defaultAddressee = agentName
defaultRoundDuration = 600

# fetch the port number
for i in range(len(sys.argv)):
    if sys.argv[i] == "--port":
        myPort = sys.argv[i + 1]

# predefined responses
rejectionMessages = [
  "No thanks. Your offer is much too low for me to consider.",
  "Forget it. That's not a serious offer.",
  "Sorry. You're going to have to do a lot better than that!"
]
acceptanceMessages = [
  "You've got a deal! I'll sell you",
  "You've got it! I'll let you have",
  "I accept your offer. Just to confirm, I'll give you"
]
confirmAcceptanceMessages = [
  "I confirm that I'm selling you ",
  "I'm so glad! This is to confirm that I'll give you ",
  "Perfect! Just to confirm, I'm giving you "
]
negotiationState = {
  "active": False,
  "startTime": None,
  "roundDuration": defaultRoundDuration
}

utilityInfo = None
bidHistory = {}

# ************************************************************************************************************ #
# REQUIRED APIs
# ************************************************************************************************************ #

# API route that receives utility information from the environment orchestrator. This also
# triggers the start of a round and the associated timer.
@app.route('/setUtility', methods=['POST'])
def setUtility():
    if request.json:
        global utilityInfo
        utilityInfo = request.json
        global agentName
        agentName = utilityInfo['name'] or agentName
        msg = {
            'status': 'Acknowledged',
            'utility': utilityInfo
        }
        return msg
    else:
        msg = {
            'status': "Failed; no message body",
            'utility': None
        }
        return msg


# API route that tells the agent that the round has started.
@app.route('/startRound', methods=['POST'])
def startRound():
    bidHistory = {}
    if request.json:
        negotiationState['roundDuration'] = request.json['roundDuration'] or negotiationState['roundDuration']
        negotiationState['roundNumber'] = request.json['roundNumber'] or negotiationState['roundNumber']
    negotiationState['active'] = True
    negotiationState['startTime'] = (time.time() * 1000)
    negotiationState['stopTime'] = negotiationState['startTime'] + (1000 * negotiationState['roundDuration'])
    msg = {
        'status': 'Acknowledged'
    }
    return msg


# API route that tells the agent that the round has ended.
@app.route('/endRound', methods=['POST'])
def endRound():
    negotiationState['active'] = False
    negotiationState['endTime'] = (time.time() * 1000)
    msg = {
        'status': 'Acknowledged'
    }
    return msg


# POST API that receives a message, interprets it, decides how to respond (e.g. Accept, Reject, or counteroffer),
# and if it desires sends a separate message to the /receiveMessage route of the environment orchestrator
@app.route('/receiveMessage', methods=['POST'])
def receiveMessage():
    timeRemaining = (negotiationState['stopTime'] - (time.time() * 1000)) / 1000
    if timeRemaining <= 0:
        negotiationState['active'] = False
    
    response = None
    if not request.json:
        response = {
            'status': "Failed; no message body"
        }
    elif negotiationState['active']: # We received a message and time remains in the round.
        message = request.json
        message['speaker'] = message['speaker'] or defaultSpeaker
        message['addressee'] = message['addressee']
        message['role'] = message['role'] or message['defaultRole']
        message['environmentUUID'] = message['environmentUUID'] or defaultEnvironmentUUID
        response = { # Acknowledge receipt of message from the environment orchestrator
            'status': "Acknowledged",
            'interpretation': message
        }
        if message['speaker'] == agentName:
            print("This message is from me!")
        else:
            bidMessage = processMessage(message)
            if bidMessage: # If warranted, proactively send a new negotiation message to the environment orchestrator
                sendMessage(bidMessage)
    else: # Either there's no body or the round is over.
        response = {
            'status': "Failed; round not active"
        }
    return response


# POST API that receives a rejection message, and decides how to respond to it. If the rejection is based upon
# insufficient funds on the part of the buyer, generate an informational message to send back to the human, as a courtesy
# (or rather to explain why we are not able to confirm acceptance of an offer).
@app.route('/receiveRejection', methods=['POST'])
def receiveRejection():
    timeRemaining = (negotiationState['stopTime'] - (time.time() * 1000)) / 1000
    if timeRemaining <= 0:
        negotiationState['active'] = False
    
    response = None
    if not request.json:
        response = {
            'status': 'Failed; no message body'
        }
    elif negotiationState['active']: # We received a message and time remains in the round.
        message = request.json
        response = { # Acknowledge receipt of message from the environment orchestrator
            'status': 'Acknowledged',
            'message': message
        }
        if (message['ratiolan']
            and message['rational'] == 'Insufficient budget'
            and message['bid']
            and message['bid']['type'] == "Accept"): # We tried to respond with an accept, but were rejected.
                                                     # So that the buyer will not interpret our apparent silence as rudeness, 
                                                     # explain to the Human that he/she were rejected due to insufficient budget.
            msg2 = json.loads(json.dumps(message))
            del msg2['rational']
            del msg2['bid']
            msg2['timestamp'] = (time.time() * 1000)
            msg2['text'] = "I'm sorry, " + msg2['addressee'] + ". I wasready to make a deal, but apparently you don't have enough money left."
            sendMessage(msg2)
    else: # Either there's no body or the round is over.
        response = {
            'status': "Failed; round not active"
        }

    return response

# ************************************************************************************************************ #
# Non-required APIs (useful for unit testing)
# ************************************************************************************************************ #

# GET API route that simply calls Watson Assistant on the supplied text message to obtain intent and entities
@app.route('/classifyMessage', methods=['GET'])
def classifyMessageGet():

    data = request.json

    if data['text']:
        text = data['text']
        message = { # Hard-code the speaker, role and envUUID
            'text': text,
            'speaker': defaultSpeaker,
            'addressee': defaultAddressee,
            'role': defaultRole,
            'environmentUUID': defaultEnvironmentUUID
        }
        waResponse = conversation.classifyMessage(message)
        return waResponse


# POST API route that simply calls Watson Assistant on the supplied text message to obtain intents and entities
@app.route('/classifyMessage', methods=['POST'])
def classifyMessagePost():
    if request.json:
        message = request.json
        message['speaker'] = message['speaker'] or defaultSpeaker
        message['addressee'] = message['addressee'] or None
        message['role'] = message['role'] or message['defaultRole']
        message['environmentUUID'] = message['environmentUUID'] or defaultEnvironmentUUID
        waResponse = conversation.classifyMessage(message, message['environmentUUID'])
        if waResponse:
            return waResponse
        return "error classifying post"


# POST API route that is similar to /classify Message, but takes the further
# step of determining the type and parameters of the message (if it is a negotiation act),
# and formatting this information in the form of a structured bid.
@app.route('/extractBid', methods=['POST'])
def extractBid():

    if request.json:
        message = request.json
        message['speaker'] = message['speaker'] or defaultSpeaker
        message['addressee'] = message['addressee'] or None
        message['role'] = message['role'] or message['defaultRole']
        message['environmentUUID'] = message['environmentUUID'] or defaultEnvironmentUUID
        extractedBid = extract_bid.extractBidFromMessage(message)
        if extractedBid:
            return extractedBid
        return "error extracting bid"


# API route that reports the current utility information.
@app.route('/reportUtility', methods=['GET'])
def reportUtility():
    if utilityInfo:
        return utilityInfo
    else:
        return {'error': 'utilityInfo not initialized'}


# ******************************************************************************************************* #
# ******************************************************************************************************* #
#                                               Functions
# ******************************************************************************************************* #
# ******************************************************************************************************* #


# ******************************************************************************************************* #
#                                         Bidding Algorithm Functions                                     #
# ******************************************************************************************************* #

# *** mayIRespond()                 
# Choose not to respond to certain messages, either because the received offer has the wrong role
# or because a different agent is being addressed. Note that this self-censoring is stricter than that required
# by competition rules, i.e. this agent is not trying to steal a deal despite this being permitted under the
# right circumstances. You can do better than this!
def mayIRespond(interpretation):
    return (interpretation and
            interpretation['metadata']['role'] and
            (interpretation['metadata']['addressee'] == agentName or
            not interpretation['metadata']['addressee']))


# *** calculateUtilitySeller() 
# Calculate utility for a given bundle of goods and price, given the utility function
def calculateUtilityAgent(utilityInfo, bundle):
    utilityParams = utilityInfo['utility']
    util = 0
    price = bundle['price']['value'] or 0

    if bundle['quantity']:
        util = price
        unit = bundle['price']['value'] or None
        if not unit: # Check units -- not really used, but a good practice in case we want
                     # to support currency conversion some day
            print("no currency units provided")
        elif unit == utilityInfo['currencyUnit']:
            print("Currency units match")
        else:
            print("Currency units do not match")
    
    for good in bundle['quantity'].keys():
        util -= utilityParams[good]['parameters']['unitcost'] * bundle['quantity'][good]
    
    return util


# *** generateBid()
# Given a received offer and some very recent prior bidding history, generate a bid
# including the type (Accept, Reject, and the terms (bundle and price).
def generateBid(offer):
    minDicker = 0.10
    buyerName = offer['metadata']['speaker']
    
    myRecentOffers = [bidBlock for bidBlock in bidHistory[buyerName] if bidBlock['type'] == "SellOffer"]
    myLastPrice = None
    if len(myRecentOffers):
        myLastPrice = myRecentOffers[len(myRecentOffers) - 1]['price']['value']
    
    timeRemaining = (negotiationState['stopTime'] - (time.time() * 1000)) / 1000
    utility = calculateUtilityAgent(utilityInfo, offer)

    # Note that we are making no effort to upsell the buyer on a different package of goods than what they requested.
    # It would be legal to do so, and perhaps profitable in some situations -- consider doing that!

    bid = {
        'quantity': offer['quantity']
    }

    if offer['price'] and offer['price']['value']: # The buyer included a proposed price, which we must take into account
        bundleCost = offer['price']['value'] - utility
        markupRatio = utility / bundleCost

        if (markupRatio > 2.0
            or (myLastPrice != None
            and abs(offer['price']['value'] - myLastPrice) < minDicker)): # If our markup is large, accept the offer

            bid['type'] = 'Accept'
            bid['price'] = offer['price']

        elif markupRatio < -0.5: # If buyer's offer is substantially below our cost, reject their offer
            bid['type'] = 'Reject'
            bid['price'] = None
        else: # If buyer's offer is in a range where an agreement seems possible, generate a counteroffer
            bid['type'] = 'SellOffer'
            bid['price'] = generateSellPrice(bundleCost, offer['price'], myLastPrice, timeRemaining)
            if bid['price']['value'] < offer['price']['value'] + minDicker:
                bid['type'] = 'Accept'
                bid['price'] = offer['price']
    else: # The buyer didn't include a proposed price, leaving us free to consider how much to charge.
    # Set markup between 2 and 3 times the cost of the bundle and generate price accordingly.
        markupRatio = 2.0 + random.random()
        bid['type'] = 'SellOffer'
        bid['price'] = {
            'unit': utilityInfo['currencyUnit'],
            'value': quantize((1.0 - markupRatio) * utility, 2)
        }
    return bid


# *** generateSellPrice()
# Generate a bid price that is sensitive to cost, negotiation history with this buyer, and time remaining in round
def generateSellPrice(bundleCost, offerPrice, myLastPrice, timeRemaining):
    minMarkupRatio = 0
    maxMarkupRatio = 0
    markupRatio = offerPrice['value']/bundleCost - 1.0
    if myLastPrice != None:
        maxMarkupRatio = myLastPrice/bundleCost - 1.0
    else:
        maxMarkupRatio = 2.0 - 1.5 * (1.0 - timeRemaining/negotiationState['roundDuration']) # Linearly decrease max markup ratio towards 
                                                                                             # just 0.5 at the conclusion of the round
    minMarkupRatio = max(markupRatio, 0.20)
    
    minProposedMarkup = max(minMarkupRatio, markupRatio)
    newMarkupRatio = minProposedMarkup + random.random() * (maxMarkupRatio - minProposedMarkup)
    
    price = {
        'unit': offerPrice['unit'],
        'value': (1.0 + newMarkupRatio) * bundleCost
    }

    price['value'] = quantize(price['value'], 2)

    return price


# *** processMessage() 
# Orchestrate a sequence of
# * classifying the message to obtain and intent and entities
# * interpreting the intents and entities into a structured representation of the message
# * determining (through self-policing) whether rules permit a response to the message
# * generating a bid (or other negotiation act) in response to the offer
def processMessage(message):
    classification = conversation.classifyMessage(message)

    classification['environmentUUID'] = message['environmentUUID']
    interpretation = extract_bid.interpretMessage(classification)

    speaker = interpretation['metadata']['speaker']
    addressee = interpretation['metadata']['addressee']
    role = interpretation['metadata']['role']

    if speaker == agentName: # The message was from me; this means that the system allowed it to go through.
        # If the message from me was an accept or reject, wipe out the bidHistory with this particular negotiation partner
        # Otherwise, add the message to the bid history with this negotiation partner
        if interpretation['type'] == 'AcceptOffer' or interpretation['type'] == 'RejectOffer':
            bidHistory[addressee] = None
        else:
            if bidHistory[addressee]:
                bidHistory[addressee].append(interpretation)
    elif addressee == agentName and role == 'buyer': # Message was addressed to me by a buyer; continue to process
        messageResponse = {
            'text': "",
            'speaker': agentName,
            'role': "seller",
            'addressee': speaker,
            'environmentUUID': interpretation['metadata']['environmentUUID'],
            'timestamp': (time.time() * 1000)
        }
        if interpretation['type'] == 'AcceptOffer': # Buyer accepted my offer! Deal with it.
            if bidHistory[speaker] and len(bidHistory[speaker]): # I actually did make an offer to this buyer;
                                                                 # fetch details and confirm acceptance
                bidHistoryIndividual = [bid for bid in bidHistory[speaker] if bid['metadata']['speaker'] == agentName and bid['type'] == "SellOffer"]
                if len(bidHistoryIndividual):
                    acceptedBid = bidHistoryIndividual[-1]
                    bid = {
                        'price': acceptedBid['price'],
                        'quantity': acceptedBid['quantity'],
                        'type': "Accept"
                    }
                    messageResponse['text'] = translateBid(bid, True)
                    messageResponse['bid'] = bid
                    bidHistory[speaker] = None
                else: # Didn't have any outstanding offers with this buyer
                    messageResponse['text'] = "I'm sorry, but I'm not aware of any outstanding offers."
            else: # Didn't have any outstanding offers with this buyer
                messageResponse['text'] = "I'm sorry, but I'm not aware of any outstanding offers."

            return messageResponse
        elif interpretation['type'] == 'RejectOffer': # The buyer claims to be rejecting an offer I made; deal with it
            if bidHistory[speaker] and len(bidHistory[speaker]): # Check whether I made an offer to this buyer
                bidHistoryIndividual = [bid for bid in bidHistory[speaker] if bid['metadata']['speaker'] == agentName and bid['type'] == "SellOffer"]
                if len(bidHistoryIndividual):
                    messageResponse['text'] = "I'm sorry you rejected my bid. I hope we can do business in the near future."
                    bidHistory[speaker] = None
                else:
                    messageResponse['text'] = "There must be some confusion; I'm not aware of any outstanding offers."
            else:
                messageResponse['text'] = "OK, but I didn't think we had any outstanding offers."
            return messageResponse
        elif interpretation['type'] == 'Information': # The buyer is just sending an informational message. Reply politely without attempting to understand.
            messageResponse = {
                'text': "OK. Thanks for letting me know.",
                'speaker': agentName,
                'role': "seller",
                'addressee': speaker,
                'evnironmentUUID': interpretation['metadata']['environmentUUID'],
                'timestamp': (time.time() * 1000)
            }
            return messageResponse
        elif interpretation['type'] == 'NotUnderstood': # The buyer said something, but we can't figure out what
                                                        # they meant. Just ignore them and hope they'll try again if it's important.
            return None
        elif ((interpretation['type'] == 'BuyOffer'
                or interpretation['type'] == 'BuyRequest')
                and mayIRespond(interpretation)): #The buyer evidently is making an offer or request; if permitted, generate a bid response
            if 'speaker' not in bidHistory:
                bidHistory[speaker] = []
            bidHistory[speaker].append(interpretation)

            bid = generateBid(interpretation) # Generate bid based on message interpretation, utility,
                                              # and the current state of negotiation with the buyer
            bidResponse = {
                'text': translateBid(bid, False), # Translate the bid into English
                'speaker': agentName,
                'role': "seller",
                'addressee': speaker,
                'environmentUUID': interpretation['metadata']['environmentUUID'],
                'timestamp': (time.time() * 1000),
                'bid': bid
            }

            return bidResponse
        else:
            return None
    elif role == 'buyer' and addressee != agentName:  # Message was not addressed to me, but is a buyer.
                                                      # A more clever agent might try to steal the deal.
        return None
    elif role == 'seller': # Message was from another seller. A more clever agent might be able to exploit this info somehow!
        return None
    return None


# ******************************************************************************************************* #
#                                                     Simple Utilities                                    #
# ******************************************************************************************************* #

# *** quantize()
# Quantize numeric quantity to desired number of decimal digits
# Useful for making sure that bid prices don't get more fine-grained than cents
def quantize(quantity, decimals):
    multiplicator = math.pow(10, decimals)
    q = float("%.2f" % (quantity * multiplicator))
    return round(q) / multiplicator


# *** getSafe() 
# Utility that retrieves a specified piece of a JSON structure safely.
# o: the JSON structure from which a piece needs to be extracted, e.g. bundle
# p: list specifying the desired part of the JSON structure, e.g.['price', 'value'] to retrieve bundle.price.value
# d: default value, in case the desired part does not exist.
def getSafe(p, o, d):
    return reduce((lambda xs, x: xs[x] if (xs and xs[x] != None) else d), p)

# ******************************************************************************************************* #
#                                                    Messaging                                            #
# ******************************************************************************************************* #

# *** translateBid()
# Translate structured bid to text, with some randomization
def translateBid(bid, confirm):
    text = ""
    if bid['type'] == 'SellOffer':
        text = "How about if I sell you"
        for good in bid['quantity'].keys():
            text += " " + str(bid['quantity'][good]) + " " + good
        text += " for " + str(bid['price']['value']) + " " + str(bid['price']['unit']) + "."
    elif bid['type'] == 'Reject':
        text = selectMessage(rejectionMessages)
    elif bid['type'] == 'Accept':
        if confirm:
            text = selectMessage(confirmAcceptanceMessages)
        else:
            text = selectMessage(acceptanceMessages)
        for good in bid['quantity'].keys():
            text += " " + str(bid['quantity'][good]) + " " + good
        text += " for " + str(bid['price']['value']) + " " + str(bid['price']['unit']) + "."
    
    return text


# *** selectMessage()
# Randomly select a message or phrase from a specified set
def selectMessage(messageSet):
    msgSetSize = len(messageSet)
    indx = int(random.random() * msgSetSize)
    return messageSet[indx]


# *** sendMessage()
# Send specified message to the /receiveMessage route of the environment orchestrator
def sendMessage(message):
    return postDataToServiceType(message, 'environment-orchestrator', '/relayMessage')


# *** postDataToServiceType()
# POST a given json to a service type; mappings to host:port are externalized in the appSettings.json file
def postDataToServiceType(json, serviceType, path):
    serviceMap = appSettings['serviceMap']
    if serviceMap[serviceType]:
        options = serviceMap[serviceType]
        options['path'] = path
        url = options2URL(options)
        
        response = requests.post(url, json=json)
        return response


# *** options2URL() 
# Convert host, port, path to URL
def options2URL(options):
    protocol = options['protocol'] or 'http'
    url = protocol + '://' + options['host']
    if options['port']:
        url += ':' + str(options['port'])
    if options['path']:
        url += options['path']
    return url


# Start the API
if __name__ == "__main__":
    app.run(host='http://localhost', port=myPort)
