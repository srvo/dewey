class TimelineView(models.Model):
    """Database view for unified timeline with tight constraints."""

    created_at = models.DateTimeField()
    event_type = models.CharField(max_length=50)
    user_id = models.IntegerField(null=True)
    description = models.TextField()
    metadata = models.JSONField()

    class Meta:
        managed = False
        db_table = "timeline_view"
        constraints = [
            models.CheckConstraint(
                check=models.Q(user_id__isnull=False) | models.Q(event_type="system"),
                name="user_or_system_event",
            ),
        ]

    @classmethod
    def create_view(cls) -> None:
        """Create the database view."""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
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
            )


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("syzygy", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="llmtransaction",
            constraint=models.CheckConstraint(
                check=models.Q(input_tokens__gte=0),
                name="input_tokens_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="llmtransaction",
            constraint=models.CheckConstraint(
                check=models.Q(output_tokens__gte=0),
                name="output_tokens_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="llmtransaction",
            constraint=models.CheckConstraint(
                check=models.Q(cost__gte=0),
                name="cost_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="llmtransaction",
            constraint=models.CheckConstraint(
                check=models.Q(latency_ms__gte=0),
                name="latency_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="toolusage",
            constraint=models.CheckConstraint(
                check=models.Q(duration_ms__gte=0),
                name="duration_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="timelineview",
            constraint=models.CheckConstraint(
                check=models.Q(user_id__isnull=False) | models.Q(event_type="system"),
                name="user_or_system_event",
            ),
        ),
        migrations.RunSQL(
            """
            ALTER TABLE syzygy_llmtransaction
            ADD CONSTRAINT unique_llm_transaction
            UNIQUE (created_at, model_name, user_id);

            ALTER TABLE syzygy_toolusage
            ADD CONSTRAINT unique_tool_usage
            UNIQUE (created_at, tool_name, user_id);
            """,
        ),
    ]


from django.db import models
