from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


@dataclass
class ChildGuest:
    age: int
    needs_own_bed: bool = True

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ChildGuest":
        return cls(
            age=int(value.get("age", 0)),
            needs_own_bed=bool(value.get("needs_own_bed", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "age": self.age,
            "needs_own_bed": self.needs_own_bed,
        }


@dataclass
class GuestConfig:
    adults: int
    children: int = 0
    rooms: int = 1
    child_guests: list[ChildGuest] = field(default_factory=list)
    preferred_beds: int | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GuestConfig":
        raw_children = value.get("children", 0)
        child_guests: list[ChildGuest] = []
        children_count = 0

        if isinstance(raw_children, list):
            child_guests = [
                ChildGuest.from_dict(dict(item))
                for item in raw_children
                if isinstance(item, dict)
            ]
            children_count = len(child_guests)
        else:
            children_count = int(raw_children or 0)

        preferred_beds = value.get("preferred_beds")
        return cls(
            adults=int(value.get("adults", 0)),
            children=children_count,
            rooms=int(value.get("rooms", 1)),
            child_guests=child_guests,
            preferred_beds=int(preferred_beds) if preferred_beds is not None else None,
        )

    def total_guests(self) -> int:
        return self.adults + self.children

    def own_beds_required(self) -> int:
        if self.preferred_beds is not None:
            return self.preferred_beds
        if self.child_guests:
            return self.adults + sum(1 for child in self.child_guests if child.needs_own_bed)
        return self.adults + self.children

    def to_dict(self) -> dict[str, Any]:
        children: int | list[dict[str, Any]]
        if self.child_guests:
            children = [child.to_dict() for child in self.child_guests]
        else:
            children = self.children
        return {
            "adults": self.adults,
            "children": children,
            "children_count": self.children,
            "rooms": self.rooms,
            "preferred_beds": self.preferred_beds,
            "own_beds_required": self.own_beds_required(),
        }


@dataclass
class TransportPreferences:
    prefer_public_transport: bool = True
    avoid_taxi_dependency: bool = True
    metro_nearby_bonus: bool = True
    max_walk_to_metro_minutes: int | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TransportPreferences":
        max_walk = value.get("max_walk_to_metro_minutes")
        return cls(
            prefer_public_transport=bool(value.get("prefer_public_transport", True)),
            avoid_taxi_dependency=bool(value.get("avoid_taxi_dependency", True)),
            metro_nearby_bonus=bool(value.get("metro_nearby_bonus", True)),
            max_walk_to_metro_minutes=int(max_walk) if max_walk is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "prefer_public_transport": self.prefer_public_transport,
            "avoid_taxi_dependency": self.avoid_taxi_dependency,
            "metro_nearby_bonus": self.metro_nearby_bonus,
            "max_walk_to_metro_minutes": self.max_walk_to_metro_minutes,
        }


@dataclass
class AreaProfile:
    name: str
    anchors: list[str] = field(default_factory=list)
    nearby_landmarks: list[str] = field(default_factory=list)
    transport_anchors: list[str] = field(default_factory=list)
    positive_terms: list[str] = field(default_factory=list)
    negative_terms: list[str] = field(default_factory=list)
    accommodation_mix: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AreaProfile":
        return cls(
            name=str(value.get("name", "")).strip(),
            anchors=_string_list(value.get("anchors", [])),
            nearby_landmarks=_string_list(value.get("nearby_landmarks", [])),
            transport_anchors=_string_list(value.get("transport_anchors", [])),
            positive_terms=_string_list(value.get("positive_terms", [])),
            negative_terms=_string_list(value.get("negative_terms", [])),
            accommodation_mix=_string_list(value.get("accommodation_mix", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "anchors": self.anchors,
            "nearby_landmarks": self.nearby_landmarks,
            "transport_anchors": self.transport_anchors,
            "positive_terms": self.positive_terms,
            "negative_terms": self.negative_terms,
            "accommodation_mix": self.accommodation_mix,
        }


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
    area_profiles: list[AreaProfile] = field(default_factory=list)
    transport_preferences: TransportPreferences = field(default_factory=TransportPreferences)
    accommodation_mix: list[str] = field(default_factory=lambda: ["hotel", "aparthotel", "private"])

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SearchRequest":
        areas = [str(item).strip() for item in value.get("areas", []) if str(item).strip()]
        aggregators = [str(item).strip() for item in value.get("aggregators", []) if str(item).strip()]
        required_amenities = [str(item).strip() for item in value.get("required_amenities", []) if str(item).strip()]
        area_profiles = [
            profile
            for profile in (
                AreaProfile.from_dict(dict(item))
                for item in value.get("area_profiles", [])
                if isinstance(item, dict)
            )
            if profile.name
        ]
        accommodation_mix = _string_list(value.get("accommodation_mix", ["hotel", "aparthotel", "private"]))
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
            area_profiles=area_profiles,
            transport_preferences=TransportPreferences.from_dict(dict(value.get("transport_preferences", {}))),
            accommodation_mix=accommodation_mix or ["hotel", "aparthotel", "private"],
        )
        if not request.area_profiles:
            request.area_profiles = [AreaProfile(name=area) for area in request.areas]
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
            "guests": self.guests.to_dict(),
            "price": {
                "min": self.price.min_amount,
                "max": self.price.max_amount,
                "currency": self.price.currency,
            },
            "required_amenities": self.required_amenities,
            "aggregators": self.aggregators,
            "max_results_per_area": self.max_results_per_area,
            "area_profiles": [profile.to_dict() for profile in self.area_profiles],
            "transport_preferences": self.transport_preferences.to_dict(),
            "accommodation_mix": self.accommodation_mix,
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
    original_total: float | None = None
    original_nightly: float | None = None
    original_currency: str = ""
    conversion_rate: float | None = None


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
    category: str = "unknown"
    sleeping_places: int | None = None
    area_fit_score: float = 0.0
    sleeping_fit_score: float = 0.0
    transport_score: float = 0.0
    category_score: float = 0.0
    risk_flags: list[str] = field(default_factory=list)
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
            "guests": self.guests.to_dict(),
            "availability_confirmed": self.availability_confirmed,
            "price": asdict(self.price),
            "room_option": self.room_option,
            "cancellation_terms": self.cancellation_terms,
            "rating": asdict(self.rating),
            "amenities": self.amenities,
            "features": self.features,
            "description": self.description,
            "images": [asdict(image) for image in self.images],
            "category": self.category,
            "sleeping_places": self.sleeping_places,
            "area_fit_score": self.area_fit_score,
            "sleeping_fit_score": self.sleeping_fit_score,
            "transport_score": self.transport_score,
            "category_score": self.category_score,
            "risk_flags": self.risk_flags,
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


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
