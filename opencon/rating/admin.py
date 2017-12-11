from django.contrib import admin
from .models import User, Round1Rating, Round2Rating, Round0Rating


class UserAdmin(admin.ModelAdmin):
    list_display = ('nick', 'email', 'first_name', 'last_name', 'organizer', 'invitation_sent', 'disabled_at')
    list_per_page = 500  # pagination
    search_fields = ('nick', 'email', 'first_name', 'last_name', )

admin.site.register(User, UserAdmin)


@admin.register(Round0Rating)
class Round0RatingAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_by', 'application', 'decision', 'created_at']
    list_per_page = 500  # pagination
    search_fields = ('application__first_name', 'application__last_name', 'application__email', )


@admin.register(Round1Rating)
class Round1RatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_by', 'application', 'rating', 'created_at')
    list_per_page = 500  # pagination
    search_fields = ('application__first_name', 'application__last_name', 'application__email', )


@admin.register(Round2Rating)
class Round2RatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_by', 'application', 'rating', 'created_at')
    list_per_page = 500  # pagination
    search_fields = ('application__first_name', 'application__last_name', 'application__email', )
