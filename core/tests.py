from django.test import TestCase
from core.templatetags.kalmi_tags import smart_ellipsis, smart_ellipsis_words


class SmartEllipsisFilterTests(TestCase):
    def test_short_text_remains_unchanged(self):
        text = "Short text"
        result = smart_ellipsis(text, 20)
        self.assertEqual(result, "Short text")

    def test_long_text_truncated_with_ellipsis_structure(self):
        text = "Interactive Topic Practice (Instant Feedback)"
        result = smart_ellipsis(text, 20)
        self.assertIn('class="kalmi-smart-ellipsis', result)
        self.assertIn('data-full-text="Interactive Topic Practice (Instant Feedback)"', result)
        self.assertIn('data-short-text="Interactive Topic Pr…"', result)
        self.assertIn("Interactive Topic Pr…", result)
        self.assertIn("▾", result)

    def test_empty_and_none_text(self):
        self.assertEqual(smart_ellipsis(""), "")
        self.assertEqual(smart_ellipsis(None), "")

    def test_words_filter(self):
        text = "One two three four five six seven eight nine ten"
        result = smart_ellipsis_words(text, 5)
        self.assertIn('class="kalmi-smart-ellipsis', result)
        self.assertIn('data-short-text="One two three four five…"', result)

