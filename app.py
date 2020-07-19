import os
from pprint import pformat
from time import time, sleep
from datetime import date
from datetime import time
from datetime import datetime
from datetime import timedelta
import json
import csv
from flask import Flask, request, redirect, session, url_for
from flask.json import jsonify
import requests
from requests_oauthlib import OAuth2Session

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(days=1)

# Keep this secret_key safe and do not share anywhere
# except in your config variables or somewhere else secure
app.secret_key = os.environ.get('APP_SECRET_KEY', None)

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
	
	# State is used to prevent CSRF, keep this for later.
	session['state'] = state
	return redirect(authorization_url)


# Step 2: User authorization, this happens on the provider.
@app.route("/callback", methods=["GET"])
def callback():
	code = request.args.get('code')
	""" Step 3: Retrieving an access token.
	
	The user has been redirected back from the provider to your registered
	callback URL. With this redirection comes an authorization code included
	in the redirect URL. We will use that to obtain an access token.
	"""
	try:
		url = 'https://oauth2.awair.is/v2/token?client_id=' + client_id + '&client_secret=' + client_secret + '&grant_type=authorization_code&code=' + code
		token_obj = requests.get(url)
		
		# We use the session as a simple DB for this example.
		session['oauth_object'] = token_obj.json()
		return redirect('/menu')
	except Exception as e:
		print(e)
		return redirect('/')


