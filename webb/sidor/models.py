"""
Webbplatsens sidtyper.

Texterna redigeras i Wagtail. Källförteckningen och uppdateringarna
hämtas ur Fornmeds databas när sidan visas (se kallor.py), så att de
alltid stämmer med det som söktjänsten svarar med.
"""

import urllib.parse

from django.db import models
from django.http import Http404
from wagtail.admin.panels import FieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import RichTextField
from wagtail.models import Page

from . import kallor, klartext, lankade_data, lankar, register, sokning, texter


class TextSida(Page):
    """En vanlig sida med ingress och brödtext."""

    ingress = models.TextField(blank=True)
    brodtext = RichTextField(blank=True)
    visa_omfang = models.BooleanField(
        "visa databasens omfång", default=False,
        help_text="Visar antal verk, passager, påståenden och källsamlingar under texten, hämtat ur databasen.")

    content_panels = Page.content_panels + [FieldPanel("ingress"), FieldPanel("brodtext"),
                                            FieldPanel("visa_omfang")]

    def get_context(self, request, *args, **kwargs):
        kontext = super().get_context(request, *args, **kwargs)
        if self.visa_omfang:
            kontext["omfang"] = kallor.omfang()
        return kontext

    class Meta:
        verbose_name = "textsida"
        verbose_name_plural = "textsidor"


class StartSida(TextSida):
    """Startsidan, med de senaste uppdateringarna under brödtexten."""

    parent_page_types = ["wagtailcore.Page"]

    def get_context(self, request, *args, **kwargs):
        kontext = super().get_context(request, *args, **kwargs)
        kontext["leveranser"] = kallor.leveranser()[:3]
        kontext["omfang"] = kallor.omfang()
        return kontext

    class Meta:
        verbose_name = "startsida"


class KallforteckningSida(RoutablePageMixin, TextSida):
    """Källorna i bokstavsordning med licens och språkversioner.

    Varje verk har dessutom en egen sida under verk/<verk_id>/, där texten
    hämtas från API:et och visas med mallen sidor/verk.html.
    """

    def get_context(self, request, *args, **kwargs):
        kontext = super().get_context(request, *args, **kwargs)
        kontext["kallor"] = kallor.kallforteckning()
        kontext["bokstaver"] = sorted({k["bokstav"] for k in kontext["kallor"]}, key=kallor.sorteringsnyckel)
        return kontext

    @path("")
    def forteckning(self, request):
        return self.render(request)

    @path("verk/<slug:adress>/")
    def verk(self, request, adress: str):
        try:
            sida = texter.verkets_sida(texter.verk_id(adress), request.GET.get("utgava"), request.GET.get("del"),
                                       request.GET.get("parallellt"))
        except texter.TextFel as fel:
            if fel.kod == 404:
                raise Http404(str(fel)) from fel
            svar = self.render(request, template="sidor/verk_fel.html", context_overrides={"fel": str(fel)})
            svar.status_code = 503 if fel.kod >= 500 else fel.kod
            return svar
        # Forskningens bedömningar av verket (äkthet, datering) med motivering
        try:
            uppgifter = texter._hamta("/v1/verk/" + urllib.parse.quote(sida["verk"]["id"], safe=":"))
            sida["bedomningar"] = [klartext.bedomningsruta(b) for b in uppgifter.get("bedomningar", [])]
            # Bedömningar av enskilda vittnen, t.ex. en förfalskad avskrift av ett äkta brev
            sida["bedomningar"] += [klartext.bedomningsruta({**b, "vittnestyp": v["typ"], "vittne": v["beskrivning"]})
                                    for v in uppgifter.get("vittnen", []) for b in v.get("bedomningar", [])]
        except texter.TextFel:
            uppgifter = None
            sida["bedomningar"] = []
        sida["tryck"] = klartext.tryck(uppgifter or {})
        # Påståendena ur verket visas i en egen ruta, skild från källtexten
        sida["pastaenden"] = register.verkets_pastaenden(sida["verk"]["id"])
        # Rutan visas när läsaren slår på reglaget; utan skript styrs den av adressen
        sida["pastaenden_pa"] = request.GET.get("pastaenden") == "1"
        param = request.GET.copy()
        if sida["pastaenden_pa"]:
            param.pop("pastaenden", None)
        else:
            param["pastaenden"] = "1"
        sida["pastaenden_vaxla_url"] = "?" + param.urlencode()
        # Länkade data: Schema.org för sökmotorer och länkar till postens RDF
        verkets_id = sida["verk"]["id"]
        sida["jsonld"] = lankade_data.verk({**sida["verk"], **(uppgifter or {})},
                                           request.build_absolute_uri(request.path))
        sida["rdf_alternativ"] = lankade_data.alternativ("verk", verkets_id)
        return self.render(request, template="sidor/verk.html", context_overrides=sida)

    class Meta:
        verbose_name = "källförteckning"


