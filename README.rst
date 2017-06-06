i3geoweather
============

This blocklet provides temperature information for the i3blocks status bar
often used in the i3 window manager. It attempts to determine your location
based on your IP address using the `freegeoip.net <http://freegeoip.net>`_
API. Based on the location it retrieves weather information from the free
`openweathermap.org API`__.

.. _openweathermap: http://api.openweathermap.org/

__ openweathermap_

.. image:: docs/i3geoweather.jpg
   :width: 800px
   :target: docs/i3geoweather.jpg
	   
i3geoweather is a pure Python 3 program. No attempt to make it compatible with
Python 2 has been or will be made. It is time to switch!


Installation
------------

The easiest way to install i3geoweather is to use pip::
  
  $ pip install i3geoweather

Depending on your system you may need to call pip3 instead of pip
  

Dependencies
------------

i3geoweather depends on the Python requests_ library. i3geoweather output uses
`FontAwesome <http://fontawesome.io>`_ for its output. You should download the
free FontAwesome zip file and copy fontawesome-webfont.ttf to your ~/.fonts/
directory. 

Usage
-----

i3geoweather runs a daemon process in the background (if started with the -d
option) and periodically updates weather information by writing to
~/.i3geoweather/i3geoweather.txt.

Start i3geoweather from your i3 configuration file::

  exec_always i3geoweather -d

You may need to use the full path to i3geoweather, e.g., for an installation
with pip install --user ...::

  exec_always ~/.local/bin/i3geoweather -d
  
A typical i3blocks.conf entry may look like this::

  [weather]
  interval=repeat
  command=inotifywait -qq -e delete_self ~/.i3geoweather/i3geoweather.txt && cat ~/.i3geoweather/i3geoweather.txt

Command line options:

- -d or --daemon run as background process
- -l or --location force a location by specifying a comma separated
  latitude/longitude pair, e.g., -l "50.0126, 7.996". North and east are
  positive. 
- -r or --restart restart background process
- -s or --stop stop running background process
- -v increase verbosity of logging to ~/.i3geoweather/i3geoweather.log. Can be
  used up to three times. Using -v twice logs informational
  messages. Debugging output is produced when -v is used three times.
     


Author
------

Jörg Dietrich astro@joergdietrich.com

Contributing
------------

Development takes place on GitHub_. Please report any bugs as an issue in the
GitHub issue tracker.

License
-------

i3geoweather is released under an MIT license. See LICENCE.txt


.. _requests: http://docs.python-requests.org/en/master/
.. _GitHub: https://github.com/joergdietrich/i3geoweather
