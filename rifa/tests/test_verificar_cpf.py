from django.test import TestCase, Client
from django.contrib.auth.models import User
from rifa.models_profile import UserProfile

class VerificarCpfTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='t@example.com', password='pass')
        UserProfile.objects.create(user=self.user, cpf='111.111.111-11', nome_social='Teste', telefone='(65) 99999-9999')
        self.client = Client()

    def test_verificar_cpf_found(self):
        resp = self.client.post('/api/verificar-cpf/', {'cpf': '111.111.111-11'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('found'))
        self.assertIn('user', data)

    def test_verificar_cpf_not_found(self):
        resp = self.client.post('/api/verificar-cpf/', {'cpf': '000.000.000-00'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get('found'))
