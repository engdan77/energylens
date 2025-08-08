# Energy Lens



## Purpose, thoughts and lessons learned

I have for quite some time receieved invoices from our energy provider [Jönköping Energi](https://jonkopingenergi.se) (for electricity and [fjärrvärme](https://sv.wikipedia.org/wiki/Fjärrvärme)) and had the process of transferring amounts and costs into a sheet for easier following up deviations or changes of prices. At the time of writing this there were not official API's nor easy way to export "all" data into any usable form. To spare me from this manual process I instead I developed some code using the [Playwright](https://playwright.dev) (Python) framework allowing to login using **2FA** ([bankid](https://www.bankid.com)) and as the underlying backend mechanics were quite sophisticated *(e.g. using different token exchanges etc)* this allowed me to efficiently instead used the dynamic frontend to download all <u>invoices</u> as **PDF** files as my first step.

The second stage would be to automatically parse the tables within those PDFs into a [parquet](https://parquet.apache.org/docs/file-format/) dataframe, for this I primarily gave [Docling](https://github.com/docling-project/docling) a spin. It turned out to do a decent work for the most recent files, but for some reason for other ones some important tables/texts were left out. After evaluating a few other poplular packages it turns out those performed even worse. So as a backup solution I went for a more programmatic text-extraction using [PyPDF](https://pypdf.readthedocs.io/en/stable/) package and straight pattern/[regex](https://en.wikipedia.org/wiki/Regular_expression) matching instead. 

Now with this I should now have raw data to do my data visualization using e.g. [Polars and Altair](https://docs.pola.rs/user-guide/misc/visualization/).

This project may be found valuable for others with this energy provider and/or find other bits of this code useful for other usage.

## Usage

...

