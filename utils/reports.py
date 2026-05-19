"""PDF Report Generation Module - Professional equipment monitoring reports"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.pdfgen import canvas
from datetime import datetime
from io import BytesIO
import os

class PDFReportGenerator:
    """Generate professional PDF reports for equipment monitoring and predictions"""

    def __init__(self):
        """Initialize PDF report generator"""
        self.width, self.height = letter
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#00d4ff'),
            spaceAfter=30,
            alignment=1,
            fontName='Helvetica-Bold'
        ))

        # Heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#00ff88'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))

        # Normal style
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#e8eaf6'),
            spaceAfter=8
        ))

    def generate_equipment_report(self, equipment_data, predictions_data, recommendations):
        """Generate comprehensive equipment status report"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        story = []

        # Header with timestamp
        story.append(self._create_header())
        story.append(Spacer(1, 0.2*inch))

        # Equipment information section
        story.append(Paragraph('Equipment Information', self.styles['CustomHeading']))
        story.append(self._create_equipment_info_table(equipment_data))
        story.append(Spacer(1, 0.3*inch))

        # Current sensor readings
        story.append(Paragraph('Current Sensor Readings', self.styles['CustomHeading']))
        story.append(self._create_sensor_table(predictions_data.get('sensors', {})))
        story.append(Spacer(1, 0.3*inch))

        # Prediction results
        story.append(Paragraph('AI Prediction Results', self.styles['CustomHeading']))
        story.append(self._create_prediction_table(predictions_data))
        story.append(Spacer(1, 0.3*inch))

        # Recommendations
        if recommendations:
            story.append(Paragraph('Maintenance Recommendations', self.styles['CustomHeading']))
            story.append(self._create_recommendations_table(recommendations))
            story.append(Spacer(1, 0.3*inch))

        # Risk assessment
        story.append(Paragraph('Risk Assessment', self.styles['CustomHeading']))
        story.append(self._create_risk_assessment(predictions_data))
        story.append(Spacer(1, 0.3*inch))

        # Footer
        story.append(self._create_footer())

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_maintenance_report(self, maintenance_schedule):
        """Generate maintenance schedule report"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        story = []

        # Title
        story.append(Paragraph('Maintenance Schedule Report', self.styles['CustomTitle']))
        story.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', self.styles['CustomNormal']))
        story.append(Spacer(1, 0.3*inch))

        # Maintenance table
        story.append(self._create_maintenance_table(maintenance_schedule))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    def _create_header(self):
        """Create report header"""
        return Paragraph(
            f'Equipment Monitoring Report<br/><font size=10>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</font>',
            self.styles['CustomTitle']
        )

    def _create_equipment_info_table(self, equipment_data):
        """Create equipment information table"""
        data = [
            ['Field', 'Value'],
            ['Equipment ID', equipment_data.get('equipment_id', 'N/A')],
            ['Equipment Name', equipment_data.get('name', 'N/A')],
            ['Machine Type', equipment_data.get('machine_type', 'N/A')],
            ['Status', equipment_data.get('status', 'N/A').upper()],
            ['Health Score', f"{equipment_data.get('health_score', 0):.2f}%"],
            ['Last Updated', equipment_data.get('updated_at', 'N/A')],
        ]

        table = Table(data, colWidths=[2*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1f3a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#00d4ff')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#242b48')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#e8eaf6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#00d4ff')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#242b48'), colors.HexColor('#1a1f3a')]),
        ]))

        return table

    def _create_sensor_table(self, sensors):
        """Create sensor readings table"""
        data = [
            ['Sensor', 'Reading', 'Unit', 'Status'],
            ['Temperature', f"{sensors.get('Temperature', 0):.2f}", '°C', '✓'],
            ['Vibration', f"{sensors.get('Vibration', 0):.2f}", 'Hz', '✓'],
            ['Pressure', f"{sensors.get('Pressure', 0):.2f}", 'bar', '✓'],
            ['Humidity', f"{sensors.get('Humidity', 0):.2f}", '%', '✓'],
            ['Runtime Hours', f"{sensors.get('RuntimeHours', 0):.1f}", 'h', '✓'],
        ]

        table = Table(data, colWidths=[1.5*inch, 1.5*inch, 1*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1f3a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#00d4ff')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#242b48')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#e8eaf6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#00d4ff')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))

        return table

    def _create_prediction_table(self, prediction_data):
        """Create prediction results table"""
        risk_color_map = {
            'Low': colors.HexColor('#00ff88'),
            'Medium': colors.HexColor('#ffaa00'),
            'High': colors.HexColor('#ff3333'),
        }

        data = [
            ['Metric', 'Value'],
            ['Prediction', prediction_data.get('prediction', 'N/A')],
            ['Confidence', f"{prediction_data.get('failure_probability', 0):.2f}%"],
            ['Risk Level', prediction_data.get('risk_level', 'N/A')],
            ['Health Status', prediction_data.get('health_status', 'N/A')],
            ['Remaining Life', f"{prediction_data.get('remaining_life', 0):.1f} days"],
        ]

        table = Table(data, colWidths=[2*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1f3a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#00d4ff')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#242b48')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#e8eaf6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#00d4ff')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))

        return table

    def _create_recommendations_table(self, recommendations):
        """Create recommendations table"""
        data = [['Recommendation', 'Action Required', 'Priority']]

        for rec in recommendations[:5]:  # Limit to 5 recommendations per page
            data.append([
                Paragraph(rec.get('message', 'N/A'), self.styles['CustomNormal']),
                Paragraph(rec.get('action', 'N/A'), self.styles['CustomNormal']),
                rec.get('priority', 'Medium')
            ])

        table = Table(data, colWidths=[2.5*inch, 2.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1f3a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#00d4ff')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#242b48')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#e8eaf6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#00d4ff')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        return table

    def _create_risk_assessment(self, prediction_data):
        """Create risk assessment section"""
        risk_level = prediction_data.get('risk_level', 'Unknown')
        health_score = prediction_data.get('health_score', 0)

        risk_text = f"""
        <b>Overall Risk Level:</b> {risk_level}<br/>
        <b>Health Score:</b> {health_score:.2f}%<br/>
        <b>Recommendation:</b> """

        if risk_level == 'Low':
            risk_text += "Equipment is operating normally. Continue regular monitoring and scheduled maintenance."
        elif risk_level == 'Medium':
            risk_text += "Equipment shows signs of wear. Schedule preventive maintenance within next 2 weeks."
        else:  # High
            risk_text += "Equipment requires immediate attention. Schedule urgent maintenance before continued operation."

        return Paragraph(risk_text, self.styles['CustomNormal'])

    def _create_maintenance_table(self, schedule):
        """Create maintenance schedule table"""
        data = [
            ['Equipment ID', 'Type', 'Due Date', 'Priority', 'Estimated Hours'],
        ]

        for item in schedule:
            data.append([
                item.get('equipment_id', 'N/A'),
                item.get('maintenance_type', 'N/A'),
                item.get('due_date', 'N/A'),
                item.get('priority', 'N/A'),
                f"{item.get('estimated_hours', 0):.1f}",
            ])

        table = Table(data, colWidths=[1.2*inch, 1.5*inch, 1.5*inch, 1*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1f3a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#00d4ff')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#242b48')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#e8eaf6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#00d4ff')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#242b48'), colors.HexColor('#1a1f3a')]),
        ]))

        return table

    def _create_footer(self):
        """Create report footer"""
        footer_text = f"""
        <font size=8>
        This report was automatically generated by the AI Equipment Failure Prediction System.<br/>
        For questions or concerns, please contact your system administrator.<br/>
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </font>
        """
        return Paragraph(footer_text, self.styles['Normal'])


def generate_report(report_type, data, output_path=None):
    """
    Generate a PDF report

    Args:
        report_type: 'equipment', 'maintenance', or 'analytics'
        data: Dictionary containing report data
        output_path: Optional file path to save report

    Returns:
        BytesIO buffer containing PDF or path to saved file
    """
    generator = PDFReportGenerator()

    if report_type == 'equipment':
        buffer = generator.generate_equipment_report(
            data.get('equipment', {}),
            data.get('prediction', {}),
            data.get('recommendations', [])
        )
    elif report_type == 'maintenance':
        buffer = generator.generate_maintenance_report(
            data.get('schedule', [])
        )
    else:
        raise ValueError(f"Unknown report type: {report_type}")

    if output_path:
        with open(output_path, 'wb') as f:
            f.write(buffer.getvalue())
        return output_path

    return buffer
