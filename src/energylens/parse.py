from pathlib import Path

import bs4
import pandas as pd
import polars as pl
import itertools
import numpy as np

TableType = str
TableTypeDict = dict[TableType, pd.DataFrame]


# Keywords to determine what type of table within invoice
table_types = {
    ('Energiskatt', 'kWh', 'Överföring', 'Summa'): 'elnät',
    ('Medelspotpris', 'påslag', 'kWh'): 'elhandel',
    ('Energiavgift', 'MWh'): 'fjärrvärme',
    ('Serviceavgift'): 'stadsnät'
}


def to_float(s):
    """Convenience method to convert string to float."""
    if isinstance(s, str):
        return float(np.char.replace(np.char.replace(s, ' ', ''), ',', '.'))
    else:
        return s


def categorize_tables(tables: list[pd.DataFrame]) -> TableTypeDict:
    """Parse through raw list of Pandas tables and categorize them."""
    output_tables = {}
    for table, (terms, table_type) in itertools.product(tables, table_types.items()):
        text = table.to_string()
        if all((term in text for term in terms)):
            output_tables[table_types[terms]] = table
            continue
    return output_tables


def get_data_dict_from_tables(tables: TableTypeDict) -> dict:
    """Extract data from tables and return as dictionary."""
    col1 = 'Unnamed: 0'
    d = {}

    df = tables['elnät']
    d['El förbrukning (kWh)'] = df[df[col1].str.startswith('Överföring')].iloc[0]['Antal']
    d['Elnät fast avgift enkeltariff (kr/mån)'] = df[df[col1].str.startswith('Fast avgift')].iloc[0]['Pris']
    d['Elnät överföring enkeltariff (öre/kWh)'] = df[df[col1].str.startswith('Överföring')].iloc[0]['Pris']
    d['Elnät energiskatt (öre/kWh)'] = df[df[col1].str.startswith('Energiskatt')].iloc[0]['Pris']
    d['Elnät totalt belopp (kr)'] = df[df[col1].str.startswith('TOTALT BELOPP')].iloc[0]['Summa']

    df = tables['elhandel']
    d['Elhandel medelspotpris (öre/kWh)'] = df[df[col1].str.startswith('Medelspotpris')].iloc[0]['Pris']
    d['Elhandel rörliga kostnader (öre/kWh)'] = df[df[col1].str.startswith('Rörliga kostnader')].iloc[0]['Pris']
    d['Elhandel fasta påslag (öre/kWh)'] = df[df[col1].str.startswith('Fasta påslag')].iloc[0]['Pris']
    d['Elhandel fasta avgift (kr/mån)'] = df[df[col1].str.startswith('Fast avgift')].iloc[0]['Pris']
    d['Elhandel totalt belopp (kr)'] = df[df[col1].str.startswith('TOTALT BELOPP')].iloc[0]['Summa']

    df = tables['fjärrvärme']
    d['Fjärrvärme förbrukning (MWh)'] = df[df[col1].str.startswith('Energiavgift')].iloc[0]['Antal']
    d['Fjärrvärme fast avgift (kr/år)'] = to_float(df[df[col1].str.startswith('Fast Avgift')].iloc[0]['Pris'])
    d['Fjärrvärme energiavgift (kr/MWh)'] = to_float(df[df[col1].str.startswith('Energiavgift')].iloc[0]['Pris'])
    d['Fjärrvärme totalt belopp (kr)'] = df[df[col1].str.startswith('TOTALT BELOPP')].iloc[0]['Summa']

    df = tables['stadsnät']
    d['Stadsnät serviceavgift villa (kr/st)'] = df[df[col1].str.startswith('Serviceavgift')].iloc[0]['Pris']
    return d


def get_date_and_invoice_number(html_path: Path) -> tuple[str, str]:
    """Extract date and invoice number from HTML file name."""
    html = bs4.BeautifulSoup(open(html_path.as_posix()))
    date = next((e.text.split().pop(0) for e in html.find_all('h2') if e.text.endswith('FAKTURA')))
    invoice_number = next((list(html.find_all('p'))[idx + 1].text for idx, p in enumerate(list(html.find_all('p'))) if p.text.startswith('Faktura')), None)
    return date, invoice_number


def parse_html_to_pl(html_path: Path) -> pl.DataFrame:
    """Parse HTML file to Polars DataFrame."""
    input_tables = pd.read_html(html_path.as_posix(), decimal=',', thousands='.', header=0)
    tables = categorize_tables(input_tables)
    data_dict = get_data_dict_from_tables(tables)
    date, invoice_number = get_date_and_invoice_number(html_path)
    return pl.DataFrame(data_dict).with_columns([pl.lit(date).alias('date'), pl.lit(invoice_number).alias('invoice_number')])
