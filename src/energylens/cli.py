import tempfile
from pathlib import Path
from typing import Annotated, Literal

from energylens.pypdf_parser import parse_html_to_pl_using_pypdf
from energylens.types import Common
from .log import logger
import cyclopts
from cyclopts import validators, Parameter
from . import __version__

from .scrape import Scraper
from .docling_parser import parse_html_to_pl_using_docling, convert_pdf_to_html
import polars as pl
import warnings

warnings.filterwarnings("ignore", module="torch")

import platformdirs

cli_app = cyclopts.App(
    help="Application for accessing, parse and convert invoices from Jonkoping Energi",
    version=__version__
)

DOWNLOAD_PATH = platformdirs.user_downloads_path()


@cli_app.command()
def download_invoices(
    invoice_path: Annotated[
        Path,
        Parameter(
            validator=validators.Path(exists=True), help="Path to download invoices to."
        ),
    ] = DOWNLOAD_PATH,
    login_timout: Annotated[
        int, Parameter(help="Number of seconds to wait for 2FA to expire.")
    ] = 20,
    limit_invoices: Annotated[int, Parameter(help="Max months back to process")] = 0,
    *,
    common: Common | None = None,
):
    """
    Downloads invoices to the specified path.

    Downloads invoices using a scraper, with additional configurations for login
    timeout and the limit on the number of months for which to process invoices.
    The downloaded invoices are saved to the given path. Optionally, accepts a
    common configuration object.
    """
    logger.info(f"Starting {__name__} {__version__}")
    scraper = Scraper(
        download_path=invoice_path,
        login_secs=login_timout,
        limit_invoices=limit_invoices,
        common=common,
    )
    scraper.download_invoices()
    scraper.close()


@cli_app.command()
def parse_invoices(
    invoice_path: Annotated[
        Path,
        Parameter(
            validator=validators.Path(exists=True), help="Path to download invoices to."
        ),
    ] = DOWNLOAD_PATH,
    output_file: Annotated[
        Path, Parameter(help="Path to output parsed invoices to.")
    ] = DOWNLOAD_PATH / "invoices.parquet",
    output_format: Annotated[
        Literal["parquet", "csv"], Parameter(help="Output format.")
    ] = "parquet",
    *,
    common: Common | None = None,
):
    """
    Parses invoice files in the specified location and saves the parsed output to a file in the desired format.

    This function processes PDF files, converts them to HTML, and then extracts the invoice data using
    two different parsers. The parsed data is consolidated and saved in the specified output file and format.
    """
    prefix = common.filename_prefix if common else "invoice_"
    logger.info(f"Starting {__name__} {__version__}")
    output_df = pl.DataFrame()
    for f in sorted(invoice_path.glob(f"{prefix}*.pdf"), key=lambda x: x.name):
        logger.info(f"Parsing {f.as_posix()}")
        html_content = convert_pdf_to_html(f)
        with tempfile.NamedTemporaryFile() as tmp_file:
            tmp_file.write(html_content.encode())
            try:
                invoice_df = parse_html_to_pl_using_docling(Path(tmp_file.name))
            except (KeyError, IndexError) as e:
                # logger.error(f'Error parsing invoice {f.as_posix()}: {e.__class__.__name__} {e}')
                logger.info("Attempt to parse again with different parser")
                invoice_df = parse_html_to_pl_using_pypdf(f)
        output_df = pl.concat([invoice_df, output_df], how="diagonal_relaxed")
        logger.info(f"✅ Parsed {f.as_posix()}")
    match output_format:
        case "parquet":
            output_df.write_parquet(output_file)
        case "csv":
            output_df.write_csv(output_file)
    logger.info(f"Finished - saved to {output_file.as_posix()}")


def main():
    cli_app()


if __name__ == "__main__":
    main()
