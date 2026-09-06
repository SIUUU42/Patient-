import uvicorn
from pyngrok import ngrok

# 1. Set your ngrok authtoken (only needed once per machine)
NGROK_AUTHTOKEN = "3Iva5lz48cXylsPb7NkSU4b2DEt_89SNUcTHFpahZ1m8L8YuR"
ngrok.set_auth_token(NGROK_AUTHTOKEN)

# 2. Open HTTP tunnel on port 8000
public_url = ngrok.connect(8000)
print(f"\n==================================================")
print(f" PUBLIC NGROK URL: {public_url.public_url}")
print(f" Swagger Docs:     {public_url.public_url}/docs")
print(f"==================================================\n")

# 3. Start Uvicorn serving FastAPI
if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)