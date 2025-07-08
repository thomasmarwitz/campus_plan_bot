import sys
from pathlib import Path

# Add project root to path to allow imports
sys.path.append(str(Path(__file__).resolve().parents[1]))

from campus_plan_bot.query_rewriter import QuestionRephraser
from campus_plan_bot.interfaces.persistence_types import Conversation, Message, Role


def run_test_case(name: str, messages: list[Message]):
    """Runs a single test case for query rephrasing."""
    print(f"--- Running Test Case: {name} ---")

    conversation = Conversation.new()
    for msg in messages:
        conversation.add_message(msg)

    print("Original Conversation:")
    for msg in conversation.messages:
        print(f"  {msg.role.value}: {msg.content}")

    rephraser = QuestionRephraser()
    rephrased_query = rephraser.rephrase(conversation)

    print(f"\nRephrased Query:\n{rephrased_query}\n")


def main():
    """Main function to run all test cases."""
    # Test Case 1: Cafeteria location and type
    cafeteria_messages = [
        Message.from_content("Ich suche die Cafeteria.", Role.USER),
        Message.from_content(
            "Die Cafeteria befindet sich am Adenauerring.",
            Role.ASSISTANT,
        ),
        Message.from_content("Wann hat sie morgen auf?", Role.USER),
    ]
    run_test_case("Cafeteria Location", cafeteria_messages)

    # Test Case 2: Library opening hours on a specific day
    library_messages = [
        Message.from_content(
            "Wie sind die Öffnungszeiten der KIT-Bibliothek?",
            Role.USER,
        ),
        Message.from_content(
            "Die KIT-Bibliothek hat unter der Woche von 8 bis 22 Uhr geöffnet. An Wochenenden und Feiertagen gelten andere Zeiten.",
            Role.ASSISTANT,
        ),
        Message.from_content("Und was ist mit nächstem Montag?", Role.USER),
    ]
    run_test_case("Library Opening Hours", library_messages)


if __name__ == "__main__":
    main() 