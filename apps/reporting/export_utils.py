# C:\Users\Adeyanju Joshua\Desktop\lexy sofware\accounting_system_2\apps\reporting\export_utils.py
import csv
import io
import xlsxwriter
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime
import re

def analyze_content_requirements(headers, data):
    """Enhanced analysis with better column compression detection and currency formatting"""
    analysis = {}
    
    # Import currency utilities
    from apps.core.utils import safe_decimal, format_currency
    
    for col_idx, header in enumerate(headers):
        header_str = str(header).lower()
        
        # Initialize analysis
        analysis[col_idx] = {
            'header': str(header),
            'header_length': len(str(header)),
            'max_content_length': 0,
            'avg_content_length': 0,
            'unique_values': set(),
            'has_long_content': False,
            'content_type': 'text',
            'needs_wrapping': False,
            'column_importance': 'medium',
            'space_efficiency': 1.0,
            'recommended_width': 0,
            'longest_word': 0,
            'avg_word_length': 0,
            'word_break_friendly': True,
            'is_description_column': False,
            'is_account_column': False,
            'is_compressed': False,
            'is_currency_column': False  # ✅ NEW: Flag for currency columns
        }
        
        # ✅ ENHANCED COLUMN TYPE DETECTION WITH CURRENCY SUPPORT
        if any(keyword in header_str for keyword in ['description', 'detail', 'note', 'comment', 'memo', 'narrative']):
            analysis[col_idx]['column_importance'] = 'critical'
            analysis[col_idx]['is_description_column'] = True
            analysis[col_idx]['space_efficiency'] = 2.0
        elif any(keyword in header_str for keyword in ['account', 'ledger']):
            analysis[col_idx]['column_importance'] = 'high'
            analysis[col_idx]['is_account_column'] = True
            analysis[col_idx]['space_efficiency'] = 1.5
        elif any(keyword in header_str for keyword in ['name', 'customer', 'vendor', 'party']):
            analysis[col_idx]['column_importance'] = 'high'
            analysis[col_idx]['space_efficiency'] = 1.3
        elif any(keyword in header_str for keyword in ['amount', 'total', 'balance', 'debit', 'credit', 'value', 'price', 'cost']):
            analysis[col_idx]['column_importance'] = 'high'
            analysis[col_idx]['space_efficiency'] = 0.8
            analysis[col_idx]['content_type'] = 'currency'
            analysis[col_idx]['is_currency_column'] = True
        elif any(keyword in header_str for keyword in ['sku', 'code', 'id', 'reference']):
            analysis[col_idx]['column_importance'] = 'medium'
            analysis[col_idx]['space_efficiency'] = 0.7
        elif any(keyword in header_str for keyword in ['status', 'type', 'category']):
            analysis[col_idx]['column_importance'] = 'low'
            analysis[col_idx]['space_efficiency'] = 0.6
        elif any(keyword in header_str for keyword in ['date', 'time']):
            analysis[col_idx]['column_importance'] = 'medium'
            analysis[col_idx]['space_efficiency'] = 0.8
            analysis[col_idx]['content_type'] = 'date'
        
        # Analyze actual data content
        content_lengths = []
        word_lengths = []
        
        for row in data:
            if col_idx < len(row) and row[col_idx] is not None:
                cell_content = str(row[col_idx])
                
                # ✅ FORMAT CURRENCY VALUES PROPERLY
                if analysis[col_idx]['is_currency_column']:
                    try:
                        # Convert to safe decimal and format
                        decimal_value = safe_decimal(cell_content)
                        formatted_content = format_currency(decimal_value, include_symbol=False)
                        cell_content = formatted_content
                    except:
                        pass  # Keep original if conversion fails
                
                analysis[col_idx]['unique_values'].add(cell_content)
                content_length = len(cell_content)
                content_lengths.append(content_length)
                
                # Check for compressed content (very long strings without spaces)
                if len(cell_content) > 30 and ' ' not in cell_content:
                    analysis[col_idx]['is_compressed'] = True
                
                # Word analysis
                words = cell_content.split()
                if words:
                    word_lengths.extend([len(word) for word in words])
                    analysis[col_idx]['longest_word'] = max(
                        analysis[col_idx]['longest_word'], 
                        max(len(word) for word in words)
                    )
        
        if content_lengths:
            analysis[col_idx]['max_content_length'] = max(content_lengths)
            analysis[col_idx]['avg_content_length'] = sum(content_lengths) / len(content_lengths)
            
            if word_lengths:
                analysis[col_idx]['avg_word_length'] = sum(word_lengths) / len(word_lengths)
            
            # ✅ ADJUST FOR COMPRESSED CONTENT
            if analysis[col_idx]['is_compressed']:
                analysis[col_idx]['needs_wrapping'] = True
                analysis[col_idx]['space_efficiency'] *= 1.2
            
            # Enhanced wrapping detection
            analysis[col_idx]['has_long_content'] = analysis[col_idx]['max_content_length'] > 25
            analysis[col_idx]['needs_wrapping'] = (
                analysis[col_idx]['is_description_column'] or
                analysis[col_idx]['is_account_column'] or
                analysis[col_idx]['is_compressed'] or
                (analysis[col_idx]['column_importance'] in ['critical', 'high'] and
                 analysis[col_idx]['max_content_length'] > 20)
            )
    
    return analysis

