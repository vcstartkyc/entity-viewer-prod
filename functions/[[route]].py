from flask import Flask, Response
import sys
import os

# Add the root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app

def onRequest(context):
    """Handle the incoming request using the Flask app."""
    with flask_app.test_client() as client:
        # Forward the request to Flask
        response = client.open(
            path=context.request.path or '/',  # Default to / if path is empty
            method=context.request.method,
            headers=dict(context.request.headers),
            data=context.request.get_data()
        )
        
        # Convert Flask response to Pages response
        return Response(
            response.get_data(),
            status=response.status_code,
            headers=dict(response.headers)
        )
