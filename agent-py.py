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

# Global Variables
conversation = importlib.import_module('conversation')
extract_bid = importlib.import_module('extract-bid')

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

for i in range(len(sys.argv)):
    if sys.argv[i] == "--port":
        myPort = sys.argv[i + 1]

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

# ************************************************************************************************************ //
# REQUIRED APIs
# ************************************************************************************************************ //

@app.route('/setUtility', methods=['POST'])
def setUtility():
    if request.json:
        global utilityInfo
        utilityInfo = request.json
        print("NEW NAME", utilityInfo['name'])
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

@app.route('/startRound', methods=['POST'])
def startRound():
    bidHistory = {}
    if request.json:
        negotiationState['roundDuration'] = request.json['roundDuration'] or negotiationState['roundDuration']
        negotiationState['roundNumber'] = request.json['roundNumber'] or negotiationState['roundNumber']
    negotiationState['active'] = True
    negotiationState['startTime'] = time.time()
    negotiationState['stopTime'] = negotiationState['startTime'] + (1000 * negotiationState['roundDuration'])
    msg = {
        'status': 'Acknowledged'
    }
    return msg

@app.route('/endRound', methods=['POST'])
def endRound():
    negotiationState['active'] = False
    negotiationState['endTime'] = time.time()
    msg = {
        'status': 'Acknowledged'
    }
    return msg

@app.route('/receiveMessage', methods=['POST'])
def receiveMessage():
    timeRemaining = negotiationState['stopTime'] - (time.time()/ 1000.0)
    if timeRemaining <= 0:
        negotiationState['active'] = False
    
    response = None
    if not request.json:
        response = {
            'status': "Failed; no message body"
        }
    elif negotiationState['active']:
        message = request.json
        message['speaker'] = message['speaker'] or defaultSpeaker
        message['addressee'] = message['addressee']
        message['role'] = message['role'] or message['defaultRole']
        message['environmentUUID'] = message['environmentUUID'] or defaultEnvironmentUUID
        response = {
            'status': "Acknowledged",
            'interpretation': message
        }
        if message['speaker'] == agentName:
            print("This message is from me!")
        else:
            print("new message,", message)
            bidMessage = processMessage(message)
            if bidMessage:
                sendMessage(bidMessage)
    else:
        response = {
            'status': "Failed; round not active"
        }
    return response

@app.route('/receiveRejection', methods=['POST'])
def receiveRejection():
    timeRemaining = negotiationState['stopTime'] - (time.time()/ 1000.0)
    if timeRemaining <= 0:
        negotiationState['active'] = False
    
    response = None
    if not request.json:
        response = {
            'status': 'Failed; no message body'
        }
    elif negotiationState['active']:
        message = request.json
        response = {
            'status': 'Acknowledged',
            'message': message
        }
        if message['ratiolane'] and message['rationale'] == 'Insufficient budget' and message['bid'] and message['bid']['type'] == "Accept":
            msg2 = json.loads(json.dumps(message))
            del msg2['rationale']
            del msg2['bid']
            msg2['timestamp'] = time.time()
            msg2['text'] = "I'm sorry, " + msg2['addressee'] + ". I wasready to make a deal, but apparently you don't have enough money left."
            sendMessage(msg2)
    else:
        response = {
            'status': "Failed; round not active"
        }

    return response

# ************************************************************************************************************ //
# Non-required APIs (useful for unit testing)
# ************************************************************************************************************ //

@app.route('/classifyMessage', methods=['GET'])
def classifyMessageGet():

    data = request.json

    if data['text']:
        text = data['text']
        message = {
            'text': text,
            'speaker': defaultSpeaker,
            'addressee': defaultAddressee,
            'role': defaultRole,
            'environmentUUID': defaultEnvironmentUUID
        }
        waResponse = conversation.classifyMessage(message)
        return waResponse
        
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

@app.route('/reportUtility', methods=['GET'])
def reportUtility():
    if utilityInfo:
        return utilityInfo
    else:
        return {'error': 'utilityInfo not initialized'}


# ******************************************************************************************************* //
# ******************************************************************************************************* //
#                                               Functions
# ******************************************************************************************************* //
# ******************************************************************************************************* //


# ******************************************************************************************************* //
#                                         Bidding Algorithm Functions                                     //
# ******************************************************************************************************* //


