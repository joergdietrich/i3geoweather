#!/usr/bin/env python3

import argparse
import logging
import logging.handlers
import json
import os
import sys
import tempfile
import time
import traceback

import requests

from i3geoweather.daemon import Daemon

geo_url = "http://freegeoip.net/json/"
weather_url = "http://api.openweathermap.org/data/2.5/weather"

RETRY_INTERVAL = 900         # 15 minutes
LOCATION_TIMEOUT = 3 * 3600  # 3 hours
WEATHER_TIMEOUT = 3600       # 1 hour
WAIT_FAILURE = 60            # 1 minute
WAIT_SUCCESS = 300           # 5 minutes
COLOR_NORMAL = '#FFFFFF'
COLOR_TIMEOUT = '#505050'

assert(LOCATION_TIMEOUT > RETRY_INTERVAL)
assert(WEATHER_TIMEOUT > RETRY_INTERVAL)


class I3Geoweather(Daemon):
    def __init__(self, base_dir, log_level=logging.DEBUG, location=None):
        if not os.path.exists(base_dir):
            os.mkdir(base_dir)
        self.base_dir = base_dir
        self.log_level = log_level
        pidfile = os.path.join(base_dir, "i3geoweather.pid")
        super(I3Geoweather, self).__init__(pidfile)
        self.thermometers = ["", "", "", "", ""]
        self.thresholds = [-270, 0, 10, 20, 28]
        if location is not None:
            self.latitude, self.longitude = map(float, location.split(","))
            self.forced_location = True
        else:
            self.latitude = None
            self.longitude = None
            self.forced_location = False
        self.location = None
        self.temperature = None
        self.geo_cache = None
        self.weather_cache = None
        now = time.time()
        self.location_time = now - LOCATION_TIMEOUT - 1
        self.weather_time = now - WEATHER_TIMEOUT - 1
        self.appid = "62d5bdef1ef5e8dfccb382765b499577"

    def write_cache(self, fname, d):
        with open(fname, "w") as f:
            json.dump(d, f)

    def read_cache(self, fname, mode):
        if mode not in ['location', 'weather']:
            raise ValueError("mode must be weather or location")
        if os.path.exists(fname):
            mtime = os.path.getmtime(fname)
            age = time.time() - mtime
            logging.debug("found %s cache file age %d" % (mode, age))
        else:
            logging.debug("cache file %s does not exist" % fname)
            if mode == "weather":
                return (None, None, self.weather_time)
            else:
                return (None, None, self.location_time)

        logging.info("reading cached %s" % mode)
        try:
            with open(fname, "r") as f:
                d = json.load(f)
                logging.debug("reading cached %s: %s" % (mode, str(d)))
                if mode == "location":
                    return d['latitude'], d['longitude'], mtime
                else:
                    return d['name'], d['main']['temp'], mtime
        except:
            logging.error("Could not read cache file %s", fname)
            logging.error(traceback.format_exc())
            logging.error("%s cache %s seems to be invalid." %
                          (mode, fname))
            os.remove(fname)
        if mode == "weather":
            return (None, None, self.weather_time)
        else:
            return (None, None, self.location_time)

    def geolocate(self):
        if self.forced_location is True:
            logging.info("using forced location %f %f" %
                         (self.latitude, self.longitude))
            self.location_time = time.time() - LOCATION_TIMEOUT + 60
            return self.latitude, self.longitude
        location_age = time.time() - self.location_time
        if location_age < RETRY_INTERVAL:
            logging.debug("location is still young (%d seconds)" %
                          location_age)
            return self.latitude, self.longitude
        try:
            r = requests.get(geo_url)
            r.raise_for_status()
            d = r.json()
            logging.debug("geolocation response %s" % str(d))
            if d['latitude'] != 0 and d['longitude'] != 0:
                self.write_cache(self.geo_cache, d)
                self.location_time = time.time()
                msg = "retrieved location {latitude}, {longitude} for ip " \
                      "{ip}".format(**d)
                logging.info(msg)
                return d['latitude'], d['longitude']
            else:
                msg = "received invalid location 0, 0 for ip {:s}".format(
                    d['ip'])
                logging.warn(msg)
                return self.latitude, self.longitude
        except:
            logging.exception("error receiving location")
            return self.latitude, self.longitude

    def get_weather(self, lat, lon):
        if lat is None or lon is None:
            return (None, None)
        weather_age = time.time() - self.weather_time
        if weather_age < RETRY_INTERVAL and \
           self.weather_time >= self.location_time:
            logging.debug("weather is still young (%d seconds)" % weather_age)
            return self.location, self.temperature
        try:
            payload = {"lat": lat, "lon": lon, "appid": self.appid,
                       "units": "metric"}
            r = requests.get(weather_url, payload)
            r.raise_for_status()
            d = r.json()
            logging.debug("weather response %s" % str(d))
            if isinstance(d, dict) and isinstance(d['name'], str) and \
               (isinstance(d['main']['temp'], float) or
                    isinstance((d['main']['temp']), int)):
                self.write_cache(self.weather_cache, d)
                self.weather_time = time.time()
                msg = "retrieved weather information {:s}".format(str(d))
                logging.info("updated weather")
                logging.debug(msg)
                return d['name'], d['main']['temp']
            else:
                msg = "received invalid weather information for " \
                      "payload {:s}".format(str(payload))
                logging.error(msg)
                return self.location, self.temperature
        except:
            logging.exception("error receiving weather")
            return self.location, self.temperature

    def write_weather(self, fname, location, temp):
        idx = [temp >= x for x in self.thresholds]
        therm_idx = max(loc for loc, val in enumerate(idx)
                        if val is True)
        try:
            thermometer = self.thermometers[therm_idx]
        except IndexError:
            thermometer = self.thermometers[-1]
            logging.error("length of thresholds %d does not match "
                          "thermometer %d" % (len(self.thresholds),
                                              len(self.thermometers)))
        now = time.time()
        location_age = now - self.location_time
        loc_color = COLOR_NORMAL if location_age < LOCATION_TIMEOUT \
            else COLOR_TIMEOUT
        weather_age = now - self.weather_time
        weather_color = COLOR_NORMAL if weather_age < WEATHER_TIMEOUT \
            else COLOR_TIMEOUT
        long_output = "<span color='{:s}'>{:.15s}</span> " \
                      "<span color='{:s}'>{:s} {:.1f}°C</span>\n".format(
                          loc_color, location, weather_color, thermometer,
                          temp)
        short_output = "<span color='{:s}'>{:s} {:.1f}°C</span>\n".format(
            weather_color, thermometer, temp)
        fd, tmpname = tempfile.mkstemp()
        os.write(fd, long_output.encode())
        os.write(fd, short_output.encode())
        os.close(fd)
        os.rename(tmpname, fname)
        logging.info(long_output[:-1])

    def read_caches(self):
        logging.info("i3geoweather started")
        if self.forced_location is False:
            self.geo_cache = os.path.join(self.base_dir, "location.cache")
            self.latitude, self.longitude, \
                self.location_time = self.read_cache(self.geo_cache,
                                                     "location")
        self.weather_cache = os.path.join(self.base_dir, "weather.cache")
        self.location, self.temperature, \
            self.weather_time = self.read_cache(self.weather_cache,
                                                "weather")

    def run(self):
        log_file = os.path.join(self.base_dir, "i3geoweather.log")
        handler = logging.handlers.RotatingFileHandler(log_file,
                                                       maxBytes=200000,
                                                       backupCount=2)
        logging.basicConfig(level=self.log_level,
                            format='%(asctime)s %(levelname)s: %(message)s',
                            handlers=(handler, ),
                            )
        self.read_caches()
        fname = os.path.join(self.base_dir, "i3geoweather.txt")
        while True:
            try:
                lat, lon = self.geolocate()
                if lat is not None and lon is not None:
                    self.latitude, self.longitude = (lat, lon)
                location, temp = self.get_weather(self.latitude,
                                                  self.longitude)
                if location is not None and temp is not None:
                    self.location, self.temperature = (location, temp)
                if self.location is not None and self.temperature is not None:
                    self.write_weather(fname, self.location, self.temperature)
                    sleep = WAIT_SUCCESS
                else:
                    sleep = WAIT_FAILURE
                logging.debug("next update attempt in %d seconds" % sleep)
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


def my_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--daemon", help="run in daemon mode",
                        action="store_true", dest="daemon")
    parser.add_argument("-s", "--stop", help="stop daemon",
                        action="store_true", dest="stop")
    parser.add_argument("-r", "--restart", help="restart daemon",
                        action="store_true", dest="restart")
    parser.add_argument('--verbose', '-v', help="increase verbosity",
                        action='count', dest="verbose", default=0)
    parser.add_argument('-l', '--location', help="force location (lat, lon)")
    args = parser.parse_args()
    return args


def main():
    args = my_argparser()
    log_levels = [logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG]
    log_level = log_levels[min(len(log_levels) - 1, args.verbose)]
    base_dir = os.path.join(os.getenv("HOME"), ".i3geoweather")

    i3geoweather = I3Geoweather(base_dir, log_level, args.location)
    if args.stop is True:
        i3geoweather.stop()
        sys.exit(0)
    if args.daemon is True:
        i3geoweather.start()
    elif args.restart is True:
        i3geoweather.restart()
    else:
        i3geoweather.run()
    if args.daemon is True:
        i3geoweather.stop()


if __name__ == "__main__":
    main()
