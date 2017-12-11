from django.core.management.base import BaseCommand, CommandError
from ...models import Application2017
import sys


class Command(BaseCommand):
    help = 'Recalculate ratings for applications'

    def handle(self, *args, **options):
        applications = Application2017.objects.all()
        app_count = applications.count()

        for i, application in enumerate(applications):
            application.save()
            if i % 20 == 0:
                sys.stdout.write('\rRecalculated: {0:.2f}%'.format(i/app_count*100))

        print('\nRecalculation done!')
