import os
import json
import requests
from flask import Flask , request

twitch_client_id = os.environ['CLIENT_ID']
twitch_client_secret = os.environ['CLIENT_SECRET']


app = Flask(__name__, '')

@app.route('/')
def index():
    code = request.args.get('code')
    response = json.dumps(
        {
            "client_id": twitch_client_id, 
            "client_secret": twitch_client_secret,
            "code": code,
        }
    )
    return response



#teste heroku
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
