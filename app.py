import os
from pprint import pformat
from time import time, sleep
from datetime import datetime, timedelta
import json
from flask import Flask, request, redirect, session, url_for
from flask.json import jsonify
import requests
from requests_oauthlib import OAuth2Session

app = Flask(__name__)
app.secret_key = os.urandom(24)

# This information is obtained upon registration of a new Awair OAuth
# application at https://developer.getawair.com
client_id = os.environ.get('CLIENT_ID', None)
client_secret = os.environ.get('CLIENT_SECRET', None)
redirect_uri = "https://awair-data-downloader.herokuapp.com/callback"

# Uncomment for detailed oauthlib logs
import logging
import sys
log = logging.getLogger('oauthlib')
log.addHandler(logging.StreamHandler(sys.stdout))
log.setLevel(logging.DEBUG)

# OAuth endpoints given in the Awair API documentation
authorization_base_url = "https://oauth-login.awair.is"
token_url = "https://oauth2.awair.is/v2/token"
refresh_url = token_url # True for Awair but not all providers.
scope = ""

session['oauth_object'] = ''

@app.route("/")
def demo():
	"""Step 1: User Authorization.
	
	Redirect the user/resource owner to the OAuth provider (i.e. Awair)
	using an URL with a few key OAuth parameters.
	"""
	oauth = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)
	authorization_url, state = oauth.authorization_url(authorization_base_url)
	print('authorization_url: ' + authorization_url)
	print('state: ' + state)
	
	# State is used to prevent CSRF, keep this for later.
	session['state'] = state
	return redirect(authorization_url)


# Step 2: User authorization, this happens on the provider.
@app.route("/callback", methods=["GET"])
def callback():
	sleep(1)
	code = request.args.get('code')
	print('code: ' + code)
	""" Step 3: Retrieving an access token.
	
	The user has been redirected back from the provider to your registered
	callback URL. With this redirection comes an authorization code included
	in the redirect URL. We will use that to obtain an access token.
	"""
	
	oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, state=request.url)
	token_obj = oauth.fetch_token(token_url, client_secret=client_secret, code=code, authorization_response=request.url)
	
	# We use the session as a simple DB for this example.
	session['oauth_object'] = token_obj
	
	return redirect(url_for('.menu'))


@app.route("/menu", methods=["GET"])
def menu():
	sleep(1)
	"""Main menu
	"""
	return """
	<h1>You have successfully logged into your Awair account!</h1>
	<h2>What would you like to do next?</h2>
	<ul>
		<li><a href="/profile"> Get account profile</a></li>
		<li><a href="/devices"> Get account devices</a></li>
		<li><a href="/air-data"> Get device air-data</a></li>
	</ul>
	<br><br>
	<ul>
		<li><a href="/automatic-refresh"> Implicitly refresh the token</a></li>
		<li><a href="/manual-refresh"> Explicitly refresh the token</a></li>
		<li><a href="/"> Re-Authenticate</a></li>
	</ul>
	
	<pre>
	%s
	</pre>
	""" % pformat(session['oauth_object'], indent=4)


@app.route("/profile", methods=["GET"])
def profile():
	sleep(1)
	"""Fetching profile data
	"""
	oauth = OAuth2Session(client_id, token=session['oauth_object'])
	sleep(0.5)
	return jsonify(oauth.get('https://developer-apis.awair.is/v1/users/self', headers={'Authorization': 'Bearer ' + session['oauth_object']['access_token']}).json())


@app.route("/devices", methods=["GET"])
def devices():
	sleep(1)
	"""Fetching device list
	"""
	oauth = OAuth2Session(client_id, token=session['oauth_object'])
	sleep(0.5)
	return jsonify(oauth.get('https://developer-apis.awair.is/v1/users/self/devices', headers={'Authorization': 'Bearer ' + session['oauth_object']['access_token']}).json())


