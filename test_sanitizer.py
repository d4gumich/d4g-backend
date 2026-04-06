from sanitizer import get_sanitizer

test_text = """
John Doe
123 Main St, Ann Arbor, MI 48109
Phone: (734) 555-0123
Email: john.doe@example.com
Worked at Google for 5 years.
"""

print("Original Text:")
print(test_text)
print("-" * 20)

sanitizer = get_sanitizer()
sanitized = sanitizer.redact(test_text)

print("Sanitized Text:")
print(sanitized)

# Simple assertions
assert "[NAME]" in sanitized or "John" not in sanitized
assert "[EMAIL]" in sanitized
assert "[PHONE]" in sanitized
assert "[LOCATION]" in sanitized
print("\nTest Passed!")
