from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.contrib.syndication.views import Feed
from django.conf import settings
from django.views.generic.dates import YearArchiveView

from .models import Entry, Tag


def index(request):
    entries = Entry.objects.filter(
        is_draft=False, created__lte=timezone.now()
    ).order_by("-created")
    return render(request, "blog/index.html", {"entries": entries})


def entry(request, year, slug):
    entry = get_object_or_404(
        Entry,
        created__year=year,
        slug=slug,
    )
    return render(request, "blog/entry.html", {"entry": entry})


def year(request, year):
    entries = Entry.objects.filter(
        is_draft=False, created__year=year, created__lte=timezone.now()
    ).order_by("-created")
    return render(
        request,
        "blog/year.html",
        {
            "entries": entries,
            "year": year,
        },
    )


def archive(request):
    entries = Entry.objects.filter(
        is_draft=False, created__lte=timezone.now()
    ).order_by("-created")
    return render(request, "blog/archive.html", {"entries": entries})


def tag(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    entries = Entry.objects.filter(
        tags=tag, is_draft=False, created__lte=timezone.now()
    ).order_by("-created")
    return render(
        request,
        "blog/tag.html",
        {
            "entries": entries,
            "tag": tag,
        },
    )


class BlogFeed(Feed):
    title = "Blog Feed"
    link = "/blog/"
    description = "Latest blog entries"

    def items(self):
        return Entry.objects.filter(
            is_draft=False, created__lte=timezone.now()
        ).order_by("-created")[:10]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.summary_rendered

    def item_pubdate(self, item):
        return item.created
