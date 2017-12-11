import math
import uuid

from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.core.validators import MinLengthValidator
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.template.loader import render_to_string
from .validators import rating_validator

from decimal import Decimal

from opencon.application.utils import parse_raw_choices

RATING_METADATA_1_CHOICES = [
    ('needs_followup', 'This application includes interesting projects or ideas that should be followed up on (include notes above)'),
    ('strong_application', 'This is an especially strong application and it should be sent to the Organizing Committee immediately'),
    ('know_applicant_or_conflict', 'I personally know this applicant or have a conflict of interest'),
    ('problem_spotted', 'There is a problem with this application'),
]

RATING_METADATA_2_CHOICES = [
    ('award_certificate', 'This applicant has done meaningful work to advance Open Access, Open Education or Open Data and should be awarded a certificate'),
    ('add_to_shortlist', 'This applicant should be added to the short list'),
    ('know_applicant_or_conflict', 'I personally know this applicant or have a conflict of interest'),
    ('problem_spotted', 'There is a problem with this application'),
]


class TimestampMixin(models.Model):
    """ Mixin for saving the creation time and the time of the last update """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(TimestampMixin, models.Model):
    """
    Users allowed to rate applications.
    """
    uuid = models.UUIDField(default=uuid.uuid4)
    first_name = models.CharField(max_length=100, default='', blank=False)
    last_name = models.CharField(max_length=100, default='', blank=False)
    nick = models.CharField(max_length=200, default='', blank=False)
    email = models.EmailField()

    is_round_0_reviewer = models.BooleanField(default=False)
    is_round_1_reviewer = models.BooleanField(default=True)
    is_round_2_reviewer = models.BooleanField(default=False)

    organizer = models.BooleanField(default=False)
    invitation_sent = models.BooleanField(default=False)

    disabled_at = models.DateTimeField(blank=True, null=True)

    def invite(self):
        """
        Send invite mail to application email address.
        """
        if not settings.REVIEWER_MAIL_ENABLED:
            return

        context = {
            "user": self,
            "link": "{}{}".format(
                settings.BASE_URL,
                reverse("rating:rate", args=[self.uuid])
            )
        }

        subject = render_to_string(
            "rating/email/invite.subject", context
        ).strip()
        message = render_to_string("rating/email/invite.message", context)

        send_mail(
            subject,
            message,
            settings.FROM_MAIL,
            [self.email],
            fail_silently=False
        )
        self.invitation_sent = True
        self.save()

    def __str__(self):
        return self.nick

    def avg(self):
        count = self.rated.count()
        if count == 0:
            return 0

        return sum(rating.rating for rating in self.rated.all()) / count

    def avg2(self):
        count = self.rated2.count()
        if count == 0:
            return 0

        return sum(rating.rating for rating in self.rated2.all()) / count

    def standard_deviation(self):
        count = self.rated.count()
        if count == 0:
            return 0

        ratings = self.rated.all()
        mean = sum(rating.rating for rating in ratings) / count
        sm = sum((mean-rating.rating)**2 for rating in ratings)
        return math.sqrt(sm/count)

    def standard_deviation2(self):
        count = self.rated2.count()
        if count == 0:
            return 0

        ratings = self.rated2.all()
        mean = sum(rating.rating for rating in ratings) / count
        sm = sum((mean-rating.rating)**2 for rating in ratings)
        return math.sqrt(sm/count)


STATE_CHOICES = (
    (True, u'Yes'),
    (False, u'No'),
)


class Round0Rating(TimestampMixin, models.Model):
    """
    Application rating.
    """

    created_by = models.ForeignKey(
        User,
        related_name="rated0"
    )
    application = models.ForeignKey(
        "application.Application2017",
        related_name="ratings0"
    )
    ipaddress = models.GenericIPAddressField(blank=True, null=True)

    # R0A
    DECISION_CHOICES=parse_raw_choices(
        """
        Yes [yes]
        No [no]
        Review Now [review]
        """
    )
    decision = models.CharField(
        verbose_name='Do you recommend this application for Round 1 rating?',
        help_text='',
        choices=DECISION_CHOICES,
        max_length=10,
    )

    def save(self, *args, **kwargs):
        obj = super().save(*args, **kwargs)
        self.application.save()  # when save is envoked ratings are recalculated
        return obj


