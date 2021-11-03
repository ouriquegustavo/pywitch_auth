import os
import json
import requests
from flask import Flask , request

twitch_client_id = os.environ['CLIENT_ID']
twitch_client_secret = os.environ['CLIENT_SECRET']
twitch_auth_url = 'https://id.twitch.tv/oauth2/token'
redirect_uri = 'http://localhost:13486/token'

app = Flask(__name__, '')

@app.route('/')
def index():
    code = request.args.get('code')
    params = {
        'client_id': twitch_client_id,
        'client_secret': twitch_client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri
    }
    response = requests.post(twitch_auth_url, params=params)
    return response.json()



#teste heroku
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
