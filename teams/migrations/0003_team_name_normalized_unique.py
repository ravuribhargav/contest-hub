import re
from django.db import migrations, models


def _normalize(name):
    return re.sub(r'\s+', ' ', (name or '').strip()).lower()


def populate_name_normalized(apps, schema_editor):
    Team = apps.get_model('teams', 'Team')

    used = set()
    base_counts = {}

    for team in Team.objects.all().order_by('id'):
        original_display = re.sub(r'\s+', ' ', (team.name or '').strip()) or 'Team'
        base_normalized = _normalize(original_display)

        # First occurrence keeps the original display name. Duplicates are renamed
        # deterministically to ensure uniqueness before adding DB unique constraint.
        candidate_display = original_display
        candidate_normalized = base_normalized

        if candidate_normalized in used:
            index = base_counts.get(base_normalized, 1) + 1
            while True:
                candidate_display = f"{original_display} {index}"
                candidate_normalized = _normalize(candidate_display)
                if candidate_normalized not in used:
                    break
                index += 1
            base_counts[base_normalized] = index
        else:
            base_counts[base_normalized] = 1

        team.name = candidate_display
        team.name_normalized = candidate_normalized
        team.save(update_fields=['name', 'name_normalized'])
        used.add(candidate_normalized)


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0002_team_is_locked'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='name_normalized',
            field=models.CharField(default='', editable=False, max_length=120),
            preserve_default=False,
        ),
        migrations.RunPython(populate_name_normalized, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='team',
            name='name_normalized',
            field=models.CharField(editable=False, max_length=120, unique=True),
        ),
    ]
