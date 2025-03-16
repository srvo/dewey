from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("syzygy", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LLMTransaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("event_type", models.CharField(max_length=50)),
                ("metadata", models.JSONField(default=dict)),
                ("model_name", models.CharField(max_length=100)),
                ("prompt", models.TextField()),
                ("response", models.TextField()),
                ("input_tokens", models.IntegerField()),
                ("output_tokens", models.IntegerField()),
                ("cost", models.DecimalField(decimal_places=6, max_digits=10)),
                ("latency_ms", models.IntegerField()),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        null=True,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ToolUsage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("event_type", models.CharField(max_length=50)),
                ("metadata", models.JSONField(default=dict)),
                ("tool_name", models.CharField(max_length=100)),
                ("parameters", models.JSONField()),
                ("result", models.JSONField()),
                ("duration_ms", models.IntegerField()),
                ("success", models.BooleanField()),
                ("error_message", models.TextField(blank=True)),
                ("resource_usage", models.JSONField()),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        null=True,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE VIEW timeline_view AS
            SELECT
                created_at,
                'llm' AS event_type,
                user_id,
                model_name || ' interaction' AS description,
                jsonb_build_object(
                    'model', model_name,
                    'prompt', prompt,
                    'response', response,
                    'tokens', input_tokens + output_tokens,
                    'cost', cost,
                    'latency', latency_ms
                ) AS metadata
            FROM syzygy_llmtransaction

            UNION ALL

            SELECT
                created_at,
                'tool' AS event_type,
                user_id,
                tool_name || ' usage' AS description,
                jsonb_build_object(
                    'tool', tool_name,
                    'parameters', parameters,
                    'result', result,
                    'duration', duration_ms,
                    'success', success,
                    'error', error_message,
                    'resources', resource_usage
                ) AS metadata
            FROM syzygy_toolusage

            ORDER BY created_at DESC;
            """,
            reverse_sql="DROP VIEW IF EXISTS timeline_view;",
        ),
    ]