def mayIRespond(interpretation):
    print("entered mayIRespond")
    return (interpretation and
            interpretation['metadata']['role'] and
            (interpretation['metadata']['addressee'] == agentName or
            not interpretation['metadata']['addressee']))

def calculateUtilityAgent(utilityInfo, bundle):
    print("entered calculateUtilityAgent")
    utilityParams = utilityInfo['utility']
    util = 0
    price = bundle['price']['value'] or 0

    if bundle['quantity']:
        util = price
        unit = bundle['price']['value'] or None
        if not unit:
            print("no currency units provided")
        elif unit == utilityInfo['currencyUnit']:
            print("Currency units match")
        else:
            print("Currency units do not match")
    
    for good in bundle['quantity'].keys():
        util -= utilityParams[good]['parameters']['unitcost'] * bundle['quantity'][good]
    
    return util

def generateBid(offer):
    print("entered generateBid")
    minDicker = 0.10
    buyerName = offer['metadata']['speaker']
    
    myRecentOffers = [bidBlock for bidBlock in bidHistory[buyerName] if bidBlock['type'] == "SellOffer"]
    myLastPrice = None
    if len(myRecentOffers):
        myLastPrice = myRecentOffers[len(myRecentOffers) - 1]['price']['value']
    
    timeRemaining = negotiationState['stopTime'] - (time.time()/ 1000.0)
    utility = calculateUtilityAgent(utilityInfo, offer)
    bid = {
        'quantity': offer['quantity']
    }

    if offer['price'] and offer['price']['value']:
        bundleCost = offer['price']['value'] - utility
        markupRatio = utility / bundleCost

        if markupRatio > 2.0 or (myLastPrice != None and abs(offer['price']['value'] - myLastPrice) < minDicker):
            bid['type'] = 'Accept'
            bid['price'] = offer['price']
        elif markupRatio < -0.5:
            bid['type'] = 'Reject'
            bid['price'] = None
        else:
            bid['type'] = 'SellOffer'
            bid['price'] = generateSellPrice(bundleCost, offer['price'], myLastPrice, timeRemaining)
            if bid['price']['value'] < offer['price']['value'] + minDicker:
                bid['type'] = 'Accept'
                bid['price'] = offer['price']
    else:
        markupRatio = 2.0 + random.random()
        bid['type'] = 'SellOffer'
        bid['price'] = {
            'unit': utilityInfo['currencyUnit'],
            'value': quantize((1.0 - markupRatio) * utility, 2)
        }
    return bid

def generateSellPrice(bundleCost, offerPrice, myLastPrice, timeRemaining):
    print("entered generateSellPrice")
    minMarkupRatio = 0
    maxMarkupRatio = 0
    markupRatio = offerPrice['value']/bundleCost - 1.0
    if myLastPrice != None:
        maxMarkupRatio = myLastPrice/bundleCost - 1.0
    else:
        maxMarkupRatio = 2.0 - 1.5 * (1.0 - timeRemaining/100000/negotiationState['roundDuration'])
    minMarkupRatio = max(markupRatio, 0.20)
    
    minProposedMarkup = max(minMarkupRatio, markupRatio)
    newMarkupRatio = minProposedMarkup + random.random() * (maxMarkupRatio - minProposedMarkup)
    
    price = {
        'unit': offerPrice['unit'],
        'value': (1.0 + newMarkupRatio) * bundleCost
    }

    price['value'] = quantize(price['value'], 2)

    return price


