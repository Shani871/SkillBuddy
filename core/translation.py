from modeltranslation.translator import register, TranslationOptions
from .models import NewsAndEvents


@register(NewsAndEvents)
class NewsAndEventsTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "summary",
        "content",
    )
    empty_values = None
