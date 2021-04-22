var har_func = module.exports = {

    events: [],

    addResponseBodyPromises: [],

    register_events: async function(page) {
        const sleep = require('util').promisify(setTimeout);
        // list of events for converting to HAR

        // event types to observe
        const observe = [
            'Page.loadEventFired',
            'Page.domContentEventFired',
            'Page.frameStartedLoading',
            'Page.frameAttached',
            'Network.requestWillBeSent',
            'Network.requestServedFromCache',
            'Network.dataReceived',
            'Network.responseReceived',
            'Network.resourceChangedPriority',
            'Network.loadingFinished',
            'Network.loadingFailed',
        ];

        // register events listeners
        const client = await page.target().createCDPSession();
        await client.send('Page.enable');
        await client.send('Network.enable');
        await client.send('Network.setCacheDisabled', {
            cacheDisabled: true,
        });

        const EventEmitter = require('events');
        const emitter = new EventEmitter();

        observe.forEach(method => {
            //console.log(method);
            client.on(method, params => {
                const harEvent = {
                    method,
                    params
                };
                har_func.events.push(harEvent);
                //console.log("event " + method + " added to array");
                if (harEvent.method === 'Network.loadingFinished') {
                    emitter.emit(params.requestId);
                }

                if (harEvent.method === 'Network.responseReceived') {

                    const response = harEvent.params.response;
                    const requestId = harEvent.params.requestId;
                    // response body is unavailable for redirects, no-content, image, audio
                    // and video responses
                    if (response.status !== 204 &&
                        response.headers.location == null &&
                        !response.mimeType.includes('image') &&
                        !response.mimeType.includes('audio') &&
                        !response.mimeType.includes('video')
                    ) {
                        //console.log(harEvent.params.response.url);
                        emitter.on(requestId, () => {
                            const addResponseBodyPromise = client.send(
                                'Network.getResponseBody', {
                                    requestId
                                },
                            ).then((responseBody) => {
                                // set the response so chrome-har can add it to the HAR
                                //console.log(harEvent.params.response.url);
                                harEvent.params.response = {
                                    ...response,
                                    body: Buffer.from(
                                        responseBody.body,
                                        responseBody.base64Encoded ? 'base64' : undefined,
                                    ).toString(),
                                };
                            }, (reason) => {
                                //console.log(reason);
                                // resources (i.e. response bodies) are flushed after page commits
                                // navigation and we are no longer able to retrieve them. In this
                                // case, fail soft so we still add the rest of the response to the
                                // HAR.
                            });
                            har_func.addResponseBodyPromises.push(addResponseBodyPromise);
                        }); // fin emitter.on
                    } // fin if
                    else {
                        //console.log("pas network received");
                    }
                }
            });
        });

    },

    get_har: async function() {
        const {
            harFromMessages
        } = require('chrome-har');
        const fs = require('fs');
        const {
            promisify
        } = require('util');
        //await promisify(fs.writeFile)('events.txt', JSON.stringify(har_func.events));
        await Promise.all(har_func.addResponseBodyPromises);
        const har = harFromMessages(har_func.events, {
            includeTextFromResponseBody: true
        });
        return har
    }
}