def calculate_smart_column_widths(headers, data, available_width, min_width=0.5*inch, max_width=4*inch):
    """
    🎯 ENHANCED: Priority-based width calculation with SAFETY CHECKS for content overflow
    """
    analysis = analyze_content_requirements(headers, data)
    num_cols = len(headers)
    
    # 🎯 STEP 1: Calculate ideal widths with SAFETY MINIMUMS
    ideal_widths = []
    total_importance_score = 0
    
    for col_idx in range(num_cols):
        col_analysis = analysis[col_idx]
        
        # Base width from content
        header_need = col_analysis['header_length'] * 0.08
        content_need = col_analysis['max_content_length'] * 0.08
        base_content_width = max(header_need, content_need)
        
        # 🛡️ SAFETY CHECK: Ensure minimum width for actual content
        absolute_minimum = max(
            col_analysis['max_content_length'] * 0.06,  # At least 60% of longest content
            len(str(headers[col_idx])) * 0.08,          # At least header width
            min_width * 0.7                             # At least 70% of min_width
        )
        
        # 🎯 IMPORTANCE MULTIPLIERS (but respect safety minimum)
        importance_multipliers = {
            'critical': 2.0,    # Description columns get 2x space
            'high': 1.3,        # Names, amounts get 1.3x space  
            'medium': 1.0,      # Dates, references get normal space
            'low': 0.6          # Status, type get 0.6x space
        }
        
        importance_multiplier = importance_multipliers.get(
            col_analysis['column_importance'], 1.0
        )
        
        # 🎯 APPLY SPACE EFFICIENCY
        space_efficiency = col_analysis['space_efficiency']
        
        # Calculate ideal width
        calculated_width = base_content_width * importance_multiplier * space_efficiency
        
        # 🛡️ ENFORCE SAFETY MINIMUM - content must fit!
        ideal_width = max(calculated_width, absolute_minimum)
        
        # Apply maximum bounds
        ideal_width = min(ideal_width, max_width)
        
        ideal_widths.append(ideal_width)
        
        # Calculate importance score for distribution
        importance_score = importance_multiplier * (2.0 - space_efficiency + 1.0)
        total_importance_score += importance_score
        analysis[col_idx]['importance_score'] = importance_score
        analysis[col_idx]['ideal_width'] = ideal_width
        analysis[col_idx]['absolute_minimum'] = absolute_minimum  # Store for later use
    
    total_ideal_width = sum(ideal_widths)
    
    # 🎯 STEP 2: Distribute available width with SAFETY ENFORCEMENT
    if total_ideal_width <= available_width:
        # We have extra space - distribute by importance
        extra_space = available_width - total_ideal_width
        final_widths = []
        
        for col_idx in range(num_cols):
            importance_ratio = analysis[col_idx]['importance_score'] / total_importance_score
            extra_for_col = extra_space * importance_ratio
            final_width = ideal_widths[col_idx] + extra_for_col
            final_widths.append(min(final_width, max_width))
    
    else:
        # Need to compress - but NEVER below safety minimums
        final_widths = []
        
        for col_idx in range(num_cols):
            col_analysis = analysis[col_idx]
            ideal_width = ideal_widths[col_idx]
            safety_minimum = col_analysis['absolute_minimum']
            
            # Calculate compression factor based on importance
            if col_analysis['column_importance'] == 'critical':
                compression_factor = 0.95  # Minimal compression for critical columns
            elif col_analysis['column_importance'] == 'high':
                compression_factor = 0.85  # Light compression for high importance
            elif col_analysis['column_importance'] == 'medium':
                compression_factor = 0.75  # Moderate compression
            else:  # low importance
                compression_factor = 0.6   # Heavy compression for low importance
            
            compressed_width = ideal_width * compression_factor
            
            # 🛡️ CRITICAL SAFETY CHECK: Never go below what's needed for content
            final_width = max(compressed_width, safety_minimum)
            final_widths.append(final_width)
        
        # Final adjustment if still over budget
        current_total = sum(final_widths)
        if current_total > available_width:
            # 🛡️ SMART FINAL ADJUSTMENT: Only compress columns that can afford it
            excess = current_total - available_width
            
            # Find columns that can be compressed further (above their safety minimum)
            compressible_columns = []
            for col_idx in range(num_cols):
                safety_minimum = analysis[col_idx]['absolute_minimum']
                current_width = final_widths[col_idx]
                if current_width > safety_minimum * 1.1:  # 10% buffer above minimum
                    compressible_columns.append(col_idx)
            
            if compressible_columns:
                # Distribute the excess reduction among compressible columns
                reduction_per_col = excess / len(compressible_columns)
                for col_idx in compressible_columns:
                    safety_minimum = analysis[col_idx]['absolute_minimum']
                    new_width = final_widths[col_idx] - reduction_per_col
                    final_widths[col_idx] = max(new_width, safety_minimum * 1.05)  # Small safety buffer
            else:
                # Last resort: proportional scaling but respect absolute minimums
                total_minimums = sum(analysis[col_idx]['absolute_minimum'] for col_idx in range(num_cols))
                if available_width >= total_minimums:
                    # We can fit minimums, distribute remaining space proportionally
                    remaining_space = available_width - total_minimums
                    for col_idx in range(num_cols):
                        safety_minimum = analysis[col_idx]['absolute_minimum']
                        proportion = ideal_widths[col_idx] / total_ideal_width
                        final_widths[col_idx] = safety_minimum + (remaining_space * proportion)
                else:
                    # Extreme case: use absolute minimums
                    for col_idx in range(num_cols):
                        final_widths[col_idx] = analysis[col_idx]['absolute_minimum']
    
    return final_widths, analysis

