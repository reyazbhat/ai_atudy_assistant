from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Note

class StudyAssistantTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')
        
        # Create a note for user1
        self.note1 = Note.objects.create(
            user=self.user1,
            title="User 1 Note",
            content="This is content for user 1 note.",
            summary="User 1 summary",
            mcqs="User 1 MCQs"
        )
        
        # Create a note for user2
        self.note2 = Note.objects.create(
            user=self.user2,
            title="User 2 Note",
            content="This is content for user 2 note.",
            summary="User 2 summary",
            mcqs="User 2 MCQs"
        )

    def test_signup_view(self):
        # GET request
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/signup.html')
        
        # POST request with correct form fields (UserCreationForm uses username, password1, password2)
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'password1': 'newpassword123',
            'password2': 'newpassword123'
        })
        self.assertEqual(response.status_code, 302)  # Should redirect to home
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_login_required_redirect(self):
        # Trying to access dashboard without login should redirect to login
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, '/login/?next=/')

    def test_dashboard_view(self):
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/home.html')
        
        # User 1 should see only their notes
        self.assertIn(self.note1, response.context['notes'])
        self.assertNotIn(self.note2, response.context['notes'])

    def test_note_detail_privacy(self):
        self.client.login(username='user1', password='password123')
        
        # User 1 accessing user 1 note -> 200 OK
        response = self.client.get(reverse('note_detail', args=[self.note1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/note_detail.html')
        
        # User 1 accessing user 2 note -> 404 NOT FOUND (privacy block)
        response = self.client.get(reverse('note_detail', args=[self.note2.id]))
        self.assertEqual(response.status_code, 404)
