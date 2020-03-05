# agent-py
This is a simple sample negotiation agent that works with the HUMAINE negotiating agents platform. It is intended to serve as

- A simple agent against which others may be tested
- A simple code example upon which more sophisticated negotiation agents can be based
- An example of how to use Watson Assistant to help interpret English into a structured bid representation

How to install the HUMAINE negotiation agent
----

To install an instance of the sample HUMAINE negotiation agent, execute the following commands:

```sh
git clone git@github.com:humaine-anac/agent-py.git
cd agent-py
cp appSettings.json.template1 appSettings.json
cp assistantParams.json.template assistantParams.json
npm install
```

For this particular sample agent, you need a Watson Assistant instance and an associated skill. You can visit this site to set up a free account: https://cloud.ibm.com/registration?target=/developer/watson/launch-tool/conversation&hideTours=true&cm_sp=WatsonPlatform-WatsonPlatform-_-OnPageNavCTA-IBMWatson_Conversation-_-Watson_Developer_Website&cm_mmca1=000027BD. This will guide you through the process of setting up an account, and creating a Watson Assistant. You will need to create a skill to associate with your Watson Assistant instance.

To do that, upload the file `skill-HUMAINE-agent-v2.json`, which is in this repository.

Edit the file assistantParams.json to include the correct apikey, url, and assistantId for the Watson Assistant instance that you created.

Finally, to instantiate the agent, execute
```sh
node agent-jok.js -level 2 -port 14007 > agent001.log &
```

Now you should have a running instance of the negotiation agent.

To instantiate a second instance of the agent, repeat all of the steps above, with *jok2* replacing *jok1*, *template2* replacing *template1*, and *-port 14008* replacing *-port 14007*. Explicitly, assuming you are starting from the agent-jok1 directory, execute:

```sh
cd ..
git clone git@github.com:humaine-anac/agent-jok.git
mv agent-jok agent-jok2
cd agent-jok2
cp appSettings.json.template2 appSettings.json
cp ../agent-jok1/assistantParams.json .
npm install
node agent-jok.js -level 2 -port 14008 > agent001.log &
```
*Note that the assistantParams.json file should be the same in the agent-jok1 and agent-jok2 directories.*


How to test the negotiation agent (normal setup)
----

To test this agent under normal circumstances, you need at a minimum:
- The environment orchestrator (repository `environment-orchestrator`)
- The utility generator (repository `utility` )
- The chat UI (repository `chatUI`)
- Two instances of this negotiation agent (this repository, `agent-jok`)

Here are brief instructions for testing:
- Configure and install the 5 services listed above, following the instructions in the README files of each repository.

Now you should be able to test the system by performing the following steps in order:

- **To start a round**: Click the Start Round button on the chat UI.

- **To act as a human negotiator**: Wait a few seconds for the round to start. Type text into the chat window. You can do this repeatedly while the round is active. Once either you or a seller agent accepts an offer, the goods are recorded as sold for the agreed-upon amount, and you can start a new negotiation if there is time remaining in the round and you have enough cash. Note that, in this stand-alone version, you will have to address the agents by name with each request so that the agents can know when they are being addressed. Example phrases include:
  - Celia, I want to buy 5 eggs, 3 cups of sugar and 4 ounces of chocolate for $5.
  - Watson, I'll give you $4.50 for 4 cups of milk and 3 packets of blueberries.
  - Celia, I accept your offer of 5 eggs, 3 cups of sugar and 4 ounces of chocolate for $8.50.
  - Watson, that's too expensive. Forget about it.
 

- **To view the queue of messages** received by the environment orchestrator: `<host>:14010/viewQueue`

- **To view the round totals thus far**: `<host>:14010/viewTotals`

- At the end of the round, the chat UI will display round totals (utility, revenue/cost, and goods purchased) for both agents and for the human

*Note that there is some delay between when you ask for a round to start and the actual start of the round;
this delay is established when the round is started . So a bid will not be valid until the round actually starts.
The default value is 5 seconds; we may want to set it to 30 seconds in the actual competition to give humans time
to think about their negotiation strategy.*

How to test the negotiation agent (minimal setup)
----

In situations where the chat UI is not available, testing this agent is a little more awkward, but still possible. In this case, you need at a minimum:
- The environment orchestrator (see the repository `environment-orchestrator`)
- Two instances of this negotiation agent (see instructions above)
- The utility generator (see the repository `utility`)

