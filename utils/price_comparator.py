import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
import logging
from datetime import datetime

class PriceComparator:
    def __init__(self):
        """Initialize the price comparator."""
        self.logger = logging.getLogger(__name__)
        
    def load_initial_pricing(self, file_path: str) -> pd.DataFrame:
        """
        Load initial pricing data from Excel file.
        
        Args:
            file_path (str): Path to the initial pricing Excel file
            
        Returns:
            pd.DataFrame: Initial pricing data
        """
        try:
            df = pd.read_excel(file_path)
            required_columns = ['item_code', 'description', 'unit_price']
            
            # Validate required columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
            
            return df
        except Exception as e:
            self.logger.error(f"Error loading initial pricing file: {str(e)}")
            return pd.DataFrame()

    def compare_prices(self, 
                      invoice_data: Dict[str, Any], 
                      initial_pricing: pd.DataFrame,
                      tolerance: float = 0.05) -> Dict[str, Any]:
        """
        Compare invoice prices with initial pricing data.
        
        Args:
            invoice_data (Dict[str, Any]): Processed invoice data
            initial_pricing (pd.DataFrame): Initial pricing data
            tolerance (float): Acceptable percentage difference (default: 5%)
            
        Returns:
            Dict[str, Any]: Comparison results
        """
        try:
            comparison_results = {
                'date': datetime.now(),
                'invoice_number': invoice_data.get('invoice_number', ''),
                'total_variance': 0.0,
                'items_analysis': [],
                'summary': {
                    'total_items': 0,
                    'items_with_variance': 0,
                    'total_variance_percentage': 0.0,
                    'high_variance_items': 0
                }
            }
            
            if not invoice_data.get('line_items'):
                return comparison_results
            
            total_expected = 0.0
            total_actual = 0.0
            
            for item in invoice_data['line_items']:
                item_analysis = self._analyze_item(item, initial_pricing, tolerance)
                comparison_results['items_analysis'].append(item_analysis)
                
                if item_analysis['matched']:
                    total_expected += item_analysis['expected_total']
                    total_actual += item_analysis['actual_total']
                    
                    if abs(item_analysis['variance_percentage']) > 0:
                        comparison_results['summary']['items_with_variance'] += 1
                        
                    if abs(item_analysis['variance_percentage']) > (tolerance * 100):
                        comparison_results['summary']['high_variance_items'] += 1
            
            # Calculate summary statistics
            comparison_results['summary']['total_items'] = len(invoice_data['line_items'])
            comparison_results['total_variance'] = total_actual - total_expected
            
            if total_expected > 0:
                comparison_results['summary']['total_variance_percentage'] = \
                    (comparison_results['total_variance'] / total_expected) * 100
            
            return comparison_results
            
        except Exception as e:
            self.logger.error(f"Error comparing prices: {str(e)}")
            return {}

    def _analyze_item(self, 
                     item: Dict[str, Any], 
                     initial_pricing: pd.DataFrame,
                     tolerance: float) -> Dict[str, Any]:
        """
        Analyze a single invoice item against initial pricing.
        
        Args:
            item (Dict[str, Any]): Invoice line item
            initial_pricing (pd.DataFrame): Initial pricing data
            tolerance (float): Acceptable percentage difference
            
        Returns:
            Dict[str, Any]: Analysis results for the item
        """
        analysis = {
            'description': item['description'],
            'quantity': item.get('quantity', 1),
            'unit_price': item['unit_price'],
            'amount': item['amount'],
            'matched': False,
            'expected_unit_price': 0.0,
            'expected_total': 0.0,
            'variance': 0.0,
            'variance_percentage': 0.0,
            'within_tolerance': True,
            'notes': []
        }
        
        # Try to find matching item in initial pricing
        matches = initial_pricing[
            initial_pricing['description'].str.contains(item['description'], case=False, na=False)
        ]
        
        if len(matches) == 1:
            # Exact match found
            analysis['matched'] = True
            analysis['expected_unit_price'] = matches.iloc[0]['unit_price']
            analysis['expected_total'] = analysis['expected_unit_price'] * analysis['quantity']
            
            # Calculate variance
            analysis['variance'] = analysis['amount'] - analysis['expected_total']
            if analysis['expected_total'] > 0:
                analysis['variance_percentage'] = (analysis['variance'] / analysis['expected_total']) * 100
                
            # Check if within tolerance
            analysis['within_tolerance'] = abs(analysis['variance_percentage']) <= (tolerance * 100)
            
            if not analysis['within_tolerance']:
                analysis['notes'].append(
                    f"Price variance of {analysis['variance_percentage']:.2f}% exceeds tolerance of {tolerance * 100}%"
                )
                
        elif len(matches) > 1:
            analysis['notes'].append("Multiple matching items found in initial pricing")
        else:
            analysis['notes'].append("No matching item found in initial pricing")
        
        return analysis

    def generate_variance_report(self, 
                               comparison_results: Dict[str, Any],
                               output_path: str) -> bool:
        """
        Generate a detailed variance report in Excel format.
        
        Args:
            comparison_results (Dict[str, Any]): Price comparison results
            output_path (str): Path to save the Excel report
            
        Returns:
            bool: True if report generation successful, False otherwise
        """
        try:
            # Create DataFrames for different sections of the report
            summary_data = pd.DataFrame([comparison_results['summary']])
            
            items_data = pd.DataFrame(comparison_results['items_analysis'])
            
            # Create Excel writer
            with pd.ExcelWriter(output_path) as writer:
                # Write summary sheet
                summary_data.to_excel(writer, sheet_name='Summary', index=False)
                
                # Write detailed analysis sheet
                items_data.to_excel(writer, sheet_name='Detailed Analysis', index=False)
                
                # Apply formatting
                workbook = writer.book
                worksheet = writer.sheets['Detailed Analysis']
                
                # Add conditional formatting for variance percentage
                worksheet.conditional_format('H2:H1000', {
                    'type': '3_color_scale',
                    'min_color': '#63BE7B',  # Green
                    'mid_color': '#FFEB84',  # Yellow
                    'max_color': '#F8696B'   # Red
                })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating variance report: {str(e)}")
            return False

    def analyze_trends(self, 
                      comparison_results_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze price variance trends across multiple invoices.
        
        Args:
            comparison_results_list (List[Dict[str, Any]]): List of comparison results
            
        Returns:
            Dict[str, Any]: Trend analysis results
        """
        try:
            trend_analysis = {
                'period_start': None,
                'period_end': None,
                'total_invoices': len(comparison_results_list),
                'average_variance': 0.0,
                'trend_by_item': {},
                'high_variance_items': [],
                'summary_stats': {
                    'max_variance': 0.0,
                    'min_variance': 0.0,
                    'std_dev': 0.0
                }
            }
            
            if not comparison_results_list:
                return trend_analysis
            
            # Initialize period dates
            dates = [result['date'] for result in comparison_results_list if 'date' in result]
            if dates:
                trend_analysis['period_start'] = min(dates)
                trend_analysis['period_end'] = max(dates)
            
            # Collect variances for statistical analysis
            all_variances = []
            
            # Analyze each comparison result
            for result in comparison_results_list:
                all_variances.append(result.get('total_variance', 0.0))
                
                # Analyze items
                for item in result.get('items_analysis', []):
                    item_desc = item['description']
                    if item_desc not in trend_analysis['trend_by_item']:
                        trend_analysis['trend_by_item'][item_desc] = {
                            'variance_history': [],
                            'average_variance': 0.0,
                            'variance_trend': 'stable'
                        }
                    
                    trend_analysis['trend_by_item'][item_desc]['variance_history'].append(
                        item.get('variance_percentage', 0.0)
                    )
            
            # Calculate average variance
            if all_variances:
                trend_analysis['average_variance'] = np.mean(all_variances)
                trend_analysis['summary_stats']['max_variance'] = max(all_variances)
                trend_analysis['summary_stats']['min_variance'] = min(all_variances)
                trend_analysis['summary_stats']['std_dev'] = np.std(all_variances)
            
            # Analyze trends for each item
            for item_desc, item_data in trend_analysis['trend_by_item'].items():
                variances = item_data['variance_history']
                if variances:
                    item_data['average_variance'] = np.mean(variances)
                    
                    # Determine trend
                    if len(variances) > 1:
                        slope = np.polyfit(range(len(variances)), variances, 1)[0]
                        if slope > 0.05:
                            item_data['variance_trend'] = 'increasing'
                        elif slope < -0.05:
                            item_data['variance_trend'] = 'decreasing'
                    
                    # Add to high variance items if average variance is significant
                    if abs(item_data['average_variance']) > 10.0:  # 10% threshold
                        trend_analysis['high_variance_items'].append({
                            'description': item_desc,
                            'average_variance': item_data['average_variance'],
                            'trend': item_data['variance_trend']
                        })
            
            return trend_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing trends: {str(e)}")
            return {} 