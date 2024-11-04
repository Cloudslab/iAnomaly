"""
A python service to emulate an IOT device in vehicle which will send its location when an API call is made
"""
import random

from flask import Flask

app = Flask(__name__)
prev_location = None


@app.route('/')
def info():
    return "A python emulator to send the location of the vehicle."


@app.route('/get_location/<int:vehicleID>', methods=['GET'])
def get_location(vehicleID=None): #vehicleID is not used since this is a mock service.
    """
    A python function to emulate a GPS tracker that sends its location when queried.
    :return: JSON List with [latitude, longitude]
    """
    global prev_location

    if prev_location:
        long_delta = random.randrange(-100, 100) / 100000
        lat_delta = random.randrange(-100, 100) / 100000
        prev_location = [prev_location[0] + lat_delta, prev_location[1] + long_delta]
    else:
        long = random.randrange(-18000000, +18000000, 1) / 100000
        lat = random.randrange(-9000000, +9000000, 1) / 100000
        prev_location = [lat, long]

    return prev_location


if __name__ == '__main__':
    DEBUG = False
    app.run(host='0.0.0.0', port=9091)