# i3geoweather

This blocklet provides temperature information for the i3blocks status
bar often used in the i3 window manager. It attempts to determine your
location based on your IP address using the
[ipinfo.io](http://ipinfo.io) API. Based on the location it retrieves
weather information from the free [openweathermap.org
API](http://api.openweathermap.org/).

[![image](docs/i3geoweather.jpg){width="800px"}](docs/i3geoweather.jpg)

i3geoweather is a pure Python 3 program. No attempt to make it
compatible with Python 2 has been or will be made. It is time to switch!

## Installation

i3geoweather is published on [PyPI](https://pypi.org/project/i3geoweather/).
Install it with pip:

    $ pip install --user i3geoweather

Depending on your system you may need to call pip3 instead of pip.

If you use [uv](https://docs.astral.sh/uv/), install it as an isolated
tool instead:

    $ uv tool install i3geoweather

Both methods place the `i3geoweather` executable in `~/.local/bin`.

## Dependencies

i3geoweather depends on the Python
[requests](http://docs.python-requests.org/en/master/) library.
i3geoweather output uses [FontAwesome](http://fontawesome.io) for its
output. You should download the free FontAwesome zip file and copy
fontawesome-webfont.ttf to your \~/.fonts/ directory.

## Usage

i3geoweather runs a daemon process in the background (if started with
the -d option) and periodically updates weather information by writing
to \~/.i3geoweather/i3geoweather.txt.

Start i3geoweather from your i3 configuration file:

    exec_always ~/.local/bin/i3geoweather -d

i3 starts commands with its own, often minimal, PATH, so the examples
use the full path to i3geoweather. This is where pip install \--user
and uv tool install put it. If yours is elsewhere, run
`which i3geoweather` in a shell to find it.

If a previous daemon is still running, -d leaves it alone and exits
with a message on stderr, which i3 does not show. A pidfile left behind
by a crashed daemon is detected and replaced. To restart the daemon on
every i3 reload, use -r instead:

    exec_always ~/.local/bin/i3geoweather -r

A typical i3blocks.conf entry may look like this:

    [weather]
    interval=repeat
    command=inotifywait -qq -e delete_self ~/.i3geoweather/i3geoweather.txt && cat ~/.i3geoweather/i3geoweather.txt

Command line options:

-   -d or \--daemon run as background process
-   -l or \--location force a location by specifying a comma separated
    latitude/longitude pair, e.g., -l \"50.0126, 7.996\". North and east
    are positive.
-   -r or \--restart restart background process
-   -s or \--stop stop running background process
-   -v increase verbosity of logging to
    \~/.i3geoweather/i3geoweather.log. Can be used up to three times.
    Using -v twice logs informational messages. Debugging output is
    produced when -v is used three times.

## Author

Jörg Dietrich <joerg@joergdietrich.com>

## Contributing

Development takes place on
[GitHub](https://github.com/joergdietrich/i3geoweather). Please report
any bugs as an issue in the GitHub issue tracker.

## License

i3geoweather is released under an MIT license. See LICENCE.txt
