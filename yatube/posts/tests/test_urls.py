from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.guest_client = Client()
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
        cache.clear()

    def test_urls_uses_correct_template(self):
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

    def test_urls_exists_at_desired_location_all_users(self):
        """Страницы доступны всем пользователям"""
        url = (
            reverse('posts:index'),
            reverse('posts:group_list', args={self.group.slug}),
            reverse('posts:profile', args={self.post.author}),
            reverse('posts:post_detail', args={self.post.id}),
        )
        for address in url:
            with self.subTest():
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_exists_at_desired_location_auth_users(self):
        """Страница create/ доступна авторизованному пользователю"""
        responce = self.authorized_client.get(reverse('posts:post_create'))
        self.assertEqual(responce.status_code, HTTPStatus.OK)

    def test_unexisting_page(self):
        """Запрос к несуществующей странице вернет ошибку 404"""
        responce = self.guest_client.get('/unexisting_page/')
        self.assertEqual(responce.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(responce, 'core/404.html')

    def test_post_edit_author(self):
        """Автор может редактировать свой пост"""
        auth = PostURLTests.authorized_client
        guest = PostURLTests.guest_client
        responce = auth.get(reverse('posts:post_edit',
                            kwargs={'post_id': self.post.pk}))
        responce2 = guest.get(reverse('posts:post_edit',
                              kwargs={'post_id': self.post.pk}))
        self.assertEqual(responce.status_code, HTTPStatus.OK)
        self.assertEqual(responce2.status_code, HTTPStatus.FOUND)
