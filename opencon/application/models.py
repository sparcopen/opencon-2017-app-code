import string
import uuid
import random
import datetime

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from .validators import MaxChoicesValidator, MinChoicesValidator, EverythingCheckedValidator, none_validator, twitter_username_validator, orcid_validator, expenses_validator

from .data import *
from .constants import *

from .utils import parse_raw_choices

STATUS_CHOICES = [
    ('regular', 'Regular'),  # First one is default
    ('blacklisted', 'Blacklist'),
    ('whitelist2', 'Whitelist for round 2'),
    ('whitelist3', 'Whitelist for round 3'),
    ('deleted', 'Deleted'),
]


class HideInactive(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(inactive=False)


class TimestampMixin(models.Model):
    """ Mixin for saving the creation time and the time of the last update """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Draft(TimestampMixin, models.Model):
    email = models.EmailField(unique=True)
    data = models.TextField()
    uuid = models.UUIDField(default=uuid.uuid4)
    inactive = models.BooleanField(default=False)
    sent_email_data = models.DateTimeField(blank=True, null=True)

    objects = HideInactive()
    all_objects = models.Manager()

    def __str__(self):
        return self.email

    def send_access(self):
        if self.sent_email_data:
            can_send = timezone.now() - self.sent_email_data > datetime.timedelta(minutes=settings.SEND_ACCESS_INTERVAL)
        else:
            can_send = True

        if can_send:
            self.sent_email_data = timezone.now()
            self.save()
            if settings.SEND_EMAILS:
                message = render_to_string('application/email/draft.txt', {'uuid': self.uuid, 'email': self.email,})
                email = EmailMessage(
                    subject='OpenCon 2017 Draft Application',
                    body=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[self.email],
                    reply_to=[settings.DEFAULT_REPLYTO_EMAIL],
                )
                email.content_subtype = "html"
                try:
                    email.send(fail_silently=True)
                except:
                    pass # #todo -- fix problem with sending e-mail
            return True
        return False


class Airport(models.Model):
    iata_code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)

    def __str__(self):
        return '[{}] {}'.format(self.iata_code, self.name)


# #todo -- clean this up / delete completely instead of just commenting it out (in the meanwhile, keeping this here to prevent migrations from blowing up)
class Application(models.Model):
    pass
class Institution(models.Model):
    pass
class Organization(models.Model):
    pass
class Country(models.Model):
    pass

"""
class Institution(models.Model):
    name = models.CharField(max_length=300)
    show = models.BooleanField(default=False)  # shown in autocomplete or not

    def __str__(self):
        return self.name


class Organization(models.Model):
    name = models.CharField(max_length=300)
    show = models.BooleanField(default=False)  # shown in autocomplete or not

    def __str__(self):
        return self.name


class Country(models.Model):
    name = models.CharField(max_length=120)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Countries'
"""

# #todo -- #annualcheck -- check these fields if they are in sync with Application2017
MULTIFIELD_NAMES = [] # check forms.py
MULTIFIELD_NAMES += 'events profession degrees skills expenses permissions acknowledgments'.split() # CheckboxSelectMultiple
MULTIFIELD_NAMES += 'gender'.split(', ') # OptionalChoiceField
MULTIFIELD_NAMES += 'ethnicity'.split(', ') # OptionalMultiChoiceField
# # NOT INCLUDED: HiddenInput, Select, RadioSelect, ModelChoiceField

DISPLAYED_FIELDS_ROUND_0 = 'bio essay_interest essay_ideas events events_detail comments first_name last_name citizenship residence profession field affiliation_1 affiliation_2 affiliation_3 affiliation_4 affiliation_5 engagement twitter_username orcid'.split()

DISPLAYED_FIELDS_ROUND_1 = 'first_name last_name citizenship residence profession field affiliation_1 affiliation_2 affiliation_3 affiliation_4 affiliation_5 bio essay_interest essay_ideas events events_detail comments experience engagement twitter_username orcid'.split()

DISPLAYED_FIELDS_ROUND_2 = 'first_name last_name citizenship residence profession field affiliation_1 affiliation_2 affiliation_3 affiliation_4 affiliation_5 bio essay_interest essay_ideas events events_detail comments engagement attended twitter_username orcid experience degrees gender age ethnicity expenses fundraising_potential scholarship_comments location'.split()

class ApplicationManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(status='deleted')

    def get_all(self):
        return super().get_queryset()

    def get_unrated0(self, user):
        return self.get_queryset().filter(need_rating0=True).exclude(ratings0__created_by=user)

    def get_unrated(self, user):
        return self.get_queryset().filter(need_rating1=True).exclude(ratings__created_by=user)

    def get_unrated2(self, user):
        return self.get_all_round2().filter(need_rating2=True).exclude(ratings2__created_by=user)

    def get_all_round1(self):
        return self.get_queryset().filter(need_rating1=True).filter(need_rating0=False).exclude(status__exact='whitelist2').exclude(status__exact='whitelist3')

    def get_all_round2(self):
        queryset = self.get_queryset().filter(need_rating1=False)
        return queryset.filter(Q(rating1__gte=NEEDED_RATING_TO_ROUND2) | Q(status__exact='whitelist2')).exclude(status__exact='whitelist3')
        # Nicole: "Whitelisted 3 should be marked as fully reviewed and never shown anywhere."