class Round1Rating(TimestampMixin, models.Model):
    """
    Application rating.
    """
    created_by = models.ForeignKey(
        User,
        related_name="rated"
    )
    application = models.ForeignKey(
        "application.Application2017",
        related_name="ratings"
    )
    ipaddress = models.GenericIPAddressField(blank=True, null=True)

    # R1A
    rating = models.DecimalField(
        verbose_name='Rating',
        help_text='Please provide a rating between 0.1 (low) and 10.0 (high). Whole numbers and decimals up to one place are allowed.',
        decimal_places=1,
        max_digits=3,
        validators=[rating_validator, MinValueValidator(Decimal('0.1')), MaxValueValidator(Decimal('10.0'))],
    )

    # R1B
    RECOMMENDATIONS_CHOICES=parse_raw_choices(
        """
        This applicant has an interesting or unique project idea [project]
        This applicant is actively doing work to advance Open [active]
        This applicant has significant potential to have an impact [impact]
        I recommend this application for Round 2 review by the Organizing Committee [oc]
        I nominate this applicant for a certificate of recognition [certificate]
        """
    )
    recommendations = models.TextField(
        # Widget: Checkboxes -- choices are defined in forms.py
        verbose_name='Recommendations',
        help_text='',
        blank=True, # optional
    )

    # R1C
    ISSUES_CHOICES=parse_raw_choices(
        """
        There is a problem with this application (explain below) [problem]
        This applicant does not seem like a student or early career professional [not_early_career]
        I personally know this applicant [personal_relationship]
        """
    )
    issues = models.TextField(
        # Widget: Checkboxes -- choices are defined in forms.py
        verbose_name='Special Situations',
        help_text='',
        blank=True, # optional
    )

    # R1D
    comments = models.TextField(
        verbose_name='Comments for the Organizing Committee',
        help_text='Please add any comments about this application you would like to share with the Organizing Committee. If you made a recommendation or indicated a problem above, please provide a brief explanation here.',
        blank=True, # optional
        max_length=1400,
    )

    #R1E
    note = models.TextField(
        verbose_name='Comments for the Applicant (Optional)',
        help_text='If you would like to provide a short note for the applicant, please enter it here. This may be a few general words of encouragement, or something more specific. It’s not expected that you do this for all applicants, but it may be nice for ones that stand out. Comments will be shared anonymously.',
        blank=True, # optional
        max_length=600,
        # validators=[MinLengthValidator(3)],
    )

    def save(self, *args, **kwargs):
        obj = super().save(*args, **kwargs)
        self.application.save()  # when save is envoked ratings are recalculated
        return obj


class Round2Rating(TimestampMixin, models.Model):
    """
    Application rating.
    """
    created_by = models.ForeignKey(
        User,
        related_name="rated2"
    )
    application = models.ForeignKey(
        "application.Application2017",
        related_name="ratings2"
    )
    ipaddress = models.GenericIPAddressField(blank=True, null=True)

    # R2A
    rating = models.DecimalField(
        verbose_name='Rating',
        help_text='Please select a rating between 0.1 (low) and 10.0 (high).',
        decimal_places=1,
        max_digits=3,
        validators=[rating_validator, MinValueValidator(Decimal('0.1')), MaxValueValidator(Decimal('10.0'))],
    )

    # R2B
    DECISION_CHOICES=parse_raw_choices(
        """
        Yes [yes]
        Neutral [neutral]
        No [no]
        """
    )
    decision = models.TextField(
        # Widget: Radio -- choices are defined in forms.py
        verbose_name='Do you recommend inviting this applicant to OpenCon 2017?',
        help_text='',
        blank=False, # required
    )

    # R2C
    RECOMMENDATIONS_CHOICES=parse_raw_choices(
        """
        I nominate this applicant for a certificate of recognition [certificate]
        This applicant is a potential speaker for OpenCon 2017 [speaker]
        """
    )
    recommendations = models.TextField(
        # Widget: Checkboxes -- choices are defined in forms.py
        verbose_name='Other Recommendations',
        help_text='',
        blank=True, # optional
    )

    # R2D
    ISSUES_CHOICES=parse_raw_choices(
        """
        There is a problem with this application (explain below) [problem]
        This applicant does not seem like a student or early career professional [not_early_career]
        I personally know this applicant [personal_relationship]
        """
    )
    issues = models.TextField(
        # Widget: Checkboxes -- choices are defined in forms.py
        verbose_name='Special Situations',
        help_text='',
        blank=True, # optional
        max_length=1400,
    )

    # R2E
    comments = models.TextField(
        verbose_name='Comments for the OC',
        help_text='Please add a brief comment to explain your rating. At least a few words are required, since it will help fellow OC members understand your thinking when we make application decisions.',
        blank=False, # required
        max_length=1000,
        validators=[MinLengthValidator(5)],
    )

    # R2F
    note = models.TextField(
        verbose_name='Comments for the Applicant',
        help_text='If you would like to provide a short note for the applicant, please enter it here. This may be a few general words of encouragement, or something more specific. It’s not expected that you do this for all applicants, but it may be nice for ones that stand out. Comments will be shared anonymously.',
        blank=True, # optional
        max_length=600,
    )

    def save(self, *args, **kwargs):
        obj = super().save(*args, **kwargs)
        self.application.save()  # when save is envoked ratings are recalculated
        return obj