Here are brief instructions for testing:
- Start the environment orchestrator, the utility generator, and two instances of this agent in the manner described above in the normal setup instructions.

- To start a round: `<host>:14010/startRound?round=1` *This calls the environment orchestrator and asks it to start a round.*

- To simulate a human speaking: `<host>:14010/sendOffer?text=%22Hey%20Watson%20I%20will%20give%20you%204.75%20for%202%20eggs,%201%20cup%20of%20chocolate,%201%20packet%20of%20blueberries,%20and%208%20cups%20of%20milk.%20Also%203%20loaves%20of%20bread.%22`.
  *This uses a GET route of the environment orchestrator to simulate a human speaking.*

- To view the queue of messages received by the environment orchestrator: `<host>:14010/viewQueue`
- You can iterate the second two steps several times to simulate a human buyer responding to the agent message in the message queue. 
  This step will become much easier with the ChatUI. Then you'll be able to type the human buyer message and see agent responses.
  Note that, in this stand-alone version, you will have to address the agents by name with each request so that the agents
  know when they are being addressed.

Note that there is some delay between when you ask for a round to start and the actual start of the round;
this delay is set in appSettings.json (roundWarmupDelay). So a bid will not be valid until the round actually starts.
The default value is 5 seconds; we may want to set it to 30 seconds in the actual competition to give humans time to think about their negotiation strategy. 

Essential APIs
----


`/setUtility (POST)`
-----

This API, typically called by the Environment Orchestrator, establishes the utility for the agent just before the round starts. It may also contain the name to be used by the agent. 

Example POST body:

```
{
  "currencyUnit": "USD",
  "utility": {
    "egg": {
      "type": "unitcost",
      "unit": "each",
      "parameters": {
        "unitcost": 0.32
      }
    },
    "flour": {
      "type": "unitcost",
      "unit": "cup",
      "parameters": {
        "unitcost": 0.85
      }
    },
    "sugar": {
      "type": "unitcost",
      "unit": "cup",
      "parameters": {
        "unitcost": 0.71
      }
    },
    "milk": {
      "type": "unitcost",
      "unit": "cup",
      "parameters": {
        "unitcost": 0.35
      }
    },
    "chocolate": {
      "type": "unitcost",
      "unit": "ounce",
      "parameters": {
        "unitcost": 0.2
      }
    },
    "blueberry": {
      "type": "unitcost",
      "unit": "packet",
      "parameters": {
        "unitcost": 0.45
      }
    },
    "vanilla": {
      "type": "unitcost",
      "unit": "teaspoon",
      "parameters": {
        "unitcost": 0.27
      }
    }
  },
  "name": "Watson"
}
```

In response, the agent sends a status message indicating whether the message has been received successfully: either 

```
{
    "status": "Acknowleged",
    "utility": <exact copy of utility info that was received in the POST body>
}
```

or 

```
{
    "status": "Failed; no message body",
    "utility": null
}
```
respectively.


`/startRound (POST)`
-----

This API call, typically received from the Environment Orchestrator, informs the agent that a new round has begun, and provides information about the duration and the round number.

Example POST body:

```
{
    "roundDuration": 300,
    "roundNumber": 1,
    "timestamp": "2020-02-23T06:27:10.282Z"
}
```

In response, the agent sends an acknowledgment of the form:

```
{
    "status": "Acknowledged"
}
```

`/endRound (POST)`
-----
This API call, typically received from the Environment Orchestrator, informs the agent that the current round has ended. Beyond this point, no offers can be sent or received.

Example POST body:

```
{
    roundNumber: 1,
    "timestamp": "2020-02-23T06:32:10.282Z"
}
```

In response, the agent sends an acknowledgment of the form:

```
{
    "status": "Acknowledged"
}
```

`/receiveMessage (POST)`
-----
Receives a message, interprets it, decides how to respond (e.g. Accept, Reject, or counteroffer),
// and if it desires sends a separate message to the /relayMessage route of the environment orchestrator. The POST body is the same as is expected for `/classifyMessage (POST)`, above.

Example: http://localhost:14007/receiveMessage with POST body

```
{
  "speaker": "Human",
  "addressee": "Watson",
  "text": "Watson I'd like to buy 5 eggs for $2",
  "role": "buyer",
  "environmentUUID": "abcdefg",
  "timestamp": 1582184608849
}
```

