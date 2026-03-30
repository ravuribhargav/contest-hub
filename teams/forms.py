from django import forms

from .models import Team


class TeamCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.contest = kwargs.pop('contest', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Team
        fields = ['name']

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        normalized = Team.normalize_name(name)

        if not normalized:
            raise forms.ValidationError('Team name is required.')

        if self.contest and Team.objects.filter(contest=self.contest, name_normalized=normalized).exists():
            raise forms.ValidationError('Team name already exists in this contest.')

        # Preserve user intent while removing duplicate whitespace.
        return ' '.join(name.split())
