from .log import logger
from . import __version__
from .scrape import Scraper


def main():
    logger.info(f'Starting {__name__} {__version__}')
    scraper = Scraper()
    scraper.download_all_invoices()
    scraper.close()


if __name__ == '__main__':
    main()
