import asyncio
from pathlib import Path

from playwright.async_api import Playwright, expect, async_playwright

from .error import async_exception_handler
from .types import Common
from .log import logger
from .__about__ import __version__


class AsyncScraper:
    def __init__(
        self,
        download_path: Path,
        login_secs: int = 20,
        limit_invoices: int = 0,
        *,
        common: Common | None = None,
    ):
        self.common = common
        self.download_path = None
        self.filename_prefix = None
        self.my_account_url = None
        self.login_url = None
        self.context = None
        self.browser = None
        self.playwright = None
        self.limit_invoices = limit_invoices
        self.login_secs = login_secs  # Timeout before 2FA expires
        self.ready_start = False
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(async_exception_handler)
        asyncio.create_task(self.async_init(download_path, common))

    def start(self):
        asyncio.create_task(self.async_init(self.download_path, self.common))

    async def async_init(self, download_path: Path, common: Common | None = None):
        logger.info(f"Initializing scraper {__version__}")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.firefox.launch(headless=False)
        self.context = await self.browser.new_context()
        self.login_url = "https://idp.jonkopingenergi.se/Account/BankID?returnUrl=%2Fconnect%2Fauthorize%2Fcallback%3Fclient_id%3Dweb-MinaSidor%26redirect_uri%3Dhttps%253A%252F%252Fminasidor.jonkopingenergi.se%252Fsignin-oidc%26response_type%3Dcode%26scope%3Dopenid%2520offline_access%26type%3Dprivate"
        self.my_account_url = "https://minasidor.jonkopingenergi.se/"
        self.filename_prefix = common.filename_prefix if common else "invoice_"
        self.download_path = download_path
        self.ready_start = True
        logger.info(f"Scraper initialized .. ready to scrape")
        assert self.download_path.exists(), "Download path does not exist"

    @staticmethod
    async def scroll_to_bottom(page):
        _prev_height = -1
        _max_scrolls = 20
        _scroll_count = 0
        while _scroll_count < _max_scrolls:
            await page.keyboard.down("End")
            await page.wait_for_timeout(1000)
            _scroll_count += 1
            logger.info(f"scrolling to bottom - {_scroll_count / _max_scrolls:.0%}")

    @staticmethod
    async def scroll_to_top(page):
        _prev_height = -1
        _max_scrolls = 20
        _scroll_count = 0
        while _scroll_count < _max_scrolls:
            await page.keyboard.down("Home")
            await page.wait_for_timeout(1000)
            _scroll_count += 1
            logger.info(f"scrolling to top - {_scroll_count / _max_scrolls:.0%}")

    @staticmethod
    async def pause(page, time_ms=1000):
        await page.wait_for_timeout(time_ms)

    async def download_invoices(self) -> None:
        for _ in range(10):
            logger.info(f"Waiting for scraper to be ready - attempt {_ + 1}")
            if self.ready_start and self.context is not None:
                logger.info("Starting scraper")
                break
            logger.info("Scraper not ready yet, waiting 5 seconds")
            await asyncio.sleep(5)
        else:
            assert False, "Scraper not ready"
        page = await self.context.new_page()
        await page.goto(self.login_url)
        await expect(
            page.get_by_role("button", name="BankID logga BankID med QR-kod")
        ).to_be_visible()
        await page.get_by_role("button", name="BankID logga BankID med QR-kod").click()
        for time_elapsed in range(self.login_secs):
            logger.info(
                f"Waiting for you to login using BankID on your device - {self.login_secs - time_elapsed} seconds left ..."
            )
            await self.pause(page)
        await page.goto(self.my_account_url)
        await expect(page.get_by_role("link", name="Fakturor", exact=True)).to_be_visible()
        await page.get_by_role("link", name="Fakturor", exact=True).click()
        await self.pause(page, 10000)
        p = await page.get_by_text("Daniel Engvall", exact=True).all()
        await p[1].click()
        await self.pause(page)
        p = await page.get_by_text("Daniel Engvall", exact=True).all()
        await p[1].click()
        await self.pause(page)
        await self.scroll_to_bottom(page)
        all_rows = await page.get_by_text("Daniel Engvall", exact=True).all()
        await self.scroll_to_top(page)
        if self.limit_invoices:
            assert self.limit_invoices > 1, "Limit must be greater than 1"
            process_rows = all_rows[1 : self.limit_invoices]
        else:
            process_rows = all_rows[1:]
        for idx, r in enumerate(process_rows):
            logger.info(f"clicking on row {idx} of {len(all_rows)}")
            await r.click()
            await self.pause(page)
            all_pdf_buttons = await page.get_by_text("Visa PDF-faktura", exact=True).all()
            logger.info(
                f"Currently {len(all_pdf_buttons)} expanded, clicking on idx {idx}"
            )
            try:
                pdf_button = all_pdf_buttons[idx]
            except IndexError:
                logger.info(f"No more PDFs to download, exiting")
                break
            async with page.expect_download() as download_info:
                await pdf_button.scroll_into_view_if_needed()
                await pdf_button.click()
            download = download_info.value
            fn = self.download_path / f"{self.filename_prefix}{idx}.pdf"
            d = await download
            await d.save_as(fn.as_posix())
            await self.pause(page)
        logger.info("Done")
        await page.get_by_role("button", name="Öppna profil").click()
        await self.pause(page)
        await page.get_by_role("button", name="Logga ut").click()
        await self.pause(page)
        await page.close()

    async def close(self):
        await self.context.close()
        await self.browser.close()
