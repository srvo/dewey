from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0008_email_is_deleted"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contact",
            name="additional_emails",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="contact",
            name="contact_metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="enrichmenttask",
            name="result",
            field=models.JSONField(blank=True, help_text="Task result data", null=True),
        ),
        migrations.AlterField(
            model_name="enrichmenttask",
            name="extra_data",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Additional task context",
            ),
        ),
        migrations.AlterField(
            model_name="email",
            name="to_emails",
            field=models.JSONField(default=list),
        ),
        migrations.AlterField(
            model_name="email",
            name="cc_emails",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="email",
            name="bcc_emails",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="email",
            name="labels",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="email",
            name="email_metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="rawemail",
            name="raw_data",
            field=models.JSONField(),
        ),
        migrations.AlterField(
            model_name="eventlog",
            name="details",
            field=models.JSONField(default=dict),
        ),
    ]
