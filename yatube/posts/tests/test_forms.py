import shutil
import tempfile
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.urls import reverse
from django.core.cache import cache

from ..models import Post, Group

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormsTests(TestCase):
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
            content_type='image.gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.test_author,
            group=cls.group,
            text='Очередной тестовый пост1!!1',
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.test_author)
        cache.clear()

    def test_create_post(self):
        """Создается пост с правильной формой"""
        posts_count = Post.objects.count()
        self.uploaded.seek(0)
        form_data = {
            'group': self.group.id,
            'text': 'Очередной тестовый пост1!!1',
            'image': self.uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': str(self.test_author)}
        ))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.latest('pub_date')
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])
        self.assertIsNotNone(form_data['image'])

    def test_edit_post(self):
        """Идет перезапись поста с правильной формой"""
        self.group2 = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание2',
        )
        # тут интересно, не знаю как решить. Если я в форм дата эдит
        # добавляю 'group':self.group2.id то тест не проходит, потому что
        # название группы не соответсвует номеру. Если без id то в целом
        # получается что запись не валидна и он не переписывает форму.
        # ковырялся и не понял как передать именно наименование группы 2 :(
        form_data_edit = {
            'text': 'Ну сколько можно тестов уже'
        }
        self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}),
            data=form_data_edit,
            follow=True
        )
        response2 = self.authorized_client.get(reverse('posts:index'))
        first_object = response2.context['page_obj'][0]
        self.assertEqual(first_object.text,
                         form_data_edit.get('text'))
        self.assertEqual(first_object.group,
                         form_data_edit.get('group'))
