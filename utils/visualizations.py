import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any

class Visualizer:
    @staticmethod
    def create_expense_breakdown_pie(data: List[Dict[str, Any]]) -> go.Figure:
        """Create a pie chart showing expense breakdown by category."""
        df = pd.DataFrame(data)
        fig = px.pie(
            df,
            values='amount',
            names='category',
            title='توزيع المصروفات حسب الفئة',
            template='plotly_white'
        )
        fig.update_layout(
            font=dict(family='Arial, sans-serif'),
            title_font=dict(size=20),
            showlegend=True
        )
        return fig

    @staticmethod
    def create_budget_vs_actual_bar(
        categories: List[str],
        budget: List[float],
        actual: List[float]
    ) -> go.Figure:
        """Create a bar chart comparing budget vs actual expenses."""
        fig = go.Figure(data=[
            go.Bar(name='الميزانية', x=categories, y=budget),
            go.Bar(name='الفعلي', x=categories, y=actual)
        ])
        
        fig.update_layout(
            title='مقارنة الميزانية مع المصروفات الفعلية',
            barmode='group',
            template='plotly_white',
            font=dict(family='Arial, sans-serif'),
            title_font=dict(size=20)
        )
        return fig

    @staticmethod
    def create_expense_trend_line(
        dates: List[str],
        amounts: List[float],
        cumulative: bool = False
    ) -> go.Figure:
        """Create a line chart showing expense trends over time."""
        if cumulative:
            amounts = pd.Series(amounts).cumsum().tolist()
        
        fig = go.Figure(data=go.Scatter(
            x=dates,
            y=amounts,
            mode='lines+markers'
        ))
        
        title = 'تطور المصروفات التراكمي' if cumulative else 'تطور المصروفات'
        fig.update_layout(
            title=title,
            template='plotly_white',
            font=dict(family='Arial, sans-serif'),
            title_font=dict(size=20),
            xaxis_title='التاريخ',
            yaxis_title='المبلغ'
        )
        return fig

    @staticmethod
    def create_variance_heatmap(variance_data: pd.DataFrame) -> go.Figure:
        """Create a heatmap showing price and quantity variances."""
        fig = go.Figure(data=go.Heatmap(
            z=variance_data.values,
            x=variance_data.columns,
            y=variance_data.index,
            colorscale='RdYlGn',
            reversescale=True
        ))
        
        fig.update_layout(
            title='خريطة حرارية للفروقات',
            template='plotly_white',
            font=dict(family='Arial, sans-serif'),
            title_font=dict(size=20)
        )
        return fig

    @staticmethod
    def create_project_progress_gauge(
        percentage: float,
        title: str = 'نسبة إنجاز المشروع'
    ) -> go.Figure:
        """Create a gauge chart showing project progress."""
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = percentage,
            title = {'text': title},
            gauge = {
                'axis': {'range': [0, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 33], 'color': "lightgray"},
                    {'range': [33, 66], 'color': "gray"},
                    {'range': [66, 100], 'color': "darkgray"}
                ]
            }
        ))
        
        fig.update_layout(
            font=dict(family='Arial, sans-serif'),
            title_font=dict(size=20)
        )
        return fig

    @staticmethod
    def create_vendor_analysis_scatter(
        vendors_data: List[Dict[str, Any]]
    ) -> go.Figure:
        """Create a scatter plot analyzing vendors by invoice count and total amount."""
        df = pd.DataFrame(vendors_data)
        
        fig = px.scatter(
            df,
            x='invoice_count',
            y='total_amount',
            size='average_amount',
            color='category',
            hover_name='vendor_name',
            title='تحليل الموردين'
        )
        
        fig.update_layout(
            template='plotly_white',
            font=dict(family='Arial, sans-serif'),
            title_font=dict(size=20),
            xaxis_title='عدد الفواتير',
            yaxis_title='إجمالي المبالغ'
        )
        return fig

    @staticmethod
    def create_weekly_summary_subplot(weekly_data: Dict[str, Any]) -> go.Figure:
        """Create a subplot with weekly summary charts."""
        fig = go.Figure()
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'المصروفات اليومية',
                'توزيع الفئات',
                'حالة الفواتير',
                'أعلى الموردين'
            )
        )
        
        # Daily expenses line chart
        fig.add_trace(
            go.Scatter(
                x=weekly_data['daily_expenses']['dates'],
                y=weekly_data['daily_expenses']['amounts'],
                name='المصروفات اليومية'
            ),
            row=1, col=1
        )
        
        # Category distribution pie chart
        fig.add_trace(
            go.Pie(
                labels=weekly_data['category_distribution']['categories'],
                values=weekly_data['category_distribution']['amounts'],
                name='توزيع الفئات'
            ),
            row=1, col=2
        )
        
        # Invoice status bar chart
        fig.add_trace(
            go.Bar(
                x=weekly_data['invoice_status']['status'],
                y=weekly_data['invoice_status']['count'],
                name='حالة الفواتير'
            ),
            row=2, col=1
        )
        
        # Top vendors bar chart
        fig.add_trace(
            go.Bar(
                x=weekly_data['top_vendors']['names'],
                y=weekly_data['top_vendors']['amounts'],
                name='أعلى الموردين'
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=800,
            showlegend=True,
            template='plotly_white',
            font=dict(family='Arial, sans-serif'),
            title_text='ملخص الأسبوع',
            title_font=dict(size=24)
        )
        return fig 