def processMessage(message):
    print("entered processOffer")
    classification = conversation.classifyMessage(message)

    classification['environmentUUID'] = message['environmentUUID']
    interpretation = extract_bid.interpretMessage(classification)

    speaker = interpretation['metadata']['speaker']
    addressee = interpretation['metadata']['addressee']
    role = interpretation['metadata']['role']

    if speaker == agentName:
        print("this message is from me")
        if interpretation['type'] == 'AcceptOffer' or interpretation['type'] == 'RejectOffer':
            bidHistory[addressee] = None
        else:
            if bidHistory[addressee]:
                bidHistory[addressee].append(interpretation)
    elif addressee ==agentName and role == 'buyer':
        messageResponse = {
            'text': "",
            'speaker': agentName,
            'role': "seller",
            'addressee': speaker,
            'environmentUUID': interpretation['metadata']['environmentUUID'],
            'timestamp': time.time()
        }
        if interpretation['type'] == 'AcceptOffer':
            if bidHistory[speaker] and len(bidHistory[speaker]):
                bidHistoryIndividual = [bid for bid in bidHistory[speaker] if bid['metadata']['speaker'] == agentName and bid['type'] == "SellOffer"]
                if len(bidHistoryIndividual):
                    acceptedBid = bidHistoryIndividual[-1]
                    bid = {
                        'price': acceptedBid['price'],
                        'quantity': acceptedBid['quantity'],
                        'type': "Accept"
                    }
                    messageResponse['text'] = translateBid(bid, True)
                    bidHistory[speaker] = None
                else:
                    messageResponse['text'] = "I'm sorry, but I'm not aware of any outstanding offers."
            else:
                messageResponse['text'] = "I'm sorry, but I'm not aware of any outstanding offers."
            return messageResponse
        elif interpretation['type'] == 'RejectOffer':
            if bidHistory[speaker] and len(bidHistory[speaker]):
                bidHistoryIndividual = [bid for bid in bidHistory[speaker] if bid['metadata']['speaker'] == agentName and bid['type'] == "SellOffer"]
                if len(bidHistoryIndividual):
                    messageResponse['text'] = "I'm sorry you rejected my bid. I hope we can do business in the near future."
                    bidHistory[speaker] = None
                else:
                    messageResponse['text'] = "There must be some confusion; I'm not aware of any outstanding offers."
            else:
                messageResponse['text'] = "OK, but I didn't think we had any outstanding offers."
            return messageResponse
        elif interpretation['type'] == 'Information':
            messageResponse = {
                'text': "OK. Thanks for letting me know.",
                'speaker': agentName,
                'role': "seller",
                'addressee': speaker,
                'evnironmentUUID': interpretation['metadata']['environmentUUID'],
                'timestamp': time.time()
            }
            return messageResponse
        elif interpretation['type'] == 'NotUnderstood':
            return None
        elif (interpretation['type'] == 'BuyOffer' or interpretation['type'] == 'BuyRequest') and mayIRespond(interpretation):
            if 'speaker' not in bidHistory:
                bidHistory[speaker] = []
            bidHistory[speaker].append(interpretation)

            bid = generateBid(interpretation)
            bidResponse = {
                'text': translateBid(bid, False),
                'speaker': agentName,
                'role': "seller",
                'addressee': speaker,
                'environmentUUID': interpretation['metadata']['environmentUUID'],
                'timestamp': time.time()
            }
            bidResponse['bid'] = bid
            return bidResponse
        else:
            return None
    elif role == 'buyer' and addressee != agentName:
        return None
    elif role == 'seller':
        return None
    return None


# ******************************************************************************************************* //
#                                                     Simple Utilities                                    //
# ******************************************************************************************************* //

def quantize(quantity, decimals):
    print("entered quantize")
    multiplicator = math.pow(10, decimals)
    q = float("%.2f" % (quantity * multiplicator))
    return round(q) / multiplicator

def getSafe(p, o, d):
    return reduce((lambda xs, x: xs[x] if (xs and xs[x] != None) else d), p)

# ******************************************************************************************************* //
#                                                    Messaging                                            //
# ******************************************************************************************************* //

def translateBid(bid, confirm):
    print("entered translateBid")
    text = ""
    print("Bid: ", bid)
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

def selectMessage(messageSet):
    print("entered selectMessage")
    msgSetSize = len(messageSet)
    indx = int(random.random() * msgSetSize)
    return messageSet[indx]

def sendMessage(message):
    print("entered sendMessage")
    return postDataToServiceType(message, 'environment-orchestrator', '/relayMessage')

def postDataToServiceType(json, serviceType, path):
    print("entered postDataToServiceType")
    serviceMap = appSettings['serviceMap']
    if serviceMap[serviceType]:
        options = serviceMap[serviceType]
        options['path'] = path
        url = options2URL(options)
        rOptions = {
            'method': 'POST',
            'uri': url,
            'body': json,
            'json': True
        }
        response = requests.post(url, data=json)
        return response

def options2URL(options):
    print("entered options2URL")
    protocol = options['protocol'] or 'http'
    url = protocol + '://' + options['host']
    if options['port']:
        url += ':' + str(options['port'])
    if options['path']:
        url += options['path']
    return url



if __name__ == "__main__":
    app.run(host='http://localhost', port=myPort)