def calculate_dynamic_column_widths(headers, data, available_width, min_width=0.8*inch, max_width=3*inch):
    """
    🎯 LEGACY FUNCTION: Calculate column widths based on actual content length
    (Keeping for backward compatibility)
    
    Args:
        headers: List of column headers
        data: List of data rows
        available_width: Total available width for the table
        min_width: Minimum width for any column
        max_width: Maximum width for any column
    
    Returns:
        List of column widths
    """
    # Calculate the maximum content length for each column
    col_max_lengths = []
    
    for col_idx in range(len(headers)):
        # Start with header length
        max_length = len(str(headers[col_idx]))
        
        # Check all data rows for this column
        for row in data:
            if col_idx < len(row):
                cell_content = str(row[col_idx]) if row[col_idx] is not None else ""
                # Remove any formatting characters and measure actual text
                clean_content = re.sub(r'[^\w\s.-]', '', cell_content)
                max_length = max(max_length, len(clean_content))
        
        col_max_lengths.append(max_length)
    
    # Convert character lengths to approximate widths (1 char ≈ 0.1 inch for most fonts)
    char_to_inch = 0.08  # Adjusted for better fit
    estimated_widths = [max(min_width, min(length * char_to_inch, max_width)) for length in col_max_lengths]
    
    # Calculate total estimated width
    total_estimated = sum(estimated_widths)
    
    # If total exceeds available width, scale down proportionally
    if total_estimated > available_width:
        scale_factor = available_width / total_estimated
        scaled_widths = [width * scale_factor for width in estimated_widths]
        
        # Ensure no column is smaller than min_width
        final_widths = [max(min_width, width) for width in scaled_widths]
        
        # Recalculate if we still exceed available width after applying min_width
        total_final = sum(final_widths)
        if total_final > available_width:
            # Distribute available width proportionally, respecting min_width
            remaining_width = available_width - (len(headers) * min_width)
            if remaining_width > 0:
                extra_per_col = remaining_width / len(headers)
                final_widths = [min_width + extra_per_col for _ in headers]
            else:
                # Last resort: equal distribution
                final_widths = [available_width / len(headers) for _ in headers]
    else:
        # We have extra space, distribute it proportionally
        extra_space = available_width - total_estimated
        extra_per_col = extra_space / len(headers)
        final_widths = [width + extra_per_col for width in estimated_widths]
    
    return final_widths

