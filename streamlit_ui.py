import time
import streamlit as st
import requests
import os

from datetime import datetime, date
from typing import Dict, List


# Configuration
API_BASE_URL = st.secrets["API_BASE_URL"]
# Change this to your API URL
POLLING_INTERVAL = 2  # seconds

# Page Configuration
st.set_page_config(
    page_title="Account Reconciliation",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 28px;
        font-weight: 600;
        margin-bottom: 30px;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s;
    }
    .metric-card:hover {
        background-color: #e9ecef;
        transform: translateY(-2px);
    }
    .metric-value {
        font-size: 48px;
        font-weight: bold;
        margin: 10px 0;
    }
    .metric-label {
        font-size: 16px;
        color: #666;
    }
    .stButton > button {
        background-color: #5e2750;
        color: white;
        border-radius: 5px;
        padding: 10px 30px;
        font-weight: 500;
    }
    .export-button {
        background-color: white;
        color: #5e2750;
        border: 2px solid #5e2750;
    }
    .tab-content {
        padding: 20px 0;
    }
    .filter-section {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
    }
    .status-auto {
        background-color: #d4edda;
        color: #155724;
    }
    .status-manual {
        background-color: #cce5ff;
        color: #004085;
    }
    .action-buttons {
        display: flex;
        gap: 10px;
    }
    .processing-spinner {
        text-align: center;
        padding: 50px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'reconciliation'
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'main'
if 'current_thread_id' not in st.session_state:
    st.session_state.current_thread_id = None
if 'reconciliation_status' not in st.session_state:
    st.session_state.reconciliation_status = None
if 'start_date' not in st.session_state:
    st.session_state.start_date = datetime(2025, 8, 1)
if 'end_date' not in st.session_state:
    st.session_state.end_date = datetime(2025, 8, 31)
if 'demo_mode' not in st.session_state:
    st.session_state.demo_mode = True
if 'rec_counter' not in st.session_state:
    st.session_state.rec_counter = 1
if 'history' not in st.session_state:
    st.session_state.history = []
if 'selected_history_item' not in st.session_state:
    st.session_state.selected_history_item = None
if 'pending_actions' not in st.session_state:
    st.session_state.pending_actions = []
# Add proper simulation mode state management
if 'simulation_mode' not in st.session_state:
    st.session_state.simulation_mode = True


def check_api_health():
    """Check if API is healthy"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def start_reconciliation(start_date: str, end_date: str, simulation: bool = True):
    """Start reconciliation process with specified parameters"""
    try:
        payload = {
            "start_date": start_date,
            "end_date": end_date,
            "simulation_mode": simulation
        }
        response = requests.post(f"{API_BASE_URL}/reconcile/start", json=payload)
        if response.status_code == 200:
            data = response.json()
            return data.get("thread_id")
        return None
    except Exception as e:
        st.error(f"Failed to start reconciliation: {str(e)}")
        return None


def get_reconciliation_status(thread_id: str):
    """Get the current status of a reconciliation process"""
    try:
        response = requests.get(f"{API_BASE_URL}/reconcile/status/{thread_id}")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Failed to get status: {str(e)}")
        return None


def submit_review_actions(thread_id: str, actions: List[Dict]):
    """Submit user review actions"""
    try:
        payload = {
            "thread_id": thread_id,
            "actions": actions
        }
        response = requests.post(f"{API_BASE_URL}/reconcile/resolve", json=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Failed to submit actions: {str(e)}")
        return False


def update_exception_decision(thread_id: str, exception_id: str, decision: str, notes: str = ""):
    """Update a single exception decision (approve/reject)"""
    try:
        payload = {
            "thread_id": thread_id,
            "exception_id": exception_id,
            "decision": decision,
            "notes": notes
        }
        response = requests.post(f"{API_BASE_URL}/reconcile/exceptions/update", json=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Failed to update exception: {str(e)}")
        return False


def get_generated_excel_reports():
    """Get list of generated Excel reports from reports folder"""
    import os
    import glob
    
    reports_dir = "reports"
    if os.path.exists(reports_dir):
        excel_reports = glob.glob(os.path.join(reports_dir, "*.xlsx"))
        # Sort by modification time, newest first
        excel_reports = sorted(excel_reports, key=os.path.getmtime, reverse=True)
        return excel_reports
    return []


def export_excel_report(thread_id: str):
    """Generate and download Excel report using the same approach as streamlit_ui.py"""
    try:
        # First check for locally generated reports
        excel_reports = get_generated_excel_reports()
        
        if excel_reports:
            # Get the most recent report
            latest_report = excel_reports[0]
            filename = os.path.basename(latest_report)
            
            # Read the file and return for download
            with open(latest_report, 'rb') as f:
                file_data = f.read()
            
            return {
                'file_data': file_data,
                'filename': filename,
                'success': True
            }
        
        # If no local files, try the API endpoint to trigger generation
        response = requests.post(f"{API_BASE_URL}/reconcile/export/excel", 
                               json={"thread_id": thread_id})
        if response.status_code == 200:
            # Check if it's a file response
            content_type = response.headers.get('content-type', '')
            if 'application/vnd.openxmlformats' in content_type:
                filename = "reconciliation_report.xlsx"
                # Extract filename from content-disposition if available
                cd = response.headers.get('content-disposition', '')
                if 'filename=' in cd:
                    filename = cd.split('filename=')[-1].strip('"')
                
                return {
                    'file_data': response.content,
                    'filename': filename,
                    'success': True
                }
            else:
                # JSON response
                json_response = response.json()
                return json_response
        return None
    except Exception as e:
        st.error(f"Failed to generate Excel report: {str(e)}")
        return None


def approve_reconciliation(thread_id: str, decision: str):
    """Submit final approval decision"""
    try:
        payload = {
            "thread_id": thread_id,
            "decision": decision
        }
        response = requests.post(f"{API_BASE_URL}/reconcile/approve", json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Approval failed: {response.text}")
            return None
    except Exception as e:
        st.error(f"Failed to submit approval: {str(e)}")
        return None


def get_next_rec_id():
    """Generate next incremental REC-ID"""
    current_counter = st.session_state.rec_counter
    rec_id = f"REC-{current_counter:03d}"
    st.session_state.rec_counter += 1
    return rec_id


def format_currency(amount):
    """Format amount as currency"""
    if amount is None:
        return "₦0.00"
    return f"₦{amount:,.2f}"


def format_date_display(date_str):
    """Format date for display as YYYY-MM-DD"""
    if not date_str:
        return ""
    
    # Handle different date formats
    try:
        # Try parsing ISO format first (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        if 'T' in str(date_str) or ' ' in str(date_str):
            # Contains time component, extract date part
            date_part = str(date_str).split('T')[0].split(' ')[0]
        else:
            date_part = str(date_str)
        
        # Parse and reformat to ensure consistency
        from datetime import datetime
        dt = datetime.strptime(date_part, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except:
        # If parsing fails, return as-is
        return str(date_str)


def format_date_mm_dd_yyyy(date_str):
    """Format date for display as MM/DD/YYYY"""
    if not date_str:
        return ""
    
    try:
        # Handle different date formats
        if 'T' in str(date_str) or ' ' in str(date_str):
            # Contains time component, extract date part
            date_part = str(date_str).split('T')[0].split(' ')[0]
        else:
            date_part = str(date_str)
        
        # Parse and reformat to MM/DD/YYYY
        from datetime import datetime
        dt = datetime.strptime(date_part, '%Y-%m-%d')
        return dt.strftime('%m/%d/%Y')
    except:
        # If parsing fails, return as-is
        return str(date_str)


def format_reconciliation_period(reconciliation_period):
    """Format reconciliation period for display (e.g., 'July 1 - July 31, 2025')"""
    # Try to get from provided reconciliation_period first
    start_date = None
    end_date = None
    
    if reconciliation_period and isinstance(reconciliation_period, dict):
        start_date = reconciliation_period.get('start_date', '')
        end_date = reconciliation_period.get('end_date', '')
    
    # Fallback to session state if not available
    if not start_date or not end_date:
        if hasattr(st.session_state, 'start_date') and hasattr(st.session_state, 'end_date'):
            start_date = st.session_state.start_date.strftime('%Y-%m-%d') if st.session_state.start_date else ''
            end_date = st.session_state.end_date.strftime('%Y-%m-%d') if st.session_state.end_date else ''
    
    if not start_date or not end_date:
        return "Period not available"
    
    try:
        from datetime import datetime
        
        # Parse start date
        if 'T' in str(start_date) or ' ' in str(start_date):
            start_part = str(start_date).split('T')[0].split(' ')[0]
        else:
            start_part = str(start_date)
        start_dt = datetime.strptime(start_part, '%Y-%m-%d')
        
        # Parse end date
        if 'T' in str(end_date) or ' ' in str(end_date):
            end_part = str(end_date).split('T')[0].split(' ')[0]
        else:
            end_part = str(end_date)
        end_dt = datetime.strptime(end_part, '%Y-%m-%d')
        
        # Format as "Month Day - Month Day, Year"
        if start_dt.year == end_dt.year and start_dt.month == end_dt.month:
            # Same month and year: "July 1 - 31, 2025"
            return f"{start_dt.strftime('%B %d')} - {end_dt.strftime('%d, %Y')}"
        elif start_dt.year == end_dt.year:
            # Same year: "July 1 - August 31, 2025"
            return f"{start_dt.strftime('%B %d')} - {end_dt.strftime('%B %d, %Y')}"
        else:
            # Different years: "December 1, 2024 - January 31, 2025"
            return f"{start_dt.strftime('%B %d, %Y')} - {end_dt.strftime('%B %d, %Y')}"
    except Exception as e:
        # If parsing fails, return raw dates
        return f"{start_date} - {end_date}"


def parse_bank_matches(bank_matches: Dict, unmatched_gl_transactions: list = None) -> Dict:
    """Parse bank matches data for UI display"""
    summary = {
        'matched_count': 0,
        'unmatched_count': 0,
        'exceptions_count': 0,
        'matched_transactions': [],
        'unmatched_bank': [],
        'unmatched_gl': [],
        'exceptions': [],  # New: actual exceptions array
        'ai_suggestions': []  # Legacy compatibility
    }
    
    # Add unmatched GL transactions from top-level (if provided)
    if unmatched_gl_transactions:
        summary['unmatched_gl'] = unmatched_gl_transactions
    
    for bank_name, bank_data in bank_matches.items():
        # Aggregate matched transactions
        matched = bank_data.get('matched_transactions', [])
        summary['matched_count'] += len(matched)
        for match in matched:
            # Get GL transaction from gl_entries array (first entry)
            gl_entries = match.get('gl_entries', [])
            gl_transaction = gl_entries[0] if gl_entries else {}
            
            summary['matched_transactions'].append({
                'bank': bank_name,
                'bank_transaction': match.get('bank_transaction', {}),
                'gl_transaction': gl_transaction,
                'match_type': ('Auto' if match.get('confidence', 0) >= 0.75
                               else 'Manual'),
                'confidence': match.get('confidence', 0)
            })
        
        # Aggregate exceptions (0.60-0.74 confidence matches)
        exceptions = bank_data.get('exceptions', [])
        summary['exceptions_count'] += len(exceptions)
        for exception in exceptions:
            summary['exceptions'].append({
                'bank': bank_name,
                **exception
            })
        
        # Aggregate unmatched bank transactions
        unmatched_bank = bank_data.get('unmatched_bank_transactions', [])
        summary['unmatched_count'] += len(unmatched_bank)
        for tx in unmatched_bank:
            summary['unmatched_bank'].append({
                'bank': bank_name,
                **tx
            })
        
        # Legacy: Aggregate AI suggestions
        ai_suggestions = bank_data.get('ai_suggestions', [])
        for suggestion in ai_suggestions:
            summary['ai_suggestions'].append({
                'bank': bank_name,
                **suggestion
            })
    
    return summary


def poll_status_until_ready():
    """Poll the API status until reconciliation is ready for review or complete"""
    if not st.session_state.current_thread_id:
        return None
    
    max_attempts = 30  # Max 60 seconds of polling
    for _ in range(max_attempts):
        status = get_reconciliation_status(st.session_state.current_thread_id)
        if status:
            current_status = status.get('status')
            # Store the status data in session state like original UI
            st.session_state.reconciliation_status = status
            
            if current_status in ['review_required', 'awaiting_final_approval', 'complete']:
                return status
                
        time.sleep(POLLING_INTERVAL)
    
    return None


def render_reconciliation_main():
    """Render main reconciliation page"""
    # Date selection and data source section
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Select start and end date")
        
        # Set defaults based on simulation mode like original UI
        if st.session_state.simulation_mode:
            # Use July 2025 for simulation mode (matches generated test data)
            default_start = date(2025, 7, 1)
            default_end = date(2025, 7, 31)
            st.info("📅 **Simulation dates set to July 2025**")
        else:
            # Default to current month for live mode
            today = date.today()
            default_start = date(today.year, today.month, 1)
            default_end = date(today.year, today.month, today.day)
        
        start_date = st.date_input("Start Date", 
                                   value=default_start,
                                   key='start_date_input')
        end_date = st.date_input("End Date", 
                                 value=default_end,
                                 key='end_date_input')
        
        if st.button("Run", use_container_width=True, type="primary"):
            # Update session state with selected dates
            st.session_state.start_date = datetime.combine(start_date, datetime.min.time())
            st.session_state.end_date = datetime.combine(end_date, datetime.min.time())
            
            # Start reconciliation via API with proper simulation mode
            thread_id = start_reconciliation(
                start_date=str(start_date),
                end_date=str(end_date),
                simulation=st.session_state.simulation_mode  # Use the proper state
            )
            
            if thread_id:
                st.session_state.current_thread_id = thread_id
                st.session_state.view_mode = 'processing'
                
                # Generate incremental REC-ID
                rec_id = get_next_rec_id()
                
                # Add to history
                st.session_state.history.append({
                    'rec_id': rec_id,
                    'thread_id': thread_id,
                    'period': f"{start_date} → {end_date}",
                    'status': 'processing',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                st.rerun()
        
        st.markdown("### Data sources")
        st.markdown("**Bank**")
        st.markdown("🏦 Mono")
        
        st.markdown("**General Ledger**")
        st.markdown("📊 Acumatica")
    
    with col2:
        # Display metrics based on current status
        if st.session_state.reconciliation_status:
            render_metrics_display()
        else:
            # Display placeholders
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                st.markdown("### Matched transactions for period")
                st.markdown("# —")
            
            with col_m2:
                st.markdown("### Unmatched transactions for period")
                st.markdown("# —")
            
            st.markdown("")
            st.markdown("### Exceptions for period")
            st.markdown("# —")
            
            # Disabled export button
            st.markdown("")
            st.button("📊 Export report", use_container_width=True, disabled=True)


def render_metrics_display():
    """Render the metrics display based on current reconciliation status"""
    status = st.session_state.reconciliation_status
    
    if not status:
        return
    
    # Parse the bank matches data
    if 'bank_matches' in status:
        summary = parse_bank_matches(
            status['bank_matches'], 
            status.get('unmatched_gl_transactions', [])
        )
        
        col_m1, col_m2 = st.columns(2)
        
        with col_m1:
            if st.button(f"### Matched transactions for period\n\n# {summary['matched_count']}",
                       use_container_width=True,
                       key='matched_btn'):
                st.session_state.view_mode = 'matched'
                st.rerun()
        
        with col_m2:
            if st.button(f"### Unmatched transactions for period\n\n# {summary['unmatched_count']}",
                       use_container_width=True,
                       key='unmatched_btn'):
                st.session_state.view_mode = 'unmatched'
                st.rerun()
        
        st.markdown("")
        if st.button(f"### Exceptions for period\n\n# {summary['exceptions_count']}",
                   use_container_width=True,
                   key='exceptions_btn'):
            st.session_state.view_mode = 'exceptions'
            st.rerun()
        
        # Export button
        st.markdown("")
        if st.button("📊 Export report", use_container_width=True, key='export_btn'):
            st.session_state.view_mode = 'export'
            st.rerun()


def render_processing():
    """Render processing screen with status polling"""
    st.markdown("## Processing Reconciliation")
    
    # Show single spinner for entire process
    with st.spinner("Running reconciliation process..."):
        status = poll_status_until_ready()
        
        if status:
            st.session_state.reconciliation_status = status
            
            if status.get('status') == 'awaiting_human_review':
                st.success("✅ Reconciliation ready for review!")
                time.sleep(1)
                st.session_state.view_mode = 'main'
                st.rerun()
            elif status.get('status') == 'awaiting_final_approval':
                st.session_state.view_mode = 'approval'
                st.rerun()
            elif status.get('status') == 'complete':
                st.success("✅ Reconciliation complete!")
                st.session_state.view_mode = 'main'
                st.rerun()
        else:
            st.error("Failed to complete reconciliation. Please try again.")
            st.session_state.view_mode = 'main'
            st.rerun()


def render_matched_transactions():
    """Render matched transactions page"""
    if st.button("← Matched transaction", key='back_matched'):
        st.session_state.view_mode = 'main'
        st.rerun()
    
    status = st.session_state.reconciliation_status
    if not status:
        st.info("No data available")
        return
    
    summary = parse_bank_matches(
        status.get('bank_matches', {}), 
        status.get('unmatched_gl_transactions', [])
    )
    matched = summary['matched_transactions']
    
    period_text = format_reconciliation_period(status.get('reconciliation_period', {}))
    st.markdown(f"**Period:** {period_text}")
    
    # Filter by bank
    banks = ['All Banks'] + list(set([tx['bank'] for tx in matched]))
    selected_bank = st.selectbox("Filter by Bank", banks, key='bank_filter')
    
    # Filter transactions
    if selected_bank != 'All Banks':
        matched = [tx for tx in matched if tx['bank'] == selected_bank]
    
    # Pagination for matched transactions
    total_matches = len(matched)
    items_per_page = 5
    total_pages = max(1, (total_matches + items_per_page - 1) // items_per_page)
    
    if 'matched_page' not in st.session_state:
        st.session_state.matched_page = 1
    
    # Page navigation
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        if st.button("← Previous", key="matched_prev", disabled=st.session_state.matched_page <= 1):
            st.session_state.matched_page -= 1
            st.rerun()
    
    with col_nav2:
        st.markdown(f"<div style='text-align: center; padding: 8px;'>Showing results {st.session_state.matched_page} of {total_pages}</div>", unsafe_allow_html=True)
    
    with col_nav3:
        if st.button("Next →", key="matched_next", disabled=st.session_state.matched_page >= total_pages):
            st.session_state.matched_page += 1
            st.rerun()
    
    # Get current page items
    start_idx = (st.session_state.matched_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    current_page_matches = matched[start_idx:end_idx]
    
    # Display matched transactions
    for tx in current_page_matches:
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.markdown("**Bank**")
            bank_tx = tx['bank_transaction']
            date_formatted = format_date_display(bank_tx.get('date', ''))
            st.markdown(f"{date_formatted} • {format_currency(bank_tx.get('amount', 0))}")
            st.markdown(f"{bank_tx.get('description', bank_tx.get('narration', ''))}")
            st.markdown(f"{tx['bank']}")
        
        with col2:
            st.markdown("**General Ledger**")
            gl_tx = tx['gl_transaction']
            date_formatted = format_date_display(gl_tx.get('date', ''))
            st.markdown(f"{date_formatted} • {format_currency(gl_tx.get('amount', 0))}")
            st.markdown(f"{gl_tx.get('description', '')}")
            st.markdown(f"Acumatica ERP")
        
        with col3:
            st.markdown("**Match Type**")
            badge_class = 'status-auto' if tx['match_type'] == 'Auto' else 'status-manual'
            st.markdown(f'<span class="status-badge {badge_class}">{tx["match_type"]}</span>', 
                      unsafe_allow_html=True)
        
        st.divider()
    
    st.markdown(f"Showing {len(matched)} results")


def render_unmatched_transactions():
    """Render unmatched transactions page"""
    if st.button("← Unmatched transaction", key='back_unmatched'):
        st.session_state.view_mode = 'main'
        st.rerun()
    
    status = st.session_state.reconciliation_status
    if not status:
        st.info("No data available")
        return
    
    summary = parse_bank_matches(
        status.get('bank_matches', {}), 
        status.get('unmatched_gl_transactions', [])
    )
    
    period_text = format_reconciliation_period(status.get('reconciliation_period', {}))
    st.markdown(f"**Period:** {period_text}")
    
    st.info("ℹ️ These transactions have no matches. Review and decide on appropriate action.")
    
    # Tabs for Bank and GL
    tab1, tab2 = st.tabs(["Unmatched Bank", "Unmatched GL"])
    
    with tab1:
        unmatched_bank = summary['unmatched_bank']
        if unmatched_bank:
            # Pagination for unmatched bank transactions
            total_bank = len(unmatched_bank)
            items_per_page = 5
            total_pages = max(1, (total_bank + items_per_page - 1) // items_per_page)
            
            if 'unmatched_bank_page' not in st.session_state:
                st.session_state.unmatched_bank_page = 1
            
            # Page navigation
            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            with col_nav1:
                if st.button("← Previous", key="bank_prev", disabled=st.session_state.unmatched_bank_page <= 1):
                    st.session_state.unmatched_bank_page -= 1
                    st.rerun()
            
            with col_nav2:
                st.markdown(f"<div style='text-align: center; padding: 8px;'>Showing results {st.session_state.unmatched_bank_page} of {total_pages}</div>", unsafe_allow_html=True)
            
            with col_nav3:
                if st.button("Next →", key="bank_next", disabled=st.session_state.unmatched_bank_page >= total_pages):
                    st.session_state.unmatched_bank_page += 1
                    st.rerun()
            
            # Get current page items
            start_idx = (st.session_state.unmatched_bank_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            current_page_bank = unmatched_bank[start_idx:end_idx]
            
            # Display each unmatched bank transaction properly formatted
            for tx in current_page_bank:
                col1, col2, col3, col4, col5 = st.columns([1, 1, 1.5, 2, 0.8])
                
                with col1:
                    st.markdown("**Bank**")
                    st.markdown(f"{tx.get('bank', '')}")
                
                with col2:
                    st.markdown("**Date**")
                    date_formatted = format_date_mm_dd_yyyy(tx.get('date', ''))
                    st.markdown(f"{date_formatted}")
                
                with col3:
                    st.markdown("**Amount**")
                    st.markdown(f"{format_currency(tx.get('amount', 0))}")
                
                with col4:
                    st.markdown("**Description**")
                    description = tx.get('description', tx.get('narration', ''))
                    st.markdown(f"{description}")
                
                with col5:
                    st.markdown("**Type**")
                    tx_type = tx.get('type', tx.get('transaction_type', 'Debit' if tx.get('amount', 0) < 0 else 'Credit'))
                    st.markdown(f"{tx_type}")
                
                st.divider()
            
            st.markdown(f"Showing {len(current_page_bank)} of {total_bank} unmatched bank transactions")
        else:
            st.info("No unmatched bank transactions")
    
    with tab2:
        unmatched_gl = summary['unmatched_gl']
        if unmatched_gl:
            # Pagination for unmatched GL transactions
            total_gl = len(unmatched_gl)
            items_per_page = 5
            total_pages = max(1, (total_gl + items_per_page - 1) // items_per_page)
            
            if 'unmatched_gl_page' not in st.session_state:
                st.session_state.unmatched_gl_page = 1
            
            # Page navigation
            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            with col_nav1:
                if st.button("← Previous", key="gl_prev", disabled=st.session_state.unmatched_gl_page <= 1):
                    st.session_state.unmatched_gl_page -= 1
                    st.rerun()
            
            with col_nav2:
                st.markdown(f"<div style='text-align: center; padding: 8px;'>Showing results {st.session_state.unmatched_gl_page} of {total_pages}</div>", unsafe_allow_html=True)
            
            with col_nav3:
                if st.button("Next →", key="gl_next", disabled=st.session_state.unmatched_gl_page >= total_pages):
                    st.session_state.unmatched_gl_page += 1
                    st.rerun()
            
            # Get current page items
            start_idx = (st.session_state.unmatched_gl_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            current_page_gl = unmatched_gl[start_idx:end_idx]
            
            # Display each unmatched GL transaction properly formatted
            # Order: General Ledger (GL), Date, Amount, Description
            for tx in current_page_gl:
                col1, col2, col3, col4 = st.columns([1.5, 1, 1.5, 2])
                
                with col1:
                    st.markdown("**General Ledger (GL)**")
                    st.markdown("Acumatica ERP")
                
                with col2:
                    st.markdown("**Date**")
                    date_formatted = format_date_mm_dd_yyyy(tx.get('date', ''))
                    st.markdown(f"{date_formatted}")
                
                with col3:
                    st.markdown("**Amount**")
                    st.markdown(f"{format_currency(tx.get('amount', 0))}")
                
                with col4:
                    st.markdown("**Description**")
                    description = tx.get('description', tx.get('narration', ''))
                    st.markdown(f"{description}")
                
                st.divider()
            
            st.markdown(f"Showing {len(current_page_gl)} of {total_gl} unmatched GL transactions")
        else:
            st.info("No unmatched GL transactions")


def render_exceptions():
    """Render exceptions page with AI suggestions"""
    if st.button("← Back to Main", key='back_exceptions'):
        st.session_state.view_mode = 'main'
        st.rerun()
    
    status = st.session_state.reconciliation_status
    if not status:
        st.info("No data available")
        return
    
    summary = parse_bank_matches(
        status.get('bank_matches', {}), 
        status.get('unmatched_gl_transactions', [])
    )
    exceptions = summary.get('exceptions', [])
    
    period_text = format_reconciliation_period(status.get('reconciliation_period', {}))
    st.markdown(f"**Period:** {period_text}")
    
    st.title(f"🔍 Exceptions Review ({len(exceptions)} items)")
    
    if not exceptions:
        st.info("✅ No exceptions found! All transactions were either "
                "auto-matched or have confidence below the review threshold.")
        return
    
    st.warning(
        "⚠️ **Exceptions requiring review:** These transactions have "
        "moderate confidence (60-74%) and need human judgment."
    )
    
    # Track actions for this session
    if 'pending_actions' not in st.session_state:
        st.session_state.pending_actions = []
    
    # Display exceptions in Bank|GL side-by-side format with AI analysis
    for idx, exception in enumerate(exceptions):
        bank_tx = exception.get('bank_transaction', {})
        gl_entries = exception.get('gl_entries', [])
        confidence = exception.get('confidence', 0)
        ai_confidence = exception.get('ai_confidence', 0)
        ai_reasoning = exception.get('ai_reasoning', 'No AI analysis available')
        ai_analyzed = exception.get('ai_analyzed', False)
        
        # Exception header with both rule-based and AI confidence
        rule_confidence_pct = confidence * 100
        ai_confidence_pct = ai_confidence * 100
        
        if ai_confidence_pct >= 70:
            ai_color = "green"
            ai_label = "Strong"
        elif ai_confidence_pct >= 65:
            ai_color = "orange"
            ai_label = "Moderate"
        else:
            ai_color = "red"
            ai_label = "Weak"
            
        st.markdown(f"""
        ### Exception #{idx + 1}
        <div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <strong>Rule-based: {rule_confidence_pct:.1f}%</strong> | 
                    <strong style='color: {ai_color};'>AI: {ai_confidence_pct:.1f}% ({ai_label})</strong>
                </div>
                <div style='font-size: 14px; color: #666;'>
                    {exception.get('bank_account', 'Unknown Account')}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Bank | GL | Flags columns
        col_bank, col_gl, col_flags, col_actions = st.columns([2, 2, 2, 1])
        
        with col_bank:
            st.markdown("#### 🏦 Bank Transaction")
            st.markdown(f"**Date:** {bank_tx.get('date', 'N/A')}")
            st.markdown(f"**Amount:** {format_currency(bank_tx.get('amount', 0))}")
            st.markdown(f"**Description:** {bank_tx.get('description', 'N/A')}")
            st.markdown(f"**ID:** `{bank_tx.get('transaction_id', 'N/A')}`")
            if bank_tx.get('balance'):
                st.markdown(f"**Balance:** {format_currency(bank_tx.get('balance'))}")
        
        with col_gl:
            st.markdown("#### 📚 Suggested GL Match")
            if gl_entries:
                gl_tx = gl_entries[0]  # Show first GL entry
                st.markdown(f"**Date:** {gl_tx.get('date', 'N/A')}")
                st.markdown(f"**Amount:** {format_currency(gl_tx.get('debit_base', gl_tx.get('credit_base', gl_tx.get('amount', 0))))}")
                st.markdown(f"**Description:** {gl_tx.get('description', 'N/A')}")
                st.markdown(f"**Account:** {gl_tx.get('account', 'N/A')}")
                st.markdown(f"**ID:** `{gl_tx.get('transaction_id', 'N/A')}`")
                
                # Show match scores
                scores = exception.get('scores', {})
                if scores:
                    st.markdown("**Matching Scores:**")
                    st.markdown(f"• Amount: {scores.get('amount', 0):.2f}")
                    st.markdown(f"• Date: {scores.get('date', 0):.2f}") 
                    st.markdown(f"• Description: {scores.get('description', 0):.2f}")
            else:
                st.info("No GL match found in rule-based matching")

        with col_flags:
            st.markdown("#### 🚩 AI Analysis")
            if ai_analyzed:
                st.markdown(f"**Confidence:** {ai_confidence_pct:.1f}%")
                with st.expander("💬 AI Reasoning", expanded=True):
                    st.markdown(ai_reasoning)
            else:
                st.warning("AI analysis pending...")
        
        with col_actions:
            st.markdown("#### ⚡ Actions")
            
            # Generate unique exception ID
            exception_id = f"{exception.get('bank_account', 'unknown')}_{bank_tx.get('transaction_id', 'unknown')}"
            
            # Approve button
            if st.button(
                "✅ Approve", 
                key=f"approve_exception_{idx}", 
                type="primary",
                help="Accept this match and move to Matched Transactions"
            ):
                result = update_exception_decision(
                    st.session_state.current_thread_id,
                    exception_id,
                    "approve"
                )
                if result:
                    st.success("✅ Approved! Moving to matched transactions...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to approve")
            
            # Reject button  
            if st.button(
                "❌ Reject", 
                key=f"reject_exception_{idx}",
                help="Reject this match and move to unmatched"
            ):
                result = update_exception_decision(
                    st.session_state.current_thread_id,
                    exception_id,
                    "reject"
                )
                if result:
                    st.info("❌ Rejected! Moving to unmatched transactions...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to reject")
        
        st.divider()

    # All exceptions now processed individually - no batch actions needed
    st.info("💡 **Tip:** Each exception is processed immediately when you click Approve or Reject. "
            "No need to submit batch actions!")


def render_approval():
    """Render final approval page"""
    st.markdown("## Final Approval Required")
    
    status = st.session_state.reconciliation_status
    if not status:
        st.info("No data available")
        return
    
    statement = status.get('reconciliation_statement', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Starting Balance", format_currency(statement.get('starting_balance', 0)))
        st.metric("Net Change", format_currency(statement.get('net_change', 0)))
    
    with col2:
        st.metric("Ending Balance", format_currency(statement.get('ending_balance', 0)))
        st.metric("Variance", format_currency(statement.get('variance', 0)))
    
    # Show if balanced
    if statement.get('is_balanced'):
        st.success("✅ Reconciliation is balanced")
    else:
        st.warning("⚠️ Reconciliation has variances")
    
    # Adjustments
    adjustments = statement.get('adjustments', [])
    if adjustments:
        st.markdown("### Adjustments")
        for adj in adjustments:
            st.markdown(f"- {adj.get('description', '')}: {format_currency(adj.get('amount', 0))}")
    
    # Approval buttons
    col1, col2, col3 = st.columns([1, 1, 3])
    
    with col1:
        if st.button("Approve", use_container_width=True, type="primary"):
            if approve_reconciliation(st.session_state.current_thread_id, "approve"):
                st.success("Reconciliation approved!")
                st.session_state.view_mode = 'processing'
                st.rerun()
    
    with col2:
        if st.button("Reject", use_container_width=True):
            if approve_reconciliation(st.session_state.current_thread_id, "reject"):
                st.warning("Reconciliation rejected")
                st.session_state.view_mode = 'main'
                st.rerun()

def render_export():
    """Render export page"""
    if st.button("← Export report", key='back_export'):
        st.session_state.view_mode = 'main'
        st.rerun()
    
    status = st.session_state.reconciliation_status
    
    period_text = format_reconciliation_period(status.get('reconciliation_period', {}))
    st.markdown(f"**Period:** {period_text}")
    
    # Get exception counts to determine if approval is available
    bank_matches = status.get('bank_matches', {})
    unmatched_gl = status.get('unmatched_gl_transactions', [])
    summary = parse_bank_matches(bank_matches, unmatched_gl)
    exceptions_count = summary.get('exceptions_count', 0)
    
    # Check if report is available (after approval) or ready for approval 
    # (0 exceptions)
    report_approved = status and status.get('status') == 'complete'
    ready_for_approval = exceptions_count == 0 and not report_approved
    
    # Show approval section if ready
    if ready_for_approval:
        st.markdown("### 📋 Reconciliation Approval")
        st.success(
            "No exceptions found - reconciliation is ready for approval!"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "✅ Approve Reconciliation",
                use_container_width=True,
                type="primary",
                disabled=st.session_state.get('approval_submitted', False)
            ):
                # Set flag to prevent multiple submissions
                st.session_state.approval_submitted = True
                
                with st.spinner("Submitting approval and generating reports..."):
                    result = approve_reconciliation(
                        st.session_state.current_thread_id,
                        "approved"
                    )
                    if result:
                        st.success("✅ Reconciliation approved!")
                        st.info("📊 Reports are being generated...")
                        
                        # Update the reconciliation status to approved
                        st.session_state.reconciliation_status['status'] = 'complete'
                        
                        # Set a flag to show we're waiting for reports
                        st.session_state.reports_generating = True
                        st.session_state.reports_generation_time = time.time()
                        
                        # Wait a moment for report generation to complete
                        time.sleep(2)
                        st.rerun()
                    else:
                        # Reset flag if approval failed
                        st.session_state.approval_submitted = False
                        
        with col2:
            if st.button("❌ Reject", use_container_width=True):
                result = approve_reconciliation(
                    st.session_state.current_thread_id,
                    "rejected"
                )
                if result:
                    st.warning("Reconciliation rejected")
                    st.session_state.reconciliation_status['status'] = 'rejected'
                    st.rerun()
        
        st.markdown("---")
    elif exceptions_count > 0:
        st.warning(
            f"⚠️ {exceptions_count} exceptions need to be reviewed "
            f"before approval"
        )
        st.info(
            "Please go to the Exceptions tab to review and resolve "
            "all issues first"
        )
        st.markdown("---")
    elif report_approved:
        st.success("✅ Reconciliation has been approved")
        
        # Check if reports are still being generated
        if st.session_state.get('reports_generating', False):
            generation_time = st.session_state.get('reports_generation_time', 0)
            elapsed = time.time() - generation_time
            
            if elapsed < 30:  # Wait up to 30 seconds for reports
                st.info(f"📊 Reports are being generated... ({elapsed:.1f}s)")
                # Check if reports are ready
                reports = get_generated_excel_reports()
                if reports:
                    st.session_state.reports_generating = False
                    st.success("✅ Reports are ready for download!")
                    st.rerun()
                else:
                    # Auto-refresh every 2 seconds
                    time.sleep(1)
                    st.rerun()
            else:
                # Timeout - stop waiting
                st.session_state.reports_generating = False
                st.warning("Report generation is taking longer than expected")
        
        st.markdown("---")
    else:
        st.info("📋 Reports will be available after reconciliation is approved")
        st.markdown("---")
    
    # Export format options
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("� PDF Export", use_container_width=True, key='pdf_export', disabled=True):
            st.info("PDF export is not yet available")
    
    with col2:
        excel_disabled = not report_approved
        if st.button("📊 Excel Export", use_container_width=True, key='excel_export', disabled=excel_disabled):
            if report_approved:
                # Call the Excel export endpoint
                with st.spinner("Generating Excel report..."):
                    result = export_excel_report(st.session_state.current_thread_id)
                    if result and result.get('success'):
                        # Show download button
                        st.download_button(
                            label="📥 Download Excel Report",
                            data=result['file_data'],
                            file_name=result['filename'],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                        st.success("Excel report generated successfully!")
                    elif result and 'message' in result:
                        st.success(result['message'])
                        if 'report_paths' in result:
                            st.info("Report paths: " + str(result['report_paths']))
                    else:
                        st.error("Failed to generate Excel report")
            else:
                st.warning("Excel export will be available after approval")
    
    with col3:
        if st.button("📁 CSV Export", use_container_width=True, key='csv_export', disabled=True):
            st.info("CSV export is not yet available")
    
    with col4:
        st.markdown("### Send to accounting software")
        st.markdown("(coming soon)")
    
    # Status message for export availability
    if not report_approved:
        st.info("📋 Reports will be available after reconciliation is approved")
    else:
        st.success("✅ Reconciliation approved - Reports are now available for download")

def render_history():
    """Render history page with API data"""
    if st.session_state.selected_history_item:
        render_history_detail()
    else:
        st.markdown("### Reconciliation History")
        
        # Pagination for history
        total_history = len(st.session_state.history)
        items_per_page = 5
        total_pages = max(1, (total_history + items_per_page - 1) // items_per_page)
        
        if 'history_page' not in st.session_state:
            st.session_state.history_page = 1
        
        # Page navigation
        if total_history > 0:
            col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
            with col_nav1:
                if st.button("← Previous", key="history_prev", disabled=st.session_state.history_page <= 1):
                    st.session_state.history_page -= 1
                    st.rerun()
            
            with col_nav2:
                st.markdown(f"<div style='text-align: center; padding: 8px;'>Showing results {st.session_state.history_page} of {total_pages}</div>", unsafe_allow_html=True)
            
            with col_nav3:
                if st.button("Next →", key="history_next", disabled=st.session_state.history_page >= total_pages):
                    st.session_state.history_page += 1
                    st.rerun()
        
        # Get current page items
        start_idx = (st.session_state.history_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_page_history = st.session_state.history[start_idx:end_idx]
        
        # Display history items
        if current_page_history:
            for idx, item in enumerate(current_page_history):
                col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
                
                with col1:
                    st.markdown("**Run ID**")
                    st.markdown(item.get('rec_id', f"REC-{item['thread_id'][:8]}"))
                
                with col2:
                    st.markdown("**Period**")
                    st.markdown(item['period'])
                
                with col3:
                    st.markdown("**Created**")
                    created_at = item.get('created_at', 'N/A')
                    if created_at != 'N/A':
                        # Format the created_at timestamp
                        try:
                            dt = datetime.strptime(
                                created_at, '%Y-%m-%d %H:%M:%S'
                            )
                            formatted_date = dt.strftime('%b %d, %Y')
                            formatted_time = dt.strftime('%I:%M %p')
                            st.markdown(f"{formatted_date}")
                            st.markdown(f"{formatted_time}")
                        except Exception:
                            st.markdown(created_at)
                    else:
                        st.markdown("N/A")
                
                with col4:
                    if st.button(
                        "View", 
                        key=f"view_history_{idx}", 
                        type="primary"
                    ):
                        # Load historical data
                        status = get_reconciliation_status(item['thread_id'])
                        if status:
                            st.session_state.reconciliation_status = status
                            st.session_state.selected_history_item = item
                            st.rerun()
                
                st.divider()
        else:
            st.info("No reconciliation history available")
        
        st.markdown(f"Showing {len(current_page_history)} of {total_history} results")


def render_history_detail():
    """Render history detail page"""
    if st.button("← Back", key='back_history_detail'):
        st.session_state.selected_history_item = None
        st.rerun()
    
    item = st.session_state.selected_history_item
    status = st.session_state.reconciliation_status
    
    rec_id = item.get('rec_id', f"REC-{item['thread_id'][:8]}")
    st.markdown(f"## {rec_id}")
    st.markdown(f"**Period:** {item['period']}")
    
    # Display metrics from status
    if status and 'bank_matches' in status:
        summary = parse_bank_matches(
            status['bank_matches'], 
            status.get('unmatched_gl_transactions', [])
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Matched transactions for period")
            st.markdown(f"# {summary['matched_count']}")
        
        with col2:
            st.markdown("### Unmatched transactions for period")
            st.markdown(f"# {summary['unmatched_count']}")

        st.markdown("### Exceptions for period")
        st.markdown(f"# {summary['exceptions_count']}")

        if st.button(
            "📊 Export report",
            use_container_width=True,
            key='history_export_btn'
        ):
            st.session_state.view_mode = 'export'
            st.rerun()


# Main execution logic (moved to end like streamlit_ui.py)
if not check_api_health():
    st.error("⚠️ Cannot connect to the reconciliation API. Please ensure the backend is running.")
    st.stop()

col1, _, col3 = st.columns([6, 2, 1])
with col1:
    st.markdown('<h1 class="main-header">Account Reconciliation</h1>', unsafe_allow_html=True)
with col3:
    # Proper toggle state management like original streamlit_ui.py
    demo_toggle = st.toggle(
        'Demo Mode',
        value=st.session_state.simulation_mode,
        help="Toggle between Live mode (real APIs) and Demo mode (simulation data)"
    )
    # Update session state when toggle changes
    st.session_state.simulation_mode = demo_toggle
    st.session_state.demo_mode = demo_toggle  # Keep both for compatibility
    
    if demo_toggle:
        st.caption("🎭 Demo Mode")
    else:
        st.caption("🔴 Live Mode")

tab1, tab2 = st.tabs(["Reconcile", "History"])

with tab1:
    if st.session_state.view_mode == 'main':
        render_reconciliation_main()
    elif st.session_state.view_mode == 'matched':
        render_matched_transactions()
    elif st.session_state.view_mode == 'unmatched':
        render_unmatched_transactions()
    elif st.session_state.view_mode == 'exceptions':
        render_exceptions()
    elif st.session_state.view_mode == 'export':
        render_export()
    elif st.session_state.view_mode == 'processing':
        render_processing()
    elif st.session_state.view_mode == 'approval':
        render_approval()

with tab2:
    render_history()
