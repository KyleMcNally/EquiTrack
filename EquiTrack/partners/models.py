__author__ = 'jcranwellward'

import datetime
from copy import deepcopy

import reversion
from django.db import models, transaction
from django.core import urlresolvers

from filer.fields.file import FilerFileField
from smart_selects.db_fields import ChainedForeignKey

from funds.models import Grant
from reports.models import (
    ResultStructure,
    IntermediateResult,
    Rrp5Output,
    Indicator,
    Activity,
    Sector,
    Goal,
    WBS,
)
from locations.models import (
    Governorate,
    GatewayType,
    Locality,
    Location,
    Region,
)


class PartnerOrganization(models.Model):

    name = models.CharField(max_length=45L, unique=True)
    description = models.CharField(max_length=256L, blank=True)
    email = models.CharField(max_length=128L, blank=True)
    contact_person = models.CharField(max_length=64L, blank=True)
    phone_number = models.CharField(max_length=32L, blank=True)

    def __unicode__(self):
        return self.name


class PCA(models.Model):

    PCA_STATUS = (
        (u'in_process', u"In Process"),
        (u'active', u"Active"),
        (u'implemented', u"Implemented"),
        (u'cancelled', u"Cancelled"),
    )

    result_structure = models.ForeignKey(ResultStructure, blank=True, null=True)
    number = models.CharField(max_length=45L, blank=True)
    title = models.CharField(max_length=256L)
    status = models.CharField(max_length=32L, blank=True, choices=PCA_STATUS, default=u'in_process')
    partner = models.ForeignKey(PartnerOrganization)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    initiation_date = models.DateField()
    signed_by_unicef_date = models.DateField(null=True, blank=True)
    signed_by_partner_date = models.DateField(null=True, blank=True)
    unicef_mng_first_name = models.CharField(max_length=64L, blank=True)
    unicef_mng_last_name = models.CharField(max_length=64L, blank=True)
    unicef_mng_email = models.CharField(max_length=128L, blank=True)
    partner_mng_first_name = models.CharField(max_length=64L, blank=True)
    partner_mng_last_name = models.CharField(max_length=64L, blank=True)
    partner_mng_email = models.CharField(max_length=128L, blank=True)
    partner_contribution_budget = models.IntegerField(null=True, blank=True, default=0)
    unicef_cash_budget = models.IntegerField(null=True, blank=True, default=0)
    in_kind_amount_budget = models.IntegerField(null=True, blank=True, default=0)
    cash_for_supply_budget = models.IntegerField(null=True, blank=True, default=0)
    total_cash = models.IntegerField(null=True, blank=True, verbose_name='Total Budget', default=0)

    # meta fields
    sectors = models.CharField(max_length=255, null=True, blank=True)
    current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    amendment = models.BooleanField(default=False)
    amended_at = models.DateTimeField(null=True)
    amendment_number = models.IntegerField(default=0)
    original = models.ForeignKey('PCA', null=True)

    class Meta:
        verbose_name = 'PCA'
        verbose_name_plural = 'PCAs'

    def __unicode__(self):
        title = u'{}: {}'.format(
            self.partner.name,
            self.number
        )
        if self.amendment:
            title = u'{} (Amendment: {})'.format(
                title, self.amendment
            )
        return title

    @property
    def sector_id(self):
        sectors = self.pcasector_set.all()
        if sectors:
            return sectors[0].sector.id
        return 0

    def total_unicef_contribution(self):
        return self.unicef_cash_budget + self.in_kind_amount_budget
    total_unicef_contribution.short_description = 'Total Unicef contribution budget'

    def make_amendment(self, user):
        """
        Creates an amendment (new record) of this PCA copying
        over all values and related objects, marks the existing
        PCA as non current and creates a manual restore point.
        The user who created the amendment is also captured.
        """
        with transaction.atomic(), reversion.create_revision():

            # make original as non current
            original = self
            original.current = False
            original.save()

            # copy base properties to new object
            amendment = deepcopy(original)
            amendment.pk = None
            amendment.amendment = True
            amendment.amended_at = datetime.datetime.now()
            amendment.amendment_number += 1  # increment amendment count
            amendment.original = original
            amendment.save()

            # make manual revision point
            reversion.set_user(user)
            reversion.set_comment("Amendment {} created for PCA: {}".format(
                self.amendment_number,
                self.number)
            )

        # copy over grants
        for grant in original.pcagrant_set.all():
            PCAGrant.objects.create(
                pca=amendment,
                grant=grant.grant,
                funds=grant.funds
            )

        # copy over sectors
        for pca_sector in original.pcasector_set.all():
            new_sector = PCASector.objects.create(
                pca=amendment,
                sector=pca_sector.sector
            )

            for output in pca_sector.pcasectoroutput_set.all():
                PCASectorOutput.objects.create(
                    pca_sector=new_sector,
                    output=output.output
                )

            for goal in pca_sector.pcasectorgoal_set.all():
                PCASectorGoal.objects.create(
                    pca_sector=new_sector,
                    goal=goal.goal
                )

            for activity in pca_sector.pcasectoractivity_set.all():
                PCASectorActivity.objects.create(
                    pca_sector=pca_sector,
                    activity=activity.activity
                )

            # copy over indicators for sectors and reset programmed number
            for pca_indicator in pca_sector.indicatorprogress_set.all():
                IndicatorProgress.objects.create(
                    pca_sector=new_sector,
                    indicator=pca_indicator.indicator,
                    programmed=0
                )

            # copy over intermediate results and activities
            for pca_ir in pca_sector.pcasectorimmediateresult_set.all():
                new_ir = PCASectorImmediateResult.objects.create(
                    pca_sector=new_sector,
                    Intermediate_result=pca_ir.Intermediate_result
                )
                new_ir.wbs_activities = pca_ir.wbs_activities.all()

        # copy over locations
        for location in original.locations.all():
            GwPCALocation.objects.create(
                pca=amendment,
                governorate=location.governorate,
                region=location.region,
                locality=location.locality,
                gateway=location.location.gateway,
                location=location.location
            )

    def save(self, **kwargs):
        """
        Calculate total cash on save
        """
        self.total_cash = (
            self.partner_contribution_budget or 0 +
            self.unicef_cash_budget or 0 +
            self.in_kind_amount_budget or 0
        )

        # populate sectors display string
        if self.pcasector_set.all().count():
            self.sectors = ", ".join(
                [sector.sector.name for sector in self.pcasector_set.all()]
            )

        super(PCA, self).save(**kwargs)


