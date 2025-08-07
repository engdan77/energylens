import tempfile
from pathlib import Path
from typing import Annotated, Literal

from .log import logger
import cyclopts
from cyclopts import validators, Parameter
from . import __version__

from .scrape import Scraper
from .parse import parse_html_to_pl, convert_pdf_to_html
import polars as pl
import warnings

warnings.filterwarnings("ignore", module='torch')

import platformdirs

cli_app = cyclopts.App(help='Application for accessing, parse and convert invoices from Jonkoping Energi')

DOWNLOAD_PATH = platformdirs.user_downloads_path()


@cli_app.command()
def download_invoices(invoice_path: Annotated[Path, Parameter(validator=validators.Path(exists=True), help='Path to download invoices to.')] = DOWNLOAD_PATH,
                      login_timout: Annotated[int, Parameter(help='Number of seconds to wait for 2FA to expire.')] = 20,
                      limit_invoices: Annotated[int, Parameter(help='Max months back to process')] = 0):
    """Downloads all invoices from the user's account."""
    logger.info(f'Starting {__name__} {__version__}')
    scraper = Scraper(download_path=invoice_path, login_secs=login_timout, limit_invoices=limit_invoices)
    scraper.download_invoices()
    scraper.close()


@cli_app.command()
def parse_invoices(invoice_path: Annotated[Path, Parameter(validator=validators.Path(exists=True), help='Path to download invoices to.')] = DOWNLOAD_PATH,
                   output_file: Annotated[Path, Parameter(help='Path to output parsed invoices to.')] = DOWNLOAD_PATH / 'invoices.parquet',
                   output_format: Annotated[Literal['parquet', 'csv'], Parameter(help='Output format.')] = 'parquet'):
    logger.info(f'Starting {__name__} {__version__}')
    output_df = pl.DataFrame()
    for f in sorted(invoice_path.glob('invoice_*.pdf'), key=lambda x: x.name):
        logger.info(f'Parsing {f.as_posix()}')
        html_content = convert_pdf_to_html(f)
        with tempfile.NamedTemporaryFile() as tmp_file:
            tmp_file.write(html_content.encode())
            try:
                invoice_df = parse_html_to_pl(Path(tmp_file.name))
            except (KeyError, IndexError) as e:
                logger.error(f'Error parsing invoice {f.as_posix()}: {e.__class__.__name__} {e}')
                continue
        output_df = output_df.vstack(invoice_df)
        logger.info(f'✅ Parsed {f.as_posix()}')
    match output_format:
        case 'parquet':
            output_df.write_parquet(output_file)
        case 'csv':
            output_df.write_csv(output_file)
    logger.info(f'Finished - saved to {output_file.as_posix()}')


def main():
    cli_app()


if __name__ == '__main__':
    main()
