const fetchModule = require('node-fetch');

const fetchImpl = fetchModule.default || fetchModule;

global.fetch = global.fetch || fetchImpl;
global.Request = global.Request || fetchModule.Request;
global.Response = global.Response || fetchModule.Response;
global.Headers = global.Headers || fetchModule.Headers;

if (global.Response && typeof global.Response.json !== 'function') {
  global.Response.json = function json(body, init = {}) {
    const headers = new global.Headers(init.headers || {});
    if (!headers.has('content-type')) {
      headers.set('content-type', 'application/json');
    }

    return new global.Response(JSON.stringify(body), {
      ...init,
      headers,
    });
  };
}
