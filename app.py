import os
import json
import time
import psycopg2
import requests
from flask import Flask, request

database_url = os.environ['DATABASE_URL']
database_pass = os.environ['DATABASE_PASS']
twitch_client_id = os.environ['CLIENT_ID']
twitch_client_secret = os.environ['CLIENT_SECRET']

validation_url = 'https://id.twitch.tv/oauth2/validate'
helix_users_url = 'https://api.twitch.tv/helix/users'
twitch_auth_url = 'https://id.twitch.tv/oauth2/token'
redirect_uri = 'http://localhost:13486/token'

app = Flask(__name__, '')

state_dict = {}

error_invalid_state = {'status': 'Invalid state!'}
error_missing_code = {'status': 'Missing code!'}
error_missing_state = {'status': 'Missing state'}
success_authenticate = {'status': 'Successfully authenticated!'}
success_valid_state = {'status': 'Valid state!'}

state_length = 128
state_time_limit = 120

conn = psycopg2.connect(database_url, sslmode='require')
cur = conn.cursor()

@app.route('/create_table')
def create_table():
    password = request.args.get('password')
    if database_pass != password:
        return "Invalid password"
    query = (   
        'begin;'
        'create table if not exists pywitch_users ('
        'id int generated always as identity, '
        'pw_user_id int not null, '
        'pw_login varchar(64), '
        'pw_display_name varchar(64), '
        'pw_auth_time timestamp '
        '); '
        'commit;'
    )
    cur.execute(query)
    return 'Table created!'


@app.route('/state')
def get_token():
    try:
        state = request.args.get('state')
        if not (state and state in state_dict):
            return json.dumps(error_invalid_state)
        state_data = state_dict.pop(state)
        if time.time() > state_data['time'] + state_time_limit:
            return json.dumps(error_invalid_state)
        state_data.update(success_valid_state)
        return json.dumps(state_data)
    except Exception as e:
        print(e)
        return json.dumps(error_invalid_state)


@app.route('/authenticate')
def index():
    display_name = ''
    code = request.args.get('code')
    state = request.args.get('state')

    if not code:
        return 'Failed to authenticate PyWitch Client: Missing Code!'

    if not state:
        return 'Failed to authenticate PyWitch Client: Missing state!'

    if len(state) != state_length:
        return 'Failed to authenticate PyWitch Client: Invalid state!'

    if state in state_dict:
        # If the same state is used more than one time, both are invalid!
        state_dict.pop(state)
        return 'Failed to authenticate PyWitch Client: Invalid state!'

    params = {
        'client_id': twitch_client_id,
        'client_secret': twitch_client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri,
    }
    response = requests.post(twitch_auth_url, params=params)
    if response.status_code == 200:
        response_json = response.json()
        response_json['time'] = time.time()
        state_dict[state] = response_json

        headers = {
            "Client-ID": twitch_client_id,
            "Authorization": f"Bearer {response_json['access_token']}",
        }

        response_validation = requests.get(validation_url, headers=headers)
        if response.status_code == 200:
            response_validation_json = response.json()
            params = {'id': response_validation_json.get('user_id')}

            response_user = requests.get(
                helix_users_url, headers=headers, params=params
            )

            response_user_json = response_user.json()
            data = response_user_json.get('data',[{}])[0]
            display_name = data.get('display_name','')

        return (
            f'<p> Hi {display_name}!</p>'
            '<p>Successfully authenticated PyWitch Client!</p>'
        )


# teste heroku
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
