"""Selenium smoke tests for the existing Python-served dashboard landing page."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as expected
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:
    webdriver = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@unittest.skipIf(webdriver is None, "Install requirements-dev.txt to run Selenium browser tests.")
class DashboardSeleniumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        python = os.environ.get("PYTHON", sys.executable)
        cls.server = subprocess.Popen(
            [python, str(PROJECT_ROOT / "server.py"), "--port", str(cls.port), "--skip-initial-refresh"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if cls.server.poll() is not None:
                raise RuntimeError("Dashboard server exited before becoming ready.")
            try:
                with urllib.request.urlopen(f"{cls.base_url}/api/health", timeout=1):
                    break
            except (OSError, urllib.error.URLError):
                time.sleep(0.2)
        else:
            cls.server.terminate()
            raise RuntimeError("Dashboard server health endpoint did not become ready.")

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,900")
        cls.driver = webdriver.Chrome(options=options)
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "driver", None):
            cls.driver.quit()
        if getattr(cls, "server", None) and cls.server.poll() is None:
            cls.server.terminate()
            cls.server.wait(timeout=5)

    def test_root_is_the_dashboard_and_has_live_status(self):
        self.driver.get(self.base_url + "/")
        self.assertEqual(self.driver.title, "Childhood Cancer Research Dashboard")
        self.wait.until(expected.visibility_of_element_located((By.ID, "main-content")))
        self.wait.until(lambda driver: driver.find_element(By.ID, "indexed-chunk-count").text != "—")
        self.assertIn("Childhood cancer", self.driver.find_element(By.ID, "page-title").text)

    def test_health_api_reports_ready(self):
        self.driver.get(self.base_url + "/api/health")
        payload = json.loads(self.driver.find_element(By.TAG_NAME, "body").text)
        self.assertTrue(payload["ok"])
        self.assertGreater(payload["indexed_chunks"], 0)

    def test_keyboard_skip_link_moves_to_main_content(self):
        self.driver.get(self.base_url + "/")
        self.driver.find_element(By.TAG_NAME, "body").send_keys("\ue00f")
        skip_link = self.driver.find_element(By.CLASS_NAME, "skip-link")
        self.assertEqual(skip_link.get_attribute("href"), self.base_url + "/#main-content")
        skip_link.send_keys("\ue007")
        self.assertEqual(self.driver.switch_to.active_element.get_attribute("id"), "main-content")

    def test_navigation_anchor_reaches_questions_section(self):
        self.driver.get(self.base_url + "/")
        self.driver.find_element(By.CSS_SELECTOR, '.nav a[href="#questions"]').click()
        self.assertEqual(self.driver.current_url, self.base_url + "/#questions")
        self.assertTrue(self.driver.find_element(By.ID, "questions").is_displayed())

    def test_treatment_guide_is_linked_and_carries_clinical_caveat(self):
        self.driver.get(self.base_url + "/")
        self.driver.find_element(By.LINK_TEXT, "Treatment plan guide").click()
        self.assertIn("treatment-plan.html", self.driver.current_url)
        self.assertIn("does not recommend a treatment", self.driver.page_source)


if __name__ == "__main__":
    unittest.main()