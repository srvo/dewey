from django.contrib import admin

from .models import Authorship, Entry, Tag


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ["title", "created", "is_draft"]
    list_filter = ["is_draft", "created"]
    search_fields = ["title", "summary", "body"]
    prepopulated_fields = {"slug": ["title"]}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Authorship)
class AuthorshipAdmin(admin.ModelAdmin):
    list_display = ["entry", "user", "order"]
    list_filter = ["user"]
    search_fields = ["entry__title", "user__username"]
