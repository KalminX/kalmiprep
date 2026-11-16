from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class AccountsTests(TestCase):
    def test_registration_and_authentication(self):
        reg_data = {
            "first_name": "Kalmin",
            "last_name": "X",
            "username": "kalmin_user",
            "email": "kalmin@example.com",
            "password": "Password123!",
            "target_exam": "UTME",
        }
        resp = self.client.post(reverse("accounts:register"), data=reg_data)
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username="kalmin_user")
        self.assertEqual(user.profile.target_exam, "UTME")

        login_res = self.client.post(reverse("accounts:login"), data={"username": "kalmin_user", "password": "Password123!"})
        self.assertEqual(login_res.status_code, 302)
        logout_res = self.client.get(reverse("accounts:logout"))
        self.assertEqual(logout_res.status_code, 302)

    def test_login_with_safe_next_url(self):
        User.objects.create_user(username="next_tester", password="Password123!")
        target_path = "/practice/setup/"
        login_res = self.client.post(
            f"{reverse('accounts:login')}?next={target_path}",
            data={"username": "next_tester", "password": "Password123!"}
        )
        self.assertEqual(login_res.status_code, 302)
        self.assertEqual(login_res.headers.get("Location"), target_path)

    def test_login_rejects_open_redirect(self):
        User.objects.create_user(username="safe_redirect_tester", password="Password123!")
        malicious_url = "https://malicious-external-site.com/steal"
        login_res = self.client.post(
            f"{reverse('accounts:login')}?next={malicious_url}",
            data={"username": "safe_redirect_tester", "password": "Password123!"}
        )
        self.assertEqual(login_res.status_code, 302)
        # Must fall back to dashboard, not the external url
        self.assertEqual(login_res.headers.get("Location"), reverse("progress:dashboard"))

    def test_htmx_login_and_logout_returns_hx_redirect(self):
        User.objects.create_user(username="htmx_tester", password="Password123!")
        login_res = self.client.post(
            reverse("accounts:login"),
            data={"username": "htmx_tester", "password": "Password123!"},
            HTTP_HX_REQUEST="true"
        )
        self.assertEqual(login_res.status_code, 200)
        self.assertEqual(login_res.headers.get("HX-Redirect"), reverse("progress:dashboard"))

        logout_res = self.client.post(
            reverse("accounts:logout"),
            HTTP_HX_REQUEST="true"
        )
        self.assertEqual(logout_res.status_code, 200)
        self.assertEqual(logout_res.headers.get("HX-Redirect"), reverse("core:landing"))
