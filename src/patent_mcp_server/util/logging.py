import httpx
import logging
import json

logger = logging.getLogger('logging_transport')

# Define custom transport that logs all requests and responses
class LoggingTransport(httpx.AsyncBaseTransport):

    def __init__(self, transport):
        self.transport = transport

    async def handle_async_request(self, request):
        # Log the request
        logger.debug(f"REQUEST: {request.method} {request.url}")
        logger.debug(f"REQUEST HEADERS: {dict(request.headers)}")
        
        try:
            # For body logging, convert to string if possible
            if request.content:
                body = request.content
                try:
                    if isinstance(body, bytes):
                        body = body.decode('utf-8')
                    # Try to parse and pretty-print JSON
                    try:
                        json_body = json.loads(body)
                        logger.debug(f"REQUEST BODY: \n{json.dumps(json_body, indent=2)}")
                    except:
                        logger.debug(f"REQUEST BODY: {body}")
                except:
                    logger.debug(f"REQUEST BODY: {body}")
        except Exception as e:
            logger.debug(f"Error logging request body: {e}")

        # Get the response
        response = await self.transport.handle_async_request(request)
        
        # Log the response
        logger.debug(f"RESPONSE: {response.status_code} from {request.url}")
        logger.debug(f"RESPONSE HEADERS: {dict(response.headers)}")
        
        return response
