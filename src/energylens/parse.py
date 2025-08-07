import functools
from pathlib import Path

import bs4
import pandas as pd
import polars as pl
import itertools
import numpy as np
from docling.document_converter import DocumentConverter

from energylens.log import logger

TableType = str
TableTypeDict = dict[TableType, pd.DataFrame]


# Keywords to determine what type of table within invoice
table_types = {
    ('Energiskatt', 'kWh', 'Överföring', 'Summa'): 'elnät',
    ('Medelspotpris', 'påslag', 'kWh'): 'elhandel',
    ('Energiavgift', 'MWh'): 'fjärrvärme',
    ('Serviceavgift'): 'stadsnät'
}


def _to_float(s):
    """Convenience method to convert string to float."""
    if isinstance(s, str):
        return float(np.char.replace(np.char.replace(s, ' ', ''), ',', '.'))
    else:
        return s


def _categorize_tables(tables: list[pd.DataFrame]) -> TableTypeDict:
    """Parse through raw list of Pandas tables and categorize them."""
    output_tables = {}
    for table, (terms, table_type) in itertools.product(tables, table_types.items()):
        text = table.to_string()
        if all((term in text for term in terms)):
            output_tables[table_types[terms]] = table
            ...
    return output_tables


def _get_first_row_beginning_with(df: pd.DataFrame, first_col_name: str, starts_with: str, return_col: str = 'Antal'):
    try:
        return _to_float(df[df[first_col_name].fillna('').str.startswith(starts_with)].iloc[0][return_col])
    except ValueError as e:
        logger.warning(f'Could not find row starting with "{starts_with}" in table. Returning NaN.')
        return np.nan


def _get_data_dict_from_tables(tables: TableTypeDict) -> dict:
    """Extract data from tables and return as dictionary."""
    col1 = 'Unnamed: 0'
    d = {}

    df = tables['elnät']
    r = functools.partial(_get_first_row_beginning_with, df, col1)
    d['El förbrukning (kWh)'] = r('Överföring', 'Antal')
    d['Elnät fast avgift enkeltariff (kr/mån)'] = r('Fast avgift', 'Pris')
    d['Elnät överföring enkeltariff (öre/kWh)'] = r('Överföring', 'Pris')
    d['Elnät energiskatt (öre/kWh)'] = r('Energiskatt', 'Pris')
    d['Elnät totalt belopp (kr)'] = r('TOTALT BELOPP', 'Summa')

    df = tables['elhandel']
    r = functools.partial(_get_first_row_beginning_with, df, col1)
    d['Elhandel medelspotpris (öre/kWh)'] = r('Medelspotpris', 'Pris')
    d['Elhandel rörliga kostnader (öre/kWh)'] = r('Rörliga kostnader', 'Pris')
    d['Elhandel fasta påslag (öre/kWh)'] = r('Fasta påslag', 'Pris')
    d['Elhandel fasta avgift (kr/mån)'] = r('Fast avgift', 'Pris')
    d['Elhandel totalt belopp (kr)'] = r('TOTALT BELOPP', 'Summa')

    df = tables['fjärrvärme']
    r = functools.partial(_get_first_row_beginning_with, df, col1)
    d['Fjärrvärme förbrukning (MWh)'] = r('Energiavgift', 'Antal')
    d['Fjärrvärme fast avgift (kr/år)'] = r('Fast Avgift','Pris')
    d['Fjärrvärme energiavgift (kr/MWh)'] = r('Energiavgift', 'Pris')
    d['Fjärrvärme totalt belopp (kr)'] = r('TOTALT BELOPP', 'Summa')

    df = tables['stadsnät']
    r = functools.partial(_get_first_row_beginning_with, df, col1)
    d['Stadsnät serviceavgift villa (kr/st)'] = r('Serviceavgift', 'Pris')
    return d


def _get_date_and_invoice_number(html_path: Path) -> tuple[str, str]:
    """Extract date and invoice number from HTML file name."""
    html = bs4.BeautifulSoup(open(html_path.as_posix()), features="lxml")
    date = next((e.text.split().pop(0) for e in html.find_all('h2') if e.text.endswith('FAKTURA')))
    invoice_number = next((list(html.find_all('p'))[idx + 1].text for idx, p in enumerate(list(html.find_all('p'))) if p.text.startswith('Faktura')), None)
    return date, invoice_number


def convert_pdf_to_html(source: Path) -> str:
    converter = DocumentConverter()
    result = converter.convert(source.as_posix())
    html = result.document.export_to_html()
    return html


def parse_html_to_pl(html_path: Path) -> pl.DataFrame:
    """Parse HTML file to Polars DataFrame."""
    input_tables = pd.read_html(html_path.as_posix(), decimal=',', thousands='.', header=0)
    tables = _categorize_tables(input_tables)
    data_dict = _get_data_dict_from_tables(tables)
    date, invoice_number = _get_date_and_invoice_number(html_path)
    return pl.DataFrame(data_dict).with_columns([pl.lit(date).alias('date'), pl.lit(invoice_number).alias('invoice_number')])
