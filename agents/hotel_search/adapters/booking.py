from __future__ import annotations

import os
import re
import tempfile
import time
from html import unescape
from pathlib import Path
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from agents.hotel_search.adapters.base import AggregatorAdapter
from agents.hotel_search.errors import AdapterParsingError, AdapterUnavailableError
from agents.hotel_search.models import GuestConfig, HotelResult, ImageInfo, PriceInfo, RatingInfo, SearchRequest


class BookingAdapter(AggregatorAdapter):
    name = "booking"
    _CHROME_BINARY = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    _SEARCH_URL_TEMPLATE = (
        "https://www.booking.com/searchresults.en-gb.html?"
        "ss={query}&checkin={check_in}&checkout={check_out}&"
        "group_adults={adults}&group_children={children}&no_rooms={rooms}"
    )

    def search(self, request: SearchRequest, area: str) -> list[HotelResult]:
        driver = self._build_driver()
        try:
            url = self._build_search_url(request, area)
            driver.get(url)
            self._wait_for_results(driver)
            cards = self._find_result_cards(driver)
            return self._parse_cards(request, area, cards)
        except TimeoutException as err:
            raise AdapterUnavailableError(f"booking search page timeout for area {area}") from err
        finally:
            driver.quit()

    def _build_driver(self):
        browser = os.getenv("BOOKING_BROWSER", "").strip().lower()
        if browser == "safari":
            return self._build_safari_driver()
        if browser == "chrome":
            return self._build_chrome_driver()

        if self._CHROME_BINARY.exists():
            try:
                return self._build_chrome_driver()
            except AdapterUnavailableError:
                pass

        return self._build_safari_driver()

    def _build_chrome_driver(self) -> webdriver.Chrome:
        options = ChromeOptions()
        options.binary_location = str(self._CHROME_BINARY)
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--remote-debugging-pipe")
        options.add_argument("--disable-dev-shm-usage")
        profile_dir = tempfile.mkdtemp(prefix="familytriphelper-booking-chrome-", dir="/tmp")
        options.add_argument(f"--user-data-dir={profile_dir}")
        if os.getenv("BOOKING_HEADLESS", "").strip().lower() in {"1", "true", "yes"}:
            options.add_argument("--headless")
        options.page_load_strategy = "eager"

        try:
            driver = webdriver.Chrome(options=options)
        except WebDriverException as err:
            raise AdapterUnavailableError(
                "booking adapter could not start Chrome WebDriver."
            ) from err
        driver.set_page_load_timeout(60)
        driver.set_window_size(1440, 1200)
        return driver

    def _build_safari_driver(self) -> webdriver.Safari:
        try:
            driver = webdriver.Safari()
        except WebDriverException as err:
            raise AdapterUnavailableError(
                "booking adapter needs browser WebDriver. Chrome headless did not start, and Safari WebDriver is unavailable. Run `safaridriver --enable` and enable Remote Automation in Safari, or use installed Google Chrome."
            ) from err
        driver.set_page_load_timeout(60)
        return driver

    def _build_search_url(self, request: SearchRequest, area: str) -> str:
        _ = area
        query = request.trip_city
        return self._SEARCH_URL_TEMPLATE.format(
            query=quote_plus(query),
            check_in=request.check_in.isoformat(),
            check_out=request.check_out.isoformat(),
            adults=request.guests.adults,
            children=request.guests.children,
            rooms=request.guests.rooms,
        )

    def _wait_for_results(self, driver) -> None:
        time.sleep(8)
        wait = WebDriverWait(driver, 45)
        wait.until(
            lambda current_driver: len(
                current_driver.find_elements(By.XPATH, "//a[contains(@href, '/hotel/')]")
            ) > 20
        )

    def _find_result_cards(self, driver: webdriver.Safari) -> list:
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '/hotel/')]")
        seen: set[str] = set()
        cards: list = []
        for link in links:
            href = (link.get_attribute("href") or "").strip()
            if not href or href in seen:
                continue
            container = self._find_card_container(link)
            if container is None:
                continue
            seen.add(href)
            cards.append(container)
            if len(cards) >= 10:
                break
        return cards

    def _find_card_container(self, link) -> object | None:
        xpath_candidates = [
            "./ancestor::*[.//a[contains(., 'See availability')]][1]",
            "./ancestor::*[.//a[contains(@href, '/hotel/')] and .//*[contains(text(), 'Price')]][1]",
            "./ancestor::*[.//*[contains(text(), 'See availability')]][1]",
        ]
        for xpath in xpath_candidates:
            matches = link.find_elements(By.XPATH, xpath)
            if matches:
                return matches[0]
        return None

    def _parse_cards(self, request: SearchRequest, area: str, cards: list) -> list[HotelResult]:
        results: list[HotelResult] = []
        for card in cards:
            try:
                parsed = self._parse_card(request, area, card)
            except AdapterParsingError:
                continue
            if parsed is not None:
                results.append(parsed)
        filtered = [result for result in results if self._matches_area(area, result)]
        return filtered or results

    def _parse_card(self, request: SearchRequest, area: str, card) -> HotelResult | None:
        hotel_link = card.find_element(By.XPATH, ".//a[contains(@href, '/hotel/')]")
        source_url = (hotel_link.get_attribute("href") or "").strip()
        name = self._extract_hotel_name(hotel_link.text)
        if not name:
            raise AdapterParsingError("booking result card has empty hotel name")

        card_text = self._clean_multiline(card.text)
        price = self._extract_price(card_text)
        rating = self._extract_rating(card_text)
        features = self._extract_features(card_text)
        room_option = self._extract_room_option(card_text)
        image_url = self._extract_image(card)
        location_summary = self._extract_location_summary(card_text, area)
        neighborhood = self._extract_neighborhood(card_text, area)

        return HotelResult(
            dedupe_key="",
            name=name,
            aggregator=self.name,
            source_url=source_url,
            area=neighborhood or area,
            city=request.trip_city,
            location_summary=location_summary,
            check_in=request.check_in,
            check_out=request.check_out,
            guests=GuestConfig(
                adults=request.guests.adults,
                children=request.guests.children,
                rooms=request.guests.rooms,
            ),
            availability_confirmed="See availability" in card_text,
            price=price,
            room_option=room_option,
            cancellation_terms=self._extract_cancellation_terms(card_text),
            rating=rating,
            amenities=self._extract_amenities(card_text),
            features=features,
            description=card_text[:500],
            images=[ImageInfo(url=image_url, is_primary=True)] if image_url else [],
        )

    def _extract_hotel_name(self, raw_text: str) -> str:
        text = self._clean_text(raw_text)
        text = text.replace("Opens in new window", "").strip()
        return text

    def _extract_price(self, text: str) -> PriceInfo:
        match = re.search(r"Price\s+([A-Z]{3})?\s*([0-9][0-9,\.\s]*)", text)
        if not match:
            match = re.search(r"([A-Z]{3})\s*([0-9][0-9,\.\s]*)", text)

        currency = "USD"
        total = None
        if match:
            if match.group(1):
                currency = match.group(1).strip()
            total = self._parse_number(match.group(2))

        nightly = None
        if total is not None:
            nights = max((self._days_between(text)), 1)
            nightly = round(total / nights, 2)

        return PriceInfo(
            total=total,
            nightly=nightly,
            currency=currency,
            includes_taxes="Includes taxes and charges" in text,
        )

    def _extract_rating(self, text: str) -> RatingInfo:
        match = re.search(r"Scored\s+([0-9]+(?:\.[0-9]+)?)", text)
        reviews_match = re.search(r"([0-9][0-9,\.]*)\s+reviews", text)
        return RatingInfo(
            value=float(match.group(1)) if match else None,
            count=int(self._parse_number(reviews_match.group(1))) if reviews_match else None,
        )

    def _extract_room_option(self, text: str) -> str:
        candidates = [
            "Superior",
            "Apartment",
            "Suite",
            "Family",
            "Studio",
            "Room",
        ]
        lines = [self._clean_text(line) for line in text.splitlines()]
        for line in lines:
            if any(token in line for token in candidates):
                return line
        return ""

    def _extract_cancellation_terms(self, text: str) -> str:
        for marker in [
            "Free cancellation",
            "No prepayment needed",
            "Non-refundable",
        ]:
            if marker in text:
                return marker
        return ""

    def _extract_amenities(self, text: str) -> list[str]:
        known = [
            ("Free WiFi", "wifi"),
            ("Breakfast included", "breakfast"),
            ("Beachfront", "beachfront"),
            ("Swimming pool", "pool"),
            ("Parking", "parking"),
            ("Kitchen", "kitchen"),
            ("Fitness centre", "fitness"),
            ("24-hour front desk", "24h_front_desk"),
        ]
        found: list[str] = []
        for source, normalized in known:
            if source in text:
                found.append(normalized)
        return found

    def _extract_features(self, text: str) -> list[str]:
        features: list[str] = []
        for marker in [
            "Beachfront",
            "Breakfast included",
            "Free stay for both of your children",
            "Recommended for your group",
            "Private suite",
            "Sea view",
            "City View",
        ]:
            if marker in text:
                features.append(marker.lower())
        return features

    def _extract_image(self, card) -> str:
        images = card.find_elements(By.XPATH, ".//img[@src]")
        for image in images:
            src = (image.get_attribute("src") or "").strip()
            if src:
                return src
        return ""

    def _extract_location_summary(self, text: str, area: str) -> str:
        if area.lower() in text.lower():
            return area
        match = re.search(r"([0-9]+(?:\.[0-9]+)? km from centre)", text)
        if match:
            return match.group(1)
        return area

    def _extract_neighborhood(self, text: str, area: str) -> str:
        markers = [
            "Old Boulevard",
            "New Boulevard",
            "Guests' favourite area",
            "Batumi",
            "Chakvi",
        ]
        for marker in markers:
            if marker.lower() in text.lower():
                return marker
        return area

    def _matches_area(self, area: str, result: HotelResult) -> bool:
        haystack = " ".join(
            [
                result.area,
                result.location_summary,
                result.description,
                " ".join(result.features),
            ]
        ).lower()
        needles = self._area_aliases(area)
        return any(needle in haystack for needle in needles)

    def _area_aliases(self, area: str) -> list[str]:
        normalized = area.strip().lower()
        aliases = {
            "old batumi": ["old batumi", "old boulevard", "europe square", "piazza"],
            "chakvi": ["chakvi"],
            "new boulevard": ["new boulevard"],
        }
        return aliases.get(normalized, [normalized])

    def _days_between(self, text: str) -> int:
        match = re.search(r"([0-9]+)\s+nights", text)
        if not match:
            return 1
        return int(match.group(1))

    def _parse_number(self, value: str) -> float:
        normalized = value.replace(",", "").replace(" ", "").strip()
        return float(normalized)

    def _clean_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", unescape(value or "")).strip()

    def _clean_multiline(self, value: str) -> str:
        return "\n".join(self._clean_text(line) for line in value.splitlines() if self._clean_text(line))
