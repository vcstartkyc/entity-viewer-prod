from flask import Response

def onRequest(context):
    # Add CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    
    # Handle OPTIONS requests
    if context.request.method == 'OPTIONS':
        return Response(None, headers=headers)

    # Add CORS headers to all responses
    context.next().headers.update(headers)
    return context.next()
