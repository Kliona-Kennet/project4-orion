from fastapi.middleware.cors import CORSMiddleware

EXPOSE_HEADERS = ["X-API-Version", "X-Request-ID"]

def add_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],          
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=EXPOSE_HEADERS,
    )