class SokSida(TextSida):
    """Sökningen med filter, fasetter, karta och tidslinje (se sokning.py)."""

    def get_context(self, request, *args, **kwargs):
        kontext = super().get_context(request, *args, **kwargs)
        kontext.update(sokning.sok(request.GET))
        return kontext

    class Meta:
        verbose_name = "söksida"


class RegisterSida(RoutablePageMixin, TextSida):
    """
    Registret över personer, platser, institutioner, ämbeten, folk och begrepp.
    Varje entitet har en egen sida under sin adress (se lankar.entitetsadress och register.py).
    """

    # Översikten är en vanlig textsida; Wagtail skulle annars söka sidor/register_sida.html
    template = "sidor/text_sida.html"

    @path("")
    def oversikt(self, request):
        return self.render(request)

    @path("<str:adress>/")
    def entitet(self, request, adress: str):
        fran = request.GET.get("fran", "0")
        try:
            sida = register.entitetens_sida(lankar.entitet_id(adress), int(fran) if fran.isdigit() else 0)
        except texter.TextFel as fel:
            if fel.kod == 404:
                raise Http404(str(fel)) from fel
            svar = self.render(request, template="sidor/verk_fel.html", context_overrides={"fel": str(fel)})
            svar.status_code = 503 if fel.kod >= 500 else fel.kod
            return svar
        sida["jsonld"] = lankade_data.entitet(sida["entitet"], request.build_absolute_uri(request.path))
        sida["rdf_alternativ"] = lankade_data.alternativ("entitet", sida["entitet"]["id"])
        return self.render(request, template="sidor/entitet.html", context_overrides=sida)

    class Meta:
        verbose_name = "register"


class UppdateringarSida(TextSida):
    """Leveranserna av databasen och skrivna inlägg, senaste först."""

    subpage_types = ["sidor.Inlagg"]

    def get_context(self, request, *args, **kwargs):
        kontext = super().get_context(request, *args, **kwargs)
        poster = [{"slag": "leverans", "datum": lev["tidpunkt"], **lev} for lev in kallor.leveranser()]
        for inlagg in Inlagg.objects.child_of(self).live().specific():
            poster.append({"slag": "inlagg", "datum": inlagg.datum, "sida": inlagg})
        kontext["poster"] = sorted(poster, key=lambda p: p["datum"].isoformat(), reverse=True)
        return kontext

    class Meta:
        verbose_name = "uppdateringar"


class Inlagg(Page):
    """Ett skrivet inlägg i listan över uppdateringar."""

    datum = models.DateField()
    brodtext = RichTextField(blank=True)

    content_panels = Page.content_panels + [FieldPanel("datum"), FieldPanel("brodtext")]
    parent_page_types = ["sidor.UppdateringarSida"]
    subpage_types = []

    class Meta:
        verbose_name = "inlägg"
        verbose_name_plural = "inlägg"
