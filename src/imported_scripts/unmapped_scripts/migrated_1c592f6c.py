from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("syzygy", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            """
            DROP TABLE IF EXISTS syzygy_client;
            DROP TABLE IF EXISTS syzygy_transcript;
            DROP TABLE IF EXISTS syzygy_transcriptanalysis;
            DROP TABLE IF EXISTS syzygy_activity;
            """,
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
                ) AS metadata,
                0 AS importance_level,
                '[]'::jsonb AS related_objects
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
                ) AS metadata,
                0 AS importance_level,
                '[]'::jsonb AS related_objects
            FROM syzygy_toolusage

            ORDER BY created_at DESC;
            """,
        ),
    ]
