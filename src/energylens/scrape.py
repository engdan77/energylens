from pathlib import Path

from playwright.sync_api import Playwright, expect, sync_playwright
from .log import logger


class Scraper:
    def __init__(self, download_path: Path, login_secs: int = 20):
        """
        Initializes the instance for managing browser interactions and executing operations
        in the application environment. It configures browser instances, sets required URLs,
        and validates the provided download path.

        :param download_path: The path where downloads will be stored. Must be a valid path.
        :type download_path: Path
        :param login_secs: Timeout duration, in seconds, before 2FA expires.
        :type login_secs: int
        """
        self.login_secs = login_secs  # Timeout before 2FA expires
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.firefox.launch(headless=False)
        self.context = self.browser.new_context()
        self.login_url = "https://idp.jonkopingenergi.se/Account/BankID?returnUrl=%2Fconnect%2Fauthorize%2Fcallback%3Fclient_id%3Dweb-MinaSidor%26redirect_uri%3Dhttps%253A%252F%252Fminasidor.jonkopingenergi.se%252Fsignin-oidc%26response_type%3Dcode%26scope%3Dopenid%2520offline_access%26type%3Dprivate"
        self.my_account_url = "https://minasidor.jonkopingenergi.se/"
        self.download_path = download_path
        assert self.download_path.exists(), 'Download path does not exist'

    @staticmethod
    def scroll_to_bottom(page):
        """
        Scrolls to the bottom of a web page using keyboard interactions.

        This method simulates pressing the 'End' key to scroll incrementally down
        the page. The scrolling stops after reaching the maximum number of scrolls
        or when the required timeout completes for each scroll action.

        :param page: The page instance representing the browser tab or window.
        :type page: Any
        :return: None
        """
        _prev_height = -1
        _max_scrolls = 20
        _scroll_count = 0
        while _scroll_count < _max_scrolls:
            page.keyboard.down('End')
            page.wait_for_timeout(1000)
            _scroll_count += 1
            logger.info(f"scrolling to bottom - {_scroll_count / _max_scrolls:.0%}")

    @staticmethod
    def scroll_to_top(page):
        """
        Scrolls to the top of a webpage, ensuring complete scrolling up within a defined
        limit of attempts. If the limit is reached, the function stops further scrolling.

        :param page: The page object representing the current webpage to interact with.
        :type page: Page
        :return: None
        """
        _prev_height = -1
        _max_scrolls = 20
        _scroll_count = 0
        while _scroll_count < _max_scrolls:
            page.keyboard.down('Home')
            page.wait_for_timeout(1000)
            _scroll_count += 1
            logger.info(f"scrolling to top - {_scroll_count / _max_scrolls:.0%}")

    @staticmethod
    def pause(page, time_ms=1000):
        page.wait_for_timeout(time_ms)

    def download_all_invoices(self) -> None:
        """
        Downloads all invoices from the user's account after logging in and navigating through the webpage.
        This function manages the login using BankID authentication, navigates to the invoice page, downloads
        all available invoices in PDF format, and logs out upon completion.

        This function performs the following tasks:
        - Logs into the website using BankID QR code authentication.
        - Navigates to the "Fakturor" (Invoices) page within the user's account.
        - Downloads all available invoice PDFs iterating through the action buttons.
        - Closes the page after logging out of the user account.

        :param None
        :return: None
        """
        page = self.context.new_page()
        page.goto(self.login_url)
        expect(page.get_by_role("button", name="BankID logga BankID med QR-kod")).to_be_visible()
        page.get_by_role("button", name="BankID logga BankID med QR-kod").click()
        for time_elapsed in range(self.login_secs):
            logger.info(f"Waiting for you to login using BankID on your device - {self.login_secs - time_elapsed} seconds left ...")
            self.pause(page)
        page.goto(self.my_account_url)
        expect(page.get_by_role("link", name="Fakturor", exact=True)).to_be_visible()
        page.get_by_role("link", name="Fakturor", exact=True).click()
        self.pause(page, 10000)
        page.get_by_text('Daniel Engvall', exact=True).all()[1].click()
        self.pause(page)
        page.get_by_text('Daniel Engvall', exact=True).all()[1].click()
        self.pause(page)
        self.scroll_to_bottom(page)
        all_rows = page.get_by_text('Daniel Engvall', exact=True).all()
        self.scroll_to_top(page)
        for idx, r in enumerate(all_rows[1:]):
            logger.info(f"clicking on row {idx} of {len(all_rows)}")
            r.click()
            self.pause(page)
            all_pdf_buttons = page.get_by_text('Visa PDF-faktura', exact=True).all()
            logger.info(f'Currently {len(all_pdf_buttons)} expanded, clicking on idx {idx}')
            try:
                pdf_button = all_pdf_buttons[idx]
            except IndexError:
                logger.info(f'No more PDFs to download, exiting')
                break
            with page.expect_download() as download_info:
                pdf_button.scroll_into_view_if_needed()
                pdf_button.click()
            download = download_info.value
            fn = self.download_path / f"invoice_{idx}.pdf"
            download.save_as(fn.as_posix())
            self.pause(page)
        logger.info('Done')
        page.get_by_role("button", name="Öppna profil").click()
        self.pause(page)
        page.get_by_role("button", name="Logga ut").click()
        self.pause(page)
        page.close()

    def close(self):
        self.context.close()
        self.browser.close()



