export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // Add CORS headers
    const headers = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    // Handle OPTIONS requests for CORS
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers });
    }

    try {
      // Forward the request to the Flask app
      const response = await fetch(`https://entity-viewer-prod.pages.dev${url.pathname}${url.search}`, {
        method: request.method,
        headers: request.headers,
        body: request.method !== 'GET' ? await request.text() : undefined
      });

      // Create a new response with CORS headers
      const newResponse = new Response(response.body, response);
      Object.keys(headers).forEach(key => {
        newResponse.headers.set(key, headers[key]);
      });

      return newResponse;
    } catch (error) {
      return new Response(`Error: ${error.message}`, {
        status: 500,
        headers: {
          'Content-Type': 'text/plain',
          ...headers
        }
      });
    }
  }
}
