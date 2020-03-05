# imports
import time
import json
import importlib
conversation = importlib.import_module('conversation')

# Methods
def interpretMessage(watsonResponse):
    print("entered interpretMessage")

    intents = watsonResponse['intents']
    entities = watsonResponse['entities']
    cmd = {}

    if intents[0]['intent'] == "Offer" and intents[0]['confidence'] > 0.2:
        extractedOffer = extractOfferFromEntities(entities)
        cmd = {
            'quantity': extractedOffer['quantity']
        }
        if extractedOffer['price']:
            cmd['price'] = extractedOffer['price']
            if watsonResponse['input']['role'] == 'buyer':
                cmd['type'] = "BuyOffer"
            elif watsonResponse['input']['role'] == 'seller':
                cmd['type'] = "SellOffer"
        else:
            if watsonResponse['input']['role'] == 'buyer':
                cmd['type'] = "BuyRequest"
            elif watsonResponse['input']['role'] == 'seller':
                cmd['type'] = "SellRequest"
    elif intents[0]['intent'] == "AcceptOffer" and intents[0]['confidence'] > 0.2:
        cmd = {'type': "AcceptedOffer"}
    elif intents[0]['intent'] == "RejectOffer" and intents[0]['confidence'] > 0.2:
        cmd = {'type': "RejectOffer"}
    elif intents[0]['intent'] == 'Information' and intents[0]['confidence'] > 0.2:
        cmd = {'type': "Information"}
    else:
        cmd = {'type': "NotUnderstood"}
    
    if cmd:
        cmd['metadata'] = watsonResponse['input']
        cmd['metadata']['addressee'] = watsonResponse['input']['addressee'] or extractAddressee(entities)
        cmd['metadata']['timeStamp'] = time.time()
    return cmd

def extractAddressee(entities):
    print("entered extractAddressee")
    addressees = []
    addressee = None
    for eBlock in entities:
        if eBlock['entity'] == "avatarName":
            addressees.append(eBlock['value'])
    
    if 'agentName' in addressees.keys():
        addressee = addressees['agentName']
    else:
        addressee = addressees[0]
    return addressee

def extractOfferFromEntities(entityList):
    print("entered extractOfferFromEntities")
    entities = json.loads(json.dumps(entityList))
    removedIndices = []
    quantity = {}
    state = None
    amount = None

    for i, eBlock in enumerate(entities):
        entities[i]['index'] = i
        if eBlock['entity'] == 'sys-number':
            amount = float(eBlock['value'])
            state = 'amount'
        elif eBlock['entity'] == 'good' and state == 'amount':
            quantity[eBlock['value']] = amount
            state = None
            removedIndices.append(i - 1)
            removedIndices.append(i)
    
    entities = [entity for entity in entities if entity['index'] not in removedIndices]

    price = extractPrice(entities)

    return {'quantity': quantity, 'price': price}

def extractPrice(entities):
    print("entered extractPrice")
    price = None

    for eBlock in entities:
        if eBlock['entity'] == 'sys-currency':
            price = {
                'value': eBlock['metadata']['numeric_value'],
                'unit': eBlock['metadata']['unit']
            }
        elif eBlock['entity'] == 'sys-number' and not price:
            price = {
                'value': eBlock['metadata']['numeric_value'],
                'unit': 'USD'
            }

    return price

def extractBidFromMessage(message):
    print("entered extractBidFromMessage")
    response = conversation.classifyMessage(message)
    response['environmentUUID'] = message['environmentUUID']

    receivedOffer = interpretMessage(response)
    extractedBid = {
        'type': receivedOffer['type'],
        'price': receivedOffer['price'],
        'quantity': receivedOffer['quantity']
    }
    return extractedBid