from playwright.sync_api import Playwright, expect, sync_playwright
from .log import logger


class Scraper:
    def __init__(self, login_secs: int = 30):
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

    def run(self) -> None:
        page = self.context.new_page()
        # page.goto("https://idp.jonkopingenergi.se/Account/BankID?returnUrl=%2Fconnect%2Fauthorize%2Fcallback%3Fclient_id%3Dweb-MinaSidor%26redirect_uri%3Dhttps%253A%252F%252Fminasidor.jonkopingenergi.se%252Fsignin-oidc%26response_type%3Dcode%26scope%3Dopenid%2520offline_access%26state%3Dc12c916190eb4d56b92003ac10be6318%26code_challenge%3D6UYUzudewlsAPQIcu2mcs4Hu3iDe-cNNXbmgkbaVOAk%26code_challenge_method%3DS256%26type%3Dprivate")
        page.goto("https://idp.jonkopingenergi.se/Account/BankID?returnUrl=%2Fconnect%2Fauthorize%2Fcallback%3Fclient_id%3Dweb-MinaSidor%26redirect_uri%3Dhttps%253A%252F%252Fminasidor.jonkopingenergi.se%252Fsignin-oidc%26response_type%3Dcode%26scope%3Dopenid%2520offline_access%26type%3Dprivate")
        expect(page.get_by_role("button", name="BankID logga BankID med QR-kod")).to_be_visible()
        page.get_by_role("button", name="BankID logga BankID med QR-kod").click()
        for time_elapsed in range(self.login_secs):
            logger.info(f"Waiting for you to login using BankID on your device - {self.login_secs - time_elapsed} seconds left ...")
            page.wait_for_timeout(1000)
        page.goto("https://minasidor.jonkopingenergi.se/")
        expect(page.get_by_role("link", name="Fakturor", exact=True)).to_be_visible()
        page.get_by_role("link", name="Fakturor", exact=True).click()
        page.wait_for_timeout(2000)
        self.scroll_to_bottom(page)
        for idx, month in enumerate(['juni', 'maj']):
            page.get_by_role("button", name=f"{month} 2025").click()
            page.wait_for_timeout(2000)
            with page.expect_download() as download_info:
                page.get_by_role("button", name="Visa PDF-faktura").nth(idx).click()
            download = download_info.value
            download.save_as(f"/Users/edo/Downloads/faktura_{month}.pdf")
            page.wait_for_timeout(2000)
        logger.info('Done')

        page.get_by_role("button", name="Öppna profil").click()
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Logga ut").click()
        page.wait_for_timeout(1000)
        page.close()

    def close(self):
        self.context.close()
        self.browser.close()



