from django import forms
from opencon.application.models import Application2017

import django_filters

class Round1NeedsReviewFilter(django_filters.FilterSet):

    area_of_interest = django_filters.MultipleChoiceFilter(
        name='area_of_interest',
        label='Area of Interest',
        # choices=Application2017.AREA_OF_INTEREST_CHOICES,
        choices = [(i, dict(Application2017.AREA_OF_INTEREST_CHOICES).get(i)) for i in Application2017.objects.filter(need_rating1=True).values_list('area_of_interest', flat=True).order_by('area_of_interest').distinct()],
        widget=forms.CheckboxSelectMultiple,
    )

    field = django_filters.MultipleChoiceFilter(
        name='field',
        label='Field of Study',
        # choices=Application2017.FIELD_CHOICES,
        choices = [(i, dict(Application2017.FIELD_CHOICES).get(i)) for i in Application2017.objects.filter(need_rating1=True).values_list('field', flat=True).order_by('field').distinct()],
        widget=forms.CheckboxSelectMultiple,
    )

    citizenship = django_filters.MultipleChoiceFilter(
        name='citizenship',
        label='Citizenship of Applicant',
        # choices=Application2017.COUNTRY_CHOICES,
        choices = [(i, dict(Application2017.COUNTRY_CHOICES).get(i)) for i in Application2017.objects.filter(need_rating1=True).values_list('citizenship', flat=True).order_by('citizenship').distinct()],
        widget=forms.CheckboxSelectMultiple,
    )