def export_to_csv(data, filename, headers):
    """Export data to CSV format"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(headers)
    
    for row in data:
        writer.writerow(row)
    
    return response

def export_to_excel(data, filename, headers, sheet_name="Report", company_name=""):
    """Export data to Excel format with DYNAMIC description column handling and proper number formatting"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet(sheet_name)
    
    # 🎯 SET EXCEL TO LANDSCAPE ORIENTATION
    worksheet.set_landscape()
    worksheet.set_paper(9)  # A4 paper
    worksheet.fit_to_pages(1, 0)  # Fit to 1 page wide, unlimited pages tall
    
    # 🧠 ANALYZE CONTENT FOR SMART FORMATTING
    analysis = analyze_content_requirements(headers, data)
    
    # Define formats with enhanced number formatting
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 16,
        'align': 'center'
    })
    
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D3D3D3',
        'border': 1,
        'align': 'center',
        'text_wrap': True,
        'valign': 'vcenter'
    })
    
    # 🎯 ENHANCED NUMBER FORMATS
    currency_format = workbook.add_format({
        'num_format': '#,##0.00',  # Always show 2 decimal places
        'border': 1,
        'align': 'right',
        'valign': 'top'
    })
    
    integer_format = workbook.add_format({
        'num_format': '#,##0',  # No decimal places for integers
        'border': 1,
        'align': 'right',
        'valign': 'top'
    })
    
    date_format = workbook.add_format({
        'num_format': 'yyyy-mm-dd',
        'border': 1,
        'align': 'center',
        'valign': 'top'
    })
    
    text_format = workbook.add_format({
        'border': 1,
        'text_wrap': True,
        'valign': 'top',
        'align': 'left'
    })
    
    # 🎯 SPECIAL FORMAT FOR DESCRIPTION COLUMNS
    description_format = workbook.add_format({
        'border': 1,
        'text_wrap': True,
        'valign': 'top',
        'align': 'left',
        'font_size': 9,
        'shrink': True
    })
    
    # Add company name and report title
    if company_name:
        worksheet.merge_range('A1:' + chr(65 + len(headers) - 1) + '1', company_name, title_format)
        worksheet.merge_range('A2:' + chr(65 + len(headers) - 1) + '2', sheet_name, title_format)
        start_row = 4
    else:
        start_row = 0
    
    # 🎯 DYNAMIC COLUMN WIDTH CALCULATION
    optimal_widths = []
    
    for col_num, header in enumerate(headers):
        if col_num < len(analysis):
            col_analysis = analysis[col_num]
            
            # 🎯 SPECIAL HANDLING FOR DESCRIPTION COLUMNS
            if col_analysis['is_description_column']:
                # Description columns get dynamic width based on content
                max_desc_length = 0
                for row in data:
                    if col_num < len(row) and row[col_num] is not None:
                        desc_length = len(str(row[col_num]))
                        max_desc_length = max(max_desc_length, desc_length)
                
                # Dynamic width: minimum 30, maximum 60, based on content
                base_width = min(max(max_desc_length * 0.8, 30), 60)
                final_width = base_width
                
            elif col_analysis['content_type'] in ['currency', 'number']:
                # Numbers: precise width based on actual content
                max_num_length = 0
                for row in data:
                    if col_num < len(row) and row[col_num] is not None:
                        num_str = str(row[col_num])
                        max_num_length = max(max_num_length, len(num_str))
                
                final_width = max(max_num_length + 2, len(str(header)) + 2, 12)
                final_width = min(final_width, 18)  # Cap at reasonable width
                
            elif col_analysis['content_type'] == 'date':
                final_width = 12  # Standard date width
                
            else:
                # Other text columns: balanced approach
                actual_max_length = len(str(header))
                longest_word_in_data = col_analysis.get('longest_word', 0)
                
                for row in data:
                    if col_num < len(row) and row[col_num] is not None:
                        cell_str = str(row[col_num])
                        actual_max_length = max(actual_max_length, len(cell_str))
                
                if col_analysis['column_importance'] == 'high':
                    base_width = max(longest_word_in_data * 1.2, 15)
                    final_width = min(base_width, 25)
                else:
                    final_width = max(len(str(header)) + 2, longest_word_in_data + 2)
                    final_width = min(final_width, 18)
            
            optimal_widths.append(final_width)
        else:
            optimal_widths.append(12)  # Fallback width
    
    # 🎯 SET COLUMN WIDTHS
    for col_num, width in enumerate(optimal_widths):
        worksheet.set_column(col_num, col_num, width)
    
    # 🎯 ADD HEADERS
    header_row_height = 25
    for col, header in enumerate(headers):
        worksheet.write(start_row, col, header, header_format)
        
        if len(str(header)) > optimal_widths[col] * 1.2:
            estimated_lines = max(1, len(str(header)) // int(optimal_widths[col] * 1.2))
            header_row_height = max(header_row_height, 20 * estimated_lines)
    
    worksheet.set_row(start_row, header_row_height)
    
    # 🎯 ADD DATA WITH PROPER FORMATTING
    for row_num, row_data in enumerate(data, start_row + 1):
        row_height = 25
        
        for col_num, cell_data in enumerate(row_data):
            if col_num < len(analysis):
                col_analysis = analysis[col_num]
                
                # 🎯 CHOOSE FORMAT BASED ON CONTENT TYPE
                if col_analysis['content_type'] == 'currency':
                    # Convert to float and format as currency
                    try:
                        if cell_data is not None and str(cell_data).strip():
                            numeric_value = float(str(cell_data).replace(',', ''))
                            worksheet.write(row_num, col_num, numeric_value, currency_format)
                        else:
                            worksheet.write(row_num, col_num, 0.00, currency_format)
                    except (ValueError, TypeError):
                        worksheet.write(row_num, col_num, cell_data, text_format)
                        
                elif col_analysis['content_type'] == 'number':
                    # Convert to number and format appropriately
                    try:
                        if cell_data is not None and str(cell_data).strip():
                            numeric_value = float(str(cell_data).replace(',', ''))
                            if numeric_value == int(numeric_value):
                                worksheet.write(row_num, col_num, int(numeric_value), integer_format)
                            else:
                                worksheet.write(row_num, col_num, numeric_value, currency_format)
                        else:
                            worksheet.write(row_num, col_num, 0, integer_format)
                    except (ValueError, TypeError):
                        worksheet.write(row_num, col_num, cell_data, text_format)
                        
                elif col_analysis['content_type'] == 'date':
                    worksheet.write(row_num, col_num, cell_data, date_format)
                    
                elif col_analysis['is_description_column']:
                    # Special formatting for description columns
                    cell_str = str(cell_data) if cell_data else ""
                    col_width = optimal_widths[col_num]
                    
                    if len(cell_str) > col_width * 1.3:
                        estimated_chars_per_line = max(int(col_width * 1.2), 10)
                        estimated_lines = max(1, len(cell_str) // estimated_chars_per_line + 1)
                        row_height = max(row_height, 20 * min(estimated_lines, 8))
                    
                    worksheet.write(row_num, col_num, cell_data, description_format)
                    
                else:
                    # Regular text formatting
                    worksheet.write(row_num, col_num, cell_data, text_format)
            else:
                worksheet.write(row_num, col_num, cell_data, text_format)
        
        # Set row height with limits
        if row_height > 25:
            worksheet.set_row(row_num, min(row_height, 160))  # Increased cap for descriptions
    
    workbook.close()
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    
    return response

def export_to_pdf(data, filename, headers, title, company_name, page_size=None):
    """Export data to PDF format with DYNAMIC description handling and proper number formatting"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
    
    if page_size is None:
        page_size = landscape(A4)
    
    doc = SimpleDocTemplate(
        response, 
        pagesize=page_size, 
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Company name and title
    title_style = styles['Title']
    title_style.fontSize = 18
    
    elements.append(Paragraph(f"{company_name}", title_style))
    elements.append(Paragraph(f"{title}", styles['Heading2']))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # Calculate available width
    available_width = page_size[0] - 1*inch
    
    # 🧠 GET ANALYSIS FOR SMART FORMATTING
    try:
        analysis = analyze_content_requirements(headers, data)
    except Exception:
        analysis = {}
        for i in range(len(headers)):
            analysis[i] = {
                'content_type': 'text',
                'column_importance': 'medium',
                'is_description_column': False,
                'longest_word': 10
            }
    
    # 🎯 DYNAMIC COLUMN WIDTH CALCULATION
    num_cols = len(headers)
    col_widths = []
    
    # Calculate widths based on content analysis
    total_weight = 0
    col_weights = []
    
    for col_idx in range(num_cols):
        if col_idx < len(analysis):
            col_analysis = analysis[col_idx]
            
            # 🎯 ASSIGN WEIGHTS BASED ON COLUMN TYPE
            if col_analysis.get('is_description_column'):
                weight = 3.5  # Description columns get most space
            elif col_analysis.get('column_importance') == 'critical':
                weight = 3.0
            elif col_analysis.get('column_importance') == 'high':
                if col_analysis.get('content_type') in ['currency', 'number']:
                    weight = 1.2  # Numbers need less space
                else:
                    weight = 2.0  # Names/vendors need good space
            elif col_analysis.get('column_importance') == 'medium':
                weight = 1.0
            else:  # low importance
                weight = 0.7
            
            col_weights.append(weight)
            total_weight += weight
        else:
            col_weights.append(1.0)
            total_weight += 1.0
    
    # Distribute available width based on weights
    for col_idx in range(num_cols):
        weight_ratio = col_weights[col_idx] / total_weight
        col_width = available_width * weight_ratio
        
        # Apply minimum and maximum constraints
        min_width = 0.6 * inch
        max_width = 4.0 * inch if col_idx < len(analysis) and analysis[col_idx].get('is_description_column') else 2.5 * inch
        
        col_width = max(min_width, min(col_width, max_width))
        col_widths.append(col_width)
    
    # 🎯 ENHANCED PARAGRAPH STYLES
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        wordWrap='CJK',
        alignment=1,
        fontName='Helvetica-Bold',
        spaceBefore=2,
        spaceAfter=2
    )
    
    # 🎯 SPECIAL STYLE FOR DESCRIPTION COLUMNS
    description_style = ParagraphStyle(
        'DescriptionStyle',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        wordWrap='CJK',
        alignment=0,
        spaceBefore=0,
        spaceAfter=0,
        leftIndent=2,
        rightIndent=2
    )
    
    text_style = ParagraphStyle(
        'TextStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        wordWrap='CJK',
        alignment=0,
        spaceBefore=1,
        spaceAfter=1
    )
    
    number_style = ParagraphStyle(
        'NumberStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        alignment=2,
    )
    
    # 🎯 PROCESS DATA WITH ENHANCED FORMATTING
    processed_data = []
    
    # Process headers
    processed_headers = []
    for col_idx, header in enumerate(headers):
        header_str = str(header)
        if len(header_str) > 15:
            processed_headers.append(Paragraph(header_str, header_style))
        else:
            processed_headers.append(header_str)
    processed_data.append(processed_headers)
    
    # Process data rows
    for row_idx, row in enumerate(data):
        processed_row = []
        
        for col_idx, cell in enumerate(row):
            cell_str = str(cell) if cell is not None else ""
            
            try:
                if col_idx < len(analysis):
                    col_analysis = analysis[col_idx]
                    
                    # 🎯 SPECIAL HANDLING FOR DIFFERENT CONTENT TYPES
                    if col_analysis.get('content_type') in ['currency', 'number']:
                        # Format numbers properly
                        try:
                            if cell is not None and str(cell).strip():
                                numeric_value = float(str(cell).replace(',', ''))
                                if col_analysis.get('content_type') == 'currency':
                                    formatted_number = f"{numeric_value:,.2f}"
                                else:
                                    formatted_number = f"{numeric_value:,.0f}" if numeric_value == int(numeric_value) else f"{numeric_value:,.2f}"
                                processed_row.append(formatted_number)
                            else:
                                processed_row.append("0.00" if col_analysis.get('content_type') == 'currency' else "0")
                        except (ValueError, TypeError):
                            processed_row.append(cell_str)
                            
                    elif col_analysis.get('is_description_column'):
                        # Special handling for description columns
                        if len(cell_str) > 100:  # Long descriptions
                            if len(cell_str) > 300:
                                cell_str = cell_str[:297] + "..."
                            processed_row.append(Paragraph(cell_str, description_style))
                        else:
                            processed_row.append(cell_str)
                            
                    else:
                        # Regular text handling
                        col_width_chars = int(col_widths[col_idx] / 0.08)
                        
                        if len(cell_str) > col_width_chars:
                            if len(cell_str) > 200:
                                cell_str = cell_str[:197] + "..."
                            processed_row.append(Paragraph(cell_str, text_style))
                        else:
                            processed_row.append(cell_str)
                else:
                    # Fallback
                    if len(cell_str) > 25:
                        processed_row.append(Paragraph(cell_str, text_style))
                    else:
                        processed_row.append(cell_str)
                        
            except Exception:
                processed_row.append(str(cell)[:50] if cell else "")
        
        processed_data.append(processed_row)
    
    # 🎯 CREATE TABLE WITH DYNAMIC WIDTHS
    try:
        table = Table(
            processed_data, 
            colWidths=col_widths, 
            repeatRows=1,
            splitByRow=True,
            spaceBefore=10,
            spaceAfter=10
        )
    except Exception:
        table = Table(processed_data, repeatRows=1)
    
    # 🎯 ENHANCED TABLE STYLING
    table_style = [
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        
        # Data styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]
    
    # Apply content-type specific alignments
    try:
        if analysis:
            for col_idx in range(len(headers)):
                if col_idx < len(analysis):
                    col_analysis = analysis[col_idx]
                    if col_analysis.get('content_type') in ['currency', 'number']:
                        table_style.append(('ALIGN', (col_idx, 1), (col_idx, -1), 'RIGHT'))
                    elif col_analysis.get('content_type') == 'date':
                        table_style.append(('ALIGN', (col_idx, 1), (col_idx, -1), 'CENTER'))
    except Exception:
        pass
    
    table.setStyle(TableStyle(table_style))
    elements.append(table)
    
    # Page footer
    def add_page_number(canvas, doc):
        try:
            page_num = canvas.getPageNumber()
            text = f"Page {page_num}"
            canvas.drawRightString(page_size[0] - 0.5*inch, 0.5*inch, text)
            canvas.drawString(0.5*inch, 0.5*inch, f"{company_name} - {title}")
        except Exception:
            pass
    
    # Build document
    try:
        doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    except Exception:
        try:
            doc.build(elements)
        except Exception:
            doc = SimpleDocTemplate(response, pagesize=page_size)
            simple_elements = [
                Paragraph(f"{company_name} - {title}", styles['Title']),
                Paragraph("Export completed with formatting limitations.", styles['Normal'])
            ]
            doc.build(simple_elements)
    
    return response

def export_hierarchical_to_excel(data, filename, title, company_name):
    """Export hierarchical data with DYNAMIC column widths"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet(title)
    
    # Set to landscape orientation
    worksheet.set_landscape()
    worksheet.set_paper(9)
    worksheet.fit_to_pages(1, 0)
    
    # Define formats with text wrapping
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 16,
        'align': 'center'
    })
    
    account_header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'border': 1,
        'text_wrap': True
    })
    
    transaction_format = workbook.add_format({
        'border': 1,
        'font_size': 9,
        'text_wrap': True
    })
    
    currency_format = workbook.add_format({
        'num_format': '#,##0.00',
        'border': 1,
        'font_size': 9
    })
    
    # Add title
    worksheet.merge_range('A1:F1', f"{company_name} - {title}", title_format)
    
    row = 3
    max_desc_length = 0  # Track maximum description length
    
    # First pass: find maximum content lengths
    for account_data in data:
        for transaction in account_data['transactions']:
            desc_length = len(str(transaction.get('description', '')))
            max_desc_length = max(max_desc_length, desc_length)
    
    # Set dynamic column widths
    worksheet.set_column('A:A', 12)  # Date
    worksheet.set_column('B:B', min(max(max_desc_length * 0.8, 30), 80))  # Description - dynamic
    worksheet.set_column('C:E', 15)  # Numbers
    
    for account_data in data:
        # Account header
        worksheet.merge_range(f'A{row}:F{row}', 
                            f"{account_data['account_code']} - {account_data['account_name']}", 
                            account_header_format)
        row += 1
        
        # Transaction headers
        headers = ['Date', 'Description', 'Debit', 'Credit', 'Balance']
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, account_header_format)
        row += 1
        
        # Transactions
        for transaction in account_data['transactions']:
            worksheet.write(row, 0, transaction['date'], transaction_format)
            worksheet.write(row, 1, transaction['description'], transaction_format)
            worksheet.write(row, 2, transaction['debit'], currency_format)
            worksheet.write(row, 3, transaction['credit'], currency_format)
            worksheet.write(row, 4, transaction['balance'], currency_format)
            row += 1
        
        # Final balance
        worksheet.write(row, 3, 'Final Balance:', account_header_format)
        worksheet.write(row, 4, account_data['final_balance'], currency_format)
        row += 3
    
    workbook.close()
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    
    return response

