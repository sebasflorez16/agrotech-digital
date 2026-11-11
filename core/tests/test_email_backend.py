from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase, override_settings

from core.email_backends import ResendEmailBackend


@override_settings(
    RESEND_API_KEY='re_test_key',
    DEFAULT_FROM_EMAIL='AgroTech Digital <noreply@agrotechcolombia.com>',
)
class ResendEmailBackendTest(SimpleTestCase):
    @patch('core.email_backends.requests.post')
    def test_sends_html_and_text(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = '{"id":"email_123"}'

        message = EmailMultiAlternatives(
            subject='Verifica tu cuenta',
            body='Texto plano',
            from_email='AgroTech Digital <noreply@agrotechcolombia.com>',
            to=['user@example.com'],
        )
        message.attach_alternative('<p>Hola</p>', 'text/html')

        sent = ResendEmailBackend().send_messages([message])

        self.assertEqual(sent, 1)
        payload = mock_post.call_args.kwargs['json']
        self.assertEqual(payload['to'], ['user@example.com'])
        self.assertEqual(payload['subject'], 'Verifica tu cuenta')
        self.assertEqual(payload['text'], 'Texto plano')
        self.assertEqual(payload['html'], '<p>Hola</p>')

    @override_settings(RESEND_API_KEY='')
    def test_without_key_raises(self):
        message = EmailMultiAlternatives(
            subject='Test', body='Test', to=['user@example.com']
        )
        with self.assertRaises(ImproperlyConfigured):
            ResendEmailBackend().send_messages([message])
