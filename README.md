## Primary Features
* Predictive Analysis: Uses simple linear regression to predict future visa wait times. (timeseries analysis felt like an overkill especially if running on smaller servers)
* Automated Data Fetching: Scrapes visa wait times from the U.S. State Department's website.
* Data Visualization: Generates a combined graph of visa wait times for multiple cities.
* Email Notifications: Sends periodic email updates with the latest visa wait times and graphs.
* Web Interface: Displays the latest data and graphs on a user-friendly web page.
* Scheduled Updates: Uses a scheduler to fetch and send updates multiple times a day.The following times are scheduled for sending updates:

01:50 AM, 02:30 AM, 09:00 AM, 05:00 PM, 10:00 PM

## Data Source
The visa wait times are scraped from the U.S. State Department's [Global Visa Wait Times page](https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/global-visa-wait-times.html).

# Installation
* Clone the repository:

```
git clone <repository_url>
cd <repository_directory>
```

Create and activate a virtual environment:

```
python3 -m venv venv
source venv/bin/activate
```

Install the required packages:

```
pip install -r requirements.txt
```

Create a .env file in the project directory and add your environment variables:

```
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com
```

# Creating an App Password for Gmail
* Go to your Google Account. or [App Passwords](https://myaccount.google.com/apppasswords)
* Select "Security".
* Under "Signing in to Google", select "App passwords". You might need to sign in again.
* At the bottom, choose "Select app" and choose "Other (Custom name)".
* Enter a name (e.g., "Visa Wait Times App") and click "Generate".
* Copy the app password. This will be used as EMAIL_PASSWORD in your .env file.


# Running the Application
Start the Flask application:
```
python app.py
```

The application will be running on http://0.0.0.0:40000/.

## Routes
/: Home page displaying the latest visa wait times and graph.


/send-test-email: Sends a test email to the first recipient listed in EMAIL_RECIPIENTS.
