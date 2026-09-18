from django.test import TestCase
from django.urls import reverse


class ThemeSelectorTests(TestCase):
    def test_login_page_exposes_theme_selector_with_green_default(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-theme="green"')
        self.assertContains(response, 'id="theme-select"')
        self.assertContains(response, 'value="green"')
        self.assertContains(response, 'value="blue"')
        self.assertContains(response, 'value="purple"')
        self.assertContains(response, 'value="orange"')
        self.assertContains(response, "الأخضر الرسمي")
        self.assertContains(response, "الأزرق المهني")
        self.assertContains(response, "البنفسجي الحديث")
        self.assertContains(response, "البرتقالي الدافئ")