class Application2017(TimestampMixin, models.Model):

    # #todo -- primary keys should be UUID
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Q01
    email = models.EmailField(
        # Widget: Text box
        verbose_name='Email Address',
        help_text='Please fill in your email address and click “Start Application” to unlock the rest of the form.',
        blank=False, # required
        unique=True,
    )

    # Q02
    TYPE_CHOICES=parse_raw_choices(
        """
        Applying for an invitation and travel scholarship [invite_scholarship]
        Applying for an invitation only (no scholarship requested) [invite_only]
        Creating or updating my profile only (not applying) [update_only]
        """
    )
    type = models.TextField(
        # Widget: Radio -- choices are defined in forms.py
        verbose_name='Application Type',
        help_text='To apply for an invitation and scholarship to attend OpenCon 2017, select the first option. If you only need an invitation (not a scholarship) or just want to update your information without applying, please select one of the other options.',
        blank=False, # required
    )

    # Q03
    first_name = models.CharField(
        # Widget: Text box
        verbose_name='First Name',
        help_text='Forename / Given Name',
        blank=False, # required
        max_length=50,
    )

    # Q04
    last_name = models.CharField(
        # Widget: Text box
        verbose_name='Last Name',
        help_text='Surname / Family Name',
        blank=False, # required
        max_length=50,
    )

    # Q05
    nickname = models.CharField(
        # Widget: Text box
        verbose_name='Preferred Name (Optional)',
        help_text='If you would like us to call you something different than the first name you entered above, please enter it here. For example, if your name is “Michael” but you prefer to be called “Mike.”',
        blank=True, # optional
        max_length=50,
    )

    # Q06
    alternate_email = models.EmailField(
        # Widget: Text box
        verbose_name='Alternate Email Address (Optional)',
        help_text='If you use another email address that you would like to have on record, please enter it here.',
        blank=True, # optional
    )

    # Q07
    twitter_username = models.CharField(
        # Widget: Text box
        verbose_name='Twitter Username (Optional)',
        help_text='If you have a Twitter account, please enter your username here including the "@" (for example @open_con or @r2rc). Otherwise leave this blank. You can sign up for a free account at https://twitter.com. Twitter is commonly-used platform among OpenCon community members, but is not required or necessary to participate.',
        max_length=20,
        blank=True, # optional
        validators=[twitter_username_validator]
    )

    # Q08
    orcid = models.CharField(
        # Widget: Text box
        verbose_name='ORCID (Optional)',
        help_text='If you have an ORCID, please enter it here. You can sign up for a free ORCID at https://orcid.org. This information is optional, but can be a helpful way to let us know about your publications and academic background.',
        max_length=19,
        blank=True, # optional
        validators=[orcid_validator]
    )

    # Q09
    affiliation_1 = models.CharField(
        # Widget: Text box
        verbose_name='Primary Affiliation',
        help_text='Please provide the full name of the institution, organization, or company where you work or go to school. Please write out the meaning of any acronyms (for example, write “Massachusetts Institute of Technology” not just “MIT”). If you have multiple affiliations, please list the most important one here. You may list up to four other affiliations below, if any.',
        blank=False, # required
        max_length=100,
        validators=[MinLengthValidator(3)],
    )

    # Q10
    affiliation_2 = models.CharField(
        # Widget: Text box
        verbose_name='Affiliation 2',
        max_length=100,
        blank=True, # optional
    )
    affiliation_3 = models.CharField(
        # Widget: Text box
        verbose_name='Affiliation 3',
        max_length=100,
        blank=True, # optional
    )
    affiliation_4 = models.CharField(
        # Widget: Text box
        verbose_name='Affiliation 4',
        max_length=100,
        blank=True, # optional
    )
    affiliation_5 = models.CharField(
        # Widget: Text box
        verbose_name='Affiliation 5',
        max_length=100,
        blank=True, # optional
    )

    # Q11
    bio = models.TextField(
        # Widget: Paragraph text
        verbose_name='Who are you?',
        help_text='Please provide a brief biography about yourself. This may include what you do for work, what you study, what projects you’re involved in, or what you are passionate about. Maximum 700 characters (~100 words).',
        blank=False, # required
        max_length=700,
        validators=[MinLengthValidator(10)],
    )

    # Q12
    essay_interest = models.TextField(
        # Widget: Paragraph text
        verbose_name='Why are you interested in OpenCon?',
        help_text='In your own words, tell us why you are interested in Open Access, Open Education and/or Open Data and how these issues relate to your work. If you are already working on these issues please tell us how. Maximum 1400 characters (~200 words).',
        blank=False, # required
        max_length=1400,
        validators=[MinLengthValidator(10)],
    )

    # Q13
    essay_ideas = models.TextField(
        # Widget: Paragraph text
        verbose_name='What are your ideas for advancing Open Access, Open Education and/or Open Data?',
        help_text='The biggest goal of OpenCon is to catalyze action to advance Open Access, Open Education and Open Data. Tell us what ideas you have for taking action on these issues, and how you would use (or are currently using) your experience with OpenCon to have an impact. Maximum 1400 characters (~200 words).',
        blank=False, # required
        max_length=1400,
        validators=[MinLengthValidator(10)],
    )

    # Q14a
    EVENTS_CHOICES=parse_raw_choices(
        """
        Open Access Week [oa_week]
        Open Education Week [oe_week]
        Open Data Day [od_day]
        None of the Above [none]
        """
    )
    events = models.TextField( # 2016: participation
        # Widget: Checkboxes -- choices are defined in forms.py
        verbose_name='Event Participation^',
        help_text='All of the events listed below are global and open to participation, so anyone, anywhere can be involved. Please indicate which of the following events you have participated in, or plan to participate in next year. Check all that apply.',
        blank=False, # required
        validators=[MinChoicesValidator(1), none_validator],
    )

    # Q14b
    events_detail = models.TextField( # 2016: participation_text
        # Widget: Paragraph text
        verbose_name='For the events you checked, briefly explain what you did or plan to do.',
        help_text='Maximum 700 characters (~100 words).',
        max_length=700,
        blank=True, # optional
    )

    # Q15
    AREA_OF_INTEREST_CHOICES=parse_raw_choices(
        """
        Open Access [open_access]
        Open Education [open_education]
        Open Research Data [open_research_data]
        Open Government Data [open_gov_data]
        Open Science [open_science]
        Free and Open Source Software [open_software]
        """
    )
    area_of_interest = models.TextField(
        # Widget: Radio -- choices are defined in forms.py
        verbose_name='What is your primary OpenCon area of interest?^',
        help_text='Select the OpenCon issue area that interests you most. We understand that many applicants are interested in multiple issues on this list, but it is helpful to know which one you consider most interesting. Please note that OpenCon focuses on these issues in the specific context of research and education.',
        blank=False, # required
    )

    @property
    def area_of_interest_expanded(self):
        try:
            # if self.area_of_interest == "other":
            #     return None
            return dict(self.AREA_OF_INTEREST_CHOICES).get(self.area_of_interest, None)
        except ValueError:
            return None

    COUNTRY_CHOICES=(
        (None, '(Select an option below)'),
        ('AF', 'Afghanistan'),
        ('AX', 'Åland Islands'),
        ('AL', 'Albania'),
        ('DZ', 'Algeria'),
        ('AS', 'American Samoa'),
        ('AD', 'Andorra'),
        ('AO', 'Angola'),
        ('AI', 'Anguilla'),
        ('AQ', 'Antarctica'),
        ('AG', 'Antigua and Barbuda'),
        ('AR', 'Argentina'),
        ('AM', 'Armenia'),
        ('AW', 'Aruba'),
        ('AU', 'Australia'),
        ('AT', 'Austria'),
        ('AZ', 'Azerbaijan'),
        ('BS', 'Bahamas'),
        ('BH', 'Bahrain'),
        ('BD', 'Bangladesh'),
        ('BB', 'Barbados'),
        ('BY', 'Belarus'),
        ('BE', 'Belgium'),
        ('BZ', 'Belize'),
        ('BJ', 'Benin'),
        ('BM', 'Bermuda'),
        ('BT', 'Bhutan'),
        ('BO', 'Bolivia'),
        ('BQ', 'Bonaire, Sint Eustatius and Saba'),
        ('BA', 'Bosnia and Herzegovina'),
        ('BW', 'Botswana'),
        ('BV', 'Bouvet Island'),
        ('BR', 'Brazil'),
        ('IO', 'British Indian Ocean Territory'),
        ('BN', 'Brunei'),
        ('BG', 'Bulgaria'),
        ('BF', 'Burkina Faso'),
        ('BI', 'Burundi'),
        ('CV', 'Cabo Verde'),
        ('KH', 'Cambodia'),
        ('CM', 'Cameroon'),
        ('CA', 'Canada'),
        ('KY', 'Cayman Islands'),
        ('CF', 'Central African Republic'),
        ('TD', 'Chad'),
        ('CL', 'Chile'),
        ('CN', 'China'),
        ('CX', 'Christmas Island'),
        ('CC', 'Cocos (Keeling) Islands'),
        ('CO', 'Colombia'),
        ('KM', 'Comoros'),
        ('CG', 'Congo, Republic of the'),
        ('CD', 'Congo, the Democratic Republic of the'),
        ('CK', 'Cook Islands'),
        ('CR', 'Costa Rica'),
        ('CI', "Côte d'Ivoire"),
        ('HR', 'Croatia'),
        ('CU', 'Cuba'),
        ('CW', 'Curaçao'),
        ('CY', 'Cyprus'),
        ('CZ', 'Czechia'),
        ('DK', 'Denmark'),
        ('DJ', 'Djibouti'),
        ('DM', 'Dominica'),
        ('DO', 'Dominican Republic'),
        ('EC', 'Ecuador'),
        ('EG', 'Egypt'),
        ('SV', 'El Salvador'),
        ('GQ', 'Equatorial Guinea'),
        ('ER', 'Eritrea'),
        ('EE', 'Estonia'),
        ('ET', 'Ethiopia'),
        ('FK', 'Falkland Islands (Malvinas)'),
        ('FO', 'Faroe Islands'),
        ('FJ', 'Fiji'),
        ('FI', 'Finland'),
        ('FR', 'France'),
        ('GF', 'French Guiana'),
        ('PF', 'French Polynesia'),
        ('TF', 'French Southern Territories'),
        ('GA', 'Gabon'),
        ('GM', 'Gambia'),
        ('GE', 'Georgia'),
        ('DE', 'Germany'),
        ('GH', 'Ghana'),
        ('GI', 'Gibraltar'),
        ('GR', 'Greece'),
        ('GL', 'Greenland'),
        ('GD', 'Grenada'),
        ('GP', 'Guadeloupe'),
        ('GU', 'Guam'),
        ('GT', 'Guatemala'),
        ('GG', 'Guernsey'),
        ('GN', 'Guinea'),
        ('GW', 'Guinea-Bissau'),
        ('GY', 'Guyana'),
        ('HT', 'Haiti'),
        ('HM', 'Heard Island and McDonald Islands'),
        ('VA', 'Holy See'),
        ('HN', 'Honduras'),
        ('HK', 'Hong Kong'),
        ('HU', 'Hungary'),
        ('IS', 'Iceland'),
        ('IN', 'India'),
        ('ID', 'Indonesia'),
        ('IR', 'Iran'),
        ('IQ', 'Iraq'),
        ('IE', 'Ireland'),
        ('IM', 'Isle of Man'),
        ('IL', 'Israel'),
        ('IT', 'Italy'),
        ('JM', 'Jamaica'),
        ('JP', 'Japan'),
        ('JE', 'Jersey'),
        ('JO', 'Jordan'),
        ('KZ', 'Kazakhstan'),
        ('KE', 'Kenya'),
        ('KI', 'Kiribati'),
        ('KW', 'Kuwait'),
        ('KG', 'Kyrgyzstan'),
        ('LA', 'Laos'),
        ('LV', 'Latvia'),
        ('LB', 'Lebanon'),
        ('LS', 'Lesotho'),
        ('LR', 'Liberia'),
        ('LY', 'Libya'),
        ('LI', 'Liechtenstein'),
        ('LT', 'Lithuania'),
        ('LU', 'Luxembourg'),
        ('MO', 'Macao'),
        ('MK', 'Macedonia'),
        ('MG', 'Madagascar'),
        ('MW', 'Malawi'),
        ('MY', 'Malaysia'),
        ('MV', 'Maldives'),
        ('ML', 'Mali'),
        ('MT', 'Malta'),
        ('MH', 'Marshall Islands'),
        ('MQ', 'Martinique'),
        ('MR', 'Mauritania'),
        ('MU', 'Mauritius'),
        ('YT', 'Mayotte'),
        ('MX', 'Mexico'),
        ('FM', 'Micronesia, Federated States of'),
        ('MD', 'Moldova'),
        ('MC', 'Monaco'),
        ('MN', 'Mongolia'),
        ('ME', 'Montenegro'),
        ('MS', 'Montserrat'),
        ('MA', 'Morocco'),
        ('MZ', 'Mozambique'),
        ('MM', 'Myanmar'),
        ('NA', 'Namibia'),
        ('NR', 'Nauru'),
        ('NP', 'Nepal'),
        ('NL', 'Netherlands'),
        ('NC', 'New Caledonia'),
        ('NZ', 'New Zealand'),
        ('NI', 'Nicaragua'),
        ('NE', 'Niger'),
        ('NG', 'Nigeria'),
        ('NU', 'Niue'),
        ('NF', 'Norfolk Island'),
        ('KP', 'North Korea'),
        ('MP', 'Northern Mariana Islands'),
        ('NO', 'Norway'),
        ('OM', 'Oman'),
        ('PK', 'Pakistan'),
        ('PW', 'Palau'),
        ('PS', 'Palestine'),
        ('PA', 'Panama'),
        ('PG', 'Papua New Guinea'),
        ('PY', 'Paraguay'),
        ('PE', 'Peru'),
        ('PH', 'Philippines'),
        ('PN', 'Pitcairn'),
        ('PL', 'Poland'),
        ('PT', 'Portugal'),
        ('PR', 'Puerto Rico'),
        ('QA', 'Qatar'),
        ('RE', 'Réunion'),
        ('RO', 'Romania'),
        ('RU', 'Russia'),
        ('RW', 'Rwanda'),
        ('BL', 'Saint Barthélemy'),
        ('SH', 'Saint Helena, Ascension and Tristan da Cunha'),
        ('KN', 'Saint Kitts and Nevis'),
        ('LC', 'Saint Lucia'),
        ('MF', 'Saint Martin (French part)'),
        ('PM', 'Saint Pierre and Miquelon'),
        ('VC', 'Saint Vincent and the Grenadines'),
        ('WS', 'Samoa'),
        ('SM', 'San Marino'),
        ('ST', 'Sao Tome and Principe'),
        ('SA', 'Saudi Arabia'),
        ('SN', 'Senegal'),
        ('RS', 'Serbia'),
        ('SC', 'Seychelles'),
        ('SL', 'Sierra Leone'),
        ('SG', 'Singapore'),
        ('SX', 'Sint Maarten (Dutch part)'),
        ('SK', 'Slovakia'),
        ('SI', 'Slovenia'),
        ('SB', 'Solomon Islands'),
        ('SO', 'Somalia'),
        ('ZA', 'South Africa'),
        ('GS', 'South Georgia and the South Sandwich Islands'),
        ('KR', 'South Korea'),
        ('SS', 'South Sudan'),
        ('ES', 'Spain'),
        ('LK', 'Sri Lanka'),
        ('SD', 'Sudan'),
        ('SR', 'Suriname'),
        ('SJ', 'Svalbard and Jan Mayen'),
        ('SZ', 'Swaziland'),
        ('SE', 'Sweden'),
        ('CH', 'Switzerland'),
        ('SY', 'Syria'),
        ('TW', 'Taiwan'),
        ('TJ', 'Tajikistan'),
        ('TZ', 'Tanzania'),
        ('TH', 'Thailand'),
        ('TL', 'Timor-Leste'),
        ('TG', 'Togo'),
        ('TK', 'Tokelau'),
        ('TO', 'Tonga'),
        ('TT', 'Trinidad and Tobago'),
        ('TN', 'Tunisia'),
        ('TR', 'Turkey'),
        ('TM', 'Turkmenistan'),
        ('TC', 'Turks and Caicos Islands'),
        ('TV', 'Tuvalu'),
        ('UG', 'Uganda'),
        ('UA', 'Ukraine'),
        ('AE', 'United Arab Emirates'),
        ('GB', 'United Kingdom'),
        ('UM', 'United States Minor Outlying Islands'),
        ('US', 'United States of America'),
        ('UY', 'Uruguay'),
        ('UZ', 'Uzbekistan'),
        ('VU', 'Vanuatu'),
        ('VE', 'Venezuela'),
        ('VN', 'Vietnam'),
        ('VG', 'Virgin Islands, British'),
        ('VI', 'Virgin Islands, U.S.'),
        ('WF', 'Wallis and Futuna'),
        ('EH', 'Western Sahara'),
        ('YE', 'Yemen'),
        ('ZM', 'Zambia'),
        ('ZW', 'Zimbabwe'),
        ('other', 'Country Not Listed'),
    )

    # Q16
    citizenship = models.TextField(
        # Widget: Dropdown -- choices are defined in forms.py
        verbose_name='Country of Citizenship^',
        help_text='Please select the country where you are a citizen (where your passport is from). If your country isn’t listed, select “Country Not Listed” and indicate your country in the comments box at the end of the application form.',
        blank=False, # required
    )

    @property
    def citizenship_expanded(self):
        try:
            if self.citizenship == "other":
                return None
            return dict(self.COUNTRY_CHOICES).get(self.citizenship, None)
        except ValueError:
            return None

    # Q17
    residence = models.TextField(
        # Widget: Dropdown -- choices are defined in forms.py
        verbose_name='Country of Residence^',
        help_text='Please select the country where you currently live. If you are a resident of multiple countries, pick the one where you will spend the most time this year.',
        blank=False, # required
    )

    @property
    def residence_expanded(self):
        try:
            if self.residence == "other":
                return None
            return dict(self.COUNTRY_CHOICES).get(self.residence, None)
        except ValueError:
            return None

    # Q18
    PROFESSION_CHOICES=parse_raw_choices(
        """
        Undergraduate Student (studying for bachelor’s degree) [undergrad_student]
        Masters / Professional Student (studying for master’s or professional degree) [grad_student]
        PhD Candidate (studying for PhD) [phd_candidate]
        Post-Doc [postdoc]
        Professor / Teacher [professor]
        Researcher [researcher]
        Librarian / Archivist [librarian]
        Non-Academic University Staff [nonacademic]
        Publisher [publisher]
        Government Employee / Civil Servant [government]
        Non Profit / NGO Employee [non-profit]
        Journalist / Blogger [journalist]
        Doctor / Medical Professional [doctor]
        Lawyer / Legal Professional [lawyer]
        Funder / Philanthropist [funder]
        Software / Technology Developer [tech]
        Businessperson / Entrepreneur [businessperson]
        Activist / Advocate [advocate]
        None of these describes me [none]
        """
    )
    profession = models.TextField(
        # Widget: Checkboxes -- choices are defined in forms.py
        verbose_name='Primary Profession^',
        help_text='Please check the profession that best describes what you do. If there are multiple options that equally describe you, you may select up to three.',
        blank=False, # required
        validators=[MinChoicesValidator(1), MaxChoicesValidator(3), none_validator],
    )
    # Q19
    EXPERIENCE_CHOICES=parse_raw_choices(
        """
        0 (still in school full time or just starting first career) [0to1]
        1-5 years [1to5]
        6-10 years [6to10]
        11-15 years [11to15]
        16+ years [16plus]
        """
    )
    experience = models.TextField(
        # Widget: Radio -- choices are defined in forms.py
        verbose_name='Years of Work Experience^',
        help_text='Please indicate how many years of work experience you have in your primary profession. If you’ve worked in multiple professions at different times, please add the number of years together. Do not include time when you were also studying or going to school full time (including PhD).',
        blank=False, # required
    )

    # Q20
    DEGREES_CHOICES=parse_raw_choices(
        """
        Bachelor’s Degree (BA, BS, etc.) [bachelors]
        Master’s Degree (MBA, MFA, etc.) [masters]
        Professional Degree (MD, JD, etc.) [professional]
        PhD or other Doctoral Degree [phd]
        Other Postgraduate Degree [other_postgraduate]
        Other Professional Certification [other_certification]
        None of the above [none]
        """
    )
    degrees = models.TextField(
        # Widget: Checkboxes -- choices are defined in forms.py
        verbose_name='Academic Degrees^',
        help_text='Please select the academic degrees you have attained, if any. Only check the degrees you have already been awarded.',
        blank=False, # required
        validators=[none_validator],
    )

    # Q21
    FIELD_CHOICES=(
        (None, '(Select an option below)'),
        ('un08', 'Agriculture, forestry, fisheries and veterinary'),
        ('un073', 'Architecture and construction'),
        ('un021', 'Arts'),
        ('un051', 'Biological and related sciences'),
        ('un041', 'Business and administration'),
        ('un0531', 'Chemistry'),
        ('un0532', 'Earth sciences'),
        ('un0311', 'Economics'),
        ('un01', 'Education'),
        ('un071', 'Engineering and engineering trades'),
        ('un052', 'Environment'),
        ('un00', 'Generic programs and qualifications'),
        ('un091', 'Health (incl. medicine, nursing)'),
        ('un0222', 'History and archaeology'),
        ('un06', 'Information and Communication Technologies (ICTs)'),
        ('un0321', 'Journalism and reporting'),
        ('un0231', 'Languages'),
        ('un042', 'Law'),
        ('un0322', 'Library, information and archival studies'),
        ('un0232', 'Literature and linguistics'),
        ('un072', 'Manufacturing and processing'),
        ('un054', 'Mathematics and statistics'),
        ('un99', 'Other'),
        ('un0223', 'Philosophy and ethics'),
        ('un0533', 'Physics'),
        ('un0312', 'Political sciences and civics'),
        ('un0313', 'Psychology'),
        ('un0221', 'Religion and theology'),
        ('un10', 'Services'),
        ('un031', 'Social and behavioral sciences'),
        ('un0314', 'Sociology and cultural studies'),
        ('un092', 'Welfare (incl. social work)'),
    )
    field = models.TextField(
        # Widget: Dropdown -- choices are defined in forms.py
        verbose_name='Academic Field^',
        help_text='Which option below best describes your academic field of study or expertise? Please select only one option.',
        blank=False, # required
        # #fyi -- "none_validator" not needed for this field -- this is Select, not CheckboxSelectMultiple
    )

    @property
    def field_expanded(self):
        try:
            if self.field == "other":
                return None
            return dict(self.FIELD_CHOICES).get(self.field, None)
        except ValueError:
            return None

    # Q22
    GENDER_CHOICES=parse_raw_choices(
        """
        Female [female]
        Male [male]
        Prefer not to answer [not_specified]
        Specified below [other]
        """
    )
    GENDER_VERBOSE_NAME='Gender^'
    GENDER_HELP_TEXT='Please select an option.'
    gender = models.CharField(
        # Widget: CUSTOM Radio + fill-in other -- choices are defined in forms.py (also: verbose_name & help_text)
        # defining verbose_name & help_text here as well (in addition to forms.py) because it's accessed in get_data
        verbose_name=GENDER_VERBOSE_NAME,
        help_text=GENDER_HELP_TEXT,
        max_length=100,
        blank=False, # required
    )

    # Q23
    AGE_CHOICES=parse_raw_choices(
        """
        Under 18 [0to18]
        18 - 25 [18to25]
        26 - 33 [26to33]
        34 - 41 [34to41]
        42 - 49 [42to49]
        50 + [50plus]
        Prefer not to say [not_specified]
        """
    )
    age = models.TextField(
        # Widget: Radio -- choices are defined in forms.py
        verbose_name='Age^',
        help_text='Please select an option.',
        blank=False, # required
    )

    # Q24
    # Validation: Required. If left blank, throw the error “Please select “Prefer not to say” if you wish to leave this question blank, or provide an answer.” If “Prefer not to say” is selected, then no other option may be selected. If “Specified below” is selected, the box must have at least one character. The box may only contain characters if “Specified below” is selected. Max 100 characters.
    ETHNICITY_CHOICES=parse_raw_choices(
        """
        African origin [african]
        Asian origin [asian]
        European origin [european]
        Latin American or Caribbean origin [latin_america]
        Northern American origin [north_america]
        Oceania origin (incl. Australia and Pacific Islands) [oceania]
        Black [black]
        White / Caucasian [white]
        Indigenous [indigenous]
        Multi-racial [multi_racial]
        Prefer not to say [not_specified]
        Specified below [other]
        """
    )
    ETHNICITY_VERBOSE_NAME='Ethnicity and Race^'
    ETHNICITY_HELP_TEXT='OpenCon is committed to supporting diversity, equity and inclusion, and this information adds an important dimension to our efforts. We understand that different cultures have different  sensitivities around this type of information, so this question is optional. Select “Prefer not to say” to skip the question. If you decide to answer, select any/all options that apply. You can also write  your own answer in the box at the bottom, either in addition to the options below, or instead of checking one of the available options (just be sure to check "Specified below"). By "origin" we generally mean where your ancestors are from.'
    ethnicity = models.TextField(
        # Widget: CUSTOM Checkboxes + fill-in other -- choices are defined in forms.py (also: verbose_name & help_text)
        # defining verbose_name & help_text here as well (in addition to forms.py) because it's accessed in get_data
        verbose_name=ETHNICITY_VERBOSE_NAME,
        help_text=ETHNICITY_HELP_TEXT,
        blank=False, # required
        validators=[MinChoicesValidator(1)],
    )

    # Q25
    LANGUAGE_CHOICES=(
        (None, '(If applicable, select an option below)'),
        ('ab', 'Abkhazian'),
        ('aa', 'Afar'),
        ('af', 'Afrikaans'),
        ('ak', 'Akan'),
        ('sq', 'Albanian'),
        ('am', 'Amharic'),
        ('ar', 'Arabic'),
        ('an', 'Aragonese'),
        ('hy', 'Armenian'),
        ('as', 'Assamese'),
        ('av', 'Avaric'),
        ('ae', 'Avestan'),
        ('ay', 'Aymara'),
        ('az', 'Azerbaijani'),
        ('bm', 'Bambara'),
        ('ba', 'Bashkir'),
        ('eu', 'Basque'),
        ('be', 'Belarusian'),
        ('bn', 'Bengali'),
        ('bh', 'Bihari languages'),
        ('bi', 'Bislama'),
        ('nb', 'Bokmål, Norwegian; Norwegian Bokmål'),
        ('bs', 'Bosnian'),
        ('br', 'Breton'),
        ('bg', 'Bulgarian'),
        ('my', 'Burmese'),
        ('ca', 'Catalan; Valencian'),
        ('km', 'Central Khmer'),
        ('ch', 'Chamorro'),
        ('ce', 'Chechen'),
        ('ny', 'Chichewa; Chewa; Nyanja'),
        ('zh', 'Chinese'),
        ('cu', 'Church Slavic; Old Slavonic; Church Slavonic; Old Bulgarian; Old Church Slavonic'),
        ('cv', 'Chuvash'),
        ('kw', 'Cornish'),
        ('co', 'Corsican'),
        ('cr', 'Cree'),
        ('hr', 'Croatian'),
        ('cs', 'Czech'),
        ('da', 'Danish'),
        ('dv', 'Divehi; Dhivehi; Maldivian'),
        ('nl', 'Dutch; Flemish'),
        ('dz', 'Dzongkha'),
        ('en', 'English'),
        ('eo', 'Esperanto'),
        ('et', 'Estonian'),
        ('ee', 'Ewe'),
        ('fo', 'Faroese'),
        ('fj', 'Fijian'),
        ('fi', 'Finnish'),
        ('fr', 'French'),
        ('ff', 'Fulah'),
        ('gd', 'Gaelic; Scottish Gaelic'),
        ('gl', 'Galician'),
        ('lg', 'Ganda'),
        ('ka', 'Georgian'),
        ('de', 'German'),
        ('el', 'Greek, Modern (1453-)'),
        ('gn', 'Guarani'),
        ('gu', 'Gujarati'),
        ('ht', 'Haitian; Haitian Creole'),
        ('ha', 'Hausa'),
        ('he', 'Hebrew'),
        ('hz', 'Herero'),
        ('hi', 'Hindi'),
        ('ho', 'Hiri Motu'),
        ('hu', 'Hungarian'),
        ('is', 'Icelandic'),
        ('io', 'Ido'),
        ('ig', 'Igbo'),
        ('id', 'Indonesian'),
        ('ia', 'Interlingua (International Auxiliary Language Association)'),
        ('ie', 'Interlingue; Occidental'),
        ('iu', 'Inuktitut'),
        ('ik', 'Inupiaq'),
        ('ga', 'Irish'),
        ('it', 'Italian'),
        ('ja', 'Japanese'),
        ('jv', 'Javanese'),
        ('kl', 'Kalaallisut; Greenlandic'),
        ('kn', 'Kannada'),
        ('kr', 'Kanuri'),
        ('ks', 'Kashmiri'),
        ('kk', 'Kazakh'),
        ('ki', 'Kikuyu; Gikuyu'),
        ('rw', 'Kinyarwanda'),
        ('ky', 'Kirghiz; Kyrgyz'),
        ('kv', 'Komi'),
        ('kg', 'Kongo'),
        ('ko', 'Korean'),
        ('kj', 'Kuanyama; Kwanyama'),
        ('ku', 'Kurdish'),
        ('lo', 'Lao'),
        ('la', 'Latin'),
        ('lv', 'Latvian'),
        ('li', 'Limburgan; Limburger; Limburgish'),
        ('ln', 'Lingala'),
        ('lt', 'Lithuanian'),
        ('lu', 'Luba-Katanga'),
        ('lb', 'Luxembourgish; Letzeburgesch'),
        ('mk', 'Macedonian'),
        ('mg', 'Malagasy'),
        ('ms', 'Malay'),
        ('ml', 'Malayalam'),
        ('mt', 'Maltese'),
        ('gv', 'Manx'),
        ('mi', 'Maori'),
        ('mr', 'Marathi'),
        ('mh', 'Marshallese'),
        ('mn', 'Mongolian'),
        ('na', 'Nauru'),
        ('nv', 'Navajo; Navaho'),
        ('nd', 'Ndebele, North; North Ndebele'),
        ('nr', 'Ndebele, South; South Ndebele'),
        ('ng', 'Ndonga'),
        ('ne', 'Nepali'),
        ('se', 'Northern Sami'),
        ('no', 'Norwegian'),
        ('nn', 'Norwegian Nynorsk; Nynorsk, Norwegian'),
        ('oc', 'Occitan (post 1500)'),
        ('oj', 'Ojibwa'),
        ('or', 'Oriya'),
        ('om', 'Oromo'),
        ('os', 'Ossetian; Ossetic'),
        ('pi', 'Pali'),
        ('pa', 'Panjabi; Punjabi'),
        ('fa', 'Persian'),
        ('pl', 'Polish'),
        ('pt', 'Portuguese'),
        ('ps', 'Pushto; Pashto'),
        ('qu', 'Quechua'),
        ('ro', 'Romanian; Moldavian; Moldovan'),
        ('rm', 'Romansh'),
        ('rn', 'Rundi'),
        ('ru', 'Russian'),
        ('sm', 'Samoan'),
        ('sg', 'Sango'),
        ('sa', 'Sanskrit'),
        ('sc', 'Sardinian'),
        ('sr', 'Serbian'),
        ('sn', 'Shona'),
        ('ii', 'Sichuan Yi; Nuosu'),
        ('sd', 'Sindhi'),
        ('si', 'Sinhala; Sinhalese'),
        ('sk', 'Slovak'),
        ('sl', 'Slovenian'),
        ('so', 'Somali'),
        ('st', 'Sotho, Southern'),
        ('es', 'Spanish; Castilian'),
        ('su', 'Sundanese'),
        ('sw', 'Swahili'),
        ('ss', 'Swati'),
        ('sv', 'Swedish'),
        ('tl', 'Tagalog'),
        ('ty', 'Tahitian'),
        ('tg', 'Tajik'),
        ('ta', 'Tamil'),
        ('tt', 'Tatar'),
        ('te', 'Telugu'),
        ('th', 'Thai'),
        ('bo', 'Tibetan'),
        ('ti', 'Tigrinya'),
        ('to', 'Tonga (Tonga Islands)'),
        ('ts', 'Tsonga'),
        ('tn', 'Tswana'),
        ('tr', 'Turkish'),
        ('tk', 'Turkmen'),
        ('tw', 'Twi'),
        ('ug', 'Uighur; Uyghur'),
        ('uk', 'Ukrainian'),
        ('ur', 'Urdu'),
        ('uz', 'Uzbek'),
        ('ve', 'Venda'),
        ('vi', 'Vietnamese'),
        ('vo', 'Volapük'),
        ('wa', 'Walloon'),
        ('cy', 'Welsh'),
        ('fy', 'Western Frisian'),
        ('wo', 'Wolof'),
        ('xh', 'Xhosa'),
        ('yi', 'Yiddish'),
        ('yo', 'Yoruba'),
        ('za', 'Zhuang; Chuang'),
        ('zu', 'Zulu'),
    )
    language_1 = models.TextField(
        # Widget: Dropdown -- choices are defined in forms.py
        blank=True, # optional
    )
    language_2 = models.TextField(
        # Widget: Dropdown -- choices are defined in forms.py
        blank=True, # optional
    )
    language_3 = models.TextField(
        # Widget: Dropdown -- choices are defined in forms.py
        blank=True, # optional
    )
    language_4 = models.TextField(
        # Widget: Dropdown -- choices are defined in forms.py
        blank=True, # optional
    )

    # Q26
    SKILLS_CHOICES=parse_raw_choices(
        """
        Advocacy and Policy [advocacy]
        Blogging [blogging]
        Communications / Media Relations [comms]
        Community / Grassroots Organizing [organizing]
        Event Logistics [events]
        Fundraising [fundraising]
        Graphic Design [graphics]
        Research on Open Access / Open Education / Open Data [open_research]
        Social Media Campaigns [social_media]
        Volunteer Management [volunteers]
        Video Filming / Editing [videos]
        """
    )
    skills = models.TextField(
        # Widget: Checkboxes -- choices are defined in forms.py
        verbose_name='Skills^',
        help_text='Do you have any of the following skills that you would be interested in volunteering for an open-related project? Check all that apply below.',
        blank=True, # optional
    )

    # Q27
    EXPENSES_CHOICES=parse_raw_choices(
        """
        Full scholarship (all expenses below) [full]
        Flight / Train / Bus to Berlin [travel]
        Hotel accommodation [hotel]
        Visa application fee (costs EUR 90 without scholarship) [visa]
        Full conference registration fee (costs USD 300 without scholarship) [fee_full]
        50% discount on conference registration fee (cost to you would be USD 150) [fee_discount]
        No scholarship requested [none]
        """
    )
    expenses = models.TextField(
        # Widget: Checkboxes -- choices are defined in forms.py
        verbose_name='What expenses do you need your scholarship to cover?',
        help_text='Select the expenses below for which you would like to apply for a scholarship, or select "Full scholarship" to request all of them.',
        blank=True, # optional (required only if scholarship requested)
        validators=[none_validator, expenses_validator],
    )

    # Q28
    FUNDRAISING_POTENTIAL_CHOICES=parse_raw_choices(
        """
        Very Likely [5]
        Likely [4]
        Equally Likely as Unlikely [3]
        Unlikely [2]
        Very Unlikely [1]
        I require my full scholarship request and cannot fundraise [zero]
        Not Applicable [na]
        """
    )
    fundraising_potential = models.TextField(
        # Widget: Radio -- choices are defined in forms.py
        verbose_name='Fundraising Ability',
        help_text='If you have requested a full scholarship above, we do not expect you to be able to fundraise. However, if you have indicated that you can help cover some of your costs, we’d like to know if you have the ability to seek additional funding from other sources, should we be unable to grant the scholarship you requested. Please indicate below how likely you are to be able to seek additional funding to support your attendance costs if invited.',
        blank=True, # optional (required only if scholarship requested)
    )

    # Q29
    scholarship_comments = models.TextField(
        # Widget: Paragraph text
        verbose_name='Scholarship Comments',
        help_text='If you think you may be able to raise funding for part of your cost of attendance, please provide a brief description below. Leave this blank if you are unable to fundraise. Maximum 300 characters (~50 words).',
        max_length=300,
        blank=True, # optional
    )

    # Q30
    location = models.CharField(
        # Widget: Text box
        verbose_name='City of Departure',
        help_text='OpenCon 2017 takes place in Berlin, Germany. Please enter below the city from which you would travel to get to Berlin. Please include city and country. This information is required for those applying for a travel scholarship, and we encourage everyone else to answer too.',
        max_length=200,
        blank=True, # optional (required only if scholarship requested)
    )

    # Q31
    AIRPORT_VERBOSE_NAME='Closest International Airport'
    AIRPORT_HELP_TEXT='Please enter the nearest international airport to the city you would travel from to get to Berlin, regardless of whether you would travel to Berlin by air. This does not need to be the airport you ultimately travel from, it is simply helps us understand your location and how far you would need to travel. To fill out this question, begin by typing the name of the city, and suggestions will show up automatically. Click the correct one. You can also search by the three-letter IATA code (for example enter “LHR” for London). If your airport does not show up, please type “Other Airport” and specify your airport in the comments box below.'
    airport = models.ForeignKey(
        # Widget: CUSTOM Magic lookup box -- verbose_name & help_text are defined in forms.py (choices are not needed)
        'Airport',
        blank=False, # required
    )

    # Q32
    comments = models.TextField(
        # Widget: Paragraph text
        verbose_name='Comments (Optional)',
        help_text='Use this box for any additional information you would like to share about yourself, projects you work on, or other information that could impact your attendance or participation at OpenCon 2017, if invited. Maximum 900 characters (~150 words).',
        max_length=900,
        blank=True, # optional
    )

    # Q33
    PERMISSIONS_CHOICES=parse_raw_choices(
        """
        OpenCon has permission to occasionally use my application to connect me with future opportunities related to the mission of OpenCon (e.g. scholarships to related conferences, local events, opportunities for application) [connect]
        OpenCon has permission to share my application publicly in connection with my name and data for the purposes of connecting with others in the community (email addresses are kept private). [share]
        """
    )
    permissions = models.TextField(
        # Widget: Checkboxes -- choices are defined in forms.py
        verbose_name='Permissions',
        help_text='Please select the boxes below to give us permission to contact you and use the data you have provided. Your selections will not impact your application rating, however giving us these permissions can help make sure you get the most out of the OpenCon community.',
        blank=True, # optional
    )

    # Q34
    ACKNOWLEDGMENTS_CHOICES=parse_raw_choices(
        """
        I understand that my contact information and other information I provide in this application will be handled according to OpenCon’s Privacy Policy. [1]
        I understand that the information I provide in this application will be shared with members of the OpenCon 2017 Application Review Team for purposes of evaluation, and if I requested a scholarship, with potential sponsors for the purposes of sponsorship. [2]
        To the extent permitted under law, I release the contents of my application under a CC0 Public Domain Dedication. [3]
        I understand that my responses to the questions marked with a caret (^) will be released publicly as Open Data. [4]
        """
    )
    acknowledgments = models.TextField(
        # Widget: Checkboxes -- choices are defined in forms.py
        verbose_name='Acknowledgments',
        help_text='Please check the boxes below to acknowledge your understanding. All boxes must be checked to submit your application. Links to the OpenCon Privacy Policy and the CC0 Public Domain Dedication are provided in the instructions above.',
        blank=False, # required
        validators=[EverythingCheckedValidator(len(ACKNOWLEDGMENTS_CHOICES))],
    )

    APPLICATION_STATUS_CHOICES=parse_raw_choices(
        """
        Draft [draft]
        Submitted [submitted]
        Draft Accepted as Final Application [submitted_draft]
        Under Review [under_review]
        Under Review by Sponsor [sponsor_review]
        Invitation Waitlist [waitlist_invitation]
        Scholarship Waitlist [waitlist_scholarship]
        Sponsor Waitlist [waitlist_sponsor]
        Invited [invited]
        Notified [notified]
        Registered [registered]
        Withdrawn [withdrawn]
        Deleted [deleted]
        """
    )

    application_status = models.TextField(
        verbose_name='Application Status',
        blank = True, # optional
    )

    # importing "attended" (when did this person attend OpenCon?) and "engagement" (how is this person engaged?) from drafts

    ATTENDED_CHOICES=parse_raw_choices(
        """
        OpenCon 2014 [2014]
        OpenCon 2015 [2015]
        OpenCon 2016 [2016]
        """
    )

    attended = models.TextField(
        verbose_name = 'OpenCon Attendance',
        blank = True, # optional
    )

    ENGAGEMENT_CHOICES=parse_raw_choices(
        """
        Alum of Previous OpenCon [alum]
        Satellite Event Host [satellite_host]
        RSVP'd to a Satellite Event [satellite_rsvp]
        RSVP'd to a Community Call [community_call_rsvp]
        RSVP'd to a Librarian Community Call [librarian_call_rsvp]
        Discussion List Subscriber [discussion_list]
        Applied in a Previous Year [applied_previously]
        """
    )

    engagement = models.TextField(
        verbose_name = 'OpenCon Engagement',
        blank = True, # optional
    )

    referred_by = models.CharField(
        max_length=settings.MAX_CUSTOM_REFERRAL_LENGTH,
        blank=True, null=True,
    )

    my_referral = models.CharField(
        max_length=10,
    )

    data_sent_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args):
        if not self.my_referral:
            possible_characters = string.ascii_letters + string.digits
            self.my_referral = ''.join(random.choice(possible_characters) for _ in range(5))

        self.recalculate_ratings()

        if self.data_sent_at is None:
            self.data_sent_at = timezone.now()
            self.send_data_by_mail()

        super().save(*args)

    def __str__(self):
        return self.full_name()

    def full_name(self):
        return ' '.join([self.first_name, self.last_name])

    def send_data_by_mail(self):
        if settings.SEND_EMAILS:
            message = render_to_string('application/email/data.txt', {'object': self, 'first_name': self.first_name, 'nickname': self.nickname, 'my_referral': self.my_referral,})
            email = EmailMessage(
                subject='OpenCon 2017 Application Received',
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[self.email],
                bcc=settings.EMAIL_DATA_BACKUP,
                reply_to=[settings.DEFAULT_REPLYTO_EMAIL],
            )
            email.content_subtype = "html"
            try:
                email.send(fail_silently=True)
            except:
                pass # #todo -- fix problem with sending e-mail

    def recalculate_ratings(self):
        self.need_rating0 = not self.ratings0.filter(decision='review').exists()

        # If no-one reviewed it
        if self.need_rating0:
            if self.ratings0.filter(decision='yes').count() >= YESES_NEEDED:
                self.need_rating0 = False
            elif self.ratings0.filter(decision='no').count() >= NOS_NEEDED:
                self.status = 'blacklisted'
                self.need_rating0 = False

        # At this point we established need_rating0 -- we will not need to alter it anymore unless there is an explicit whitelist / blacklist decision

        # Calculate rating scores
        try:
            rating1 = sum(r.rating for r in self.ratings.all()) / self.ratings.count()
        except ZeroDivisionError:
            rating1 = 0

        try:
            rating2 = sum(r.rating for r in self.ratings2.all()) / self.ratings2.count()
        except ZeroDivisionError:
            rating2 = 0

        self.rating1 = rating1
        self.rating2 = rating2

        # Normally, every application should have a certain number of reviews
        self.need_rating1 = self.ratings.count() < MAX_REVIEWS_ROUND_ONE
        self.need_rating2 = self.ratings2.count() < MAX_REVIEWS_ROUND_TWO

        # However, there are exceptions...
        # If this is a very low quality application
        if self.rating1 <= RATING_R1_LOW_THRESHOLD:
            # And it has exactly 1 review
            if self.ratings.count() == 1:
                # no other reviews are needed (i.e., do not get a second review)
                self.need_rating1 = False

        # Or if the rating is in the middle range <X,Y)
        elif NEEDED_RATING_FOR_THIRD_REVIEW_ROUND1 <= self.rating1 < NEEDED_RATING_TO_ROUND2:
            # And it has exactly 2 reviews
            if self.ratings.count() == 2:
                ratings = list(self.ratings.all())
                r1 = ratings[0].rating
                r2 = ratings[1].rating

                # And the difference between them is big enough
                if abs(r1-r2) > NEEDED_DIFFERENCE_FOR_THIRD_REVIEW_ROUND1:
                    # it needs a 3rd review ("third opinion")
                    self.need_rating1 = True

        if self.need_rating0:
            self.need_rating1 = False
            self.need_rating2 = False
        if self.need_rating1:
            self.need_rating2 = False

        if self.status == 'blacklisted':
            self.rating1 = 0
            self.rating2 = 0
            self.need_rating0 = False
            self.need_rating1 = False
            self.need_rating2 = False
        elif self.status == 'whitelist2':
            self.need_rating0 = False
            self.need_rating1 = False
            # self.need_rating2 = True  # commenting out this line because whitelist2 would then accept infinite number of reviews -- instead, rely on the logic above (`self.need_rating2 = self.ratings2.count() < MAX_REVIEWS_ROUND_TWO`)
            # R2 whitelisted apps still need to be rated (repeat of the code from a few lines above)
            self.need_rating2 = self.ratings2.count() < MAX_REVIEWS_ROUND_TWO
        elif self.status == 'whitelist3':
            self.need_rating0 = False
            self.need_rating1 = False
            self.need_rating2 = False

    rating1 = models.FloatField(default=0)
    rating2 = models.FloatField(default=0)
    need_rating0 = models.BooleanField(default=True)
    need_rating1 = models.BooleanField(default=True)
    need_rating2 = models.BooleanField(default=True)

    def get_rating1(self):
        return round(self.rating1, 1)

    def get_rating2(self):
        return round(self.rating2, 1)

    objects = ApplicationManager()

    def get_data(self, fields=None):
        fields = fields or [x for x in self.__dict__.keys() if not x.startswith('_')]
        data = []
        for field_name in fields:
            current_field = {}
            clean = self._meta.get_field(field_name)
            verbose_name = clean.verbose_name
            # clean up how verbose_name is displayed on rating forms
            verbose_name = verbose_name.rstrip('^').replace(' (Optional)', '').replace('Country of ', '')
            value = getattr(self, field_name)
            if field_name=='area_of_interest':
                value=''.join([item[1] for item in AREA_OF_INTEREST_CHOICES if item[0] == value])
            # 2017-07-21`23:26:04 -- intentionally commented out: when enabled, "experience" not displayed on R2 form
            # #todo -- fix other fields as well (when rating is over)
            # if field_name=='experience':
            #     value=''.join([item[1] for item in EXPERIENCE_CHOICES if item[0] == value])
            if field_name=='fields_of_study':
                value=''.join([item[1] for item in FIELDS_OF_STUDY_CHOICES if item[0] == value])
            if value:
                current_field.update({'title': verbose_name, 'content': value, 'name': field_name})
            if clean.help_text:
                current_field.update({'help': clean.help_text})
            if current_field:
                data.append(current_field)
        return data

    status = models.TextField(choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0])
    status_reason = models.TextField(null=True, blank=True)
    status_by = models.ForeignKey('rating.User', related_name='statuses', null=True, blank=True)
    status_ip = models.GenericIPAddressField(blank=True, null=True)
    status_at = models.DateTimeField(blank=True, null=True)

    def change_status(self, to, by, ip, reason):
        self.status = to
        self.status_by = by
        self.status_ip = ip
        self.status_at = timezone.now()
        self.status_reason = reason
        self.save()

