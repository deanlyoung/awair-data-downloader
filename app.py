import os
from pprint import pformat
from time import time

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
	time.sleep(1)
	""""""
	return """
	<h1>Congratulations, you have obtained an OAuth 2 token!</h1>
	<h2>What would you like to do next?</h2>
	<ul>
		<li><a href="/profile"> Get account profile</a></li>
		<li><a href="/automatic_refresh"> Implicitly refresh the token</a></li>
		<li><a href="/manual_refresh"> Explicitly refresh the token</a></li>
		<li><a href="/validate"> Validate the token</a></li>
	</ul>
	
	<pre>
	%s
	</pre>
	""" % pformat(session['oauth_object'], indent=4)


@app.route("/profile", methods=["GET"])
def profile():
	sleep(1)
	"""Fetching a protected resource using an OAuth 2 token.
	"""
	oauth = OAuth2Session(client_id, token=session['oauth_object'])
	return jsonify(oauth.get('https://developer-apis.awair.is/v1/users/self', headers={'Authorization': 'Bearer ' + session['oauth_object']['access_token']}).json())


@app.route("/automatic_refresh", methods=["GET"])
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
	
	# Trigger the automatic refresh
	jsonify(oauth.get('https://developer-apis.awair.is/v1/users/self', headers={'Authorization': 'Bearer ' + session['oauth_object']['refresh_token']}).json())
	return jsonify(session['oauth_object'])


@app.route("/manual_refresh", methods=["GET"])
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
	session['oauth_object'] = oauth.refresh_token(refresh_url, **extra)
	return jsonify(session['oauth_object'])


if __name__ == "__main__":
	# This allows us to use a plain HTTP callback
	#os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "1"
	
	app.run(debug=True)