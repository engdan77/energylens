from playwright.sync_api import Playwright, expect, sync_playwright
from .log import logger


class Scraper:
    def __init__(self, login_secs: int = 20):
        self.login_secs = login_secs
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.firefox.launch(headless=False)
        self.context = self.browser.new_context()

    @staticmethod
    def scroll_to_bottom(page):
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

    def run(self) -> None:
        page = self.context.new_page()
        # page.goto("https://idp.jonkopingenergi.se/Account/BankID?returnUrl=%2Fconnect%2Fauthorize%2Fcallback%3Fclient_id%3Dweb-MinaSidor%26redirect_uri%3Dhttps%253A%252F%252Fminasidor.jonkopingenergi.se%252Fsignin-oidc%26response_type%3Dcode%26scope%3Dopenid%2520offline_access%26state%3Dc12c916190eb4d56b92003ac10be6318%26code_challenge%3D6UYUzudewlsAPQIcu2mcs4Hu3iDe-cNNXbmgkbaVOAk%26code_challenge_method%3DS256%26type%3Dprivate")
        page.goto("https://idp.jonkopingenergi.se/Account/BankID?returnUrl=%2Fconnect%2Fauthorize%2Fcallback%3Fclient_id%3Dweb-MinaSidor%26redirect_uri%3Dhttps%253A%252F%252Fminasidor.jonkopingenergi.se%252Fsignin-oidc%26response_type%3Dcode%26scope%3Dopenid%2520offline_access%26type%3Dprivate")
        expect(page.get_by_role("button", name="BankID logga BankID med QR-kod")).to_be_visible()
        page.get_by_role("button", name="BankID logga BankID med QR-kod").click()
        for time_elapsed in range(self.login_secs):
            logger.info(f"Waiting for you to login using BankID on your device - {self.login_secs - time_elapsed} seconds left ...")
            self.pause(page)
        page.goto("https://minasidor.jonkopingenergi.se/")
        expect(page.get_by_role("link", name="Fakturor", exact=True)).to_be_visible()
        page.get_by_role("link", name="Fakturor", exact=True).click()
        self.pause(page, 10000)
        page.get_by_text('Daniel Engvall', exact=True).all()[1].click()
        self.pause(page)
        self.scroll_to_bottom(page)
        all_rows = page.get_by_text('Daniel Engvall', exact=True).all()
        self.scroll_to_top(page)
        for idx, r in enumerate(all_rows[2:]):
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
            download.save_as(f"/Users/edo/Downloads/faktura_{idx}.pdf")
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



