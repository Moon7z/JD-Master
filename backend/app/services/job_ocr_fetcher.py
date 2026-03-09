from __future__ import annotations

import io

from app.schemas import JobInfo
from app.services.job_fetcher import JobFetcher


class JobOCRFetcher:
    @staticmethod
    async def fetch(url: str) -> JobInfo:
        """Use a real browser to view page like a human, then OCR screenshot text."""
        page_title, dom_text, screenshot_bytes = await JobOCRFetcher._browse(url)
        ocr_text = JobOCRFetcher._ocr_from_image(screenshot_bytes)
        merged_text = "\n".join(part for part in [dom_text, ocr_text] if part and part.strip())
        return JobFetcher.parse_text(url=url, text=merged_text, page_title=page_title)

    @staticmethod
    async def _browse(url: str) -> tuple[str, str, bytes]:
        try:
            from playwright.async_api import async_playwright
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("缺少 playwright 依赖，请安装后重试") from exc

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(locale="zh-CN")
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3000)

            title = await page.title()
            try:
                dom_text = await page.locator("body").inner_text(timeout=5000)
            except Exception:  # noqa: BLE001
                dom_text = ""

            screenshot_bytes = await page.screenshot(full_page=True)
            await browser.close()
            return title, dom_text, screenshot_bytes

    @staticmethod
    def _ocr_from_image(image_bytes: bytes) -> str:
        try:
            from PIL import Image
            import pytesseract
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("缺少 OCR 依赖（Pillow/pytesseract），请安装后重试") from exc

        image = Image.open(io.BytesIO(image_bytes))
        # chi_sim 依赖系统已安装 tesseract 中文语言包；若缺失自动回退英语。
        try:
            text = pytesseract.image_to_string(image, lang="chi_sim+eng")
        except Exception:  # noqa: BLE001
            text = pytesseract.image_to_string(image, lang="eng")
        return text
