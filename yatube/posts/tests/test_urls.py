from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from posts.models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_homepage(self):
        '''Smoke-test стартовой страницы'''
        response = self.guest_client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_authorpage(self):
        '''Smoke-test страницы Об авторе'''
        response = self.guest_client.get('/about/author/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_techpage(self):
        '''Smoke-test страницы О технологиях'''
        response = self.guest_client.get('/about/tech/')
        self.assertEqual(response.status_code, HTTPStatus.OK)


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.second_user = User.objects.create_user(username='other_test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_templates(self):
        '''Проверка доступности и шаблонов адресов приложения Post'''
        urls_list = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
        }
        for address, template in urls_list.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_redirect_not_auth(self):
        '''Проверка переадресации неавторизованного пользователя'''
        create_path = '/create/'
        create_redir = '/auth/login/?next=/create/'
        edit_path = f'/posts/{self.post.id}/edit/'
        edit_redir = f'/auth/login/?next=/posts/{self.post.id}/edit/'
        urls_redirect = {
            create_path: create_redir,
            edit_path: edit_redir,
        }
        for address, redirect_address in urls_redirect.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(response, redirect_address)

    def test_url_redirect_not_author(self):
        '''Проверка переадресации при попытке редактирования не автором'''
        self.guest_client.force_login(self.second_user)
        response = self.guest_client.get(f'/posts/{self.post.id}/edit/')
        self.assertRedirects(response, f'/posts/{self.post.id}/')

    def test_404(self):
        '''Проверка выводимой ошибки при открытии несуществующей страницы'''
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
