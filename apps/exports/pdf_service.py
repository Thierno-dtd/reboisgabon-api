from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


COULEUR_PRIMAIRE = colors.HexColor('#1B5E20')   # vert forêt
COULEUR_SECONDAIRE = colors.HexColor('#E8F5E9')


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='TitrePrincipal', fontSize=18, textColor=COULEUR_PRIMAIRE,
        spaceAfter=6, alignment=TA_CENTER, fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='SousTitre', fontSize=10, textColor=colors.grey,
        spaceAfter=20, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        name='SectionTitre', fontSize=13, textColor=COULEUR_PRIMAIRE,
        spaceBefore=16, spaceAfter=8, fontName='Helvetica-Bold'
    ))
    return styles


def _entete(elements, styles, titre):
    elements.append(Paragraph("ReboisGabon", styles['TitrePrincipal']))
    elements.append(Paragraph(titre, styles['SectionTitre']))
    elements.append(Paragraph(
        f"Rapport généré le {datetime.now():%d/%m/%Y à %H:%M}",
        styles['SousTitre']
    ))
    elements.append(Spacer(1, 0.5 * cm))


def _tableau(data, col_widths=None):
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COULEUR_PRIMAIRE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COULEUR_SECONDAIRE]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return table


def generer_rapport_overview_pdf(overview_data, sites_data, essences_data):
    """
    Rapport de synthèse générale — le PDF que les décideurs impriment
    ou envoient aux bailleurs.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm
    )
    styles = _styles()
    elements = []

    _entete(elements, styles, "Rapport de synthèse — Programme de reboisement")

    # Chiffres clés
    elements.append(Paragraph("Chiffres clés", styles['SectionTitre']))
    kpi_data = [
        ["Indicateur", "Valeur"],
        ["Nombre de sites", str(overview_data['total_sites'])],
        ["Superficie totale (ha)", f"{overview_data['superficie_totale_hectares']}"],
        ["Nombre de campagnes", str(overview_data['total_campagnes'])],
        ["Total plants plantés", f"{overview_data['total_plants_plantes']:,}".replace(',', ' ')],
        ["Taux de survie global", f"{overview_data['taux_survie_global']}%" if overview_data['taux_survie_global'] else "N/A"],
        ["Essences utilisées", str(overview_data['total_essences_utilisees'])],
    ]
    elements.append(_tableau(kpi_data, col_widths=[9 * cm, 6 * cm]))
    elements.append(Spacer(1, 0.8 * cm))

    # Top sites
    elements.append(Paragraph("Meilleurs sites (par taux de survie)", styles['SectionTitre']))
    sites_header = [["Site", "Localité", "Taux survie (%)", "Campagnes"]]
    sites_rows = [
        [s['nom'], s['localite'], f"{s['taux_survie_moyen']}%", str(s['nombre_campagnes'])]
        for s in sites_data.get('top_5_meilleurs_sites', [])
    ]
    elements.append(_tableau(sites_header + sites_rows, col_widths=[5 * cm, 4 * cm, 3.5 * cm, 2.5 * cm]))
    elements.append(Spacer(1, 0.8 * cm))

    # Essences
    elements.append(Paragraph("Performance par essence", styles['SectionTitre']))
    essences_header = [["Essence", "Taux survie moyen (%)", "Campagnes", "Total plants"]]
    essences_rows = [
        [e['essence'], f"{e['taux_survie_moyen']}%" if e['taux_survie_moyen'] else "N/A",
         str(e['nombre_campagnes']), f"{e['total_plants']:,}".replace(',', ' ')]
        for e in essences_data
    ]
    elements.append(_tableau(essences_header + essences_rows, col_widths=[5 * cm, 4.5 * cm, 3 * cm, 3 * cm]))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generer_rapport_financier_pdf(financier_data):
    """Rapport financier — destiné spécifiquement aux bailleurs/partenaires."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm,
                             leftMargin=2 * cm, rightMargin=2 * cm)
    styles = _styles()
    elements = []

    _entete(elements, styles, "Rapport financier — Bailleurs & financements")

    kpi_data = [
        ["Indicateur", "Valeur"],
        ["Total financé (toutes devises confondues)", f"{financier_data['total_finance']:,}".replace(',', ' ')],
        ["Partenaires actifs", str(financier_data['nombre_partenaires_actifs'])],
        ["Budget total alloué", f"{financier_data['budget_total_alloue']:,}".replace(',', ' ')],
        ["Coût réel total", f"{financier_data['cout_reel_total']:,}".replace(',', ' ')],
        ["Coût moyen par plant survivant",
         f"{financier_data['cout_moyen_par_plant_survivant']}" if financier_data['cout_moyen_par_plant_survivant'] else "N/A"],
    ]
    elements.append(_tableau(kpi_data, col_widths=[10 * cm, 5 * cm]))
    elements.append(Spacer(1, 0.8 * cm))

    elements.append(Paragraph("Financement par partenaire", styles['SectionTitre']))
    header = [["Partenaire", "Type", "Montant total", "Nb financements"]]
    rows = [
        [p['nom'], p['type_partenaire'], f"{p['total']:,}".replace(',', ' '), str(p['nb_financements'])]
        for p in financier_data['financement_par_partenaire']
    ]
    elements.append(_tableau(header + rows, col_widths=[6 * cm, 3.5 * cm, 3.5 * cm, 2 * cm]))

    doc.build(elements)
    buffer.seek(0)
    return buffer