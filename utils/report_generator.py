from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import inch
from datetime import datetime
import plotly.io as pio
import os

# Register Arabic font
FONT_PATH = os.path.join(os.path.dirname(__file__), '../data/fonts/NotoNaskhArabic-Regular.ttf')
pdfmetrics.registerFont(TTFont('Arabic', FONT_PATH))

class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.arabic_style = ParagraphStyle(
            'Arabic',
            fontName='Arabic',
            fontSize=12,
            leading=16,
            alignment=1  # Center alignment
        )

    def create_header(self, title):
        """Create a header paragraph with Arabic support."""
        return Paragraph(title, self.arabic_style)

    def create_table(self, data, colWidths=None):
        """Create a table with the given data."""
        table = Table(data, colWidths=colWidths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Arabic'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Arabic'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        return table

    def add_plot(self, fig, width=6*inch, height=4*inch):
        """Convert a plotly figure to a ReportLab image."""
        # Save plotly figure as PNG temporarily
        temp_path = 'temp_plot.png'
        pio.write_image(fig, temp_path)
        img = Image(temp_path, width=width, height=height)
        os.remove(temp_path)
        return img

    def generate_expense_report(self, output_path, project_data, start_date, end_date):
        """Generate an expense report PDF."""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Create the document content
        content = []

        # Add title
        title = f"تقرير المصروفات - {start_date} إلى {end_date}"
        content.append(self.create_header(title))
        content.append(Spacer(1, 12))

        # Add project summary
        project_summary = [
            ["اسم المشروع", "الميزانية", "المصروفات", "المتبقي"],
            [
                project_data['name'],
                f"{project_data['budget']:,.2f}",
                f"{project_data['expenses']:,.2f}",
                f"{project_data['remaining']:,.2f}"
            ]
        ]
        content.append(self.create_table(project_summary))
        content.append(Spacer(1, 24))

        # Add expense breakdown
        if project_data.get('expense_breakdown'):
            content.append(self.create_header("تفاصيل المصروفات"))
            content.append(Spacer(1, 12))
            expense_table = [["البند", "المبلغ", "النسبة"]]
            for item in project_data['expense_breakdown']:
                expense_table.append([
                    item['category'],
                    f"{item['amount']:,.2f}",
                    f"{item['percentage']:.1f}%"
                ])
            content.append(self.create_table(expense_table))

        # Add plots if available
        if project_data.get('plots'):
            for plot in project_data['plots']:
                content.append(Spacer(1, 24))
                content.append(self.add_plot(plot))

        # Build the PDF
        doc.build(content)

    def generate_variance_report(self, output_path, variance_data, start_date, end_date):
        """Generate a variance report PDF."""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        content = []

        # Add title
        title = f"تقرير الفروقات - {start_date} إلى {end_date}"
        content.append(self.create_header(title))
        content.append(Spacer(1, 12))

        # Add variance summary
        if variance_data.get('summary'):
            content.append(self.create_header("ملخص الفروقات"))
            content.append(Spacer(1, 12))
            summary_table = [
                ["البند", "التسعير المبدئي", "الفعلي", "الفرق", "النسبة"]
            ]
            for item in variance_data['summary']:
                summary_table.append([
                    item['category'],
                    f"{item['estimated']:,.2f}",
                    f"{item['actual']:,.2f}",
                    f"{item['variance']:,.2f}",
                    f"{item['percentage']:.1f}%"
                ])
            content.append(self.create_table(summary_table))

        # Add detailed variances
        if variance_data.get('details'):
            content.append(Spacer(1, 24))
            content.append(self.create_header("تفاصيل الفروقات"))
            content.append(Spacer(1, 12))
            details_table = [
                ["البند", "الكمية المقدرة", "الكمية الفعلية", "فرق الكمية", "السعر المقدر", "السعر الفعلي", "فرق السعر", "إجمالي الفرق"]
            ]
            for item in variance_data['details']:
                details_table.append([
                    item['item'],
                    str(item['estimated_qty']),
                    str(item['actual_qty']),
                    str(item['qty_variance']),
                    f"{item['estimated_price']:,.2f}",
                    f"{item['actual_price']:,.2f}",
                    f"{item['price_variance']:,.2f}",
                    f"{item['total_variance']:,.2f}"
                ])
            content.append(self.create_table(details_table))

        # Add plots if available
        if variance_data.get('plots'):
            for plot in variance_data['plots']:
                content.append(Spacer(1, 24))
                content.append(self.add_plot(plot))

        # Build the PDF
        doc.build(content)

    def generate_weekly_report(self, output_path, weekly_data):
        """Generate a weekly report PDF."""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        content = []

        # Add title
        title = f"التقرير الأسبوعي - {weekly_data['week_start']} إلى {weekly_data['week_end']}"
        content.append(self.create_header(title))
        content.append(Spacer(1, 12))

        # Add weekly summary
        if weekly_data.get('summary'):
            content.append(self.create_header("ملخص الأسبوع"))
            content.append(Spacer(1, 12))
            summary_table = [
                ["البند", "القيمة"]
            ]
            for key, value in weekly_data['summary'].items():
                summary_table.append([key, str(value)])
            content.append(self.create_table(summary_table))

        # Add invoice list
        if weekly_data.get('invoices'):
            content.append(Spacer(1, 24))
            content.append(self.create_header("الفواتير المستلمة"))
            content.append(Spacer(1, 12))
            invoice_table = [
                ["رقم الفاتورة", "المورد", "التاريخ", "المبلغ", "الحالة"]
            ]
            for invoice in weekly_data['invoices']:
                invoice_table.append([
                    invoice['number'],
                    invoice['vendor'],
                    invoice['date'],
                    f"{invoice['amount']:,.2f}",
                    invoice['status']
                ])
            content.append(self.create_table(invoice_table))

        # Add alerts and notifications
        if weekly_data.get('alerts'):
            content.append(Spacer(1, 24))
            content.append(self.create_header("التنبيهات والملاحظات"))
            content.append(Spacer(1, 12))
            alerts_table = [
                ["النوع", "الرسالة", "الأهمية", "التاريخ"]
            ]
            for alert in weekly_data['alerts']:
                alerts_table.append([
                    alert['type'],
                    alert['message'],
                    alert['severity'],
                    alert['date']
                ])
            content.append(self.create_table(alerts_table))

        # Add plots if available
        if weekly_data.get('plots'):
            for plot in weekly_data['plots']:
                content.append(Spacer(1, 24))
                content.append(self.add_plot(plot))

        # Build the PDF
        doc.build(content) 