class PCAGrant(models.Model):
    pca = models.ForeignKey(PCA)
    grant = models.ForeignKey(Grant)
    funds = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-funds']

    def __unicode__(self):
        return self.grant


class GwPCALocation(models.Model):

    pca = models.ForeignKey(PCA, related_name='locations')
    governorate = models.ForeignKey(Governorate)
    region = ChainedForeignKey(
        Region,
        chained_field="governorate",
        chained_model_field="governorate",
        show_all=False,
        auto_choose=True,
    )
    locality = ChainedForeignKey(
        Locality,
        chained_field="region",
        chained_model_field="region",
        show_all=False,
        auto_choose=True,
    )
    gateway = models.ForeignKey(GatewayType, null=True, blank=True)
    location = ChainedForeignKey(
        Location,
        chained_field="locality",
        chained_model_field="locality",
        show_all=False,
        auto_choose=True
    )

    class Meta:
        verbose_name = 'Activity Location'

    def __unicode__(self):
        return u'{} -> {} -> {} -> {} ({})'.format(
            self.governorate.name,
            self.region.name,
            self.locality.name,
            self.location.name,
            self.location.gateway.name
        )

    def view_location(self):
        if self.id:
            url_name = 'admin:{app_label}_{model_name}_{action}'.format(
                app_label=self.location._meta.app_label,
                model_name=self.location._meta.model_name,
                action='change'
            )
            location_url = urlresolvers.reverse(url_name, args=(self.location.id,))
            return u'<a class="btn btn-primary default" ' \
                   u'onclick="return showAddAnotherPopup(this);" ' \
                   u'href="{}" target="_blank">View</a>'.format(location_url)
        return u''
    view_location.allow_tags = True
    view_location.short_description = 'View Location'


class PCASector(models.Model):

    pca = models.ForeignKey(PCA)
    sector = models.ForeignKey(Sector)

    class Meta:
        verbose_name = 'PCA Sector'

    def __unicode__(self):
        return u'{}: {}: {}'.format(
            self.pca.partner.name,
            self.pca.number,
            self.sector.name,
        )

    def changeform_link(self):
        if self.id:
            url_name = 'admin:{app_label}_{model_name}_{action}'.format(
                app_label=self._meta.app_label,
                model_name=self._meta.model_name,
                action='change'
            )
            changeform_url = urlresolvers.reverse(url_name, args=(self.id,))
            return u'<a class="btn btn-primary default" ' \
                   u'onclick="return showAddAnotherPopup(this);" ' \
                   u'href="{}" target="_blank">Details</a>'.format(changeform_url)
        return u''
    changeform_link.allow_tags = True
    changeform_link.short_description = 'View Sector Details'


class PCASectorOutput(models.Model):

    pca_sector = models.ForeignKey(PCASector)
    output = models.ForeignKey(Rrp5Output)

    class Meta:
        verbose_name = 'Output'
        verbose_name_plural = 'Outputs'


class PCASectorGoal(models.Model):

    pca_sector = models.ForeignKey(PCASector)
    goal = models.ForeignKey(Goal)

    class Meta:
        verbose_name = 'CCC'
        verbose_name_plural = 'CCCs'


class PCASectorActivity(models.Model):

    pca_sector = models.ForeignKey(PCASector)
    activity = models.ForeignKey(Activity)

    class Meta:
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'


class PCASectorImmediateResult(models.Model):

    pca_sector = models.ForeignKey(PCASector)
    Intermediate_result = models.ForeignKey(IntermediateResult)

    wbs_activities = models.ManyToManyField(WBS)

    def __unicode__(self):
        return self.Intermediate_result.name


class IndicatorProgress(models.Model):

    pca_sector = models.ForeignKey(PCASector)
    indicator = models.ForeignKey(Indicator)
    programmed = models.IntegerField()
    current = models.IntegerField(blank=True, null=True, default=0)

    def __unicode__(self):
        return self.indicator.name

    def shortfall(self):
        return self.programmed - self.current if self.id and self.current else 0
    shortfall.short_description = 'Shortfall'

    def unit(self):
        return self.indicator.unit.type if self.id else ''
    unit.short_description = 'Unit'


class FileType(models.Model):
    name = models.CharField(max_length=64L, unique=True)

    def __unicode__(self):
        return self.name


class PCAFile(models.Model):

    pca = models.ForeignKey(PCA)
    type = models.ForeignKey(FileType)
    file = FilerFileField()

    def __unicode__(self):
        return file.name

    def download_url(self):
        if self.file:
            return u'<a class="btn btn-primary default" ' \
                   u'href="{}" >Download</a>'.format(self.file.file.url)
        return u''
    download_url.allow_tags = True
    download_url.short_description = 'Download Files'


class PCAReport(models.Model):
    pca = models.ForeignKey(PCA)
    title = models.CharField(max_length=128L)
    description = models.CharField(max_length=512L)
    start_period = models.DateField(null=True, blank=True)
    end_period = models.DateField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)