will cause the agent to classify the message (as for /classifyMessage), whereupon it will respond with an acknowledgment like:

```
{
  "status": "Acknowledged",
  "interpretation": {
    "text": "Watson I want to buy 5 eggs for $2",
    "speaker": "Human",
    "addressee": "Watson",
    "role": "buyer",
    "environmentUUID": "abcdefg"
  }
}
```

The agent will continue to process the message by running its negotiation algorithm to determine a negotiation action (offer, counteroffer, acceptance, rejection, no action). Then, if some negotiation action is to be taken, the agent will formulate a human-friendly message and POST it to the /relayMessage API of the `environment-orchestrator`. An example of such a message is:

```
{
  "text": "How about if I sell you 5 egg for 3.73 USD.",
  "speaker": "Watson",
  "role": "seller",
  "addressee": "Human",
  "environmentUUID": "abcdefg",
  "timeStamp": "2020-02-20T08:08:05.825Z",
  "bid": {
    "quantity": {
      "egg": 5
    },
    "type": "SellOffer",
    "price": {
      "unit": "USD",
      "value": 3.73
    }
  }
}
```
*Note that this message is *not* a direct response to the call to `/receiveMessage (POST)` API of the agent, as that response is simply an acknowledgment of the call to `/receiveMessage (POST)`. Instead, this is a separately generated message initiated by the agent (although in practice it may follow the acknowledgment message rather quickly.)*


`/receiveRejection (POST)`
-----
Receives a rejection notice from the Environment Orchestrator, signifying that the Environment Orchestrator has not accepted a message that the agent recently relayed to it. The POST body is an exact copy of the rejected message, which for example might have the following form:

```
{
  "text": "How about if I sell you 1 blueberry for 0.69 USD.",
  "speaker": "Celia",
  "role": "seller",
  "addressee": "Human",
  "environmentUUID": "abcdefg",
  "timeStamp": "2020-02-23T02:22:39.152Z",
  "bid": {
    "quantity": {
      "blueberry": 1
    },
    "type": "SellOffer",
    "price": {
      "unit": "USD",
      "value": 0.69
    }
  }
}
```

The response to this API call is either an acknowledgment (when there is a message in the POST body and the round is active) or a failure otherwise. These have the form:

```
{
    "status": "acknowledged",
    "message": *message*
}
```
or 

```
{
    "status": "Failed",
}
```

respectively. This particular agent adjusts the negotiation state to inactive (active = false) when this message is received -- but agents are free to react in any way that the developer deems appropriate.


Additional APIs implemented for this agent
---

`/classifyMessage (GET)`
-----
Calls Watson Assistant on text message supplied in the `text` query parameter. This API is intended for test purposes, and not expected to be used in the context of a round of negotiation.

Example: `http://localhost:14007/classifyMessage?text=Celia%20I%20want%20to%20buy%205%20eggs%20for%20$2` should yield an output like:
```
{
   "generic":[
      {
         "response_type":"text",
         "text":"I didn't get your meaning." // Don't be concerned about this.
      }
   ],
   "intents":[
      {
         "intent":"Offer",
         "confidence":0.39777559260191997
      },
      {
         "intent":"RejectOffer",
         "confidence":0.10084306088756137
      },
      {
         "intent":"AcceptOffer",
         "confidence":0.0901161692885708
      }
   ],
   "entities":[
      {
         "entity":"avatarName",
         "location":[
            0,
            5
         ],
         "value":"Celia",
         "confidence":1
      },
      {
         "entity":"sys-number",
         "location":[
            20,
            21
         ],
         "value":"5",
         "confidence":1,
         "metadata":{
            "numeric_value":5
         }
      },
      {
         "entity":"good",
         "location":[
            22,
            26
         ],
         "value":"egg",
         "confidence":1
      },
      {
         "entity":"sys-currency",
         "location":[
            31,
            33
         ],
         "value":"2",
         "confidence":1,
         "metadata":{
            "numeric_value":2,
            "unit":"USD"
         }
      },
      {
         "entity":"sys-number",
         "location":[
            32,
            33
         ],
         "value":"2",
         "confidence":1,
         "metadata":{
            "numeric_value":2
         }
      }
   ],
   "input":{
      "text":"Celia I want to buy 5 eggs for $2",
      "speaker":"Jeff",                             // Default used for testing
      "addressee":"agent007",                       // Default used for testing
      "role":"buyer",
      "environmentUUID":"abcdefg"                   // Default used for testing
   },
   "addressee":"agent007",
   "speaker":"Jeff",
   "environmentUUID":"abcdefg"
}
```


