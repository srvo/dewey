# Generated by Django 5.1.5 on 2025-01-17 13:14

import markdownx.models
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("syzygy", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="responsedraft",
            name="context_notes",
            field=markdownx.models.MarkdownxField(
                blank=True,
                default="",
                help_text="Additional context or notes about this response in Markdown format.",
            ),
        ),
        migrations.AlterField(
            model_name="responsedraft",
            name="draft_content",
            field=markdownx.models.MarkdownxField(
                default="",
                help_text="Write your response in Markdown format. You can use the preview panel to see how it will look.",
            ),
        ),
    ]
