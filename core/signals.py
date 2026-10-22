from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from curriculum.models import Subject, Topic, Subtopic
from questions.models import Question
from core.cache_utils import invalidate_all_curriculum_cache


@receiver([post_save, post_delete], sender=Subject)
@receiver([post_save, post_delete], sender=Topic)
@receiver([post_save, post_delete], sender=Subtopic)
@receiver([post_save, post_delete], sender=Question)
def handle_curriculum_or_question_change(sender, **kwargs):
    """
    Clears relevant Redis cache entries whenever syllabus, subjects, or questions are updated.
    """
    try:
        invalidate_all_curriculum_cache()
    except Exception:
        # Cache invalidation failure shouldn't abort DB transactions
        pass
