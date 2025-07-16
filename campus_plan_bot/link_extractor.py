import re
from typing import NamedTuple

from campus_plan_bot.constants import Constants


class LinkExtractionResult(NamedTuple):
    """Data class for link extraction results."""

    answer: str
    link: str


def extract_link(text: str) -> LinkExtractionResult | None:
    """Extracts a Google Maps link from the given text.

    If a link is found, it returns a LinkExtractionResult with a
    predefined answer and the extracted link. Otherwise, it returns
    None.
    """
    # Regex to find a Google Maps URL
    match = re.search(
        r"(https://www\.google\.com/maps/dir/\?api=1&destination=[^ ]+)", text
    )

    if match:
        link = match.group(1)
        return LinkExtractionResult(
            answer=Constants.LINK_EXTRACTED_ANSWER + link, link=link
        )

    return None


if __name__ == "__main__":
    # Test cases
    test_text_with_link = "Hier ist der Link zur Navigation: https://www.google.com/maps/dir/?api=1&destination=49.011,8.415"
    test_text_without_link = "Das Gebäude befindet sich in der Karl-Wilhelm-Straße."
    test_text_with_link_and_more = "Klar, hier ist der Link: https://www.google.com/maps/dir/?api=1&destination=KIT und hier noch mehr Text."

    # Test 1: Link present
    result1 = extract_link(test_text_with_link)
    print(f"Test 1 Input: '{test_text_with_link}'")
    assert result1 is not None
    assert result1.answer == Constants.LINK_EXTRACTED_ANSWER
    assert (
        result1.link
        == "https://www.google.com/maps/dir/?api=1&destination=49.011,8.415"
    )
    print(f"Test 1 Result: {result1}")

    # Test 2: No link present
    result2 = extract_link(test_text_without_link)
    print(f"\nTest 2 Input: '{test_text_without_link}'")
    assert result2 is None
    print(f"Test 2 Result: {result2}")

    # Test 3: Link with surrounding text
    result3 = extract_link(test_text_with_link_and_more)
    print(f"\nTest 3 Input: '{test_text_with_link_and_more}'")
    assert result3 is not None
    assert result3.link == "https://www.google.com/maps/dir/?api=1&destination=KIT"
    print(f"Test 3 Result: {result3}")

    print("\nAll tests passed!")
