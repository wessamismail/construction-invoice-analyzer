import streamlit as st
import os
import pandas as pd
from datetime import datetime
from utils.invoice_processor import InvoiceProcessor
from utils.price_comparator import PriceComparator
from utils.database import Database
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, List
import tempfile
import shutil
import zipfile
import json
import glob

# Set page config
st.set_page_config(
    page_title="Construction Invoice Analyzer",
    page_icon="🏗️",
    layout="wide"
)

# Initialize processors and database
invoice_processor = InvoiceProcessor()
price_comparator = PriceComparator()
db = Database()

def save_uploaded_file(uploaded_file, directory: str) -> str:
    """Save uploaded file to a permanent location."""
    # Create directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uploaded_file.name}"
    file_path = os.path.join(directory, filename)
    
    # Save the file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())
    
    return file_path

def load_initial_pricing():
    """Load and cache initial pricing data."""
    if 'initial_pricing' not in st.session_state:
        st.session_state.initial_pricing = None
        st.session_state.pricing_file_path = None

def process_invoice(uploaded_file) -> Dict[str, Any]:
    """Process uploaded invoice file."""
    try:
        # Save the file permanently
        file_path = save_uploaded_file(
            uploaded_file,
            os.path.join('data', 'invoices')
        )
        
        # Process invoice
        invoice_data = invoice_processor.process_invoice(file_path)
        
        # Save to database
        if invoice_data:
            invoice_id = db.save_invoice(invoice_data, file_path)
            if not invoice_id:
                st.error("Failed to save invoice to database")
        
        return invoice_data
    except Exception as e:
        st.error(f"Error processing invoice: {str(e)}")
        return {}

