# lathe-generated module — do not edit by hand


def parse_amount(s):
    import re
    try:
        if s is None:
            return 0.0
        if not isinstance(s, str):
            return 0.0
        s = s.strip()
        if not s:
            return 0.0
        # Check for negative sign
        negative = False
        if s.startswith('-'):
            negative = True
            s = s[1:]
        elif s.startswith('+'):
            s = s[1:]
        # Remove dollar sign and whitespace
        s = s.replace('$', '').replace(' ', '').replace(',', '')
        if not s:
            return 0.0
        # Validate that it's a valid number
        if not re.match(r'^\d+(\.\d+)?$', s):
            return 0.0
        result = float(s)
        if negative:
            result = -result
        return result
    except:
        return 0.0

def parse_entry(line):
    """Parse a CSV line into a dict. Never raises.
    
    Format: 'date,category,amount'
    Amount may include leading '$' and commas.
    Returns None for invalid/empty/None inputs.
    """
    try:
        if not line:
            return None
        
        line = str(line).strip()
        if not line:
            return None
        
        parts = line.split(',')
        if len(parts) < 3:
            return None
        
        date = parts[0].strip()
        category = parts[1].strip()
        amount_str = parts[2].strip()
        
        if not date or not category:
            return None
        
        # Parse amount with money rules:
        # - Remove leading '$'
        # - Remove commas
        # - Parse as float
        if amount_str.startswith('$'):
            amount_str = amount_str[1:]
        
        amount_str = amount_str.replace(',', '')
        
        try:
            amount = float(amount_str)
        except (ValueError, TypeError):
            return None
        
        return {
            'date': date,
            'category': category,
            'amount': amount
        }
    
    except Exception:
        return None

