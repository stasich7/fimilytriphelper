from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


@dataclass
class GuestConfig:
    adults: int
    children: int = 0
    rooms: int = 1

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GuestConfig":
        return cls(
            adults=int(value.get("adults", 0)),
            children=int(value.get("children", 0)),
            rooms=int(value.get("rooms", 1)),
        )


@dataclass
class PriceRange:
    min_amount: float | None = None
    max_amount: float | None = None
    currency: str = "USD"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PriceRange":
        return cls(
            min_amount=_to_optional_float(value.get("min")),
            max_amount=_to_optional_float(value.get("max")),
            currency=str(value.get("currency", "USD")).strip().upper() or "USD",
        )


@dataclass
class SearchRequest:
    trip_city: str
    areas: list[str]
    check_in: date
    check_out: date
    guests: GuestConfig
    price: PriceRange
    required_amenities: list[str]
    aggregators: list[str]
    max_results_per_area: int = 5

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SearchRequest":
        areas = [str(item).strip() for item in value.get("areas", []) if str(item).strip()]
        aggregators = [str(item).strip() for item in value.get("aggregators", []) if str(item).strip()]
        required_amenities = [str(item).strip() for item in value.get("required_amenities", []) if str(item).strip()]
        request = cls(
            trip_city=str(value.get("trip_city", "")).strip(),
            areas=areas,
            check_in=date.fromisoformat(str(value.get("check_in", "")).strip()),
            check_out=date.fromisoformat(str(value.get("check_out", "")).strip()),
            guests=GuestConfig.from_dict(dict(value.get("guests", {}))),
            price=PriceRange.from_dict(dict(value.get("price", {}))),
            required_amenities=required_amenities,
            aggregators=aggregators,
            max_results_per_area=max(1, int(value.get("max_results_per_area", 5))),
        )
        request.validate()
        return request

    def validate(self) -> None:
        if not self.trip_city:
            raise ValueError("trip_city is required")
        if not self.areas:
            raise ValueError("areas must not be empty")
        if not self.aggregators:
            raise ValueError("aggregators must not be empty")
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be later than check_in")
        if self.guests.adults <= 0:
            raise ValueError("guests.adults must be greater than 0")
        if self.guests.rooms <= 0:
            raise ValueError("guests.rooms must be greater than 0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "trip_city": self.trip_city,
            "areas": self.areas,
            "check_in": self.check_in.isoformat(),
            "check_out": self.check_out.isoformat(),
            "guests": asdict(self.guests),
            "price": {
                "min": self.price.min_amount,
                "max": self.price.max_amount,
                "currency": self.price.currency,
            },
            "required_amenities": self.required_amenities,
            "aggregators": self.aggregators,
            "max_results_per_area": self.max_results_per_area,
        }


@dataclass
class ImageInfo:
    url: str
    is_primary: bool = False


@dataclass
class PriceInfo:
    total: float | None = None
    nightly: float | None = None
    currency: str = "USD"
    includes_taxes: bool | None = None


@dataclass
class RatingInfo:
    value: float | None = None
    count: int | None = None


@dataclass
class AlternateSource:
    aggregator: str
    source_url: str
    nightly_price: float | None = None
    total_price: float | None = None


@dataclass
class HotelResult:
    dedupe_key: str
    name: str
    aggregator: str
    source_url: str
    area: str
    city: str
    location_summary: str
    check_in: date
    check_out: date
    guests: GuestConfig
    availability_confirmed: bool
    price: PriceInfo = field(default_factory=PriceInfo)
    room_option: str = ""
    cancellation_terms: str = ""
    rating: RatingInfo = field(default_factory=RatingInfo)
    amenities: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    description: str = ""
    images: list[ImageInfo] = field(default_factory=list)
    score: float = 0.0
    alternate_sources: list[AlternateSource] = field(default_factory=list)

    def primary_image_url(self) -> str:
        for image in self.images:
            if image.is_primary and image.url:
                return image.url
        for image in self.images:
            if image.url:
                return image.url
        return ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "hotel_id": self.dedupe_key,
            "name": self.name,
            "aggregator": self.aggregator,
            "source_url": self.source_url,
            "area": self.area,
            "city": self.city,
            "location_summary": self.location_summary,
            "check_in": self.check_in.isoformat(),
            "check_out": self.check_out.isoformat(),
            "guests": asdict(self.guests),
            "availability_confirmed": self.availability_confirmed,
            "price": asdict(self.price),
            "room_option": self.room_option,
            "cancellation_terms": self.cancellation_terms,
            "rating": asdict(self.rating),
            "amenities": self.amenities,
            "features": self.features,
            "description": self.description,
            "images": [asdict(image) for image in self.images],
            "score": self.score,
            "alternate_sources": [asdict(item) for item in self.alternate_sources],
        }


@dataclass
class SearchJob:
    area: str
    aggregator: str


def _to_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