"""
class Application(TimestampMixin, models.Model):
    # field no. 1
    email = models.EmailField(
        verbose_name='E-Mail Address',
        help_text='Please fill in your e-mail address and click “Start Application” to unlock the rest of the form.',
        unique=True,
    )
    # field no. 2
    first_name = models.CharField(
        verbose_name='First / Given Name',
        max_length=50,
    )
    # field no. 3
    last_name = models.CharField(
        verbose_name='Last / Family Name',
        max_length=50,
    )
    # field no. 4
    nickname = models.CharField(
        verbose_name='Nickname / Preferred Name (Optional)',
        help_text='If you would like us to call you something different than the first name you entered above, '
                  'please tell us here. For example, if your name is “Michael” and you want to be called “Mike.”',
        max_length=50,
        blank=True, null=True,
    )
    # field no. 5
    alternate_email = models.EmailField(
        verbose_name='Alternate E-mail Address (Optional)',
        help_text='If you use another e-mail address that you would like to have on record, please enter it '
                  'here. We will only use this address if we cannot reach you at the address you provided above.',
        blank=True, null=True,
    )
    # field no. 6
    twitter_username = models.CharField(
        verbose_name='Twitter Username (Optional)',
        help_text='Include the username only, for example “@open_con”.',
        max_length=50,
        blank=True, null=True,
    )
    # field no. 7
    institution = models.ForeignKey(  # update the related name and verbose name in forms.py
        'Institution',
        related_name='person',
        blank=True, null=True,
    )
    # field no. 8
    # #todo -- consider renaming "organization" (affiliation_2?) + also "institution" (affiliation_1?)
    organization = models.ForeignKey(  # update the related name and verbose name in forms.py
        'Organization',
        related_name='person',
        blank=True, null=True,
    )
    # field no. 9
    area_of_interest = models.TextField(
        verbose_name='What is your primary area of interest?^',
        help_text='If there are multiple areas you are interested in, please select the one that best describes '
                  'your interest. Please note that OpenCon focuses on these issues in the specific context of '
                  'research and education.',
    )
    # field no. 10
    description = models.TextField(
        verbose_name='Describe yourself in 1-2 sentences.',
        help_text='Maximum 280 characters (~40 words). It’s up to you what information to provide. Many people '
                  'write something similar to their Twitter or Facebook bio.',
        max_length=280,
        validators=[MinLengthValidator(10)],
    )
    # field no. 11
    interested = models.TextField(
        verbose_name='Why are you interested in Open Access, Open Education and/or Open Data and how does it '
                     'relate to your work? If you are already involved in these issues, tell us how.',
        help_text='Maximum 1600 characters (~250 words). There are many reasons why Open is important. This '
                  'question is asking specifically why Open is important to *you*. Please use your own words '
                  'to describe your perspective and experience.',
        max_length=1600,
        validators=[MinLengthValidator(10)],
    )
    # field no. 12
    goal = models.TextField(
        verbose_name='The biggest goal of OpenCon is to catalyze action. What ideas do you have for advancing '
                     'Open Access, Open Education and/or Open Data, and how would you use your experience at '
                     'OpenCon to have an impact?',
        help_text='Maximum 1600 characters (~250 words).',
        max_length=1600,
        validators=[MinLengthValidator(10)],
    )
    # field no. 13
    # this is an optional question where we don't mention "(Optional)" in the verbose_name
    participation = models.TextField(
        verbose_name='Are you planning to participate in any of the following events in the next year? Have '
                     'you participated in any of them in the past?^',
        help_text='Check all that apply.',
        validators=[MinChoicesValidator(1), none_validator],
    )
    # field no. 14
    participation_text = models.TextField(
        verbose_name='For the events you checked, please explain how you participated and/or how you plan to '
                     'participate.',
        help_text='Maximum 600 characters (~100 words).',
        max_length=600,
        blank=True, null=True,
    )
    # field no. 15 (formerly 16)
    citizenship = models.TextField(
        verbose_name='Country of Citizenship^',
        help_text='Please select the country where you are a citizen (i.e. where your passport is from). If your '
                  'country isn’t listed, select “Country Not Listed” and indicate your country in the Comments '
                  'Box at the end of the application form.',
    )
    # field no. 16 (formerly 17)
    residence = models.TextField(
        verbose_name='Country of Residence^',
        help_text='Please select the country where you currently reside. If you are a resident of multiple '
                  'countries, pick the one where you will spend the most time this year. If your country isn’t '
                  'listed, see the previous question for instructions.',
    )
    # field no. 17 (formerly 15)
    # Has special field
    gender = models.CharField(
        max_length=80
    )
    # field no. 18
    occupation = models.TextField(
        verbose_name='What is your primary occupation?^',
        help_text='Please check the occupation that best describes what you do. If there are multiple options '
                  'that equally describe you, you may select up to three.',
        validators=[MaxChoicesValidator(3), none_validator],
    )
    # field no. 19
    degree = models.TextField(
        verbose_name='Which academic degrees have you attained, if any?^',
        help_text='Only check the degrees you have already been awarded. Note that there are no minimum academic '
                  'requirements to attend OpenCon, this question just helps us understand more about you.',
        validators=[none_validator],
    )
    # field no. 20
    experience = models.TextField(
        verbose_name='How many years have you worked in a career full time? For the purposes of this question, '
                     'please do *not* include time when you were a full time student or working full time as '
                     'a PhD candidate.^',
        help_text='If you have worked in multiple careers, please add the years together. Note that there is no '
                  'minimum career experience required to attend OpenCon, this question just helps us understand '
                  'more about you.',
        max_length=80,
    )
    # field no. 21
    fields_of_study = models.TextField(
        verbose_name='Which option below best describes your field of expertise or study?^',
        # #fyi -- "none_validator" not needed for this field -- this is Select, not CheckboxSelectMultiple
    )
    # field no. x (DELETED)
    # ideas = models.TextField(
    #     verbose_name='What ideas do you have for getting involved in Open Access, Open Education and/or Open Data? '
    #                  'If you are already involved, tell us how.',
    #     help_text='Maximum 1200 characters (~200 words).',
    #     max_length=1200,
    #     validators=[MinLengthValidator(10)],
    # )
    # field no. 22
    skills = models.TextField(
        # verbose_name and help_text are defined in forms.py
    )
    # field no. 23
    how_did_you_find_out = models.TextField(
        # verbose_name and help_text are defined in forms.py
        blank=True, null=True,
    )
    # # field no. x (DELETED)
    # visa_requirements = models.TextField(
    #     verbose_name='Visa requirements',
    #     help_text='Please review information on U.S. Visa eligibility and the Visa Waiver Program (ESTA) select '
    #               'the option below that best describes you. Note that requirements have recently changed. If you '
    #               'are still not sure, select “I’m not sure”.',
    # )
    # field no. 24
    # #todo -- rename field more appropriately?
    scholarship = models.CharField(
        verbose_name='OpenCon is a global event that seeks to bring together participants regardless of their '
                     'ability to pay for travel and expenses. Therefore, we seek to allocate our limited '
                     'scholarship funding carefully to the participants who need it most. How likely would '
                     'you be able to raise or contribute funding to your attendance at OpenCon 2016 if invited?',
        help_text='If you are applying for a sponsored scholarship from a university or organization, please select '
                  '“I couldn’t cover any of my expenses and could only attend if a full scholarship is provided.”',
        choices=(
            ('i_can_pay_everything', 'I could cover all of my expenses and do not need any scholarship funding'),
            ('i_can_pay_large_part', 'I could likely cover a large part of my expenses'),
            ('i_can_pay_small_part', 'I could likely cover a small part of my expenses'),
            ('i_can_pay_nothing',    'I couldn’t cover any of my expenses and could only attend if a full scholarship is provided'),
        ),
        default=None,
        max_length=20, # longest string above ('i_can_pay_everything') is 20 characters long
    )
    # field no. 25
    expenses = models.TextField(
        verbose_name='Which expenses would you need a scholarship to pay for?',
        help_text='Please select the expenses for which you would need scholarship funding in order to attend. If you are applying '
                  'for a sponsored scholarship from a university or organization, please select all of the expenses below. Please '
                  'note that scholarships do not include incidental expenses such as airport transit or meals outside of the conference.',
        validators=[none_validator],
    )
    # field no. 26
    location = models.CharField(
        verbose_name='OpenCon 2016 takes place in Washington, DC. If invited to attend, what city would you travel '
                     'to and from to get there?',
        help_text='Please list city, state/province (if applicable) AND country. For example, “San Francisco, '
                  'CA, United States”.',
        max_length=200,
    )
    # field no. 27
    airport = models.ForeignKey(
        'Airport',
        # verbose_name and help_text are defined in forms.py
    )
    # field no. 28
    additional_info = models.TextField(
        verbose_name='Comments Box (Optional)',
        help_text='Use this box for any additional information you would like to share about yourself, '
                  'projects you work on, or other information that could impact your attendance or participation '
                  'at OpenCon 2016, if invited. Maximum 900 characters, ~150 words.',
        max_length=900,
        blank=True, null=True
    )
    # field no. 29
    opt_outs = models.TextField(
        verbose_name='Opt-Outs',
        help_text='Please check the boxes below to opt-out.',
        blank=True, null=True
    )
    # field no. 30
    acknowledgements = models.TextField(
        help_text='Please check the boxes below to acknowledge your understanding. All boxes must be checked. '
                  'To review OpenCon’s Privacy Policy, click here: http://www.opencon2016.org/privacy',
        validators=[EverythingCheckedValidator(len(ACKNOWLEDGEMENT_CHOICES))],
    )

    referred_by = models.CharField(
        max_length=settings.MAX_CUSTOM_REFERRAL_LENGTH,
        blank=True, null=True,
    )

    my_referral = models.CharField(
        max_length=10,
    )

    data_sent_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args):
        if not self.my_referral:
            possible_characters = string.ascii_letters + string.digits
            self.my_referral = ''.join(random.choice(possible_characters) for _ in range(5))

        self.recalculate_ratings()

        if self.data_sent_at is None:
            self.data_sent_at = timezone.now()
            self.send_data_by_mail()

        super().save(*args)

    def __str__(self):
        return self.full_name()

    def full_name(self):
        return ' '.join([self.first_name, self.last_name])

    def send_data_by_mail(self):
        if settings.SEND_EMAILS:
            message = render_to_string('application/email/data.txt', {'object': self, 'first_name': self.first_name, 'nickname': self.nickname, 'my_referral': self.my_referral,})
            email = EmailMessage(
                subject='OpenCon 2017 Application Received',
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[self.email],
                bcc=settings.EMAIL_DATA_BACKUP,
                reply_to=[settings.DEFAULT_REPLYTO_EMAIL],
            )
            email.content_subtype = "html"
            try:
                email.send(fail_silently=True)
            except:
                pass # #todo -- fix problem with sending e-mail


    def recalculate_ratings(self):
        try:
            rating1 = sum(r.rating for r in self.ratings.all()) / self.ratings.count()
        except ZeroDivisionError:
            rating1 = 0

        try:
            rating2 = sum(r.rating for r in self.ratings2.all()) / self.ratings2.count()
        except ZeroDivisionError:
            rating2 = 0

        self.rating1 = rating1
        self.rating2 = rating2

        # Normally, every application should have a certain number of reviews
        self.need_rating1 = self.ratings.count() < MAX_REVIEWS_ROUND_ONE
        self.need_rating2 = self.ratings2.count() < MAX_REVIEWS_ROUND_TWO

        # However, there are exceptions...
        # If this is a very low quality application
        if self.rating1 <= RATING_R1_LOW_THRESHOLD:
            # And it has exactly 1 review
            if self.ratings.count() == 1:
                # no other reviews are needed (i.e., do not get a second review)
                self.need_rating1 = False

        # Or if the rating is in the middle range <X,Y)
        elif NEEDED_RATING_FOR_THIRD_REVIEW_ROUND1 <= self.rating1 < NEEDED_RATING_TO_ROUND2:
            # And it has exactly 2 reviews
            if self.ratings.count() == 2:
                ratings = list(self.ratings.all())
                r1 = ratings[0].rating
                r2 = ratings[1].rating

                # And the difference between them is big enough
                if abs(r1-r2) > NEEDED_DIFFERENCE_FOR_THIRD_REVIEW_ROUND1:
                    # it needs a 3rd review ("third opinion")
                    self.need_rating1 = True

        if self.status == 'blacklisted':
            self.rating1 = 0
            self.rating2 = 0
            self.need_rating1 = False
            self.need_rating2 = False
        elif self.status == 'whitelist2':
            self.need_rating1 = False
        elif self.status == 'whitelist3':
            self.need_rating1 = False
            self.need_rating2 = False

    rating1 = models.FloatField(default=0)
    rating2 = models.FloatField(default=0)
    need_rating1 = models.BooleanField(default=True)
    need_rating2 = models.BooleanField(default=True)

    def get_rating1(self):
        return round(self.rating1, 1)

    def get_rating2(self):
        return round(self.rating2, 1)

    objects = ApplicationManager()

    def get_data(self, fields=None):
        fields = fields or [x for x in self.__dict__.keys() if not x.startswith('_')]
        data = []
        for field_name in fields:
            current_field = {}
            clean = self._meta.get_field(field_name)
            value = getattr(self, field_name)
            if field_name=='area_of_interest':
                value=''.join([item[1] for item in AREA_OF_INTEREST_CHOICES if item[0] == value])
            if field_name=='experience':
                value=''.join([item[1] for item in EXPERIENCE_CHOICES if item[0] == value])
            if field_name=='fields_of_study':
                value=''.join([item[1] for item in FIELDS_OF_STUDY_CHOICES if item[0] == value])
            if value:
                current_field.update({'title': clean.verbose_name, 'content': value, 'name': field_name})
            if clean.help_text:
                current_field.update({'help': clean.help_text})
            if current_field:
                data.append(current_field)
        return data

    status = models.TextField(choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0])
    status_reason = models.TextField(null=True, blank=True)
    # status_by = models.ForeignKey('rating.User', related_name='statuses', null=True, blank=True)
    status_by = models.TextField(null=True, blank=True)
    status_ip = models.GenericIPAddressField(blank=True, null=True)
    status_at = models.DateTimeField(blank=True, null=True)

    def change_status(self, to, by, ip, reason):
        self.status = to
        self.status_by = by
        self.status_ip = ip
        self.status_at = timezone.now()
        self.status_reason = reason
        self.save()
"""

class Reference(TimestampMixin, models.Model):
    key = models.CharField(max_length=settings.MAX_CUSTOM_REFERRAL_LENGTH, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    text = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='organizations/', blank=True, null=True) # not used in 2017 due to switch to Docker (use image_url instead)
    image_url = models.CharField(max_length=255, blank=True) # optional URL to image (e.g. logo)
    deadline = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return '{1} - {0}'.format(self.name, self.key)
