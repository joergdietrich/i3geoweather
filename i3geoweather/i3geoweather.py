import argparse
import logging
import json
import os
import sys
import tempfile
import time
import traceback

import requests

from daemon import Daemon


geo_url = "http://freegeoip.net/json/"
payload = {"lat": 48.2499, "lon": 11.63,
           "appid": "62d5bdef1ef5e8dfccb382765b499577"}

weather_url = "http://api.openweathermap.org/data/2.5/weather"

retry_interval = 15 * 60     # 15 minutes
location_timeout = 3 * 3600  # 3 hours
weather_timeout = 3600       # 1 hour
wait_failure = 60
wait_success = 300


class I3Geoweather(Daemon):
    def __init__(self, base_dir, log_level=logging.DEBUG):
        if not os.path.exists(base_dir):
            os.mkdir(base_dir)
        self.base_dir = base_dir
        self.log_level = log_level
        pidfile = os.path.join(base_dir, "i3geoweather.pid")
        super(I3Geoweather, self).__init__(pidfile)
        self.thermometers = ["", "", "", "", ""]
        self.thresholds = [-270, 0, 10, 20, 28]
        self.appid = "62d5bdef1ef5e8dfccb382765b499577"

    def write_cache(self, fname, d):
        with open(fname, "w") as f:
            json.dump(d, f)

    def read_cache(self, fname, mode):
        if mode not in ['location', 'weather']:
            raise ValueError("mode must be weather or location")
        try:
            with open(fname, "r") as f:
                d = json.load(f)
                logging.debug("using cached %s: %s" % (mode, str(d)))
                if mode == "location":
                    return d['latitude'], d['longitude']
                else:
                    return d['name'], d['main']['temp']
        except:
            logging.error("Could not read cache file %s", fname)
            logging.error(traceback.format_exc())
            logging.error("%s cache %s seems to be invalid." %
                          (mode, fname))
            os.remove(fname)
        return (None, None)

    def geolocate(self):
        geo_cache = os.path.join(self.base_dir, "location.cache")
        if os.path.exists(geo_cache):
            age = time.time() - os.path.getmtime(geo_cache)
            logging.debug("found geolocation cache file age %d" % age)
            if age < retry_interval:
                return self.read_cache(geo_cache, "location")
        try:
            r = requests.get(geo_url)
            r.raise_for_status()
            d = r.json()
            if d['latitude'] != 0 and d['longitude'] != 0:
                self.write_cache(geo_cache, d)
                msg = "retrieved location {latitude}, {longitude} for ip " \
                      "{ip}".format(**d)
                logging.debug(msg)
                return d['latitude'], d['longitude']
            else:
                msg = "received invalid location 0, 0 for ip {:s}".format(
                    d['ip'])
                logging.error(msg)
                return (None, None)
        except:
            logging.exception("error receiving location")
            return (None, None)

    def get_weather(self, lat, lon):
        weather_cache = os.path.join(self.base_dir, "weather.cache")
        if os.path.exists(weather_cache):
            age = time.time() - os.path.getmtime(weather_cache)
            logging.debug("found weather cache file age %d" % age)
            if age < retry_interval:
                return self.read_cache(weather_cache, "weather")
        if lat is None or lon is None:
            return (None, None)
        try:
            payload = {"lat": lat, "lon": lon, "appid": self.appid}
            r = requests.get(weather_url, payload)
            r.raise_for_status()
            d = r.json()
            if isinstance(d, dict) and isinstance(d['name'], str) and \
               isinstance(d['main']['temp'], float):
                self.write_cache(weather_cache, d)
                msg = "retrieved weather information {:s}".format(str(d))
                logging.debug(msg)
                return d['name'], d['main']['temp']
            else:
                msg = "received invalid weather information for " \
                      "payload {:s}".format(payload)
                logging.error(msg)
                return None, None
        except:
            logging.exception("error receiving weather")
            return None, None

    def kelvin2celsus(self, x):
        return x - 273.25

    def run(self):
        logging.basicConfig(filename=os.path.join(self.base_dir,
                                                  "i3geoweather.log"),
                            filemode='w',
                            level=self.log_level,
                            format='%(asctime)s %(levelname)s: %(message)s',
                            )
        logging.debug("i3geoweather started")
        fname = os.path.join(self.base_dir, "i3geoweather.txt")
        while True:
            try:
                lat, lon = self.geolocate()
                location, temp = self.get_weather(lat, lon)
                if location is not None and temp is not None:
                    temp = self.kelvin2celsus(temp)
                    idx = [temp >= x for x in self.thresholds]
                    therm_idx = max(loc for loc, val in enumerate(idx)
                                    if val is True)
                    thermometer = self.thermometers[therm_idx]
                    output = "{0:.15s} {1:s} {2:.1f}°C\n".format(location,
                                                                thermometer,
                                                                temp)
                    fd, tmpname = tempfile.mkstemp()
                    os.write(fd, output.encode())
                    os.close(fd)
                    os.rename(tmpname, fname)
                    sleep = wait_success
                else:
                    sleep = wait_failure
                time.sleep(sleep)
            except:
                logging.CRITICAL("Unhandled exception")
                logging.CRITICAL(traceback.format_exc())
                fd, tmpname = tempfile.mkstemp()
                os.write(fd, "i3geoweather error\n".encode())
                os.close(fd)
                os.rename(tmpname, fname)
                logging.CRITICAL("i3geoweather stopping")
                self.stop()
                logging.CRITICAL("i3geoweather stopped")
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", help="run in daemon mode",
                        action="store_true", dest="daemon")
    parser.add_argument("-s", help="stop daemon", action="store_true",
                        dest="stop")
    args = parser.parse_args()

    base_dir = os.path.join(os.getenv("HOME"), ".i3geoweather")
    i3geoweather = I3Geoweather(base_dir)
    if args.stop is True:
        i3geoweather.stop()
        sys.exit(0)
    if args.daemon is True:
        i3geoweather.start()
    else:
        i3geoweather.run()
    if args.daemon is True:
        i3geoweather.stop()
