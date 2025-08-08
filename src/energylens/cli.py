import tempfile
from pathlib import Path
from typing import Annotated, Literal

from energylens.pypdf_parser import parse_html_to_pl_using_pypdf
from .log import logger
import cyclopts
from cyclopts import validators, Parameter
from . import __version__

from .scrape import Scraper
from .docling_parser import parse_html_to_pl_using_docling, convert_pdf_to_html
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
    """
    Downloads invoices from a given source and saves them to a specified path using a web scraper.

    This function serves as a CLI command for downloading invoices. It utilizes a web scraper
    to fetch invoices for the specified time period and saves them to the directory provided by
    the user.

    Args:
        invoice_path (Path): Path to the directory where invoices will be downloaded. Must be a path that exists.
        login_timout (int): Number of seconds to wait for two-factor authentication (2FA) to expire.
        limit_invoices (int): Maximum number of months back for which invoices will be processed. Use 0 for no limit.

    Raises:
        None

    Returns:
        None
    """
    logger.info(f'Starting {__name__} {__version__}')
    scraper = Scraper(download_path=invoice_path, login_secs=login_timout, limit_invoices=limit_invoices)
    scraper.download_invoices()
    scraper.close()


@cli_app.command()
def parse_invoices(invoice_path: Annotated[Path, Parameter(validator=validators.Path(exists=True), help='Path to download invoices to.')] = DOWNLOAD_PATH,
                   output_file: Annotated[Path, Parameter(help='Path to output parsed invoices to.')] = DOWNLOAD_PATH / 'invoices.parquet',
                   output_format: Annotated[Literal['parquet', 'csv'], Parameter(help='Output format.')] = 'parquet'):
    """
    Parses and processes invoices from PDF files into structured data, and outputs the parsed
    data to the specified location in the desired format.

    Args:
        invoice_path (Annotated[Path, Parameter]): The path to the directory containing
            invoice PDF files to parse. Must exist.
        output_file (Annotated[Path, Parameter]): The path where the parsed invoices
            will be saved. Defaults to "invoices.parquet" in the invoice path.
        output_format (Annotated[Literal['parquet', 'csv'], Parameter]): The format
            for the output file. Supported formats are "parquet" and "csv". Defaults
            to "parquet".

    Raises:
        KeyError: If a parsing key is missing during invoice processing.
        IndexError: If an index is invalid during invoice parsing.

    Returns:
        None
    """
    logger.info(f'Starting {__name__} {__version__}')
    output_df = pl.DataFrame()
    for f in sorted(invoice_path.glob('invoice_*.pdf'), key=lambda x: x.name):
        logger.info(f'Parsing {f.as_posix()}')
        html_content = convert_pdf_to_html(f)
        with tempfile.NamedTemporaryFile() as tmp_file:
            tmp_file.write(html_content.encode())
            try:
                invoice_df = parse_html_to_pl_using_docling(Path(tmp_file.name))
            except (KeyError, IndexError) as e:
                # logger.error(f'Error parsing invoice {f.as_posix()}: {e.__class__.__name__} {e}')
                logger.info('Attempt to parse again with different parser')
                invoice_df = parse_html_to_pl_using_pypdf(f)
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
