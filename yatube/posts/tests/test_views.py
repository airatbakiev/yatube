import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Follow, Group, Post

User = get_user_model()


class PostsPagesTests(TestCase):
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
        cls.second_group = Group.objects.create(
            title='Вторая тестовая группа',
            slug='second_test-slug',
            description='Описание второй группы',
        )
        cls.post_1 = Post.objects.create(
            author=cls.user,
            text='Пост_1 пользователя test_user',
            group=cls.group,
        )
        cls.post_2 = Post.objects.create(
            author=cls.user,
            text='Пост_2 пользователя test_user',
            group=cls.second_group,
        )
        cls.post_3 = Post.objects.create(
            author=cls.second_user,
            text='Пост_1 пользователя other_test_user',
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_posts_pages_template(self):
        '''По именам адресов posts открываются нужные шаблоны'''
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.user.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post_1.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post_1.id}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_context(self):
        '''По имени index отправлен правильный контекст'''
        response = self.authorized_client.get(reverse('posts:index'))
        post_list = response.context['page_obj']
        self.assertIn(self.post_1, post_list)
        post_from_response = post_list[post_list.index(self.post_1)]
        self.assertEqual(
            post_from_response.author.username, self.post_1.author.username
        )
        self.assertEqual(
            post_from_response.text, self.post_1.text
        )
        self.assertEqual(
            post_from_response.group.title, self.post_1.group.title
        )

    def test_group_list_context(self):
        '''По имени group_list отправлен правильный контекст'''
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        post_list = response.context['page_obj']
        for index in range(0, len(post_list)):
            with self.subTest(index=index):
                self.assertEqual(
                    post_list[index].group.title, self.group.title
                )
        self.assertEqual(
            response.context['group'].title, self.group.title
        )

    def test_profile_context(self):
        '''По имени profile отправлен правильный контекст'''
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        post_list = response.context['page_obj']
        for index in range(0, len(post_list)):
            with self.subTest(index=index):
                self.assertEqual(
                    post_list[index].author.username, self.user.username
                )
        self.assertEqual(
            response.context['username'].username, self.user.username
        )

    def test_post_detail_context(self):
        """По имени post_detail отправлен правильный контекст."""
        post = Post.objects.get(group=self.second_group)
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': post.id})
        )
        self.assertEqual(
            response.context['post'].author.username, self.user.username
        )
        self.assertEqual(
            response.context['post'].text, self.post_2.text
        )
        count = post.author.posts.count()
        self.assertEqual(response.context['count'], count)

    def test_create_context(self):
        '''По имени post_create отправлен правильный контекст'''
        response = self.authorized_client.get(
            reverse('posts:post_create')
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_context(self):
        '''По имени post_edit отправлен правильный контекст'''
        post_id = Post.objects.last().pk
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': post_id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        self.assertEqual(
            response.context['post'].author.username, self.user.username
        )
        self.assertEqual(
            response.context['post'].text, self.post_1.text
        )
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertTrue(response.context['is_edit'])

    def test_third_task(self):
        '''Появляется ли пост на нужных страницах'''
        page_names_in = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        page_names_not_in = [
            reverse(
                'posts:group_list', kwargs={'slug': self.second_group.slug}
            ),
            reverse(
                'posts:profile', kwargs={
                    'username': self.second_user.username
                }
            ),
        ]
        for reverse_name in page_names_in:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertIn(self.post_1, response.context['page_obj'])
        for reverse_name in page_names_not_in:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertNotIn(self.post_1, response.context['page_obj'])


class ViewsPaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        objs = (
            Post(
                author=cls.user,
                text='Тестовый пост',
                group=cls.group
            ) for i in range(16)
        )
        Post.objects.bulk_create(objs)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_index_paginator(self):
        '''По имени index пагинатор работает правильно'''
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), settings.QUANTITY)
        response = self.authorized_client.get(
            reverse('posts:index') + '?page=2'
        )
        second_page_count = Post.objects.count() - settings.QUANTITY
        self.assertEqual(len(response.context['page_obj']), second_page_count)

    def test_group_list_paginator(self):
        '''По имени group_list пагинатор работает правильно'''
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertEqual(len(response.context['page_obj']), settings.QUANTITY)
        response = self.authorized_client.get(
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ) + '?page=2'
        )
        second_page_count = Post.objects.filter(
            group=self.group
        ).count() - settings.QUANTITY
        self.assertEqual(len(response.context['page_obj']), second_page_count)

    def test_profile_paginator(self):
        '''По имени profile пагинатор работает правильно'''
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        self.assertEqual(len(response.context['page_obj']), settings.QUANTITY)
        response = self.authorized_client.get(
            reverse(
                'posts:profile', kwargs={'username': self.user.username}
            ) + '?page=2'
        )
        second_page_count = Post.objects.filter(
            author=self.user
        ).count() - settings.QUANTITY
        self.assertEqual(len(response.context['page_obj']), second_page_count)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ImageInContextTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_image_in_context(self):
        '''При создании через форму поста с картинкой в БД создаётся запись'''
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост',
            'group': self.group.pk,
            'image': uploaded,
        }
        # создаём единственную запись в БД
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                image='posts/small.gif'
            ).exists()
        )
        reverse_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        for reverse_name in reverse_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                post_list = response.context['page_obj']
                post_from_response = post_list[0]
                self.assertEqual(
                    post_from_response.image, 'posts/small.gif'
                )
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': '1'})
        )
        post_from_response = response.context['post']
        self.assertEqual(post_from_response.image, 'posts/small.gif')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_cache_index(self):
        '''По имени index выводится кеш'''
        # Смотрим на страницу перед созданием поста
        response1 = self.guest_client.get(reverse('posts:index'))
        content1 = response1.content
        # Создаём пост
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small3.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост',
            'group': self.group.pk,
            'image': uploaded,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Смотрим на страницу после создания поста
        response2 = self.guest_client.get(reverse('posts:index'))
        content2 = response2.content
        # Убеждаемся, что на странице ничего не изменилось
        self.assertEqual(content1, content2)
        # Чистим кэш
        cache.clear()
        # Смотрим на страницу после очистки кэша
        response3 = self.guest_client.get(reverse('posts:index'))
        content3 = response3.content
        self.assertNotEqual(content3, content2)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user_1')
        cls.second_user = User.objects.create_user(username='test_user_2')
        cls.third_user = User.objects.create_user(username='test_user_3')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.second_user)

    def test_authorized_client_can_follow(self):
        '''Авторизованный пользователь может подписаться'''
        # пользователь second_user подписывается на автора user
        count_start = Follow.objects.filter(user=self.second_user).count()
        self.authorized_client.get(
            reverse(
                'posts:profile_follow', kwargs={
                    'username': self.user.username
                }
            )
        )
        count_follow = Follow.objects.filter(user=self.second_user).count()
        self.assertEqual(count_start, count_follow - 1)

    def test_authorized_client_can_unfollow(self):
        '''Авторизованный пользователь может отписаться'''
        # теперь second_user подписывается на автора third_user
        Follow.objects.create(
            user=self.second_user,
            author=self.third_user
        )
        count_start = Follow.objects.filter(user=self.second_user).count()
        # second_user отписывается от third_user
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow', kwargs={
                    'username': self.third_user.username
                }
            )
        )
        count_follow = Follow.objects.filter(user=self.second_user).count()
        self.assertEqual(count_start, count_follow + 1)

    def test_follow_self_account(self):
        '''Авторизованный пользователь не может подписаться на себя'''
        # пользователь second_user пытается подписаться на себя
        count_start = Follow.objects.filter(user=self.second_user).count()
        self.authorized_client.get(
            reverse(
                'posts:profile_follow', kwargs={
                    'username': self.second_user.username
                }
            )
        )
        count_self = Follow.objects.filter(user=self.second_user).count()
        self.assertEqual(count_self, count_start)

    def test_post_output_on_follow_pages(self):
        '''Новый пост появляется в ленте подписчика'''
        # second_user подписывается на автора third_user
        self.authorized_client.get(
            reverse(
                'posts:profile_follow', kwargs={
                    'username': self.third_user.username
                }
            )
        )
        # авторизуется third_user и публикует пост
        self.authorized_client.force_login(self.third_user)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small4.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост third_user',
            'group': self.group.pk,
            'image': uploaded,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # авторизуется second_user (подписчик) и смотрит свою ленту
        self.authorized_client.force_login(self.second_user)
        follow_response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        post_list = follow_response.context['page_obj']
        self.assertEqual(post_list[0].text, form_data['text'])
        self.assertEqual(post_list[0].group.id, form_data['group'])
        self.assertEqual(post_list[0].image, 'posts/small4.gif')

    def test_post_not_exist_on_unfollow_pages(self):
        # авторизуется third_user и подписывается на user
        self.authorized_client.force_login(self.third_user)
        self.authorized_client.get(
            reverse(
                'posts:profile_follow', kwargs={
                    'username': self.user.username
                }
            )
        )
        # авторизуется user и публикует пост
        self.authorized_client.force_login(self.user)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small5.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост user',
            'group': self.group.pk,
            'image': uploaded,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # авторизуется second_user (не подписчик) и смотрит свою ленту
        self.authorized_client.force_login(self.second_user)
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        post_list = response.context['page_obj']
        self.assertEqual(len(post_list), 0)
