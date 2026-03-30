from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0001_initial'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='registration',
            constraint=models.UniqueConstraint(
                fields=('team', 'contest'),
                condition=models.Q(team__isnull=False),
                name='uniq_team_contest_registration',
            ),
        ),
    ]
