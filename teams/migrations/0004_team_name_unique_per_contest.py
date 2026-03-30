from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0003_team_name_normalized_unique'),
    ]

    operations = [
        migrations.AlterField(
            model_name='team',
            name='name_normalized',
            field=models.CharField(editable=False, max_length=120),
        ),
        migrations.AddConstraint(
            model_name='team',
            constraint=models.UniqueConstraint(
                fields=('contest', 'name_normalized'),
                name='uniq_team_name_normalized_per_contest',
            ),
        ),
    ]
