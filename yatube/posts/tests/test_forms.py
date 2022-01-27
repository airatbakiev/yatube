from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, Comment

User = get_user_model()


class PostsFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Пост_1 пользователя test_user',
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        '''Создаётся ли в БД пост'''
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост',
            'group': self.group.pk
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        new_post = Post.objects.first()
        self.assertEqual(new_post.text, form_data['text'])
        self.assertEqual(new_post.group.pk, form_data['group'])
        self.assertEqual(new_post.author, self.user)

    def test_change_post_in_db_after_edit(self):
        '''После редактирования и отправки формы пост изменяется в БД'''
        form_data = {
            'text': 'Новый тестовый пост',
            'group': self.group.pk
        }
        self.authorized_client.post(
            reverse('posts:post_edit', args=(str(self.post.id))),
            data=form_data,
            follow=True
        )
        self.assertTrue(
            Post.objects.filter(text=form_data['text']).exists()
        )

    def test_guest_client_not_create_and_redirect(self):
        '''Постить может только авторизованный'''
        posts_count = Post.objects.count()
        create_redirect = (f'{reverse("users:login")}?next='
                           f'{reverse("posts:post_create")}')
        form_data = {
            'text': 'Тестовый пост guest_client'
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, create_redirect)
        self.assertEqual(Post.objects.count(), posts_count)


class CommentsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Пост_1 пользователя test_user',
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            author=cls.user,
            post = cls.post,
            text='Тестовый комментарий'
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_comments_from_guest_client(self):
        '''Комментировать может только авторизованный'''
        comments_count = Comment.objects.count()
        add_comment_redirect = (
            f'{reverse("users:login")}?next='
            f'{reverse("posts:add_comment", kwargs={"post_id": self.post.id})}'
        )
        form_data = {
            'text': 'Тестовый комментарий guest_client'
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, add_comment_redirect)
        self.assertEqual(Comment.objects.count(), comments_count)
    
    def test_comment_output_on_page(self):
        '''Созданный комментарий появляется на странице поста'''
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertIn(self.comment, response.context['comments'])
