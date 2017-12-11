from opencon.application.models import STATUS_CHOICES
from django import forms
from django.forms import widgets
from .models import Round0Rating, Round1Rating, Round2Rating

import ast


class Round0RateForm(forms.ModelForm):
    class Meta:
        model = Round0Rating
        fields = ['application', 'decision']
        widgets = {
            'application': widgets.HiddenInput,
        }


class Round1RateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        if kwargs.get('instance'):
            kwargs['initial'] = {
                'recommendations': ast.literal_eval(kwargs.get('instance').recommendations or '[]'),
                'issues': ast.literal_eval(kwargs.get('instance').issues or '[]'),
            }

        super().__init__(*args, **kwargs)

    class Meta:
        model = Round1Rating
        fields = 'application rating recommendations issues comments note'.split()
        widgets = {
            'application': widgets.HiddenInput,
            'recommendations': widgets.CheckboxSelectMultiple(choices=Round1Rating.RECOMMENDATIONS_CHOICES),
            'issues': widgets.CheckboxSelectMultiple(choices=Round1Rating.ISSUES_CHOICES),
        }

    def clean_comments(self):
        comments = self.cleaned_data['comments']
        if self.cleaned_data['recommendations'] and not comments:
            raise forms.ValidationError('This field is required when recommendations are checked.')
        return comments

class Round2RateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        if kwargs.get('instance'):
            kwargs['initial'] = {
                'recommendations': ast.literal_eval(kwargs.get('instance').recommendations or '[]'),
                'issues': ast.literal_eval(kwargs.get('instance').issues or '[]'),
            }

        super().__init__(*args, **kwargs)

    class Meta:
        model = Round2Rating
        fields = 'application rating decision recommendations issues comments note'.split()
        widgets = {
            'application': widgets.HiddenInput,
            'decision': widgets.RadioSelect(choices=Round2Rating.DECISION_CHOICES),
            'recommendations': widgets.CheckboxSelectMultiple(choices=Round2Rating.RECOMMENDATIONS_CHOICES),
            'issues': widgets.CheckboxSelectMultiple(choices=Round2Rating.ISSUES_CHOICES),
        }

    """
    def clean_acceptance_reason(self):
        reason = self.cleaned_data['acceptance_reason']
        if self.cleaned_data['acceptance'] == 'yes' and not reason:
            raise forms.ValidationError('This field is required.')
        return reason
    """

class ChangeStatusForm(forms.Form):
    STATUS_CHOICES_NO_DELETED = STATUS_CHOICES[:-1]
    choice = forms.ChoiceField(choices=STATUS_CHOICES_NO_DELETED, label='Current status')
    reason = forms.CharField(widget=widgets.Textarea, required=False)
    application = forms.CharField(widget=forms.HiddenInput)
