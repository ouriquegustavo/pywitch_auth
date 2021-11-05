import os
import json
import time
import requests
from flask import Flask , request

twitch_client_id = os.environ['CLIENT_ID']
twitch_client_secret = os.environ['CLIENT_SECRET']
twitch_auth_url = 'https://id.twitch.tv/oauth2/token'
redirect_uri = 'http://localhost:13486/token'

app = Flask(__name__, '')

state_dict={}

error_invalid_state = {'status': 'Invalid state!'}
error_missing_code = {'status': 'Missing code!'}
error_missing_state = {'status': 'Missing state'}
success_authenticate = {'status': 'Successfully authenticated!'}
success_valid_state = {'status': 'Valid state!'}

@app.route('/token')
def get_token():
    try:
        state = request.args.get('state')
        if not (state and state in state_dict):
            return json.dumps(error_invalid_state)
        state_data = json.loads(state_dict.pop(state))
        state_data.update(success_valid_state)
        return json.dumps(state_data)
    except Exception as e:
        print(e)
        return json.dumps(error_invalid_state)


@app.route('/authenticate')
def index():
    print(request.args)
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code:
        return 'Failed to authenticate PyWitch Client: Missing Code!'
    
    if not state or len(state) != 8:
        return 'Failed to authenticate PyWitch Client: Missing state!'
    
    params = {
        'client_id': twitch_client_id,
        'client_secret': twitch_client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri
    }
    response = requests.post(twitch_auth_url, params=params)
    if response.status_code==200:
        state_dict[state] = response.json()
        return 'Successfully authenticated PyWitch Client!'



#teste heroku
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
