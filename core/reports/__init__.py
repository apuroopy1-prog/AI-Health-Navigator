"""
Reports module for AI Health Navigator.
Provides chart generation and enhanced PDF report building.
"""

from .chart_generator import (
    generate_symptom_severity_chart,
    generate_risk_gauge,
    generate_treatment_timeline,
    generate_history_trend,
)
from .pdf_builder import EnhancedPDFBuilder, generate_enhanced_pdf_report

__all__ = [
    "generate_symptom_severity_chart",
    "generate_risk_gauge",
    "generate_treatment_timeline",
    "generate_history_trend",
    "EnhancedPDFBuilder",
    "generate_enhanced_pdf_report",
]
