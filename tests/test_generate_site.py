"""
Pytest test suite for generate_site.py

Tests all utility functions, rendering functions, and page generation.
"""

import json
import os
import sys
import tempfile
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import generate_site


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def clear_json_cache():
    """Clear the JSON cache before each test."""
    generate_site._JSON_CACHE.clear()
    yield
    generate_site._JSON_CACHE.clear()


@pytest.fixture
def temp_json_dir(tmp_path):
    """Create a temporary json directory with test data."""
    json_dir = tmp_path / "json"
    json_dir.mkdir()
    return json_dir


@pytest.fixture
def sample_home_json():
    """Sample home.json data."""
    return {
        "thumbnail": "https://example.com/thumb.jpg",
        "hero": "https://example.com/hero.jpg",
        "title": "Test\\nTitle",
        "description": "Test description",
        "email_octopus": {"id": "test-id", "cta": "Join Now"},
        "email": "test@example.com",
        "phone": "(555) 555-5555",
        "instagram": "https://instagram.com/test",
        "testimonials": [
            {
                "name": "John",
                "location": "Chicago",
                "text": "Great place!",
                "image": "https://example.com/john.jpg"
            }
        ]
    }


@pytest.fixture
def sample_events_json():
    """Sample events.json data."""
    # Use dates relative to today for testing upcoming/past filtering
    today = date.today()
    future_date = (today + timedelta(days=30)).strftime('%Y-%m-%d')
    past_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')

    return {
        "hero": "https://example.com/events-hero.jpg",
        "events": [
            {
                "name": "Future Workshop",
                "date": future_date,
                "time": "10am-12pm",
                "cost": "50",
                "instructor": "Jane Doe",
                "description": "A future event",
                "image": "https://example.com/future.jpg",
                "link": "https://book.stripe.com/test123",
                "technique": "handbuilding"
            },
            {
                "name": "Past Event",
                "date": past_date,
                "time": "6pm-9pm",
                "description": "A past event",
                "image": "https://example.com/past.jpg"
            },
            {
                "name": "Multi-Date Class",
                "dates": [future_date, (today + timedelta(days=37)).strftime('%Y-%m-%d')],
                "time": "2pm-5pm",
                "cost": "200",
                "instructor": "John Smith",
                "description": "A multi-session class",
                "image": "https://example.com/class.jpg",
                "link": "https://buy.stripe.com/class123"
            }
        ]
    }


@pytest.fixture
def sample_makers_json():
    """Sample makers.json data."""
    return {
        "hero": "https://example.com/makers-hero.jpg",
        "description": "Our makers are talented.",
        "cta": "Apply",
        "link": "mailto:test@example.com",
        "members": [
            {
                "name": "Artist One",
                "statement": "I make art.",
                "image": "https://example.com/artist1.jpg",
                "instagram": "https://instagram.com/artist1",
                "website": "https://artist1.com"
            },
            {
                "name": "Artist Two",
                "statement": "Clay is life.",
                "image": "https://example.com/artist2.jpg",
                "instagram": "https://instagram.com/artist2"
            }
        ],
        "visitors": [
            {
                "name": "Visiting Artist",
                "statement": "Visiting from afar.",
                "image": "https://example.com/visitor.jpg",
                "website": "https://visitor.com"
            }
        ]
    }


@pytest.fixture
def sample_shop_json():
    """Sample shop.json data."""
    return {
        "hero": "https://example.com/shop-hero.jpg",
        "pots": [
            {
                "title": "Cool Mug",
                "artist": "Test Artist",
                "media": "Stoneware",
                "firing": "Cone 10",
                "year": "2024",
                "cost": 50,
                "description": "A nice mug",
                "image": "https://example.com/mug.jpg",
                "link": "https://buy.stripe.com/mug123"
            }
        ],
        "merch": [
            {
                "title": "Sticker Pack",
                "artist": "Co-Op",
                "media": "Vinyl",
                "cost": 5,
                "description": "Stickers",
                "image": "https://example.com/stickers.jpg",
                "link": "https://buy.stripe.com/stickers"
            }
        ],
        "faqs": [
            {"title": "How to buy?", "description": "Click the button."},
            {"title": "Shipping?", "description": "We ship everywhere."}
        ]
    }


