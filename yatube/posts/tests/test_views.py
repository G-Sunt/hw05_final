import shutil
import tempfile
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.urls import reverse
from django.core.cache import cache

from ..models import Post, Group, Comment
from ..views import NUM_OF_PAGE

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_author = User.objects.create_user(username='test_author')
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.test_author,
            group=cls.group,
            text='Тестовый пост',
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.test_author)
        cache.clear()

    def test_post_edit_author(self):
        """Проверил что успешно авторизировался"""
        responce = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(responce.status_code, HTTPStatus.OK)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    args={self.group.slug}): 'posts/group_list.html',
            reverse('posts:profile',
                    args={self.post.author}): 'posts/profile.html',
            reverse('posts:post_detail',
                    args={self.post.id}): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.pk}): 'posts/create_post.html'
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """View функции index, group_posts, profile сформированы
        с правильным контекстом."""
        response_list = (
            reverse('posts:index'),
            reverse('posts:group_list', args={self.group.slug}),
            reverse('posts:profile', args={self.test_author}),
        )
        for reverse_name in response_list:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                first_object = response.context['page_obj'][0]
                task_author_0 = first_object.author
                task_text_0 = first_object.text
                task_group_0 = first_object.group
                task_image_0 = first_object.image
                self.assertEqual(task_author_0, self.post.author)
                self.assertEqual(task_text_0, 'Тестовый пост')
                self.assertEqual(task_group_0, self.post.group)
                self.assertEqual(task_image_0, self.post.image)

    def test_post_detail_view_context_correct(self):
        """Проверяю корректность работы функции post_detail"""
        response = self.authorized_client.get(
            reverse('posts:post_detail', args={self.post.id})
        )
        self.assertEqual(response.context.get('post').group, self.post.group)
        self.assertEqual(response.context.get('post').text, self.post.text)

    def test_new_post_is_ok(self):
        """Проверяю что созданный пост попал в нужные списки"""
        self.new_group = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание2',
        )
        self.new_post = Post.objects.create(
            author=self.test_author,
            group=self.new_group,
            text='Тестовый пост2',
        )
        response_list = (
            reverse('posts:index'),
            reverse('posts:group_list', args={self.new_group.slug}),
            reverse('posts:profile', args={self.test_author}),
        )
        for reverse_name in response_list:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                first_object = response.context['page_obj'][0]
                self.assertEqual(first_object.author, self.post.author)
                self.assertEqual(first_object.text, 'Тестовый пост2')
                self.assertEqual(first_object.group, self.new_group)
                self.assertIsNot(first_object.group, self.group)

    def test_auth_client_add_comment(self):
        """Проверяю что добавляется комментарий авториз юзером"""
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Мессага'
        }
        responce = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text=form_data['text']
            ).exists
        )
        self.assertRedirects(
            responce, reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            )
        )

    def test_cache(self):
        """Проверяю корректность работы кэша"""
        post = Post.objects.create(
            author=self.test_author,
            text='Тестовый пост',
        )
        post_text_add = self.authorized_client.get(
            reverse('posts:index')).content
        post.delete()
        post_text_delete = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertEqual(post_text_add, post_text_delete)
        cache.clear()
        post_text_cache_clear = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertNotEqual(post_text_add, post_text_cache_clear)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user2 = User.objects.create_user(username='auth2')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group2 = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание2',
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        number_of_posts = 14
        for post_num in range(number_of_posts):
            Post.objects.create(
                author=cls.user,
                group=cls.group,
                text='Текст %s' % post_num,
            )
        cls.post = Post.objects.create(
            author=cls.user2,
            group=cls.group2,
            text='Тестовый пост',
        )

    def setUp(self):
        cache.clear()

    def test_group_list_show_correct_context(self):
        """Список постов group_list равен контексту"""
        responce = self.authorized_client.get(
            reverse('posts:group_list', args={self.group2.slug}),
        )
        expected = list(Post.objects.filter(group_id=self.group2.id)[:10])
        self.assertEqual(list(responce.context['page_obj']), expected)

    def test_profile_show_correct_context(self):
        """Список постов profile равен контексту"""
        responce = self.authorized_client.get(
            reverse('posts:profile', args={self.user2}),
        )
        expected = list(Post.objects.filter(author_id=self.user2.id)[:10])
        self.assertEqual(list(responce.context['page_obj']), expected)

    def test_context_paginator_index(self):
        """Проверяем что выводится заданное количество постов"""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), NUM_OF_PAGE)

    def test_second_page_contains_four_records(self):
        """Проверяем что на 2 странице 5 постов"""
        resp = self.authorized_client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(resp.context['page_obj']), 5)

    def test_context_paginator_views(self):
        """Проверка пагинатора через цикл трех функций"""
        resp_list = (
            reverse('posts:index'),
            reverse('posts:group_list', args={self.group.slug}),
            reverse('posts:profile', args={self.user})
        )
        for reverse_name in resp_list:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(
                    len(response.context['page_obj']), NUM_OF_PAGE)
