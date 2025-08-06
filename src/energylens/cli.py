from pathlib import Path
from typing import Annotated

from .log import logger
import cyclopts
from cyclopts import validators, Parameter
from . import __version__

from .scrape import Scraper

import platformdirs

cli_app = cyclopts.App(help='Application for accessing, parse and convert invoices from Jonkoping Energi')

DOWNLOAD_PATH = platformdirs.user_downloads_path()


@cli_app.command()
def download_invoices(download_path: Annotated[Path, Parameter(validator=validators.Path(exists=True), help='Path to download invoices to.')] = DOWNLOAD_PATH,
                      login_timout: Annotated[int, Parameter(help='Number of seconds to wait for 2FA to expire.')] = 20):
    """Downloads all invoices from the user's account."""
    logger.info(f'Starting {__name__} {__version__}')
    scraper = Scraper(download_path=download_path, login_secs=login_timout)
    scraper.download_all_invoices()
    scraper.close()


def main():
    cli_app()


if __name__ == '__main__':
    main()