@pytest.fixture
def sample_about_json():
    """Sample about.json data."""
    return {
        "hero": "https://example.com/about-hero.jpg",
        "sections": [
            {
                "title": "Our Story",
                "description": "We started in 2025.",
                "image": "https://example.com/story.jpg"
            },
            {
                "title": "Our Mission",
                "description": "To spread clay love.",
                "cta": "Learn More",
                "link": "/about.html"
            }
        ]
    }


@pytest.fixture
def sample_visit_json():
    """Sample visit.json data."""
    return {
        "hero": "https://example.com/visit-hero.jpg",
        "sections": [
            {
                "title": "Address\\n123 Test St",
                "description": "Come visit us!",
                "image": "https://example.com/location.jpg",
                "cta": "Get Directions",
                "link": "https://maps.google.com"
            },
            {
                "title": "What to Bring",
                "icon": "fa-solid fa-bag",
                "lists": [
                    {
                        "title": "Required",
                        "icon": "fa-solid fa-check",
                        "items": ["Apron", "Towel"]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def setup_test_json(tmp_path, sample_home_json, sample_events_json, sample_makers_json,
                     sample_shop_json, sample_about_json, sample_visit_json):
    """Set up complete test JSON directory and change working directory."""
    original_dir = os.getcwd()

    # Create directory structure
    json_dir = tmp_path / "json"
    json_dir.mkdir()
    (tmp_path / "event").mkdir()
    (tmp_path / "maker").mkdir()
    (tmp_path / "shop").mkdir()

    # Write all JSON files
    with open(json_dir / "home.json", "w") as f:
        json.dump(sample_home_json, f)
    with open(json_dir / "events.json", "w") as f:
        json.dump(sample_events_json, f)
    with open(json_dir / "makers.json", "w") as f:
        json.dump(sample_makers_json, f)
    with open(json_dir / "shop.json", "w") as f:
        json.dump(sample_shop_json, f)
    with open(json_dir / "about.json", "w") as f:
        json.dump(sample_about_json, f)
    with open(json_dir / "visit.json", "w") as f:
        json.dump(sample_visit_json, f)

    os.chdir(tmp_path)

    yield tmp_path

    os.chdir(original_dir)


# =============================================================================
# Tests for Utility Functions
# =============================================================================

class TestSlugify:
    """Tests for the slugify function."""

    def test_basic_text(self):
        assert generate_site.slugify("Hello World") == "hello-world"

    def test_special_characters(self):
        assert generate_site.slugify("Test!@#$%^&*()Event") == "test-event"

    def test_multiple_spaces(self):
        assert generate_site.slugify("Multiple   Spaces   Here") == "multiple-spaces-here"

    def test_leading_trailing_hyphens(self):
        assert generate_site.slugify("---Test---") == "test"

    def test_numbers(self):
        assert generate_site.slugify("Event 2024") == "event-2024"

    def test_empty_string(self):
        assert generate_site.slugify("") == ""

    def test_only_special_chars(self):
        assert generate_site.slugify("!@#$%") == ""

    def test_unicode_characters(self):
        # Unicode gets stripped, only alphanumeric kept
        assert generate_site.slugify("Café Event") == "caf-event"


class TestFormatDate:
    """Tests for the format_date function."""

    def test_valid_date_long_format(self):
        result = generate_site.format_date("2025-06-15")
        assert "June" in result
        assert "15" in result
        assert "Sunday" in result

    def test_valid_date_short_format(self):
        result = generate_site.format_date("2025-06-15", short=True)
        assert "June" in result
        assert "15" in result
        assert "Sunday" not in result

    def test_invalid_date_returns_original(self):
        result = generate_site.format_date("not-a-date")
        assert result == "not-a-date"

    def test_empty_string(self):
        result = generate_site.format_date("")
        assert result == ""

    def test_wrong_format(self):
        result = generate_site.format_date("06/15/2025")
        assert result == "06/15/2025"


class TestIsPaymentLink:
    """Tests for the is_payment_link function."""

    def test_stripe_buy_link(self):
        assert generate_site.is_payment_link("https://buy.stripe.com/test123") is True

    def test_stripe_book_link(self):
        assert generate_site.is_payment_link("https://book.stripe.com/test123") is True

    def test_stripe_main_domain(self):
        assert generate_site.is_payment_link("https://stripe.com/checkout") is True

    def test_non_payment_link(self):
        assert generate_site.is_payment_link("https://example.com/event") is False

    def test_google_forms_link(self):
        assert generate_site.is_payment_link("https://docs.google.com/forms/test") is False

    def test_mailto_link(self):
        assert generate_site.is_payment_link("mailto:test@example.com") is False

    def test_invalid_url(self):
        assert generate_site.is_payment_link("not-a-url") is False

    def test_empty_string(self):
        assert generate_site.is_payment_link("") is False

    def test_custom_domains(self):
        assert generate_site.is_payment_link(
            "https://paypal.com/pay",
            domains=["paypal.com"]
        ) is True


class TestGetCtaText:
    """Tests for the get_cta_text function."""

    def test_payment_link_event(self):
        result = generate_site.get_cta_text("https://buy.stripe.com/test", event=True)
        assert result == "Register"

    def test_payment_link_non_event(self):
        result = generate_site.get_cta_text("https://buy.stripe.com/test", event=False)
        assert result == "Buy"

    def test_non_payment_link(self):
        result = generate_site.get_cta_text("https://example.com/info")
        assert result == "Learn More"

    def test_google_forms_link(self):
        result = generate_site.get_cta_text("https://docs.google.com/forms/test")
        assert result == "Learn More"


class TestGetEventDate:
    """Tests for the get_event_date function."""

    def test_single_date(self):
        event = {"date": "2025-06-15", "name": "Test"}
        result = generate_site.get_event_date(event)
        assert "June" in result
        assert "15" in result

    def test_multiple_dates(self):
        event = {
            "dates": ["2025-06-15", "2025-06-22", "2025-06-29"],
            "name": "Test Class"
        }
        result = generate_site.get_event_date(event)
        # Should show range from min to max date
        assert "–" in result  # en dash for range
        assert "June" in result


class TestGetEventCardData:
    """Tests for the get_event_card_data function."""

    def test_weekend_evening_workshop(self):
        event = {
            "date": "2025-06-14",  # Saturday
            "time": "6pm-9pm",
            "cost": "85",
            "name": "Test"
        }
        result = generate_site.get_event_card_data(event)
        assert 'data-day-type="weekend"' in result
        assert 'data-time-period="evening"' in result
        assert 'data-event-type="workshop"' in result

    def test_weekday_morning_free(self):
        event = {
            "date": "2025-06-16",  # Monday
            "time": "10am-12pm",
            "name": "Test"
        }
        result = generate_site.get_event_card_data(event)
        assert 'data-day-type="weekday"' in result
        assert 'data-time-period="morning"' in result
        assert 'data-event-type="free"' in result

    def test_afternoon_class(self):
        event = {
            "date": "2025-06-14",
            "time": "2pm-5pm",
            "cost": "200",
            "dates": ["2025-06-14", "2025-06-21"],
            "name": "Test"
        }
        result = generate_site.get_event_card_data(event)
        assert 'data-time-period="afternoon"' in result
        assert 'data-event-type="class"' in result

    def test_technique_attribute(self):
        event = {
            "date": "2025-06-14",
            "time": "10am-12pm",
            "technique": "handbuilding",
            "name": "Test"
        }
        result = generate_site.get_event_card_data(event)
        assert 'data-technique="handbuilding"' in result


# =============================================================================
# Tests for JSON Loading
# =============================================================================

class TestLoadJson:
    """Tests for the load_json function."""

    def test_load_valid_json(self, setup_test_json):
        result = generate_site.load_json("home.json")
        assert "thumbnail" in result
        assert "title" in result

    def test_caching(self, setup_test_json):
        # First load
        result1 = generate_site.load_json("home.json")
        # Modify cache to verify second load uses cache
        generate_site._JSON_CACHE["home.json"]["test_key"] = "test_value"
        # Second load should return cached version
        result2 = generate_site.load_json("home.json")
        assert result2.get("test_key") == "test_value"
        assert result1 is result2

    def test_file_not_found(self, setup_test_json):
        with pytest.raises(FileNotFoundError):
            generate_site.load_json("nonexistent.json")


# =============================================================================
# Tests for get_events Function
# =============================================================================

class TestGetEvents:
    """Tests for the get_events function."""

    def test_get_upcoming_events(self, setup_test_json):
        events = generate_site.get_events(upcoming=True, past=False)
        # Should only include future events
        today = date.today()
        for event in events:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
            assert event_date >= today

    def test_get_past_events(self, setup_test_json):
        events = generate_site.get_events(upcoming=False, past=True)
        # Should only include past events
        today = date.today()
        for event in events:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
            assert event_date < today

    def test_events_sorted_by_date(self, setup_test_json):
        events = generate_site.get_events(sort=True, upcoming=False, past=False)
        dates = [datetime.strptime(e['date'], '%Y-%m-%d') for e in events if 'date' in e]
        assert dates == sorted(dates)

    def test_expand_multi_date_events(self, setup_test_json):
        events_expanded = generate_site.get_events(expand=True, upcoming=False, past=False)
        events_collapsed = generate_site.get_events(expand=False, upcoming=False, past=False)
        # Expanded should have more events (multi-date events split)
        assert len(events_expanded) >= len(events_collapsed)


# =============================================================================
# Tests for Rendering Functions
# =============================================================================

class TestRenderHero:
    """Tests for the render_hero function."""

    def test_hero_with_image(self):
        result = generate_site.render_hero("Test Title", "https://example.com/hero.jpg")
        assert '<div class="hero">' in result
        assert '<h1>Test Title</h1>' in result
        assert 'src="https://example.com/hero.jpg"' in result

    def test_hero_without_image(self):
        result = generate_site.render_hero("Test Title")
        assert '<h1>Test Title</h1>' in result
        assert '<div class="hero">' not in result


class TestRenderDetailSection:
    """Tests for the render_detail_section function."""

    def test_basic_section(self):
        result = generate_site.render_detail_section(
            title="Test Section",
            description="Test description"
        )
        assert "page-details" in result
        assert "Test Section" in result
        assert "Test description" in result

    def test_section_with_icon(self):
        result = generate_site.render_detail_section(
            title="Test",
            icon="fa-solid fa-test"
        )
        assert 'class="fa-solid fa-test"' in result

    def test_section_with_image(self):
        result = generate_site.render_detail_section(
            title="Test",
            image="https://example.com/img.jpg"
        )
        assert 'src="https://example.com/img.jpg"' in result

    def test_section_with_iframe(self):
        result = generate_site.render_detail_section(
            title="Test",
            iframe="https://maps.google.com/embed"
        )
        assert '<iframe' in result
        assert 'src="https://maps.google.com/embed"' in result

    def test_section_with_cta(self):
        result = generate_site.render_detail_section(
            title="Test",
            link="https://example.com",
            cta_text="Click Here"
        )
        assert 'href="https://example.com"' in result
        assert 'Click Here' in result
        assert 'cta-btn' in result

    def test_reversed_section(self):
        result = generate_site.render_detail_section(
            title="Test",
            reverse=True
        )
        assert "page-details-reverse" in result

    def test_newline_in_title(self):
        result = generate_site.render_detail_section(
            title="Line1\\nLine2"
        )
        assert "<br>" in result


class TestRenderCollapsibleDetailSection:
    """Tests for the render_collapsible_detail_section function."""

    def test_collapsible_structure(self):
        result = generate_site.render_collapsible_detail_section(
            title="FAQ Item",
            description="Answer text"
        )
        assert '<details class="collapsible-section">' in result
        assert '<summary>' in result
        assert "FAQ Item" in result
        assert "Answer text" in result


class TestRenderDetailLists:
    """Tests for the render_detail_lists function."""

    def test_single_list(self):
        lists = [
            {
                "title": "Things",
                "icon": "fa-solid fa-list",
                "items": ["Item 1", "Item 2", "Item 3"]
            }
        ]
        result = generate_site.render_detail_lists(lists)
        assert "Things" in result
        assert "Item 1" in result
        assert "Item 2" in result
        assert "Item 3" in result
        assert "<li>" in result

    def test_multiple_lists(self):
        lists = [
            {"title": "List A", "icon": "fa-a", "items": ["A1"]},
            {"title": "List B", "icon": "fa-b", "items": ["B1"]}
        ]
        result = generate_site.render_detail_lists(lists)
        assert "List A" in result
        assert "List B" in result


class TestRenderShareSection:
    """Tests for the render_share_section function."""

    def test_share_section_content(self):
        result = generate_site.render_share_section("Cool Event", "cool-event-2025-01-01")
        assert 'class="share-section"' in result
        assert "sms:" in result
        assert "ccc.quest" in result
        assert "Share With A Friend" in result


class TestRenderMakerLinks:
    """Tests for the render_maker_links function."""

    def test_both_links(self):
        maker = {
            "instagram": "https://instagram.com/test",
            "website": "https://test.com"
        }
        result = generate_site.render_maker_links(maker)
        assert 'fa-brands fa-instagram' in result
        assert 'fa-solid fa-link' in result
        assert 'class="card-link half"' in result

    def test_instagram_only(self):
        maker = {"instagram": "https://instagram.com/test"}
        result = generate_site.render_maker_links(maker)
        assert 'fa-brands fa-instagram' in result
        assert 'class="card-link full"' in result

    def test_website_only(self):
        maker = {"website": "https://test.com"}
        result = generate_site.render_maker_links(maker)
        assert 'fa-solid fa-link' in result
        assert 'class="card-link full"' in result

    def test_no_links(self):
        maker = {"name": "Test"}
        result = generate_site.render_maker_links(maker)
        assert result == ""


class TestRenderEventCard:
    """Tests for the render_event_card function."""

    def test_event_card_structure(self):
        event = {
            "name": "Test Workshop",
            "date": "2025-06-14",
            "time": "10am-12pm",
            "cost": "50",
            "instructor": "Jane Doe",
            "image": "https://example.com/event.jpg",
            "link": "https://buy.stripe.com/test"
        }
        result = generate_site.render_event_card(event)
        assert 'class="card"' in result
        assert "Test Workshop" in result
        assert "w/ Jane Doe" in result
        assert "$50" in result
        assert "Register" in result  # Payment link CTA

    def test_event_card_with_callout(self):
        event = {
            "name": "New Event",
            "date": "2025-06-14",
            "time": "10am-12pm",
            "callout": "NEW"
        }
        result = generate_site.render_event_card(event)
        assert 'class="callout-bubble"' in result
        assert "NEW" in result


class TestRenderPotCard:
    """Tests for the render_pot_card function."""

    def test_pot_card_structure(self):
        pot = {
            "title": "Cool Mug",
            "artist": "Test Artist",
            "media": "Stoneware",
            "year": "2024",
            "cost": 50,
            "image": "https://example.com/mug.jpg",
            "link": "https://buy.stripe.com/mug"
        }
        result = generate_site.render_pot_card(pot)
        assert 'class="card"' in result
        assert "Cool Mug" in result
        assert "by Test Artist" in result
        assert "$50" in result
        assert "Buy" in result


class TestRenderMerchCard:
    """Tests for the render_merch_card function."""

    def test_merch_card_structure(self):
        merch = {
            "title": "Sticker",
            "artist": "Co-Op",
            "media": "Vinyl",
            "cost": 5,
            "image": "https://example.com/sticker.jpg",
            "link": "https://buy.stripe.com/sticker"
        }
        result = generate_site.render_merch_card(merch)
        assert 'class="card"' in result
        assert "Sticker" in result
        assert "$5" in result


# =============================================================================
# Tests for Header and Footer
# =============================================================================

class TestHeader:
    """Tests for the header function."""

    def test_header_structure(self, setup_test_json):
        result = generate_site.header("home")
        assert "<header>" in result
        assert '<nav class="desktop-nav">' in result
        assert '<details class="mobile-nav">' in result
        assert "hamburger-menu" in result

    def test_header_nav_links(self, setup_test_json):
        result = generate_site.header("home")
        assert 'href="/index.html"' in result
        assert 'href="/about.html"' in result
        assert 'href="/visit.html"' in result
        assert 'href="/events.html"' in result
        assert 'href="/makers.html"' in result

    def test_header_active_state(self, setup_test_json):
        result = generate_site.header("events")
        assert 'class="active"' in result


class TestFooter:
    """Tests for the footer function."""

    def test_footer_structure(self, setup_test_json):
        result = generate_site.footer()
        assert "<footer>" in result
        assert "footer-links" in result
        assert "footer-copy" in result

    def test_footer_social_links(self, setup_test_json):
        result = generate_site.footer()
        assert "fa-brands fa-instagram" in result
        assert "fa-regular fa-envelope" in result
        assert "fa-solid fa-phone" in result


# =============================================================================
# Tests for build_page_html
# =============================================================================

class TestBuildPageHtml:
    """Tests for the build_page_html function."""

    def test_page_structure(self, setup_test_json):
        result = generate_site.build_page_html(
            "Test Page",
            "<p>Content</p>",
            "home"
        )
        assert "<!DOCTYPE html>" in result
        assert "<html lang=\"en\">" in result
        assert "<title>Test Page</title>" in result
        assert "<main>" in result
        assert "<p>Content</p>" in result

    def test_page_includes_css(self, setup_test_json):
        result = generate_site.build_page_html("Test", "<p>Test</p>", "home")
        assert 'href="styles.css"' in result

    def test_page_custom_css_path(self, setup_test_json):
        result = generate_site.build_page_html(
            "Test", "<p>Test</p>", "event",
            css_path="../styles.css"
        )
        assert 'href="../styles.css"' in result

    def test_page_includes_font_awesome(self, setup_test_json):
        result = generate_site.build_page_html("Test", "<p>Test</p>", "home")
        assert "font-awesome" in result

    def test_scroll_script_on_events_page(self, setup_test_json):
        result = generate_site.build_page_html("Test", "<p>Test</p>", "events")
        assert "<script>" in result
        assert "page-nav" in result

    def test_no_scroll_script_on_home_page(self, setup_test_json):
        result = generate_site.build_page_html("Test", "<p>Test</p>", "home")
        # Home page shouldn't have the scroll script
        assert "requestAnimationFrame(updateNav)" not in result


# =============================================================================
# Tests for Page Rendering Functions
# =============================================================================

class TestRenderHome:
    """Tests for the render_home function."""

    def test_creates_index_html(self, setup_test_json):
        generate_site.render_home()
        assert (setup_test_json / "index.html").exists()

    def test_index_content(self, setup_test_json):
        generate_site.render_home()
        content = (setup_test_json / "index.html").read_text()
        assert "Chicago Clay Co-Op" in content
        assert "Upcoming Events" in content
        assert "email_octopus" in content or "Join Now" in content


class TestRenderAbout:
    """Tests for the render_about function."""

    def test_creates_about_html(self, setup_test_json):
        generate_site.render_about()
        assert (setup_test_json / "about.html").exists()

    def test_about_content(self, setup_test_json):
        generate_site.render_about()
        content = (setup_test_json / "about.html").read_text()
        assert "About" in content
        assert "Our Story" in content


class TestRenderVisit:
    """Tests for the render_visit function."""

    def test_creates_visit_html(self, setup_test_json):
        generate_site.render_visit()
        assert (setup_test_json / "visit.html").exists()

    def test_visit_content(self, setup_test_json):
        generate_site.render_visit()
        content = (setup_test_json / "visit.html").read_text()
        assert "Visit" in content


class TestRenderEvents:
    """Tests for the render_events function."""

    def test_creates_events_html(self, setup_test_json):
        generate_site.render_events()
        assert (setup_test_json / "events.html").exists()

    def test_creates_individual_event_pages(self, setup_test_json):
        generate_site.render_events()
        # Check that event directory has files
        event_dir = setup_test_json / "event"
        event_files = list(event_dir.glob("*.html"))
        assert len(event_files) > 0

    def test_events_grouped_by_month(self, setup_test_json):
        generate_site.render_events()
        content = (setup_test_json / "events.html").read_text()
        # Should have month headers
        assert 'class="page-header"' in content


class TestRenderMakers:
    """Tests for the render_makers function."""

    def test_creates_makers_html(self, setup_test_json):
        generate_site.render_makers()
        assert (setup_test_json / "makers.html").exists()

    def test_creates_individual_maker_pages(self, setup_test_json):
        generate_site.render_makers()
        maker_dir = setup_test_json / "maker"
        maker_files = list(maker_dir.glob("*.html"))
        assert len(maker_files) > 0

    def test_makers_content(self, setup_test_json):
        generate_site.render_makers()
        content = (setup_test_json / "makers.html").read_text()
        assert "Makers" in content
        assert "Members" in content or "Artist One" in content


class TestRenderShop:
    """Tests for the render_shop function."""

    def test_creates_shop_html(self, setup_test_json):
        generate_site.render_shop()
        assert (setup_test_json / "shop.html").exists()

    def test_creates_individual_item_pages(self, setup_test_json):
        generate_site.render_shop()
        shop_dir = setup_test_json / "shop"
        shop_files = list(shop_dir.glob("*.html"))
        assert len(shop_files) > 0

    def test_shop_content(self, setup_test_json):
        generate_site.render_shop()
        content = (setup_test_json / "shop.html").read_text()
        assert "Shop" in content
        assert "Pots" in content
        assert "Merch" in content
        assert "FAQs" in content


class TestRenderEvent:
    """Tests for the render_event function."""

    def test_event_page_structure(self, setup_test_json):
        event = {
            "name": "Test Event",
            "date": "2025-06-15",
            "time": "10am-12pm",
            "cost": "50",
            "instructor": "Jane Doe",
            "description": "A test event",
            "image": "https://example.com/event.jpg",
            "link": "https://buy.stripe.com/test"
        }
        generate_site.render_event(event)

        slug = f"{generate_site.slugify(event['name'])}-{event['date']}"
        page_path = setup_test_json / "event" / f"{slug}.html"
        assert page_path.exists()

        content = page_path.read_text()
        assert "Test Event" in content
        assert "with Jane Doe" in content
        assert "$50" in content


class TestRenderMaker:
    """Tests for the render_maker function."""

    def test_maker_page_structure(self, setup_test_json):
        maker = {
            "name": "Test Artist",
            "statement": "I make art.",
            "image": "https://example.com/artist.jpg",
            "instagram": "https://instagram.com/test",
            "website": "https://test.com"
        }
        generate_site.render_maker(maker)

        slug = generate_site.slugify(maker['name'])
        page_path = setup_test_json / "maker" / f"{slug}.html"
        assert page_path.exists()

        content = page_path.read_text()
        assert "Test Artist" in content
        assert "I make art." in content


class TestRenderPot:
    """Tests for the render_pot function."""

    def test_pot_page_structure(self, setup_test_json):
        pot = {
            "title": "Test Mug",
            "artist": "Test Artist",
            "media": "Stoneware",
            "firing": "Cone 10",
            "year": "2024",
            "cost": 75,
            "description": "A beautiful mug",
            "image": "https://example.com/mug.jpg",
            "link": "https://buy.stripe.com/mug"
        }
        generate_site.render_pot(pot)

        slug = generate_site.slugify(f"{pot['title']}-{pot['artist']}")
        page_path = setup_test_json / "shop" / f"{slug}.html"
        assert page_path.exists()

        content = page_path.read_text()
        assert "Test Mug" in content
        assert "by Test Artist" in content


class TestRenderMerch:
    """Tests for the render_merch function."""

    def test_merch_page_structure(self, setup_test_json):
        merch = {
            "title": "Test Sticker",
            "artist": "Co-Op",
            "media": "Vinyl",
            "cost": 5,
            "description": "Cool sticker",
            "image": "https://example.com/sticker.jpg",
            "link": "https://buy.stripe.com/sticker"
        }
        generate_site.render_merch(merch)

        slug = generate_site.slugify(f"{merch['title']}-{merch['artist']}")
        page_path = setup_test_json / "shop" / f"{slug}.html"
        assert page_path.exists()


# =============================================================================
# Tests for Main Function
# =============================================================================

class TestMain:
    """Tests for the main function."""

    def test_main_generates_all_pages(self, setup_test_json):
        generate_site.main()

        # Check all main pages exist
        assert (setup_test_json / "index.html").exists()
        assert (setup_test_json / "about.html").exists()
        assert (setup_test_json / "visit.html").exists()
        assert (setup_test_json / "events.html").exists()
        assert (setup_test_json / "makers.html").exists()
        assert (setup_test_json / "shop.html").exists()

        # Check subdirectories have content
        assert len(list((setup_test_json / "event").glob("*.html"))) > 0
        assert len(list((setup_test_json / "maker").glob("*.html"))) > 0
        assert len(list((setup_test_json / "shop").glob("*.html"))) > 0


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_event_without_cost(self, setup_test_json):
        event = {
            "name": "Free Event",
            "date": "2025-06-15",
            "time": "10am-12pm",
            "image": "https://example.com/event.jpg"
        }
        result = generate_site.render_event_card(event)
        # Should handle missing cost gracefully
        assert "Free Event" in result

    def test_event_without_instructor(self, setup_test_json):
        event = {
            "name": "Solo Event",
            "date": "2025-06-15",
            "time": "10am-12pm",
            "image": "https://example.com/event.jpg"
        }
        result = generate_site.render_event_card(event)
        assert "Solo Event" in result

    def test_pot_without_year(self, setup_test_json):
        pot = {
            "title": "Mystery Mug",
            "artist": "Unknown",
            "media": "Clay",
            "firing": "Unknown",
            "cost": 50,
            "description": "Old mug",
            "image": "https://example.com/mug.jpg"
        }
        generate_site.render_pot(pot)
        # Should not crash
        slug = generate_site.slugify(f"{pot['title']}-{pot['artist']}")
        assert (setup_test_json / "shop" / f"{slug}.html").exists()

    def test_maker_without_website(self, setup_test_json):
        maker = {
            "name": "Simple Artist",
            "statement": "Just art.",
            "image": "https://example.com/artist.jpg"
        }
        generate_site.render_maker(maker)
        slug = generate_site.slugify(maker['name'])
        assert (setup_test_json / "maker" / f"{slug}.html").exists()

    def test_empty_testimonials(self, setup_test_json, tmp_path):
        # Modify home.json to have no testimonials
        home_data = {
            "thumbnail": "https://example.com/thumb.jpg",
            "hero": "https://example.com/hero.jpg",
            "title": "Test",
            "description": "Test",
            "email_octopus": {"id": "", "cta": ""},
            "email": "test@example.com",
            "phone": "(555) 555-5555",
            "instagram": "https://instagram.com/test",
            "testimonials": []
        }
        with open(tmp_path / "json" / "home.json", "w") as f:
            json.dump(home_data, f)

        generate_site._JSON_CACHE.clear()
        generate_site.render_home()
        assert (setup_test_json / "index.html").exists()

    def test_event_with_missing_time(self, setup_test_json):
        event = {
            "name": "Timeless Event",
            "date": "2025-06-15",
            "image": "https://example.com/event.jpg"
        }
        # get_event_card_data should handle missing time
        result = generate_site.get_event_card_data(event)
        assert 'data-time-period="unknown"' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
