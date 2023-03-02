from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост345543',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        self.group = PostModelTest.group
        expected_object_name_group = self.group.title
        self.assertEqual(expected_object_name_group, str(self.group))

    def test_models_have_correct_object_names2(self):
        """Проверяем, что у моделей корректно работает __str__."""
        self.post = PostModelTest.post
        expected_object_name_post = self.post.text[:15]
        self.assertEqual(expected_object_name_post, str(self.post))
