# lathe-generated module — do not edit by hand


def parse_run_report(text):
    import re
    
    functions_passed = 0
    functions_total = 0
    integration_status = 'none'
    
    # Search for functions implemented: X / Y
    func_match = re.search(r'functions implemented:\s*(\d+)\s*/\s*(\d+)', text, re.IGNORECASE)
    if func_match:
        functions_passed = int(func_match.group(1))
        functions_total = int(func_match.group(2))
    
    # Search for integration: status
    int_match = re.search(r'integration:\s*(pass|fail|skipped)', text, re.IGNORECASE)
    if int_match:
        integration_status = int_match.group(1).lower()
        
    return {
        'functions_passed': functions_passed,
        'functions_total': functions_total,
        'integration_status': integration_status
    }

def is_green(report):
    import typing

    def is_green(report: dict) -> bool:
        total = report.get('functions_total', 0)
        passed = report.get('functions_passed', 0)
        status = report.get('integration_status', 'none')

        if total <= 0:
            return False
        
        if passed != total:
            return False
        
        if status == 'fail':
            return False
            
        return True

    return is_green(report)