`/classifyMessage (POST)`
-----
Calls Watson Assistant on a POST body that contains the text to be classified, along with other metadata such as speaker, addressee, role, etc. This API is intended for test purposes, and not expected to be used in the context of a round of negotiation.

Example: http://localhost:14007/classifyMessage with POST body
```
{
    "text": "Celia I want to buy 5 eggs for $2",
	"speaker": "Matt",
	"addressee": "Celia",
	"role": "buyer",
	"environmentUUID": "abcdefg"
}
```

should yield an output very much like the one in the `GET /classifyMessage` example above, except for the speaker and addressee being "Matt" and "Celia", respectively.

`/extractBid (POST)`
-----
Like `/classifyMessage`, `/extractBid` calls Watson Assistant on a POST body that contains the text to be classified, along with other metadata such as speaker, addressee, role, etc. It takes the further step of determining the type and parameters of the message (if it is a negotiation act), and formatting this information in the form of a structured bid. This API is intended for test purposes, and not expected to be used in the context of a round of negotiation. But it may be useful for the chatUI or humanUI to use this same code (modularized in `conversation.js` and `extract-bid.js` to extract bids from text messages.

Example: http://localhost:14007/extractBid with POST body
```
{
    "text": "Celia I want to buy 5 eggs for $2",
    "speaker": "Matt",
	"addressee": "Celia",
	"role": "buyer",
	"environmentUUID": "abcdefg"
}
```

should yield the output:
```
{
  "type": "BuyOffer",
  "price": {
    "value": 2,
    "unit": "USD"
  },
  "quantity": {
    "egg": 5
  }
}
```

`/reportUtility (GET)`
-----
This API reports the current utility function parameters in use by the agent. There are no query parameters.

Example response:

```
{
   "currencyUnit":"USD",
   "utility":{
      "egg":{
         "type":"unitcost",
         "unit":"each",
         "parameters":{
            "unitcost":0.32
         }
      },
      "flour":{
         "type":"unitcost",
         "unit":"cup",
         "parameters":{
            "unitcost":0.85
         }
      },
      "sugar":{
         "type":"unitcost",
         "unit":"cup",
         "parameters":{
            "unitcost":0.71
         }
      },
      "milk":{
         "type":"unitcost",
         "unit":"cup",
         "parameters":{
            "unitcost":0.35
         }
      },
      "chocolate":{
         "type":"unitcost",
         "unit":"ounce",
         "parameters":{
            "unitcost":0.2
         }
      },
      "blueberry":{
         "type":"unitcost",
         "unit":"packet",
         "parameters":{
            "unitcost":0.45
         }
      },
      "vanilla":{
         "type":"unitcost",
         "unit":"teaspoon",
         "parameters":{
            "unitcost":0.27
         }
      }
   },
   "name":"Watson"
}
```



Modifying this example negotiation agent to create your own
----

This is a simple negotiation agent that is intended to serve as a template upon which you can base more.

To build your own, you can borrow as much or as little of this code as you wish. You will need to ensure that you can send and receive messages in the correct formats. All of the internal workings of the agent -- the negotiation algorithm, the conversion from structured bid to text form (perhaps with some amount of attitude), etc. -- is up to you.

You can choose to imbed certain characters in the agent utterance to change the emphasis, pitch or tone of a word or phoneme; see the documentation on Watson Text to Speech for examples of how to do this.


## Contributing

We are open to contributions.

* The software is provided under the [MIT license](LICENSE). Contributions to
this project are accepted under the same license.
* Please also ensure that each commit in the series has at least one
`Signed-off-by:` line, using your real name and email address. The names in
the `Signed-off-by:` and `Author:` lines must match. If anyone else
contributes to the commit, they must also add their own `Signed-off-by:`
line. By adding this line the contributor certifies the contribution is made
under the terms of the
[Developer Certificate of Origin (DCO)](DeveloperCertificateOfOrigin.txt).
* Questions, bug reports, et cetera are raised and discussed on the issues page.
* Please make merge requests into the master branch.
