"""
HTML Email Template for Weekly Enterprise Reports

Professional, executive-facing design optimized for email clients.
"""

from typing import List
from src.reporting.weekly_report import WeeklyReport, PatternSummary


def generate_html_email(report: WeeklyReport) -> str:
    """
    Generate HTML email from weekly report

    Args:
        report: WeeklyReport object

    Returns:
        HTML string ready for email delivery
    """

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ACMS Weekly Intelligence Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 3px solid #2563eb;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        h1 {{
            color: #1e40af;
            margin: 0 0 10px 0;
            font-size: 28px;
        }}
        .subtitle {{
            color: #64748b;
            font-size: 16px;
            margin: 0;
        }}
        .executive-summary {{
            background-color: #eff6ff;
            border-left: 4px solid #2563eb;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .metric-row {{
            display: flex;
            justify-content: space-between;
            margin: 15px 0;
            padding: 15px;
            background-color: #f8fafc;
            border-radius: 6px;
        }}
        .metric-label {{
            color: #64748b;
            font-size: 14px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #1e40af;
        }}
        .section {{
            margin: 30px 0;
        }}
        .section-title {{
            color: #1e293b;
            font-size: 20px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e2e8f0;
        }}
        .pattern-card {{
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 15px;
            margin: 10px 0;
            transition: box-shadow 0.2s;
        }}
        .pattern-card:hover {{
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .pattern-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .pattern-title {{
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
        }}
        .pattern-impact {{
            font-size: 18px;
            font-weight: bold;
            color: #dc2626;
        }}
        .pattern-meta {{
            font-size: 14px;
            color: #64748b;
            margin: 5px 0;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
        }}
        .badge-blocker {{
            background-color: #fee2e2;
            color: #991b1b;
        }}
        .badge-gap {{
            background-color: #fef3c7;
            color: #92400e;
        }}
        .badge-quality {{
            background-color: #ffedd5;
            color: #9a3412;
        }}
        .badge-idea {{
            background-color: #d1fae5;
            color: #065f46;
        }}
        .recommendations {{
            margin-top: 10px;
            padding-left: 20px;
        }}
        .recommendations li {{
            margin: 5px 0;
            color: #475569;
            font-size: 14px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            text-align: center;
            color: #94a3b8;
            font-size: 12px;
        }}
        .cta-button {{
            display: inline-block;
            background-color: #2563eb;
            color: white;
            padding: 12px 24px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            margin: 20px 0;
        }}
        .trend-up {{
            color: #dc2626;
        }}
        .trend-down {{
            color: #16a34a;
        }}
        .trend-stable {{
            color: #64748b;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🤖 ACMS Weekly Intelligence Report</h1>
            <p class="subtitle">Week of {report.week_start.strftime('%B %d')} - {report.week_end.strftime('%d, %Y')}</p>
            <p class="subtitle">Generated: {report.generated_at.strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>

        <!-- Executive Summary -->
        <div class="executive-summary">
            <h2 style="margin-top: 0; color: #1e40af;">Executive Summary</h2>
            <div style="white-space: pre-line;">{report.executive_summary}</div>
        </div>

        <!-- Key Metrics -->
        <div class="section">
            <h2 class="section-title">📊 Key Metrics</h2>
            <div class="metric-row">
                <div>
                    <div class="metric-label">Total Impact</div>
                    <div class="metric-value">${report.total_impact:,.0f}/mo</div>
                </div>
                <div>
                    <div class="metric-label">Patterns Detected</div>
                    <div class="metric-value">{report.patterns_analyzed}</div>
                </div>
                <div>
                    <div class="metric-label">Cache Hit Rate</div>
                    <div class="metric-value">{report.metrics.cache_hit_rate:.1f}%</div>
                </div>
            </div>
            <div class="metric-row">
                <div>
                    <div class="metric-label">Queries Handled</div>
                    <div class="metric-value">{report.metrics.total_queries:,}</div>
                </div>
                <div>
                    <div class="metric-label">Cost Savings</div>
                    <div class="metric-value">${report.metrics.cost_savings_usd:.2f}</div>
                </div>
                <div>
                    <div class="metric-label">WoW Change</div>
                    <div class="metric-value {'trend-up' if report.week_over_week_change > 0 else 'trend-down' if report.week_over_week_change < 0 else 'trend-stable'}">
                        {'+' if report.week_over_week_change > 0 else ''}{report.week_over_week_change*100:.0f}%
                    </div>
                </div>
            </div>
        </div>

        {_render_pattern_section("🔴 Productivity Blockers", report.productivity_blockers, "blocker") if report.productivity_blockers else ""}

        {_render_pattern_section("🟡 Knowledge Gaps", report.knowledge_gaps, "gap") if report.knowledge_gaps else ""}

        {_render_pattern_section("🟠 Quality Issues", report.quality_issues, "quality") if report.quality_issues else ""}

        {_render_pattern_section("🟢 Innovation Ideas", report.innovation_ideas, "idea") if report.innovation_ideas else ""}

        <!-- Footer -->
        <div class="footer">
            <p>This report was automatically generated by ACMS (Adaptive Context Memory System)</p>
            <p>For questions or to adjust report settings, contact your ACMS administrator</p>
            <p style="margin-top: 20px;">
                <a href="#" class="cta-button">View Full Dashboard</a>
            </p>
        </div>
    </div>
</body>
</html>
    """

    return html


def _render_pattern_section(title: str, patterns: List[PatternSummary], badge_type: str) -> str:
    """Render a section of patterns"""
    if not patterns:
        return ""

    html_parts = [f'<div class="section"><h2 class="section-title">{title}</h2>']

    for pattern in patterns[:5]:  # Top 5 per section
        trend_icon = "📈" if pattern.trend == "increasing" else "📉" if pattern.trend == "decreasing" else "➡️"

        html_parts.append(f"""
        <div class="pattern-card">
            <div class="pattern-header">
                <div class="pattern-title">
                    <span class="badge badge-{badge_type}">{pattern.category}</span>
                    {pattern.description}
                </div>
                <div class="pattern-impact">${pattern.monthly_impact_usd:,.0f}/mo</div>
            </div>
            <div class="pattern-meta">
                {trend_icon} {pattern.mentions} mentions •
                {pattern.negative_feedback_rate*100:.0f}% negative feedback •
                Trend: {pattern.trend}
            </div>
            <div class="recommendations">
                <strong>Recommended Actions:</strong>
                <ul>
                    {''.join(f'<li>{rec}</li>' for rec in pattern.recommendations[:3])}
                </ul>
            </div>
        </div>
        """)

    html_parts.append('</div>')
    return ''.join(html_parts)


def generate_text_email(report: WeeklyReport) -> str:
    """
    Generate plain text email (fallback for non-HTML clients)

    Args:
        report: WeeklyReport object

    Returns:
        Plain text string
    """
    lines = []

    # Header
    lines.append("=" * 70)
    lines.append("ACMS WEEKLY INTELLIGENCE REPORT")
    lines.append(f"Week of {report.week_start.strftime('%B %d')} - {report.week_end.strftime('%d, %Y')}")
    lines.append("=" * 70)
    lines.append("")

    # Executive Summary
    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 70)
    lines.append(report.executive_summary)
    lines.append("")

    # Key Metrics
    lines.append("KEY METRICS")
    lines.append("-" * 70)
    lines.append(f"Total Impact:        ${report.total_impact:,.0f}/month")
    lines.append(f"Patterns Detected:   {report.patterns_analyzed}")
    lines.append(f"Cache Hit Rate:      {report.metrics.cache_hit_rate:.1f}%")
    lines.append(f"Cost Savings:        ${report.metrics.cost_savings_usd:.2f}")
    lines.append(f"Queries Handled:     {report.metrics.total_queries:,}")
    lines.append(f"WoW Change:          {'+' if report.week_over_week_change > 0 else ''}{report.week_over_week_change*100:.0f}%")
    lines.append("")

    # Patterns by category
    if report.productivity_blockers:
        lines.append("PRODUCTIVITY BLOCKERS")
        lines.append("-" * 70)
        for i, p in enumerate(report.productivity_blockers[:5], 1):
            lines.append(f"{i}. {p.description}")
            lines.append(f"   Impact: ${p.monthly_impact_usd:,.0f}/mo | {p.mentions} mentions | {p.trend}")
            lines.append("")

    if report.knowledge_gaps:
        lines.append("KNOWLEDGE GAPS")
        lines.append("-" * 70)
        for i, p in enumerate(report.knowledge_gaps[:5], 1):
            lines.append(f"{i}. {p.description}")
            lines.append(f"   Impact: ${p.monthly_impact_usd:,.0f}/mo | {p.mentions} mentions")
            lines.append("")

    if report.quality_issues:
        lines.append("QUALITY ISSUES")
        lines.append("-" * 70)
        for i, p in enumerate(report.quality_issues[:5], 1):
            lines.append(f"{i}. {p.description}")
            lines.append(f"   Impact: ${p.monthly_impact_usd:,.0f}/mo | {p.mentions} mentions")
            lines.append("")

    if report.innovation_ideas:
        lines.append("INNOVATION IDEAS")
        lines.append("-" * 70)
        for i, p in enumerate(report.innovation_ideas[:5], 1):
            lines.append(f"{i}. {p.description}")
            lines.append(f"   Potential ROI: ${abs(p.monthly_impact_usd):,.0f}/mo | {p.mentions} mentions")
            lines.append("")

    # Footer
    lines.append("=" * 70)
    lines.append("Generated by ACMS (Adaptive Context Memory System)")
    lines.append("=" * 70)

    return "\n".join(lines)
