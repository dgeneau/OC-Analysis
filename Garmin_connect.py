'''
Garmin Connect 

Merry Christmas Joey

'''

import streamlit as st
import pandas as pd
import numpy as np
from garminconnect import Garmin, GarminConnectConnectionError, GarminConnectTooManyRequestsError
import json
import plotly.graph_objects as go

# Replace with your Garmin Connect credentials

st.title("Joe On The Go")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.password = ""
    st.session_state.start_str = ""
    st.session_state.end_str = ""
    st.session_state.r_df = pd.DataFrame()

if not st.session_state.logged_in:
    # Login form
	user_name = st.text_input('Enter your Username')
	password = st.text_input("Enter your Password", type="password")
	login = st.button('Login')
	if login:
		st.session_state.username = user_name
		st.session_state.password = password
		st.session_state.logged_in = True
		st.success("Logged in successfully!")


else:
	def fetch_recent_activities(client, max_activities=10):

		try:
			activities = client.get_activities(0, max_activities)  # Fetch recent activities
			return activities
		except Exception as e:
			st.error(f"Error fetching activities: {e}")
			return []

	def fetch_activity_details(client, activity_id):
		try:
			activity_details = client.get_activity_details(activity_id)
			keys = [descriptor["key"] for descriptor in activity_details["metricDescriptors"]]
			return activity_details, keys

		except Exception as e:
			st.error(f"Error fetching activity details: {e}")
			return {}

	def flatten_activity_data(activity_details):
		metrics = activity_details.get('activityDetailMetrics', [])
		if not metrics:
			return pd.DataFrame()

		# Normalize the metrics list into a DataFrame
		df = pd.json_normalize(metrics)


		# Expand the 'Values' column into multiple columns
		if 'metrics' in df.columns:
			expanded_values = pd.DataFrame(df['metrics'].tolist(), columns=[f"Value {i}" for i in range(len(df['metrics'].iloc[0]))])
			df = pd.concat([df.drop(columns=['metrics']), expanded_values], axis=1)

		return df



	#loging in to Garmin
	st.subheader("Logging in to Garmin Connect...")
	try:
		client = Garmin(st.session_state.username, st.session_state.password)
		client.login()
		st.success("Logged in successfully!")
	except GarminConnectConnectionError:
		st.error("Error connecting to Garmin Connect. Please check your credentials.")

	except GarminConnectTooManyRequestsError:
		st.error("Too many requests to Garmin Connect. Try again later.")

	except Exception as e:
		st.error(f"An error occurred: {e}")


	# Fetch recent activities
	st.subheader("Fetching Recent Activities...")
	max_activities = st.sidebar.slider("Number of Activities to Fetch", min_value=5, max_value=50, value=10)
	activities = fetch_recent_activities(client, max_activities)


	if activities:
		# Extract activity names and IDs
		activity_options = {
	        f"{activity['activityName']} ({activity['startTimeLocal']})": activity['activityId']
	        for activity in activities}
		
		
		selected_activity_name = st.sidebar.selectbox("Select an Activity", options=list(activity_options.keys()))
		selected_activity_id = activity_options[selected_activity_name]
		# Fetch and display activity details
		st.subheader("Activity Details")
		activity_details, columns = fetch_activity_details(client, selected_activity_id)
		
		
		if activity_details:
			activity_df = flatten_activity_data(activity_details)
			activity_df.columns  = columns
			data = activity_df
			if not activity_df.empty:
				st.write('Activity Found')
			else:
				st.warning("No detailed metrics available for this activity.")
		else:
			st.warning("Failed to load activity details.")
	else:
		st.warning("No recent activities found.")
		st.stop()

	center_lat = data['directLatitude'][0]

	center_lon = data['directLongitude'][0]


	fig = go.Figure(go.Scattermapbox(
		lon=data['directLongitude'],
		lat=data['directLatitude'],
	    mode='markers',
	    marker=go.scattermapbox.Marker(
	        size=7,  # Generic marker size
	        color='red'  # Marker color
	    ),

	    textposition="top center",
	    hoverinfo="text"))
	fig.update_layout(
	    mapbox=dict(
	        style="carto-positron",  # Map style
	        center=dict(lat=center_lat, lon=center_lon),  # Center of the map (US-focused)
	        zoom=12  # Zoom level
	    ),
	    title="Scatter Map Plot of Cities",
	    margin={"r":0, "t":0, "l":0, "b":0}  # Remove margins
	)

	st.plotly_chart(fig)

	col1, col2, col3, col4 = st.columns(4)
	with col1:
		st.metric('Max Speed (m/s)', round(np.max(data['directSpeed']),3))
	with col2:
		st.metric('Total Distance (m)', round(np.max(data['sumDistance']),3))
	with col3: 
		st.metric('Max HR (BPM)', round(np.max(data['directHeartRate']),3))
	with col4: 
		st.metric('Avg Stroke Rate (SPM)', round(np.max(data['directStrokeCadence']),3))




	fig2 = go.Figure()
	fig2.add_trace(go.Scatter(
	    y=data['directSpeed'],
	    name='Speed'))
	fig2.add_trace(go.Scatter(
	    y=((data['directSpeed']**2)/data['directStrokeCadence']),
	    name='eWPS'))

	fig2.add_trace(go.Scatter(
	    y=data['directHeartRate'],
	    name='Heart Rate',
	    yaxis='y2'))

	fig2.update_layout(
	    yaxis=dict(title='Direct Speed'),
	    yaxis2=dict(
	        title='Direct Heart Rate',
	        overlaying='y',  # Overlay on the same plot
	        side='right'     # Position on the right
	    ),
	    title='Session Speed and Heart Rate')
	st.plotly_chart(fig2)


	fig3 = go.Figure()
	work_data = data[data['directStrokeCadence']>5]

	fig3.add_trace(go.Scatter(
	    y=((work_data['directSpeed']**2)/work_data['directStrokeCadence']),
	    x = work_data['directStrokeCadence'],
	    mode = 'markers',
	    name='eWPS'))
	fig3.add_trace(go.Scatter(
	    y=((work_data['directSpeed']**2)),
	    x = work_data['directStrokeCadence'],
	    mode = 'markers',
	    name='V-Square', 
	    yaxis = 'y2'))
	fig3.update_layout(
	    yaxis=dict(title='Effective Work Per Stroke'),
	    yaxis2=dict(
	        title='V-Squared',
	        overlaying='y',  # Overlay on the same plot
	        side='right'     # Position on the right
	    ),
	    title='Stroke Rate Profile')


	st.plotly_chart(fig3)

	# Logout from Garmin Connect
	try:
		client.logout()
		st.info("Logged out successfully.")
	except Exception:
	    st.warning("Error logging out.")


