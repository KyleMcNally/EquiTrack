__author__ = 'jcranwellward'

from rest_framework import serializers

from .models import GwPCALocation


class GWLocationSerializer(serializers.ModelSerializer):

    pca_title = serializers.CharField(source='pca.title')
    pca_number = serializers.CharField(source='pca.number')
    pca_id = serializers.CharField(source='pca.id')
    partner_name = serializers.CharField(source='pca.partner.name')
    partner_id = serializers.CharField(source='pca.partner.id')
    sector_name = serializers.CharField(source='pca.sectors')
    sector_id = serializers.CharField(source='pca.sector_id')
    latitude = serializers.CharField(source='location.point.y')
    longitude = serializers.CharField(source='location.point.x')
    location_name = serializers.CharField(source='location.name')
    location_type = serializers.CharField(source='location.gateway.name')
    gateway_name = serializers.CharField(source='location.gateway.name')
    gateway_id = serializers.CharField(source='location.gateway.id')

    class Meta:
        model = GwPCALocation