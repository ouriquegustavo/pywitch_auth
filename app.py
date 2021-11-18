import os
import json
import time
import psycopg2
import requests
from datetime import datetime
from flask import Flask, request
from _version import version

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
error_refresh_state = {'status': 'Failed to refresh access token'}
success_authenticate = {'status': 'Successfully authenticated!'}
success_valid_state = {'status': 'Valid state!'}
success_refresh = {'status': 'Token refreshed successfully!'}

state_length = 128
state_time_limit = 120

conn = psycopg2.connect(database_url, sslmode='require')
cur = conn.cursor()

page_css = """
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css?family=Poppins:100,200,300,400" rel="stylesheet">
    <style>
    .AuthBox {
      font-family: 'Poppins', sans-serif;
      background-color: white;
      width: 350px;
      border: 50px solid #9147ff;
      padding: 50px;
      margin: auto;
      padding-top: 30px;
      padding-bottom: 2px;
      text-align: center;
    }
    .row::after {
      content: "";
      clear: both;
      display: table;
    }
    </style>
    </head>
"""

page_html = """
<body>

<div class="AuthBox">
    <div class="row">
        <div style="float: left; width: 20%; padding: 10px">
            <img src="https://raw.githubusercontent.com/ouriquegustavo
                      /pywitch_client/main/logo/pywitch_logo_color.png"
          alt="pywitch_logo_color" style="max-width:100%; max-height:100%;">
        </div>
        <div style="float: left;">
            <h1>PyWitch Auth</h1>
        </div>
    </div>
    
    <div style="text-align: left;">
        <h4>Hi {display_name}!</h4>
    </div>

    <div>
        Successfully authenticated PyWitch Client!
        <br> <br>
        You can close this tab now.
        <br> <br>
        Your PyWitch Client will retrieve your access token soon.
        If it was not able to start in 10-20 seconds, close it and try again.
    </div>
    
    <br>
    <br>
    
    <div style="text-align: left;">
        <h4>Users that also used PyWitch Auth:</h4>
        <ul>
            {user_list_str}
        </ul> 
    </div>
    I'm pretty sure that you will enjoy their livestreams!
    
    <div style="text-align: left;">
        <h4>Source:</h4>
    </div>
    <div>
        <a href="https://github.com/ouriquegustavo/pywitch/">
        [PyWitch Source Code]</a>
    </div>
    <br>
    <div>
        <a href="https://github.com/ouriquegustavo/pywitch_auth/">
        [PyWitch Auth Source Code]</a>
    </div>
    <br>
    <div>
        <a href="https://github.com/ouriquegustavo/pywitch_client/">
        [PyWitch Client Source Code]</a>
    </div>
    
    <div style="text-align: right; padding-right: 2px; font-size: 12px;">
        <br><br>
        Author: Gustavo Ourique (Gleenus)
    </div>
        
</div>

</body>
</html>
"""

insert_query = """
    begin;
    with base as (
        select
            id,
            rank() over(order by pw_auth_time desc) rk
        from pywitch_users
    )
    delete from pywitch_users where id in (
        select id from base where rk > 9999
    );
    commit;
    begin;
    insert into pywitch_users (
        pw_user_id, pw_login, pw_display_name, pw_auth_time
    ) values (
        %(user_id)s, '%(login)s', '%(display_name)s',
        '%(auth_time)s'::timestamp
    );
    commit;
"""

create_table_query = """
    begin;
    create table if not exists pywitch_users (
        id int generated always as identity, 
        pw_user_id int not null, 
        pw_login varchar(64), 
        pw_display_name varchar(64), 
        pw_auth_time timestamp 
    ); 
    commit;
"""

list_users_query = """
    select distinct(pw_display_name) from pywitch_users;
"""

@app.route('/create_table')
def create_table():
    password = request.args.get('password')
    if database_pass != password:
        return "Invalid password"
    cur.execute(create_table_query)
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
        auth_time = time.time()
        response_json = response.json()
        response_json['time'] = auth_time
        state_dict[state] = response_json

        headers = {
            "Client-ID": twitch_client_id,
            "Authorization": f"Bearer {response_json['access_token']}",
        }
        
        user_list=[]

        response_validation = requests.get(validation_url, headers=headers)
        if response.status_code == 200:
            response_validation_json = response.json()
            params = {'id': response_validation_json.get('user_id')}

            response_user = requests.get(
                helix_users_url, headers=headers, params=params
            )
            
            auth_time_tq = datetime.fromtimestamp(auth_time).strftime(
                '%Y-%m-%d %H:%M:%S'
            )
            
            response_user_json = response_user.json()
            data = response_user_json.get('data',[{}])[0]
            user_id = data.get('id')
            login = data.get('login')
            display_name = data.get('display_name','')
            
            if user_id and str(user_id).isdigit():
                query = insert_query % {
                    'user_id': user_id,
                    'login': login,
                    'display_name': display_name,
                    'auth_time': auth_time_tq,
                }
                cur.execute(query)
                
                cur.execute(list_users_query)
                user_list_iter = cur.fetchall()
                user_list = [i[0] for i in user_list_iter]
                
        user_list_str = '\n'.join([f'<li>{i}</li>' for i in user_list])
        html = page_css + page_html.format(
            display_name=display_name,
            user_list_str=user_list_str
        )

        return html
        
@app.route('/refresh')
def refresh_access_token():
    try:
        refresh_token = request.args.get('refresh_token')

        if not refresh_token:
            return 'Failed to authenticate PyWitch Client: Missing Refresh Token!'

        data = {
            'client_id': twitch_client_id,
            'client_secret': twitch_client_secret,
            'refresh_token': refresh_token
            'grant_type': 'refresh_token',
        }
        response = requests.post(twitch_auth_url, data=data)
        if response.status_code == 200:
            response_json = response.json()
            response_json.update(success_refresh)
            return json.dumps(response_json) 
            
        return json.dumps(error_refresh_state)
    except Exception as e:
        print(e)


# teste heroku
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
