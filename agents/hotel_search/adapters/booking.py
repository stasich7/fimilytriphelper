from __future__ import annotations

import os
import re
import shutil
import tempfile
import time
from html import unescape
from pathlib import Path
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from agents.hotel_search.adapters.base import AggregatorAdapter
from agents.hotel_search.errors import AdapterParsingError, AdapterUnavailableError
from agents.hotel_search.models import GuestConfig, HotelResult, ImageInfo, PriceInfo, RatingInfo, SearchRequest


class BookingAdapter(AggregatorAdapter):
    name = "booking"
    _CHROME_BINARY = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    _CHROMEDRIVER_CACHE_DIR = Path.home() / ".cache" / "selenium" / "chromedriver"
    _SEARCH_URL_TEMPLATE = (
        "https://www.booking.com/searchresults.en-gb.html?"
        "ss={query}&checkin={check_in}&checkout={check_out}&"
        "group_adults={adults}&group_children={children}&no_rooms={rooms}{child_age_params}"
    )

    def search(self, request: SearchRequest, area: str) -> list[HotelResult]:
        driver = self._build_driver()
        try:
            results: list[HotelResult] = []
            seen_urls: set[str] = set()
            for url in self._build_search_urls(request):
                driver.get(url)
                self._wait_for_results(driver)
                cards = self._find_result_cards(driver)
                for parsed in self._parse_cards(request, cards):
                    if parsed.source_url in seen_urls:
                        continue
                    seen_urls.add(parsed.source_url)
                    results.append(parsed)
            return results
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
            driver = webdriver.Chrome(
                service=ChromeService(executable_path=str(self._resolve_chromedriver_path())),
                options=options,
            )
        except WebDriverException as err:
            raise AdapterUnavailableError(
                "booking adapter could not start Chrome WebDriver."
            ) from err
        driver.set_page_load_timeout(60)
        driver.set_window_size(1440, 1200)
        return driver

    def _resolve_chromedriver_path(self) -> Path:
        env_path = os.getenv("CHROMEDRIVER_PATH", "").strip()
        if env_path:
            candidate = Path(env_path).expanduser()
            if candidate.exists():
                return candidate

        cached_versions = sorted(self._CHROMEDRIVER_CACHE_DIR.glob("*/*/chromedriver"))
        if cached_versions:
            return cached_versions[-1]

        discovered = shutil.which("chromedriver")
        if discovered:
            return Path(discovered)

        raise AdapterUnavailableError("booking adapter could not find a local chromedriver binary.")

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
        query = self._build_search_query(request, area)
        return self._SEARCH_URL_TEMPLATE.format(
            query=quote_plus(query),
            check_in=request.check_in.isoformat(),
            check_out=request.check_out.isoformat(),
            adults=request.guests.adults,
            children=request.guests.children,
            rooms=request.guests.rooms,
            child_age_params=self._build_child_age_params(request),
        )

    def _build_search_urls(self, request: SearchRequest) -> list[str]:
        base_url = self._build_search_url(request, request.trip_city)
        page_count = max(1, int(os.getenv("BOOKING_PAGE_COUNT", "6")))
        page_size = max(1, int(os.getenv("BOOKING_PAGE_SIZE", "25")))
        urls: list[str] = []
        for page_index in range(page_count):
            offset = page_index * page_size
            if offset <= 0:
                urls.append(base_url)
                continue
            urls.append(f"{base_url}&offset={offset}")
        return urls

    def _build_search_query(self, request: SearchRequest, area: str) -> str:
        return request.trip_city

    def _should_search_city(self, request: SearchRequest, area: str) -> bool:
        normalized = area.strip().lower()
        city = request.trip_city.strip().lower()
        if not normalized or normalized == city:
            return True
        return normalized in {"old batumi", "new boulevard"}

    def _build_child_age_params(self, request: SearchRequest) -> str:
        if not request.guests.child_guests:
            return ""
        return "".join(f"&age={child.age}" for child in request.guests.child_guests)

    def _wait_for_results(self, driver) -> None:
        time.sleep(6)
        wait = WebDriverWait(driver, 45)
        wait.until(
            lambda current_driver: len(
                current_driver.find_elements(By.XPATH, "//a[contains(@href, '/hotel/')]")
            ) > 10
        )

    def _find_result_cards(self, driver: webdriver.Safari) -> list:
        links = self._collect_hotel_links(driver)
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
            if len(cards) >= self._max_cards():
                break
        return cards

    def _collect_hotel_links(self, driver) -> list:
        rounds = int(os.getenv("BOOKING_SCROLL_ROUNDS", "12"))
        links: list = []
        for _ in range(max(1, rounds)):
            links = driver.find_elements(By.XPATH, "//a[contains(@href, '/hotel/')]")
            if len(links) >= self._max_cards():
                break
            driver.execute_script("window.scrollBy(0, Math.floor(window.innerHeight * 0.9));")
            time.sleep(1.2)
        driver.execute_script("window.scrollTo(0, 0);")
        return driver.find_elements(By.XPATH, "//a[contains(@href, '/hotel/')]")

    def _max_cards(self) -> int:
        return max(1, int(os.getenv("BOOKING_MAX_CARDS", "80")))

    def _find_card_container(self, link) -> object | None:
        xpath_candidates = [
            "./ancestor::*[.//a[contains(., 'See availability')]][1]",
            "./ancestor::*[.//a[contains(@href, '/hotel/')] and .//*[contains(text(), 'Price')]][1]",
            "./ancestor::*[.//*[contains(text(), 'See availability')]][1]",
            "./ancestor::*[@data-testid='property-card'][1]",
            "./ancestor::*[contains(@data-testid, 'property-card')][1]",
        ]
        for xpath in xpath_candidates:
            matches = link.find_elements(By.XPATH, xpath)
            if matches:
                return matches[0]
        return None

    def _parse_cards(self, request: SearchRequest, cards: list) -> list[HotelResult]:
        results: list[HotelResult] = []
        for card in cards:
            try:
                parsed = self._parse_card(request, request.trip_city, card)
            except AdapterParsingError:
                continue
            if parsed is not None:
                results.append(parsed)
        return results

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
            area=neighborhood or request.trip_city,
            city=request.trip_city,
            location_summary=location_summary,
            check_in=request.check_in,
            check_out=request.check_out,
            guests=GuestConfig(
                adults=request.guests.adults,
                children=request.guests.children,
                rooms=request.guests.rooms,
                child_guests=list(request.guests.child_guests),
                preferred_beds=request.guests.preferred_beds,
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
        images = card.find_elements(By.XPATH, ".//img")
        for image in images:
            src = self._best_image_attribute(image)
            if src and src.startswith("http"):
                return src
        return ""

    def _best_image_attribute(self, image) -> str:
        for attr in ["src", "currentSrc", "data-src", "data-lazy-src"]:
            value = (image.get_attribute(attr) or "").strip()
            if value:
                return value
        srcset = (image.get_attribute("srcset") or image.get_attribute("data-srcset") or "").strip()
        if not srcset:
            return ""
        return srcset.split(",")[0].strip().split(" ")[0]

    def _extract_location_summary(self, text: str, area: str) -> str:
        if area.lower() in text.lower():
            return area
        match = re.search(r"([0-9]+(?:\.[0-9]+)? km from centre)", text)
        if match:
            return match.group(1)
        return ""

    def _extract_neighborhood(self, text: str, area: str) -> str:
        markers = [
            "Sololaki",
            "Freedom Square",
            "Liberty Square",
            "Old Tbilisi",
            "Rustaveli",
            "Mtatsminda",
            "Old Batumi",
            "Old Boulevard",
            "New Boulevard",
            "Guests' favourite area",
            "Batumi",
            "Chakvi",
        ]
        for marker in markers:
            if marker.lower() in text.lower():
                return marker
        return ""

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
