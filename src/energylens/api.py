import asyncio
from io import BytesIO
import tempfile
from pathlib import Path

from energylens.cli import download_invoices, parse_invoices
from energylens.log import logger

Parquet = BytesIO


def get_last_invoices(count: int = 10, login_timeout: int = 30) -> Parquet:
    """Convenience method to download and parse invoices."""
    file_object = BytesIO()
    with tempfile.TemporaryDirectory() as tmpdirname:
        outputfilename = Path(f"{tmpdirname}/tmp.parquet")
        logger.info(f"Downloading invoices to {tmpdirname}")
        download_invoices(invoice_path=Path(tmpdirname), limit_invoices=count)
        parse_invoices(Path(tmpdirname), output_file=outputfilename, output_format="parquet")
        file_object.write(outputfilename.read_bytes())
        return file_object


def async_get_last_invoices(count: int = 10, login_timeout: int = 30) -> Parquet:
    asyncio.to_thread(get_last_invoices, count, login_timeout)
