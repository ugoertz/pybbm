# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('pybb', '0005_auto_20151108_1528'),
    ]

    operations = [
        migrations.AlterField(
            model_name='forum',
            name='moderators',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name='Moderators', blank=True),
        ),
    ]
