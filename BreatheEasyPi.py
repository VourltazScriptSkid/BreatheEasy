import time
import csv
import paho.mqtt.client as mqtt
from sds011 import SDS011
from tkinter import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from threading import Thread, Event
import requests

# Configuration of our Code
BROKER_ADDRESS = "localhost" # Address of our broker
SENSOR_PORT = "/dev/ttyUSB1" #port of our sensor
LOG_FILE = "air_quality_data.csv" #csv name
IFTTT_URL = 'https://maker.ifttt.com/trigger/air_quality_update/with/key/i_0Q2IrEhAeUviYALkPfU3wsZVaHT1xR_dmaPnu6GUf' #to allow webhook of notifs

# Initialize variables
mq135_value = None
collecting_data = Event()
program_running = Event()
program_running.set()

# Sets up the MQTT client
def on_message(client, userdata, message):
    global mq135_value
    mq135_value = int(message.payload.decode("utf-8"))
    print(f"MQ135: {mq135_value}")

client = mqtt.Client(client_id="RaspberryPi")
client.on_message = on_message
client.connect(BROKER_ADDRESS)
client.subscribe("air_quality/mq135")
client.loop_start()

# Sets the up SDS011 sensor
sds011_sensor = SDS011(SENSOR_PORT)
sds011_sensor.set_work_period(0)  # Continuous measurement

# Helper functions
def read_sds011():
    try:
        return sds011_sensor.query()
    except Exception as e:
        print(f"Error reading SDS011 sensor: {e}")
        return None
#Classes our value
def classify_air_quality(value):
    if value < 500:
        return "Fresh Air"
    elif 500 <= value <= 1000:
        return "Poor Air"
    else:
        return "Very Poor Air"
 #Gui updates
def update_plot():
    data = pd.read_csv(LOG_FILE)
    ax1.clear()
    ax2.clear()
    data['Timestamp'] = pd.to_datetime(data['Timestamp'])
    data.set_index('Timestamp', inplace=True)
    ax1.plot(data.index, data['PM2.5 (ug/m3)'], label='PM2.5 (ug/m3)')
    ax1.plot(data.index, data['PM10 (ug/m3)'], label='PM10 (ug/m3)')
    ax2.plot(data.index, data['MQ135'], label='MQ135')
    ax1.legend()
    ax2.legend()
    ax1.set_xlabel('Timestamp')
    ax1.set_ylabel('Concentration')
    ax1.set_title('SDS011 Data')
    ax1.xaxis.set_major_locator(plt.MaxNLocator(10))
    ax2.set_xlabel('Timestamp')
    ax2.set_ylabel('Concentration')
    ax2.set_title('MQ135 Data')
    fig.tight_layout()
    canvas.draw()
#Data Collection
def collect_data():
    with open(LOG_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        while program_running.is_set():
            if collecting_data.is_set():
                result = read_sds011()
                if result is not None:
                    pm25, pm10 = result
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    if mq135_value is not None:
                        air_quality = classify_air_quality(mq135_value)
                        writer.writerow([timestamp, pm25, pm10, mq135_value, air_quality])
                        file.flush()  # Ensure data is written to the file
                        print(f"{timestamp} - PM2.5: {pm25} ug/m3, PM10: {pm10} ug/m3, MQ135: {mq135_value}, Air Quality: {air_quality}")
            time.sleep(1)
#Updates plot
def update_plot_periodically():
    while program_running.is_set():
        if collecting_data.is_set():
            update_plot()
        time.sleep(10)  # Update the plot every 10 seconds
#sends the notification
def send_ifttt_notification():
    while program_running.is_set():
        if collecting_data.is_set():
            data = pd.read_csv(LOG_FILE).tail(1)
            if not data.empty:
                timestamp = data['Timestamp'].values[0]
                pm25 = data['PM2.5 (ug/m3)'].values[0]
                pm10 = data['PM10 (ug/m3)'].values[0]
                mq135 = data['MQ135'].values[0]
                air_quality = data['Air Quality'].values[0]
                payload = {
                    'value1': f"Timestamp: {timestamp}",
                    'value2': f"PM2.5: {pm25} ug/m3, PM10: {pm10} ug/m3",
                    'value3': f"MQ135: {mq135}, Air Quality: {air_quality}"
                }
                requests.post(IFTTT_URL, json=payload)
        time.sleep(60)  # Send data every 5 minutes
#button for data collection
def toggle_data_collection():
    if collecting_data.is_set():
        collecting_data.clear()
        btn_toggle.config(text="Start Data Collection")
    else:
        collecting_data.set()
        btn_toggle.config(text="Stop Data Collection")
# Button to close the program
def close_program():
    program_running.clear()
    collecting_data.clear()
    root.quit()
    root.destroy()

# Initializes the CSV file
with open(LOG_FILE, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "PM2.5 (ug/m3)", "PM10 (ug/m3)", "MQ135", "Air Quality"])

# Setup the Tkinter window
root = Tk()
root.title("Live Air Quality Data")

# Create Matplotlib figure
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(fill=BOTH, expand=1)

# Add buttons
btn_toggle = Button(root, text="Start Data Collection", command=toggle_data_collection)
btn_toggle.pack(side=LEFT, padx=10, pady=10)
btn_close = Button(root, text="Close", command=close_program)
btn_close.pack(side=RIGHT, padx=10, pady=10)

# Start threads
Thread(target=collect_data).start()
Thread(target=send_ifttt_notification).start()
Thread(target=update_plot_periodically).start()

# Start Tkinter main loop
root.mainloop()
