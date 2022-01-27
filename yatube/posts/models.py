from django.contrib.auth import get_user_model
from django.db import models


class Group(models.Model):
    title = models.CharField('Название группы', max_length=200)
    slug = models.SlugField('Уникальный URL', unique=True)
    description = models.TextField('Описание группы')

    def __str__(self):
        return self.title


User = get_user_model()


class Post(models.Model):
    text = models.TextField('Текст поста')
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)
    group = models.ForeignKey(
        Group,
        verbose_name='Сообщество',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='posts'
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='posts'
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ['-pub_date']
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self) -> str:
        return self.text[:15]


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        verbose_name='Комментируемый пост',
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор комментария',
        on_delete=models.CASCADE,
        related_name='comments'
    )
    text = models.TextField('Текст комментария')
    created = models.DateTimeField('Дата комментария', auto_now_add=True)

    class Meta:
        ordering = ['-created']
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    def __str__(self) -> str:
        return self.text[:15]


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Подписчик',
        on_delete=models.CASCADE,
        related_name='follower'
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='following'
    )
    
    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
