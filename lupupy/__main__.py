"""
TODO Example Google style docstrings.
"""

import argparse
import logging
import lupupy

_LOGGER = logging.getLogger("lupusec")


def setup_logging(log_level=logging.INFO):
    """Set up the logging."""
    logging.basicConfig(level=log_level)
    fmt = "%(levelname)s " "[%(name)s] %(message)s"
    colorfmt = "%(log_color)s{}%(reset)s".format(fmt)

    logging.getLogger("requests").setLevel(logging.WARNING)

    try:
        from colorlog import ColoredFormatter

        logging.getLogger().handlers[0].setFormatter(
            ColoredFormatter(
                colorfmt,
                reset=True,
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "red",
                },
            )
        )
    except ImportError:
        pass

    logger = logging.getLogger("")
    logger.setLevel(log_level)


def get_arguments():
    """Get parsed arguments."""
    parser = argparse.ArgumentParser("Lupupy: Command Line Utility")

    parser.add_argument("-u", "--username", help="Username", required=True)
    parser.add_argument("-p", "--password", help="Password", required=True)
    parser.add_argument("-i", "--ip_address", help="IP address", required=True)

    parser.add_argument("--area", default="1", help="Area")
    parser.add_argument("--arm", help="Arm", action="store_true")
    parser.add_argument("--disarm", help="Disarm", action="store_true")
    parser.add_argument("--home", help="Set home mode")

    parser.add_argument("--sensors", help="Output all sensors", action="store_true")
    parser.add_argument(
        "--status", help="Get the status of the panel", action="store_true"
    )

    parser.add_argument("--debug", help="Enable debug logging", action="store_true")
    parser.add_argument(
        "--quiet", help="Output only warnings and errors", action="store_true"
    )

    return parser.parse_args()


def call():
    """Execute command line helper."""
    args = get_arguments()

    if args.debug:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.WARN
    else:
        log_level = logging.INFO

    setup_logging(log_level)

    lupusec = lupupy.Lupusec(
        ip_address=args.ip_address, username=args.username, password=args.password
    )

    try:
        if args.status:
            return _LOGGER.info(lupusec.areas)

        if args.sensors:
            for sensor in lupusec.sensors:
                _LOGGER.info(sensor)
            return

        area = [area for area in lupusec.areas if area.id == int(args.area)][0]

        if args.arm:
            if area.set_armed():
                _LOGGER.info("Alarm mode changed to armed")
            else:
                _LOGGER.warning("Failed to change alarm mode to armed")

        elif args.disarm:
            if area.set_disarmed():
                _LOGGER.info("Alarm mode changed to disarmed")
            else:
                _LOGGER.warning("Failed to change alarm mode to disarmed")

        elif args.home:
            if area.set_home(int(args.home)):
                _LOGGER.info("Alarm mode changed to home")
            else:
                _LOGGER.warning("Failed to change alarm mode to home")

    except lupupy.exceptions.LupusecException as exc:
        _LOGGER.error(exc)


def main():
    """Execute from command line."""
    call()

if __name__ == '__main__':
    main()
