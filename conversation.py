# Imports
import importlib
import json
import ibm_watson
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

# Global Variables & settings
AssistantV2 = ibm_watson.AssistantV2

assistantParams = None
with open('./assistantParams.json') as f:
    assistantParams = json.load(f)

authenticator = IAMAuthenticator(assistantParams['apikey'])
assistant = AssistantV2(
    version=assistantParams['version'],
    authenticator=authenticator
)
assistant.set_service_url(assistantParams['url'])
assistant.set_default_headers({'x-watson-learning-opt-out': "true"})

GLOBAL_sessionID = None

# Methods
# create a new session ID for watson assistant
def createSessionID(assistantID):
    sessionData = assistant.create_session(assistant_id=assistantID).get_result()
    return sessionData['session_id']


# Send a user message to ibm assistant to be processed and classified
def classifyMessage(input_):
    assistantId = assistantParams['assistantId']
    text = None
    if input_['text']:
        text = input_['text'].replace('/[\t\r\n]+/g', " ").strip()
    
    assistantMessageParams = {'assistantId': assistantId, 'input': {}}

    if text:
        assistantMessageParams['input'] = {
            'message_type': "text",
            'text': text,
            'options': {
                'alternate_intents': True,
                "return_context": True
            }
        }
        assistantMessageParams['sessionId'] = GLOBAL_sessionID
    
    response = None

    # try to get a response with the current session ID
    try:
        response = assistant.message(
            assistant_id=assistantId,
            session_id=GLOBAL_sessionID,
            input={
                'message_type': 'text',
                'text': text
            }
        )
        translateWatsonResponse(response, input_)
    except:

        # create a new session ID and try again
        try:

            sessionId = createSessionID(assistantId)
            response = response = assistant.message(
                assistant_id=assistantId,
                session_id=sessionId,
                input={
                    'message_type': 'text',
                    'text': text
                }
            ).get_result()

            return translateWatsonResponse(response, input_)
        except:
            print("Error creating sessionId for assistantId", assistantId)
    
    return None


# convert watsons response to a usable JSON object
def translateWatsonResponse(response, input_):

    output = response['output'] or {}
    output['input'] = input_
    output['addressee'] = input_['addressee']
    output['speaker'] = input_['speaker']

    return output
