import os
from pprint import pformat
from time import time
from time import sleep

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
	sleep(0.5)
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
	sleep(0.5)
	"""Main menu
	"""
	return """
	<h1>You have successfully logged into your Awair account!</h1>
	<h2>What would you like to do next?</h2>
	<ul>
		<li><a href="/profile"> Get account profile</a></li>
		<li><a href="/devices"> Get account devices</a></li>
		<li><a href="/air-data"> Get device air-data</a></li>
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
	sleep(0.5)
	"""Fetching profile data
	"""
	oauth = OAuth2Session(client_id, token=session['oauth_object'])
	sleep(0.5)
	return jsonify(oauth.get('https://developer-apis.awair.is/v1/users/self', headers={'Authorization': 'Bearer ' + session['oauth_object']['access_token']}).json())


@app.route("/devices", methods=["GET"])
def devices():
	sleep(0.5)
	"""Fetching device list
	"""
	oauth = OAuth2Session(client_id, token=session['oauth_object'])
	sleep(0.5)
	return jsonify(oauth.get('https://developer-apis.awair.is/v1/users/self/devices', headers={'Authorization': 'Bearer ' + session['oauth_object']['access_token']}).json())


@app.route("/air-data", methods=["GET"])
def air_data():
	sleep(0.5)
	device_type = request.args.get('device_type')
	device_id = request.args.get('device_id')
	from_date = request.args.get('from_date')
	to_date = request.args.get('to_date')
	fahrenheit = request.args.get('fahrenheit')
	"""Fetching air-data
	"""
	oauth = OAuth2Session(client_id, token=session['oauth_object'])
	sleep(0.5)
	return jsonify(oauth.get('https://developer-apis.awair.is/v1/users/self/devices/' + device_type + '/' + device_id + '/air-data/5-min-avg?from=' + from_date + '&to=' + to_date + '&limit=288&desc=false&fahrenheit=' + fahrenheit, headers={'Authorization': 'Bearer ' + session['oauth_object']['access_token']}).json())


@app.route("/automatic-refresh", methods=["GET"])
def automatic_refresh():
	sleep(0.5)
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
	
	# Trigger the automatic refresh
	jsonify(oauth.get('https://developer-apis.awair.is/v1/users/self', headers={'Authorization': 'Bearer ' + session['oauth_object']['refresh_token']}).json())
	sleep(0.5)
	return jsonify(session['oauth_object'])


@app.route("/manual-refresh", methods=["GET"])
def manual_refresh():
	sleep(0.5)
	"""Refreshing an OAuth 2 token using a refresh token.
	"""
	token = session['oauth_object']
	
	extra = {
		'client_id': client_id,
		'client_secret': client_secret
	}
	
	oauth = OAuth2Session(client_id, token=token)
	session['oauth_object'] = oauth.refresh_token(refresh_url, **extra)
	sleep(0.5)
	return jsonify(session['oauth_object'])


if __name__ == "__main__":
	# This allows us to use a plain HTTP callback
	#os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "1"
	
	app.run(debug=True)