@app.route("/menu", methods=["GET"])
def menu():
	if 'oauth_object' in session:
		creds = session.get("oauth_object", "/menu oauth_object empty")
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
		""" % pformat(creds, indent=4)
	else:
		print('redirecting to root to force login')
		return redirect('/')


@app.route("/profile", methods=["GET"])
def profile():
	if 'oauth_object' in session:
		oauth_obj = session.get("oauth_object", "/profile oauth_object empty")
		bearer_token = oauth_obj['access_token']
		"""Fetching profile data
		"""
		prof = ""
		try:
			profile = requests.get('https://developer-apis.awair.is/v1/users/self', headers={'Authorization': 'Bearer ' + bearer_token}).json()
			return jsonify(profile)
		except Exception as e:
			print(e)
			return redirect('/profile')
	else:
		print('redirecting to root to force login')
		return redirect('/')


@app.route("/devices", methods=["GET"])
def devices():
	if 'oauth_object' in session:
		oauth_obj = session.get("oauth_object", "/devices oauth_object empty")
		bearer_token = oauth_obj['access_token']
		"""Fetching device list
		"""
		devs = ""
		try:
			devs = requests.get('https://developer-apis.awair.is/v1/users/self/devices', headers={'Authorization': 'Bearer ' + bearer_token}).json()
			return jsonify(devs)
		except Exception as e:
			print(e)
			return redirect('/devices')
	else:
		print('redirecting to root to force login')
		return redirect('/')


@app.route("/air-data", methods=["GET"])
def air_data():
	if 'oauth_object' in session:
		oauth_obj = session.get("oauth_object", "/air-data oauth_object empty")
		bearer_token = oauth_obj['access_token']
		"""Fetch device list
		"""
		select_opts = ""
		try:
			devices = requests.get('https://developer-apis.awair.is/v1/users/self/devices', headers={'Authorization': 'Bearer ' + bearer_token}).json()
			devices_dict = devices['devices']
			for device in devices_dict:
				select_opts += '<option value="' + str(device['deviceUUID']) + '">' + str(device['name']) + '</option>'
			"""Select Device
			"""
			return """
			<h2>Choose a device and time range:</h2>
			<form id="air_data_download_form" action="/air-data/download" method="post" enctype="multipart/form-data">
		    	<label for="device_uuid">Select Device:<br>
					<select id="device_uuid" name="device_uuid" required>
						%s 
					</select>
				</label>
				<br><br>
				<label for="device">Choose Date (UTC):<br>
					<input type="date" id="date" name="date" required pattern="\d{4}-\d{2}-\d{2}">
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
			""" % str(select_opts)
		except Exception as e:
			print(e)
			return redirect('/air-data')
	else:
		print('redirecting to root to force login')
		return redirect('/')


@app.route("/air-data/download", methods=["POST","GET"])
def air_data_download():
	if 'oauth_object' in session:
		oauth_obj = session.get("oauth_object", "/air-data/download oauth_object empty")
		bearer_token = oauth_obj['access_token']
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
		air_data_url = 'https://developer-apis.awair.is/v1/users/self/devices/' + str(device_type) + '/' + str(device_id) + '/air-data/5-min-avg?from=' + str(from_date) + 'T00:00:00.000Z&to=' + str(to_date) + 'T00:00:00.000Z&limit=288&desc=false&fahrenheit=' + str(fahrenheit)
		try:
			air_data = requests.get(air_data_url, headers={'Authorization': 'Bearer ' + bearer_token}).json()
			samples = air_data['data']
			# timestamp,score,sensors(temp,humid,co2,voc,pm25,lux,spl_a)
			# dtype = [('timestamp', np.datetime64[s]), ('score', np.int32), ('temp', np.float64), ('humid', np.float64), ('co2', np.float64), ('voc', np.float64), ('pm25', np.float64), ('lux', np.float64), ('spl_a', np.float64)]
			samples_array = []
			header = ['timestamp','score','temp','humid','co2','voc','pm25']
			samples_array.append(header)
			for sample in samples:
				row = [None] * 7
				row[0] = sample['timestamp']
				row[1] = "{:.0f}".format(float(sample['score']))
				sensors = sample['sensors']
				for sensor in sensors:
					if sensor['comp'] == "temp":
						row[2] = "{:.2f}".format(float(sensor['value']))
					elif sensor['comp'] == "humid":
						row[3] = "{:.2f}".format(float(sensor['value']))
					elif sensor['comp'] == "co2":
						row[4] = "{:.0f}".format(float(sensor['value']))
					elif sensor['comp'] == "voc":
						row[5] = "{:.0f}".format(float(sensor['value']))
					elif sensor['comp'] == "pm25":
						row[6] = "{:.0f}".format(float(sensor['value']))
				samples_array.append(row)
		except Exception as e:
			print(e)
			return "error :("
		try:
			csv.register_dialect('awairDialect', delimiter=',', quoting=csv.QUOTE_ALL)
			samples_file = open('air-data.csv', mode='w', newline='')
			with samples_file:
				samples_writer = csv.writer(samples_file, dialect='awairDialect')
				samples_writer.writerows(samples_array)
				samples_file.close()
				return send_file(samples_file, mimetype='text/csv')
		except OSError:
			abort(404)
	else:
		print('redirecting to root to force login')
		return redirect('/')


@app.route("/automatic-refresh", methods=["GET"])
def automatic_refresh():
	if 'oauth_object' in session:
		oauth_obj = session.get("oauth_object", "/automatic-refresh oauth_object empty")
		refresh_token = oauth_obj['access_token']
		"""Refreshing an OAuth 2 token using a refresh token.
		"""
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
								token=token,
								auto_refresh_kwargs=extra,
								auto_refresh_url=refresh_url,
								token_updater=token_updater)
		
		# Trigger the automatic refresh
		refresh = ""
		try:
			refresh = oauth.get('https://developer-apis.awair.is/v1/users/self', headers={'Authorization': 'Bearer ' + refresh_token}).json()
			return jsonify(refresh)
		except Exception as e:
			print(e)
			return redirect('/automatic-refresh')
	else:
		print('redirecting to root to force login')
		return redirect('/')


@app.route("/manual-refresh", methods=["GET"])
def manual_refresh():
	if 'oauth_object' in session:
		"""Refreshing an OAuth 2 token using a refresh token.
		"""
		token = session.get("oauth_object", "/manual-refresh oauth_object empty")
		
		extra = {
			'client_id': client_id,
			'client_secret': client_secret
		}
		
		oauth = OAuth2Session(client_id, token=token)
		try:
			session['oauth_object'] = oauth.refresh_token(refresh_url, **extra)
			return jsonify(session['oauth_object'])
		except Exception as e:
			print(e)
			return redirect('/manual-refresh')
	else:
		print('redirecting to root to force login')
		return redirect('/')


if __name__ == "__main__":
	# This allows us to use a plain HTTP callback
	#os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "1"
	
	app.run(debug=True)