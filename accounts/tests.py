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