@app.route("/air-data", methods=["GET"])
def air_data():
	sleep(1)
	"""Fetch device list
	"""
	oauth = OAuth2Session(client_id, token=session['oauth_object'])
	sleep(0.5)
	devices = jsonify(oauth.get('https://developer-apis.awair.is/v1/users/self/devices', headers={'Authorization': 'Bearer ' + session['oauth_object']['access_token']}).json())
	print(devices)
	devices_dict = devices['devices']
	select_opts = {}
	for device in devices_dict:
		select_opts['device'] = '<option value="' + str(device['deviceUUID']) + '">' + str(device['name']) + '</option>'
	"""Select Device
	"""
	print(json.dumps(select_opts))
	return """
	<h2>Choose a device and time range:</h2>
	<form action="{{ url_for('air_data_download') }}" method="post">
    	<label for="device_uuid">Select Device:<br>
			<select id="device_uuid" name="device_uuid" required>
				%s 
			</select>
		</label>
		<br><br>
		<label for="device">Choose Date (UTC):<br>
			<input type="date" name="date" required pattern="\d{4}-\d{2}-\d{2}">
		</label>
		<br><br>
		<span>Temperature Unit:</span><br>
		<input type="radio" id="temp_f" name="temp_unit" value="true">
		<label for="temp_f">Fahrenheit</label><br>
		<input type="radio" id="temp_c" name="temp_unit" value="false">
		<label for="temp_c">Celsius</label>
		<br><br>
    	<input type="submit" value="Download">
	</form>
	""" % str(json.dumps(select_opts))


@app.route("/air-data/download", methods=["POST"])
def air_data_download():
	sleep(1)
	# used with GET method
	# device_type = request.args.get('device_type')
	# device_id = request.args.get('device_id')
	# from_date = request.args.get('from_date')
	# to_date = request.args.get('to_date')
	# fahrenheit = request.args.get('fahrenheit')
	# used with POST method
	"""Fetching air-data
	"""
	device_uuid = request.form['device_uuid']
	device_type = device_uuid.split("_")[0]
	device_id = device_uuid.split("_")[1]
	from_date = request.form['date']
	temp_date = datetime.strptime(from_date, "%Y-%m-%d")
	add_day = temp_date + timedelta(days=1)
	to_date = datetime.strftime(add_day, "%Y-%m-%d")
	fahrenheit = request.form['temp_unit']
	oauth = OAuth2Session(client_id, token=session['oauth_object'])
	sleep(0.5)
	return jsonify(oauth.get('https://developer-apis.awair.is/v1/users/self/devices/' + str(device_type) + '/' + str(device_id) + '/air-data/5-min-avg?from=' + str(from_date) + 'T00:00:00.000Z&to=' + str(to_date) + 'T00:00:00.000Z&limit=288&desc=false&fahrenheit=' + str(fahrenheit), headers={'Authorization': 'Bearer ' + session['oauth_object']['access_token']}).json())


@app.route("/automatic-refresh", methods=["GET"])
def automatic_refresh():
	sleep(1)
	"""Refreshing an OAuth 2 token using a refresh token.
	"""
	refresh_token = session['oauth_object']['refresh_token']
	# We force an expiration by setting expired at in the past.
	# This will trigger an automatic refresh next time we interact with
	# Awair's API.
	#token['expires_at'] = time() - 10
	
	extra = {
		'client_id': client_id,
		'client_secret': client_secret
	}
	
	def token_updater(token):
		session['oauth_object'] = token
	
	oauth = OAuth2Session(client_id,
							token=session['oauth_object'],
							auto_refresh_kwargs=extra,
							auto_refresh_url=refresh_url,
							token_updater=token_updater)
	sleep(0.5)
	# Trigger the automatic refresh
	jsonify(oauth.get('https://developer-apis.awair.is/v1/users/self', headers={'Authorization': 'Bearer ' + session['oauth_object']['refresh_token']}).json())
	return jsonify(session['oauth_object'])


@app.route("/manual-refresh", methods=["GET"])
def manual_refresh():
	sleep(1)
	"""Refreshing an OAuth 2 token using a refresh token.
	"""
	token = session['oauth_object']
	
	extra = {
		'client_id': client_id,
		'client_secret': client_secret
	}
	
	oauth = OAuth2Session(client_id, token=token)
	sleep(0.5)
	session['oauth_object'] = oauth.refresh_token(refresh_url, **extra)
	return jsonify(session['oauth_object'])


if __name__ == "__main__":
	# This allows us to use a plain HTTP callback
	#os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "1"
	
	app.run(debug=True)