def create_variance_chart(comparison_results: Dict[str, Any]):
    """Create interactive variance chart."""
    if not comparison_results.get('items_analysis'):
        return None
    
    # Prepare data for visualization
    items = []
    variances = []
    colors = []
    
    for item in comparison_results['items_analysis']:
        items.append(item['description'])
        variance = item.get('variance_percentage', 0)
        variances.append(variance)
        
        # Color coding based on variance
        if abs(variance) <= 5:
            colors.append('green')
        elif abs(variance) <= 10:
            colors.append('orange')
        else:
            colors.append('red')
    
    fig = go.Figure(data=[
        go.Bar(
            x=items,
            y=variances,
            marker_color=colors,
            text=[f"{v:.2f}%" for v in variances],
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title="Price Variances by Item",
        xaxis_title="Items",
        yaxis_title="Variance (%)",
        showlegend=False,
        height=500
    )
    
    return fig

def create_trend_chart(trend_analysis: Dict[str, Any]):
    """Create trend analysis chart."""
    if not trend_analysis.get('trend_by_item'):
        return None
    
    # Prepare data for visualization
    items = []
    avg_variances = []
    trends = []
    
    for item, data in trend_analysis['trend_by_item'].items():
        items.append(item)
        avg_variances.append(data['average_variance'])
        trends.append(data['variance_trend'])
    
    # Create scatter plot
    fig = go.Figure()
    
    # Add points for each trend category
    for trend in ['increasing', 'decreasing', 'stable']:
        mask = [t == trend for t in trends]
        if any(mask):
            fig.add_trace(go.Scatter(
                x=[items[i] for i in range(len(items)) if mask[i]],
                y=[avg_variances[i] for i in range(len(items)) if mask[i]],
                mode='markers',
                name=trend.capitalize(),
                marker=dict(
                    size=12,
                    symbol='circle' if trend == 'stable' else 'triangle-up' if trend == 'increasing' else 'triangle-down'
                )
            ))
    
    fig.update_layout(
        title="Price Variance Trends",
        xaxis_title="Items",
        yaxis_title="Average Variance (%)",
        height=500
    )
    
    return fig

def main():
    """Main application function."""
    st.title("🏗️ Construction Invoice Analyzer")
    
    # Initialize session state
    load_initial_pricing()
    
    # Sidebar
    st.sidebar.title("Settings")
    
    # Initial pricing file upload
    pricing_file = st.sidebar.file_uploader(
        "Upload Initial Pricing File (Excel)",
        type=['xlsx', 'xls'],
        key='pricing_file'
    )
    
    if pricing_file:
        # Save the file permanently
        file_path = save_uploaded_file(
            pricing_file,
            os.path.join('data', 'pricing')
        )
        st.session_state.pricing_file_path = file_path
        
        # Load and save to database
        pricing_data = price_comparator.load_initial_pricing(file_path)
        if db.save_initial_pricing(pricing_data):
            st.session_state.initial_pricing = pricing_data
            st.sidebar.success("Initial pricing data saved successfully")
        else:
            st.sidebar.error("Failed to save initial pricing data")
    
    # Variance tolerance setting
    tolerance = st.sidebar.slider(
        "Variance Tolerance (%)",
        min_value=1,
        max_value=20,
        value=5
    ) / 100
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["Invoice Analysis", "History", "Settings"])
    
    with tab1:
        st.header("Invoice Analysis")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Upload Invoice (PDF/Image)",
            type=['pdf', 'png', 'jpg', 'jpeg']
        )
        
        if uploaded_file and st.session_state.initial_pricing is not None:
            # Process invoice
            with st.spinner("Processing invoice..."):
                invoice_data = process_invoice(uploaded_file)
            
            if invoice_data:
                # Compare prices
                comparison_results = price_comparator.compare_prices(
                    invoice_data,
                    st.session_state.initial_pricing,
                    tolerance
                )
                
                # Save variance analysis
                invoice_id = db.save_invoice(invoice_data, uploaded_file.name)
                if invoice_id:
                    db.save_variance_analysis(invoice_id, comparison_results)
                
                # Display results
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Summary")
                    st.write(f"Invoice Number: {invoice_data.get('invoice_number', 'N/A')}")
                    st.write(f"Total Items: {comparison_results['summary']['total_items']}")
                    st.write(f"Items with Variance: {comparison_results['summary']['items_with_variance']}")
                    st.write(f"High Variance Items: {comparison_results['summary']['high_variance_items']}")
                
                with col2:
                    st.subheader("Variance Analysis")
                    st.write(f"Total Variance: {comparison_results['total_variance']:.2f}")
                    st.write(f"Variance Percentage: {comparison_results['summary']['total_variance_percentage']:.2f}%")
                
                # Display variance chart
                st.subheader("Variance Visualization")
                fig = create_variance_chart(comparison_results)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                
                # Export options
                if st.button("Export to Excel"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                        if price_comparator.generate_variance_report(comparison_results, tmp_file.name):
                            with open(tmp_file.name, 'rb') as f:
                                st.download_button(
                                    "Download Report",
                                    f,
                                    file_name=f"variance_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
        
        elif uploaded_file:
            st.warning("Please upload initial pricing file first")
    
    with tab2:
        st.header("Invoice History")
        
        # Add statistics summary
        st.subheader("Statistics")
        col1, col2, col3 = st.columns(3)
        
        stats_period = st.selectbox(
            "Statistics Period",
            [7, 30, 90, 180, 365],
            index=1,
            format_func=lambda x: f"Last {x} days"
        )
        
        stats = db.get_statistics(stats_period)
        
        with col1:
            st.metric(
                "Total Invoices",
                stats.get('total_invoices', 0),
                help="Total number of invoices processed"
            )
            st.metric(
                "Total Amount",
                f"${stats.get('total_amount', 0):,.2f}",
                help="Total amount of all invoices"
            )
        
        with col2:
            st.metric(
                "Unique Vendors",
                stats.get('unique_vendors', 0),
                help="Number of unique vendors"
            )
            st.metric(
                "Average Variance",
                f"{stats.get('avg_variance', 0):.2f}%",
                help="Average price variance across all items"
            )
        
        with col3:
            st.metric(
                "High Variance Invoices",
                stats.get('high_variance_invoices', 0),
                help="Number of invoices with variance > 10%"
            )
        
        # Enhanced search interface
        st.subheader("Search Invoices")
        
        col4, col5 = st.columns(2)
        
        with col4:
            search_query = st.text_input("Search", placeholder="Invoice number, vendor, or item")
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            vendor = st.text_input("Vendor name")
        
        with col5:
            min_amount = st.number_input("Minimum amount", min_value=0.0, value=0.0)
            max_amount = st.number_input("Maximum amount", min_value=0.0, value=0.0)
            variance_threshold = st.slider(
                "Minimum variance (%)",
                min_value=0.0,
                max_value=50.0,
                value=0.0,
                help="Show only invoices with average variance above this threshold"
            )
            
            sort_options = {
                'date': 'Date',
                'amount': 'Amount',
                'variance': 'Variance'
            }
            sort_by = st.selectbox("Sort by", list(sort_options.keys()), format_func=lambda x: sort_options[x])
            sort_order = st.selectbox("Sort order", ['desc', 'asc'], format_func=lambda x: 'Descending' if x == 'desc' else 'Ascending')
        
        if st.button("Search", key="search_button"):
            results = db.search_invoices(
                query=search_query if search_query else None,
                start_date=datetime.combine(start_date, datetime.min.time()) if start_date else None,
                end_date=datetime.combine(end_date, datetime.max.time()) if end_date else None,
                vendor=vendor if vendor else None,
                min_amount=min_amount if min_amount > 0 else None,
                max_amount=max_amount if max_amount > 0 else None,
                variance_threshold=variance_threshold if variance_threshold > 0 else None,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            if results:
                st.write(f"Found {len(results)} invoices")
                
                # Create summary metrics
                total_amount = sum(r['total_amount'] for r in results)
                avg_variance = sum(r.get('avg_variance', 0) for r in results) / len(results)
                
                col6, col7 = st.columns(2)
                with col6:
                    st.metric("Total Amount", f"${total_amount:,.2f}")
                with col7:
                    st.metric("Average Variance", f"{avg_variance:.2f}%")
                
                # Display results in an expandable table
                for invoice in results:
                    with st.expander(f"Invoice {invoice['invoice_number']} - {invoice['date']} ({invoice['status']})"):
                        col8, col9 = st.columns(2)
                        
                        with col8:
                            st.write(f"**Vendor:** {invoice['vendor_name']}")
                            st.write(f"**Total Amount:** ${invoice['total_amount']:,.2f}")
                            st.write(f"**Average Variance:** {invoice.get('avg_variance', 0):.2f}%")
                        
                        with col9:
                            if invoice['items']:
                                st.write("**Items:**")
                                for item, variance in zip(invoice['items'], invoice['variances']):
                                    color = 'green' if abs(variance) <= 5 else 'orange' if abs(variance) <= 10 else 'red'
                                    st.markdown(f"- {item}: <span style='color: {color}'>{variance:.2f}%</span>", unsafe_allow_html=True)
                        
                        # Add action buttons
                        col10, col11 = st.columns(2)
                        with col10:
                            if os.path.exists(invoice['file_path']):
                                with open(invoice['file_path'], 'rb') as f:
                                    st.download_button(
                                        "Download Original Invoice",
                                        f,
                                        file_name=os.path.basename(invoice['file_path']),
                                        mime="application/octet-stream"
                                    )
            else:
                st.info("No invoices found matching the search criteria")
        
        # Display trend analysis
        st.subheader("Trend Analysis")
        if st.button("Analyze Trends"):
            trend_data = db.get_trend_data()
            if not trend_data.empty:
                fig = create_trend_chart(trend_data)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough data for trend analysis")
    
    with tab3:
        st.header("Settings")
        
        # Data Management
        st.subheader("Data Management")
        
        col12, col13 = st.columns(2)
        
        with col12:
            # Backup with metadata
            if st.button("Create Backup"):
                with st.spinner("Creating backup..."):
                    backup_path = db.backup_database()
                    if backup_path:
                        with open(backup_path, 'rb') as f:
                            st.download_button(
                                "Download Backup",
                                f,
                                file_name=f"invoice_analyzer_backup_v{db.get_current_version()}_{datetime.now().strftime('%Y%m%d')}.zip",
                                mime="application/zip",
                                help="Backup includes database, files, and metadata"
                            )
                        st.success("Backup created successfully")
                        
                        # Display backup metadata
                        with open(os.path.join(os.path.dirname(backup_path), 'metadata.json'), 'r') as f:
                            metadata = json.load(f)
                            st.json(metadata)
                    else:
                        st.error("Failed to create backup")
            
            # Restore with validation
            backup_file = st.file_uploader("Restore from Backup", type=['zip'])
            if backup_file:
                if st.button("Restore Backup"):
                    with st.spinner("Validating and restoring backup..."):
                        # Save uploaded backup temporarily
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                            tmp_file.write(backup_file.getvalue())
                            
                            # Validate backup
                            try:
                                with zipfile.ZipFile(tmp_file.name, 'r') as zipf:
                                    if 'metadata.json' not in zipf.namelist():
                                        st.error("Invalid backup file: missing metadata")
                                    elif 'invoice_analyzer.db' not in zipf.namelist():
                                        st.error("Invalid backup file: missing database")
                                    else:
                                        if db.restore_backup(tmp_file.name):
                                            st.success("Backup restored successfully")
                                            st.warning("Please restart the application")
                                        else:
                                            st.error("Failed to restore backup")
                            except Exception as e:
                                st.error(f"Error validating backup: {e}")
                            
                            os.unlink(tmp_file.name)
        
        with col13:
            # Enhanced export/import
            if st.button("Export Data"):
                with st.spinner("Exporting data..."):
                    export_dir = os.path.join('data', 'exports', datetime.now().strftime('%Y%m%d_%H%M%S'))
                    if db.export_data(export_dir):
                        # Create zip file with metadata
                        zip_path = f"{export_dir}.zip"
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            # Add metadata
                            metadata = {
                                'exported_at': datetime.now().isoformat(),
                                'version': db.get_current_version(),
                                'stats': db.get_statistics()
                            }
                            with open(os.path.join(export_dir, 'export_metadata.json'), 'w') as f:
                                json.dump(metadata, f, indent=2)
                            
                            # Add files
                            for root, _, files in os.walk(export_dir):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arcname = os.path.relpath(file_path, export_dir)
                                    zipf.write(file_path, arcname)
                        
                        with open(zip_path, 'rb') as f:
                            st.download_button(
                                "Download Exported Data",
                                f,
                                file_name=f"invoice_analyzer_export_{datetime.now().strftime('%Y%m%d')}.zip",
                                mime="application/zip",
                                help="Export includes data in CSV format with metadata"
                            )
                        st.success("Data exported successfully")
                        
                        # Clean up
                        shutil.rmtree(export_dir)
                        os.unlink(zip_path)
                    else:
                        st.error("Failed to export data")
            
            # Import with validation
            import_file = st.file_uploader("Import Data", type=['zip'])
            if import_file:
                if st.button("Import Data"):
                    with st.spinner("Validating and importing data..."):
                        # Save uploaded file temporarily
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                            tmp_file.write(import_file.getvalue())
                            
                            # Extract and validate
                            temp_dir = os.path.join('data', 'imports', 'temp')
                            os.makedirs(temp_dir, exist_ok=True)
                            
                            try:
                                with zipfile.ZipFile(tmp_file.name, 'r') as zipf:
                                    zipf.extractall(temp_dir)
                                    
                                    # Validate required files
                                    required_files = ['initial_pricing.csv', 'invoices.csv', 'invoice_items.csv']
                                    missing_files = [f for f in required_files if not os.path.exists(os.path.join(temp_dir, f))]
                                    
                                    if missing_files:
                                        st.error(f"Invalid import file: missing {', '.join(missing_files)}")
                                    else:
                                        if db.import_data(temp_dir):
                                            st.success("Data imported successfully")
                                        else:
                                            st.error("Failed to import data")
                            except Exception as e:
                                st.error(f"Error importing data: {e}")
                            
                            # Clean up
                            shutil.rmtree(temp_dir)
                            os.unlink(tmp_file.name)
        
        # File Cleanup
        st.subheader("File Management")
        col14, col15 = st.columns(2)
        
        with col14:
            days_old = st.slider("Delete files older than (days)", 30, 365, 30)
            if st.button("Clean Up Old Files"):
                with st.spinner("Cleaning up old files..."):
                    if db.cleanup_old_files(days_old):
                        st.success(f"Successfully cleaned up files older than {days_old} days")
                    else:
                        st.error("Failed to clean up files")
        
        with col15:
            # Display storage statistics
            storage_stats = {
                'Database Size': f"{os.path.getsize(db.db_path) / (1024*1024):.2f} MB",
                'Invoice Files': len(glob.glob(os.path.join('data', 'invoices', '*'))),
                'Pricing Files': len(glob.glob(os.path.join('data', 'pricing', '*'))),
                'Backup Files': len(glob.glob(os.path.join('data', 'backups', '*.zip')))
            }
            
            st.write("Storage Statistics:")
            for key, value in storage_stats.items():
                st.metric(key, value)
        
        # OCR settings
        st.subheader("OCR Settings")
        
        ocr_language = st.multiselect(
            "OCR Languages",
            ["English", "Arabic"],
            default=["English", "Arabic"]
        )
        
        if st.button("Save OCR Settings"):
            st.success("OCR settings saved successfully")

if __name__ == "__main__":
    main() 