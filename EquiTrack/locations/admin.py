__author__ = 'jcranwellward'

from django.contrib.gis import admin

from . import models


class LocationAdmin(admin.GeoModelAdmin):

    fields = (
        'name',
        'gateway',
        'p_code',
        'point'
    )
    list_display = (
        'name',
        'gateway',
        'p_code',
        'locality',
    )
    search_fields = ('name', 'p_code',)
    list_filter = ('gateway', 'locality',)


class LocalityAdmin(admin.GeoModelAdmin):
    search_fields = ('name',)


admin.site.register(models.Governorate, admin.GeoModelAdmin)
admin.site.register(models.Region, admin.GeoModelAdmin)
admin.site.register(models.Locality, LocalityAdmin)
admin.site.register(models.Location, LocationAdmin)
admin.site.register(models.GatewayType)