def export_and_email(data, filename, headers, title, company_name, format_type='excel', recipient_emails=None):
    """Export data and optionally email it as attachment"""
    import tempfile
    import os
    from apps.core.email_utils import send_email
    
    if not recipient_emails:
        return None
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as temp_file:
        temp_path = temp_file.name
    
    try:
        if format_type == 'csv':
            response = export_to_csv(data, filename, headers)
        elif format_type == 'excel':
            response = export_to_excel(data, filename, headers, title, company_name)
        elif format_type == 'pdf':
            response = export_to_pdf(data, filename, headers, title, company_name)
        else:
            return None
        
        # Write response content to temp file
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        # Send email with attachment
        success = send_email(
            subject=f"{title} Report - {company_name}",
            template_name='emails/report_delivery.html',
            context={
                'company': {'name': company_name},
                'report_type': title,
                'generated_date': datetime.now(),
            },
            to_emails=recipient_emails,
            attachment_path=temp_path
        )
        
        return success
        
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def export_to_pdf_custom(data, filename, headers, title, company_name, orientation='landscape', paper_size='A4'):
    """Export to PDF with custom orientation and paper size options"""
    from reportlab.lib.pagesizes import A4, letter, legal
    
    # Select paper size
    if paper_size.upper() == 'A4':
        base_size = A4
    elif paper_size.upper() == 'LETTER':
        base_size = letter
    elif paper_size.upper() == 'LEGAL':
        base_size = legal
    else:
        base_size = A4
    
    # Apply orientation
    if orientation.lower() == 'landscape':
        page_size = landscape(base_size)
    else:
        page_size = base_size
    
    return export_to_pdf(data, filename, headers, title, company_name, page_size)
