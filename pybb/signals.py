from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, post_delete, pre_save
from pybb.models import Post, Category, Topic, Forum, create_or_check_slug
from pybb.subscription import notify_topic_subscribers, notify_forum_subscribers
from pybb import util, defaults, compat
from pybb.permissions import perms


def topic_saved(instance, **kwargs):
    if kwargs['created']:
        notify_forum_subscribers(instance)

def post_saved(instance, **kwargs):
    # signal triggered by loaddata command, ignore
    if kwargs.get('raw', False):
        return

    if getattr(instance, '_post_saved_done', False):
        #Do not spam users when post is saved more than once in a same request.
        #For eg, when we parse attachments.
        return

    instance._post_saved_done = True
    if not defaults.PYBB_DISABLE_NOTIFICATIONS:
        notify_topic_subscribers(instance)

    if util.get_pybb_profile(instance.user).autosubscribe and \
        perms.may_subscribe_topic(instance.user, instance.topic):
        instance.topic.subscribers.add(instance.user)

    if kwargs['created']:
        profile = util.get_pybb_profile(instance.user)
        profile.post_count = instance.user.posts.count()
        profile.save()


def post_deleted(instance, **kwargs):
    Profile = util.get_pybb_profile_model()
    User = compat.get_user_model()
    try:
        profile = util.get_pybb_profile(instance.user)
    except (Profile.DoesNotExist, User.DoesNotExist) as e:
        #When we cascade delete an user, profile and posts are also deleted
        pass
    else:
        profile.post_count = instance.user.posts.count()
        profile.save()


def user_saved(instance, created, **kwargs):
    # signal triggered by loaddata command, ignore
    if kwargs.get('raw', False):
        return

    if not created:
        return

    try:
        add_post_permission = Permission.objects.get_by_natural_key('add_post', 'pybb', 'post')
        add_topic_permission = Permission.objects.get_by_natural_key('add_topic', 'pybb', 'topic')
    except (Permission.DoesNotExist, ContentType.DoesNotExist):
        return
    instance.user_permissions.add(add_post_permission, add_topic_permission)
    instance.save()

    if defaults.PYBB_PROFILE_RELATED_NAME:
        ModelProfile = util.get_pybb_profile_model()
        profile = ModelProfile()
        setattr(instance, defaults.PYBB_PROFILE_RELATED_NAME, profile)
        profile.save()


def get_save_slug(extra_field=None):
    '''
    Returns a function to add or make an instance's slug unique

    :param extra_field: field needed in case of a unique_together.
    '''
    if extra_field:
        def save_slug(**kwargs):
            extra_filters = {}
            extra_filters[extra_field] = getattr(kwargs.get('instance'), extra_field)
            kwargs['instance'].slug = create_or_check_slug(kwargs['instance'], kwargs['sender'], **extra_filters)
    else:
        def save_slug(**kwargs):
            kwargs['instance'].slug = create_or_check_slug(kwargs['instance'], kwargs['sender'])
    return save_slug

pre_save_category_slug = get_save_slug()
pre_save_forum_slug = get_save_slug('category')
pre_save_topic_slug = get_save_slug('forum')


def setup():
    pre_save.connect(pre_save_category_slug, sender=Category)
    pre_save.connect(pre_save_forum_slug, sender=Forum)
    pre_save.connect(pre_save_topic_slug, sender=Topic)
    post_save.connect(topic_saved, sender=Topic)
    post_save.connect(post_saved, sender=Post)
    post_delete.connect(post_deleted, sender=Post)
    if defaults.PYBB_AUTO_USER_PERMISSIONS:
        post_save.connect(user_saved, sender=compat.get_user_model())
