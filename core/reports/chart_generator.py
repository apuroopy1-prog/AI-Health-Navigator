"""
Chart generation module using Matplotlib.
Generates visual charts for health assessment reports.
"""

import io
from typing import List, Dict, Optional
from datetime import datetime

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server environments
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Wedge, Circle
import numpy as np


# Color scheme matching the app's design
COLORS = {
    'primary': '#0066cc',
    'secondary': '#0088ff',
    'low_risk': '#28a745',
    'medium_risk': '#ffc107',
    'high_risk': '#dc3545',
    'background': '#f8f9fa',
    'text': '#333333',
    'gray': '#6c757d',
}


def generate_symptom_severity_chart(
    symptoms: List[Dict[str, any]],
    figsize: tuple = (8, 4)
) -> bytes:
    """
    Generate a horizontal bar chart showing symptom severity levels.

    Args:
        symptoms: List of dicts with 'name' and 'severity' (1-10 scale)
                  Example: [{'name': 'Headache', 'severity': 7}, ...]
        figsize: Figure size tuple (width, height)

    Returns:
        PNG image as bytes
    """
    if not symptoms:
        # Return empty chart with message
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'No symptom severity data available',
                ha='center', va='center', fontsize=12, color=COLORS['gray'])
        ax.axis('off')
        return _fig_to_bytes(fig)

    fig, ax = plt.subplots(figsize=figsize)

    # Extract data
    names = [s.get('name', 'Unknown')[:30] for s in symptoms]  # Truncate long names
    severities = [min(max(s.get('severity', 5), 1), 10) for s in symptoms]  # Clamp 1-10

    # Create color gradient based on severity
    colors = []
    for sev in severities:
        if sev <= 3:
            colors.append(COLORS['low_risk'])
        elif sev <= 6:
            colors.append(COLORS['medium_risk'])
        else:
            colors.append(COLORS['high_risk'])

    # Create horizontal bar chart
    y_pos = np.arange(len(names))
    bars = ax.barh(y_pos, severities, color=colors, edgecolor='white', height=0.6)

    # Customize appearance
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=10)
    ax.set_xlim(0, 10)
    ax.set_xlabel('Severity Level (1-10)', fontsize=10)
    ax.set_title('Symptom Severity Assessment', fontsize=14, fontweight='bold',
                 color=COLORS['primary'], pad=15)

    # Add value labels on bars
    for bar, sev in zip(bars, severities):
        width = bar.get_width()
        ax.text(width + 0.2, bar.get_y() + bar.get_height()/2,
                f'{sev}', va='center', fontsize=9, fontweight='bold')

    # Add legend
    legend_elements = [
        mpatches.Patch(color=COLORS['low_risk'], label='Low (1-3)'),
        mpatches.Patch(color=COLORS['medium_risk'], label='Moderate (4-6)'),
        mpatches.Patch(color=COLORS['high_risk'], label='High (7-10)')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=8)

    # Style
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_facecolor(COLORS['background'])
    fig.patch.set_facecolor('white')

    plt.tight_layout()
    return _fig_to_bytes(fig)


