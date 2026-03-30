from datetime import datetime

def parse_reg_no(reg_no):
    """
    Parses a registration number to derive academic details.
    Expected format: [y/l][batch][branch][roll] e.g., y23cs01
    """
    reg_no = reg_no.lower().strip()
    if not reg_no or len(reg_no) < 4:
        raise ValueError(f"Invalid registration number format: '{reg_no}'")
    
    # 1. Entry Type
    entry_char = reg_no[0]
    if entry_char == 'y':
        entry_type = 'Regular'
    elif entry_char == 'l':
        entry_type = 'Lateral'
    else:
        raise ValueError("Registration number must start with 'y' (Regular) or 'l' (Lateral).")
    
    # 2. Extract Batch Year (digits following the first character)
    batch_str = ""
    for char in reg_no[1:]:
        if char.isdigit():
            batch_str += char
        else:
            break
            
    if not batch_str:
        raise ValueError("Batch year not found in registration number.")
    
    batch = int("20" + batch_str)
    
    # 3. Academic Year Calculation
    # June to Dec -> current year is the start of academic year
    # Jan to May -> previous year is the start of academic year
    now = datetime.now()
    if now.month >= 6:
        academic_year = now.year
    else:
        academic_year = now.year - 1
        
    # 4. Year Calculation
    if entry_type == 'Regular':
        # y23 in 2025-26 academic year: 2025 - 2023 + 1 = 3rd Year
        year = academic_year - batch + 1
    else:
        # l23 (Lateral) starts at 2nd year. 
        # l23 in 2025-26 academic year: 2025 - 2023 + 2 = 4th Year
        year = academic_year - batch + 2
        
    # Clamp year between 1 and 4
    year = max(1, min(4, year))
    
    # 5. Department Mapping
    # Extract branch code (characters following the batch digits)
    branch_code = ""
    for char in reg_no[1 + len(batch_str):]:
        if not char.isdigit():
            branch_code += char
        else:
            break
            
    mapping = {
        'cd': 'CSE-DS',
        'cs': 'CSE',
        'it': 'IT',
        'co': 'CSE-IOT',
        'cb': 'CSE-BS',
        'cm': 'CSE-AIML',
    }
    
    department = mapping.get(branch_code.lower())
    if not department:
        # Try to find a partial match or default to CSE if unknown but follows format
        department = "Other"
        
    # Map department to the existing BRANCH_CHOICES in models if possible
    # BRANCH_CHOICES = [('CSE', 'CSE'), ('CSD', 'CSD'), ('CSM', 'CSM'), ('CSO', 'CSO'), ('CSBS', 'CSBS'), ('IT', 'IT')]
    branch_map = {
        'CSE': 'CSE',
        'CSE-DS': 'CSD',
        'CSE-AIML': 'CSM',
        'CSE-IOT': 'CSO',
        'CSE-BS': 'CSBS',
        'IT': 'IT'
    }
    branch = branch_map.get(department, 'CSE')
    
    return {
        'reg_no': reg_no.lower(),
        'entry_type': entry_type,
        'batch': batch,
        'year': year,
        'department': department,
        'branch': branch
    }
