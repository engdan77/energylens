import asyncio
from io import BytesIO
import tempfile
from pathlib import Path

from energylens.cli import download_invoices, parse_invoices
from energylens.async_scrape import AsyncScraper
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


async def async_get_last_invoices(count: int = 10, login_timeout: int = 30) -> Parquet:
    file_object = BytesIO()
    with tempfile.TemporaryDirectory() as tmpdirname:
        outputfilename = Path(f"{tmpdirname}/tmp.parquet")
        logger.info(f"Downloading invoices to {tmpdirname}")
        scraper = AsyncScraper(
            download_path=Path(tmpdirname),
            login_secs=login_timeout,
            limit_invoices=count
        )
        await scraper.download_invoices()
        await scraper.close()
        logger.info(f"Parsing invoices in {tmpdirname}")
        parse_invoices(Path(tmpdirname), output_file=outputfilename, output_format="parquet")
        file_object.write(outputfilename.read_bytes())
        return file_object


def test_async_get_last_invoices():
    asyncio.run(async_get_last_invoices(3))


if __name__ == "__main__":
    df = test_async_get_last_invoices()
    logger.info(f'{len(df)=}')
