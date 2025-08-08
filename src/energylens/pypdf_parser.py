import re
from pathlib import Path

import numpy as np
from pypdf import PdfReader
import polars as pl

from energylens.log import logger
from energylens.number_utils import _to_float


def _pdf_to_text(pdf_file: Path) -> list[str]:
    output_texts = []
    reader = PdfReader(pdf_file.as_posix())
    for page in reader.pages:
        output_texts.append(page.extract_text())
    return output_texts


def _texts_to_pl(text_pages: list[str]) -> pl.DataFrame:
    text = " ".join(text_pages)
    d = {}
    d['Elnät fast avgift enkeltariff (kr/mån)'] = re.findall(r'^.+?Fast avgift enkeltariff.*?(\d+,\d{2})', text,
                                                             re.DOTALL | re.IGNORECASE)
    d['El förbrukning (kWh)'] = re.findall(r'(\d+,\d{2}) kWh', text)
    d['Elnät överföring enkeltariff (öre/kWh)'] = re.findall(r'Överföring enkeltariff\s+\d+,\d{2}(\d+,\d{2})', text)
    d['Elnät energiskatt (öre/kWh)'] = re.findall(r'Energiskatt.+\d+,\d{2}(\d+,\d{2})', text)
    d['Elnät totalt belopp (kr)'] = re.findall(r'TOTALT BELOPP ELNÄT.+?(\d+,\d{2}) kr\n', text)
    d['Elhandel medelspotpris (öre/kWh)'] = np.nan
    d['Elhandel rörliga kostnader (öre/kWh)'] = re.findall(r'Rörligt månadspris.+?\d+,\d{2}(\d+,\d{2})', text)
    d['Elhandel fasta påslag (öre/kWh)'] = np.nan
    d['Elhandel fasta avgift (kr/mån)'] = re.findall(
        r'TOTALT BELOPP ELNÄT.+?ELHANDEL\n.+?kr/mån.+?Fast avgift.+?\d+,\d{2}(\d+,\d{2})', text, re.DOTALL)
    d['Elhandel totalt belopp (kr)'] = re.findall(r'ELHANDEL (\d+,\d{2}) kr', text)
    d['Fjärrvärme förbrukning (MWh)'] = re.findall(r'(\d+,\d{1,2}) MW', text)
    d['Fjärrvärme fast avgift (kr/år)'] = re.findall(r'\d+ dgr kr/år krFast Avgift\s+\d+,\d{2}([\d\s]+,\d{2})', text)
    d['Fjärrvärme energiavgift (kr/MWh)'] = re.findall(r'kr/MWh krEnergiavgift\s+[\d+\s]+,\d{2}(\d+,\d{2})', text)
    d['Fjärrvärme totalt belopp (kr)'] = re.findall(r'FJÄRRVÄRME ([\d+\s]+,\d{2}) kr', text)
    d['Stadsnät serviceavgift villa (kr/st)'] = re.findall(r'Serviceavgift villa.+?\d+,\d{2}(\d+,\d{2})', text)
    date = da[0] if (da := re.findall(r'\d{4}-\d{2}-\d{2}', text)) else np.nan
    logger.info(f'Date: {date} using PyPDF')
    invoice_number = i[0] if (i := re.findall(r'Faktura-nr: (\d+)', text)) else np.nan
    first_items = {k: _to_float(next(iter(v), np.nan)) if isinstance(v, list) else v for k, v in d.items()}
    logger.info(f'{d['Fjärrvärme förbrukning (MWh)']=}')
    return pl.DataFrame(first_items).with_columns([pl.lit(date).alias('date'), pl.lit(invoice_number).alias('invoice_number')])


def parse_html_to_pl_using_pypdf(html_path: Path) -> pl.DataFrame:
    logger.info(f'Parsing {html_path.as_posix()} using pypdf/regex method')
    text_pages = _pdf_to_text(html_path)
    return _texts_to_pl(text_pages)


if __name__ == "__main__":
    # text_pages = _pdf_to_text(Path('/Users/edo/Downloads/invoice_20.pdf'))
    # df = _texts_to_pl(text_pages)
    df = parse_html_to_pl_using_pypdf(Path('/Users/edo/Downloads/invoice_20.pdf'))
    print(df)
