from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import io
import base64
from sklearn.linear_model import LinearRegression
import threading
import pytz

app = Flask(__name__)

load_dotenv()
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_RECIPIENTS = os.getenv('EMAIL_RECIPIENTS').split(',')

CSV_FILE = 'visa_wait_times.csv'
WARNING_MESSAGE = (
    'This data is refreshed every 3 hours, but is not real-time. '
    'Use this as a reminder to check <a href="https://www.usvisascheduling.com/" target="_blank">https://www.usvisascheduling.com/</a> '
    'as the slots can be made available within seconds and immediately be booked.'
)

def get_last_updated_date(soup):
    last_updated_div = soup.find('div', class_='tsg-rwd-text parbase section')
    last_updated_text = last_updated_div.find('p').get_text(strip=True).replace("Last updated: ", "")
    return datetime.strptime(last_updated_text, "%m-%d-%Y")

def parse_visa_wait_times(soup, last_updated_date):
    table = soup.find('table', {'border': '2'})
    data = []
    columns = ["City/Post", "Visitors (B1/B2)", "Available Date"]

    for row in table.find_all('tr')[1:]:  # Skip header row
        cells = row.find_all('td')
        city = cells[0].get_text(strip=True)
        if city in ["Hyderabad", "Kolkata", "Chennai ( Madras)", "Mumbai (Bombay)", "New Delhi"]:
            wait_time = cells[4].get_text(strip=True)
            wait_time_days = int(wait_time.split()[0]) if "Days" in wait_time else float('inf')
            available_date_str = (last_updated_date + timedelta(days=wait_time_days)).strftime("%B %d, %Y") if "Days" in wait_time else "N/A"
            data.append({
                "City/Post": city.replace(" ( Madras)", "").replace(" (Bombay)", ""),
                "Visitors (B1/B2)": wait_time_days,
                "Available Date": available_date_str
            })
    
    df = pd.DataFrame(data, columns=columns).sort_values(by="Visitors (B1/B2)", ascending=True)
    return df

def fetch_visa_wait_times():
    url = "https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/global-visa-wait-times.html"
    response = requests.get(url)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    last_updated_date = get_last_updated_date(soup)
    visa_df = parse_visa_wait_times(soup, last_updated_date)

    if os.path.isfile(CSV_FILE):
        existing_df = pd.read_csv(CSV_FILE)
        most_recent_date = pd.to_datetime(existing_df['Date Checked'].iloc[-1])
        if last_updated_date > most_recent_date:
            visa_df['Date Checked'] = last_updated_date.strftime("%Y-%m-%d")
            visa_df.to_csv(CSV_FILE, mode='a', header=False, index=False)
    else:
        visa_df['Date Checked'] = last_updated_date.strftime("%Y-%m-%d")
        visa_df.to_csv(CSV_FILE, index=False)

    if 'Date Checked' in visa_df.columns:
        return visa_df.drop(columns=['Date Checked']), last_updated_date.strftime("%m-%d-%Y")
    else:
        return visa_df, last_updated_date.strftime("%m-%d-%Y")

def generate_combined_graph():
    df = pd.read_csv(CSV_FILE)
    plt.figure(figsize=(12, 8))
    ax = plt.gca()
    
    for city in df['City/Post'].unique():
        city_df = df[df['City/Post'] == city]
        recent_data = city_df.tail(7)
        
        x = np.arange(len(recent_data)).reshape(-1, 1)
        y = recent_data['Visitors (B1/B2)'].values.reshape(-1, 1)
        
        if len(recent_data) > 0:
            model = LinearRegression()
            model.fit(x, y)
            prediction_x = np.arange(len(recent_data), len(recent_data) + 4).reshape(-1, 1)
            prediction_y = model.predict(prediction_x)
            last_date_checked = pd.to_datetime(recent_data['Date Checked'].iloc[-1])
            prediction_dates = [last_date_checked + timedelta(days=i+1) for i in range(4)]
            
            plt.plot(pd.to_datetime(recent_data['Date Checked']), recent_data['Visitors (B1/B2)'], marker='o', label=city)
            plt.plot(prediction_dates, prediction_y, linestyle='dotted', marker='o', label=f'{city} (Predicted)')
        
            for i, txt in enumerate(recent_data['Visitors (B1/B2)']):
                plt.annotate(txt, (pd.to_datetime(recent_data['Date Checked']).iloc[i], recent_data['Visitors (B1/B2)'].iloc[i]),
                             textcoords="offset points", xytext=(5,0), ha='left')
            for i, txt in enumerate(prediction_y):
                plt.annotate(int(txt.item()), (prediction_dates[i], txt), textcoords="offset points", xytext=(5,0), ha='left')
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    plt.legend()
    plt.title('Visa Wait Times for All Cities')
    plt.xlabel('Date Checked')
    plt.ylabel('Visitors (B1/B2) Days')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_data = base64.b64encode(img.getvalue()).decode('utf8')
    plt.close()
    
    return img_data

called = 0

def send_email_update(recipients):
    global called
    visa_wait_times_df, last_updated = fetch_visa_wait_times()
    img_data = generate_combined_graph()
    called += 1
    print("called {}".format(called))
    
    # Email content
    subject = "Visa Wait Times Update"
    body = (
        f"{WARNING_MESSAGE}<br><br>"
        f"Last updated: {last_updated}<br><br>"
        f"{visa_wait_times_df.to_html(index=False)}<br><br>"
        f'<img src="cid:graph_image" alt="Combined Graph for All Cities" class="img-fluid">'
    )
    
    for recipient in recipients:
       
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))  
        
        
        img = MIMEImage(base64.b64decode(img_data))
        img.add_header('Content-ID', '<graph_image>')
        msg.attach(img)
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            text = msg.as_string()
            server.sendmail(EMAIL_USER, recipient, text)

@app.route('/')
def home():
    visa_wait_times_df, last_updated = fetch_visa_wait_times()
    img_data = generate_combined_graph()
    return render_template(
        'index.html',
        tables=[visa_wait_times_df.to_html(classes='data')],
        titles=visa_wait_times_df.columns.values,
        last_updated=last_updated,
        img_data=img_data,
        warning_message=WARNING_MESSAGE
    )

@app.route('/send-test-email')
def send_test_email():
    send_email_update([EMAIL_RECIPIENTS[0]])  
    return "Test email sent!"

# Scheduler setup
def start_scheduler():
    mumbai_tz = pytz.timezone('Asia/Kolkata')
    scheduler = BackgroundScheduler(timezone=mumbai_tz)
    scheduler.add_job(lambda: send_email_update(EMAIL_RECIPIENTS), 'cron', hour=1, minute=50, id='job_1')
    scheduler.add_job(lambda: send_email_update(EMAIL_RECIPIENTS), 'cron', hour=2, minute=30, id='job_2')
    scheduler.add_job(lambda: send_email_update(EMAIL_RECIPIENTS), 'cron', hour=9, minute=0, id='job_3')
    scheduler.add_job(lambda: send_email_update(EMAIL_RECIPIENTS), 'cron', hour=17, minute=0, id='job_4')
    scheduler.add_job(lambda: send_email_update(EMAIL_RECIPIENTS), 'cron', hour=22, minute=0, id='job_5')
    scheduler.start()

if __name__ == '__main__':
    if threading.current_thread().name == 'MainThread':
        start_scheduler()
    app.run(debug=False, host='0.0.0.0', port=40000)