def generate_risk_gauge(
    risk_level: str,
    risk_score: Optional[float] = None,
    figsize: tuple = (6, 4)
) -> bytes:
    """
    Generate a semicircular gauge showing risk level.

    Args:
        risk_level: 'Low', 'Medium', or 'High'
        risk_score: Optional numeric score (0-100). If not provided, derived from risk_level
        figsize: Figure size tuple

    Returns:
        PNG image as bytes
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Derive score from risk level if not provided
    if risk_score is None:
        risk_score = {'Low': 25, 'Medium': 55, 'High': 85}.get(risk_level, 50)

    risk_score = min(max(risk_score, 0), 100)  # Clamp 0-100

    # Draw gauge background (semicircle segments)
    # Green (Low): 0-33%, Yellow (Medium): 33-66%, Red (High): 66-100%
    wedge_low = Wedge((0.5, 0), 0.4, 180, 120, width=0.15,
                      facecolor=COLORS['low_risk'], edgecolor='white', linewidth=2)
    wedge_med = Wedge((0.5, 0), 0.4, 120, 60, width=0.15,
                      facecolor=COLORS['medium_risk'], edgecolor='white', linewidth=2)
    wedge_high = Wedge((0.5, 0), 0.4, 60, 0, width=0.15,
                       facecolor=COLORS['high_risk'], edgecolor='white', linewidth=2)

    ax.add_patch(wedge_low)
    ax.add_patch(wedge_med)
    ax.add_patch(wedge_high)

    # Draw needle
    # Convert score to angle (180 degrees = 0 score, 0 degrees = 100 score)
    angle = 180 - (risk_score / 100) * 180
    angle_rad = np.radians(angle)

    # Needle
    needle_length = 0.35
    needle_x = 0.5 + needle_length * np.cos(angle_rad)
    needle_y = needle_length * np.sin(angle_rad)

    ax.annotate('', xy=(needle_x, needle_y), xytext=(0.5, 0),
                arrowprops=dict(arrowstyle='->', color=COLORS['text'], lw=3))

    # Center circle
    center_circle = Circle((0.5, 0), 0.05, facecolor=COLORS['primary'], edgecolor='white', linewidth=2)
    ax.add_patch(center_circle)

    # Labels
    ax.text(0.08, 0.1, 'LOW', fontsize=9, fontweight='bold', color=COLORS['low_risk'])
    ax.text(0.45, 0.45, 'MEDIUM', fontsize=9, fontweight='bold', color=COLORS['medium_risk'])
    ax.text(0.82, 0.1, 'HIGH', fontsize=9, fontweight='bold', color=COLORS['high_risk'])

    # Risk level and score display
    risk_color = {'Low': COLORS['low_risk'], 'Medium': COLORS['medium_risk'],
                  'High': COLORS['high_risk']}.get(risk_level, COLORS['gray'])

    ax.text(0.5, -0.15, f'{risk_level.upper()} RISK', fontsize=16, fontweight='bold',
            ha='center', color=risk_color)
    ax.text(0.5, -0.25, f'Score: {int(risk_score)}', fontsize=10, ha='center', color=COLORS['gray'])

    # Title
    ax.set_title('Clinical Risk Assessment', fontsize=14, fontweight='bold',
                 color=COLORS['primary'], pad=20)

    # Setup axes
    ax.set_xlim(-0.1, 1.1)
    ax.set_ylim(-0.35, 0.6)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor('white')

    plt.tight_layout()
    return _fig_to_bytes(fig)


def generate_treatment_timeline(
    recommendations: List[str],
    care_level: str = "Primary Care",
    figsize: tuple = (10, 5)
) -> bytes:
    """
    Generate a treatment timeline visualization.

    Args:
        recommendations: List of treatment recommendation strings
        care_level: Care level string ('Self-Care', 'Primary Care', 'Urgent Care', 'Emergency')
        figsize: Figure size tuple

    Returns:
        PNG image as bytes
    """
    if not recommendations:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'No treatment recommendations available',
                ha='center', va='center', fontsize=12, color=COLORS['gray'])
        ax.axis('off')
        return _fig_to_bytes(fig)

    fig, ax = plt.subplots(figsize=figsize)

    # Categorize recommendations into phases
    phases = {
        'Immediate': [],
        'Short-term (1-7 days)': [],
        'Ongoing': [],
        'Follow-up': []
    }

    # Simple keyword-based categorization
    for rec in recommendations[:8]:  # Limit to 8 recommendations
        rec_lower = rec.lower()
        if any(word in rec_lower for word in ['immediate', 'emergency', 'now', 'urgent', 'call 911']):
            phases['Immediate'].append(rec)
        elif any(word in rec_lower for word in ['follow-up', 'follow up', 'appointment', 'return', 'revisit']):
            phases['Follow-up'].append(rec)
        elif any(word in rec_lower for word in ['daily', 'regularly', 'continue', 'maintain', 'lifestyle']):
            phases['Ongoing'].append(rec)
        else:
            phases['Short-term (1-7 days)'].append(rec)

    # Draw timeline
    phase_names = list(phases.keys())
    phase_colors = [COLORS['high_risk'], COLORS['medium_risk'], COLORS['primary'], COLORS['low_risk']]

    y_position = 0.8
    for i, (phase_name, phase_recs) in enumerate(phases.items()):
        # Phase header
        ax.add_patch(plt.Rectangle((i * 0.25, y_position), 0.23, 0.15,
                                    facecolor=phase_colors[i], alpha=0.3, edgecolor=phase_colors[i], linewidth=2))
        ax.text(i * 0.25 + 0.115, y_position + 0.075, phase_name,
                ha='center', va='center', fontsize=9, fontweight='bold', color=phase_colors[i])

        # Recommendations under each phase
        for j, rec in enumerate(phase_recs[:2]):  # Max 2 per phase for space
            rec_short = rec[:50] + '...' if len(rec) > 50 else rec
            ax.text(i * 0.25 + 0.115, y_position - 0.1 - (j * 0.12),
                    f"• {rec_short}", ha='center', va='top', fontsize=7,
                    color=COLORS['text'], wrap=True)

    # Timeline arrow
    ax.annotate('', xy=(1.0, 0.875), xytext=(0, 0.875),
                arrowprops=dict(arrowstyle='->', color=COLORS['gray'], lw=2))

    # Care level indicator
    care_color = {
        'Self-Care': COLORS['low_risk'],
        'Primary Care': COLORS['medium_risk'],
        'Urgent Care': COLORS['high_risk'],
        'Emergency': '#8B0000'
    }.get(care_level, COLORS['gray'])

    ax.text(0.5, 0.05, f'Recommended Care Level: {care_level}',
            ha='center', fontsize=11, fontweight='bold', color=care_color,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=care_color, linewidth=2))

    # Title
    ax.set_title('Treatment Timeline & Recommendations', fontsize=14, fontweight='bold',
                 color=COLORS['primary'], pad=15)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(0, 1)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    plt.tight_layout()
    return _fig_to_bytes(fig)


def generate_history_trend(
    assessments: List[Dict],
    figsize: tuple = (8, 4)
) -> bytes:
    """
    Generate a trend chart showing risk levels across multiple assessments.

    Args:
        assessments: List of assessment dicts with 'date' and 'risk_level' keys
                     Example: [{'date': '2024-01-15', 'risk_level': 'High'}, ...]
        figsize: Figure size tuple

    Returns:
        PNG image as bytes
    """
    if not assessments or len(assessments) < 2:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'Multiple assessments required for trend analysis',
                ha='center', va='center', fontsize=12, color=COLORS['gray'])
        ax.axis('off')
        return _fig_to_bytes(fig)

    fig, ax = plt.subplots(figsize=figsize)

    # Convert risk levels to numeric values
    risk_to_num = {'Low': 1, 'Medium': 2, 'High': 3}

    dates = []
    risk_values = []

    for a in assessments[-10:]:  # Limit to last 10 assessments
        try:
            if isinstance(a.get('date'), str):
                date = datetime.strptime(a['date'], '%Y-%m-%d')
            else:
                date = a.get('date', datetime.now())
            dates.append(date)
            risk_values.append(risk_to_num.get(a.get('risk_level', 'Medium'), 2))
        except (ValueError, TypeError):
            continue

    if len(dates) < 2:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'Insufficient valid assessment data for trend',
                ha='center', va='center', fontsize=12, color=COLORS['gray'])
        ax.axis('off')
        return _fig_to_bytes(fig)

    # Plot trend line
    ax.plot(dates, risk_values, marker='o', linewidth=2, markersize=8,
            color=COLORS['primary'], markerfacecolor='white', markeredgewidth=2)

    # Fill areas
    ax.fill_between(dates, risk_values, alpha=0.2, color=COLORS['primary'])

    # Color markers by risk level
    for i, (date, value) in enumerate(zip(dates, risk_values)):
        color = {1: COLORS['low_risk'], 2: COLORS['medium_risk'], 3: COLORS['high_risk']}[value]
        ax.plot(date, value, 'o', markersize=10, color=color, markeredgecolor='white', markeredgewidth=2)

    # Customize axes
    ax.set_ylim(0.5, 3.5)
    ax.set_yticks([1, 2, 3])
    ax.set_yticklabels(['Low', 'Medium', 'High'], fontsize=10)
    ax.set_ylabel('Risk Level', fontsize=10)
    ax.set_xlabel('Assessment Date', fontsize=10)

    # Add horizontal reference lines
    ax.axhline(y=1, color=COLORS['low_risk'], linestyle='--', alpha=0.3)
    ax.axhline(y=2, color=COLORS['medium_risk'], linestyle='--', alpha=0.3)
    ax.axhline(y=3, color=COLORS['high_risk'], linestyle='--', alpha=0.3)

    # Title
    ax.set_title('Health Risk Trend Over Time', fontsize=14, fontweight='bold',
                 color=COLORS['primary'], pad=15)

    # Style
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_facecolor(COLORS['background'])
    fig.patch.set_facecolor('white')

    # Format x-axis dates
    fig.autofmt_xdate()

    plt.tight_layout()
    return _fig_to_bytes(fig)


def _fig_to_bytes(fig: plt.Figure) -> bytes:
    """Convert matplotlib figure to PNG bytes."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()


# Convenience function to generate all charts at once
def generate_all_charts(
    symptoms: List[Dict] = None,
    risk_level: str = "Medium",
    risk_score: float = None,
    recommendations: List[str] = None,
    care_level: str = "Primary Care",
    assessment_history: List[Dict] = None
) -> Dict[str, bytes]:
    """
    Generate all available charts for an assessment.

    Returns:
        Dictionary with chart names as keys and PNG bytes as values
    """
    charts = {}

    if symptoms:
        charts['symptom_severity'] = generate_symptom_severity_chart(symptoms)

    charts['risk_gauge'] = generate_risk_gauge(risk_level, risk_score)

    if recommendations:
        charts['treatment_timeline'] = generate_treatment_timeline(recommendations, care_level)

    if assessment_history and len(assessment_history) >= 2:
        charts['history_trend'] = generate_history_trend(assessment_history)

    return charts
