from import_export import resources
from .models import Application2017, Draft
from opencon.rating.models import User, Round0Rating, Round1Rating, Round2Rating

class Application2017Resource(resources.ModelResource):
    class Meta:
        model = Application2017
        fields = 'id email created_at citizenship residence profession experience field gender engagement referred_by need_rating0 need_rating1 need_rating2 rating1 rating2 status'.split()
        # fields = ('id', 'name', 'author', 'price',)
        # exclude = ('tags',)
        # export_order = ('id', 'price', 'author', 'name',)

        # #todo -- check "orcid", resolve "status_by"

    def get_queryset(self):
        return self._meta.model.objects.order_by('id') # sort

class DraftResource(resources.ModelResource):
    class Meta:
        model = Draft

    def get_queryset(self):
        return self._meta.model.objects.order_by('id') # sort

class UserResource(resources.ModelResource):
    class Meta:
        model = User

    def get_queryset(self):
        return self._meta.model.objects.order_by('id') # sort

class Round0RatingResource(resources.ModelResource):
    class Meta:
        model = Round0Rating
        fields = 'id decision application created_by'.split()

    def get_queryset(self):
        return self._meta.model.objects.order_by('id') # sort

class Round1RatingResource(resources.ModelResource):
    class Meta:
        model = Round1Rating
        fields = 'id rating application created_by'.split()

    def get_queryset(self):
        return self._meta.model.objects.order_by('id') # sort

class Round2RatingResource(resources.ModelResource):
    class Meta:
        model = Round2Rating

    def get_queryset(self):
        return self._meta.model.objects.order_by('id') # sort
