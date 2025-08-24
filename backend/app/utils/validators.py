def _ensure_string(value, field_name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value.strip()


def _ensure_string_array(values, field_name):
    if not isinstance(values, list):
        raise ValueError(f"{field_name} must be a list")
    if len(values) > 20:
        raise ValueError(f"{field_name} can have at most 20 items")
    cleaned = []
    for item in values:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} items must be strings")
        s = item.strip()
        if not s:
            continue
        if len(s) > 60:
            raise ValueError(f"{field_name} items must be <= 60 characters")
        cleaned.append(s)
    return cleaned


def validate_account_type(account_type):
    return account_type in {"learner", "educator", "professional", "organization"}


def validate_profile_payload(account_type, payload):
    if account_type == 'learner':
        school = _ensure_string(payload.get('school'), 'school')
        class_name = _ensure_string(payload.get('class_name'), 'class_name')
        favorite_subjects = _ensure_string_array(payload.get('favorite_subjects', []), 'favorite_subjects')
        hobbies = _ensure_string_array(payload.get('hobbies', []), 'hobbies')
        interests = _ensure_string_array(payload.get('interests', []), 'interests')
        return {
            'school': school,
            'class_name': class_name,
            'favorite_subjects': favorite_subjects,
            'hobbies': hobbies,
            'interests': interests
        }
    elif account_type == 'educator':
        school = _ensure_string(payload.get('school'), 'school')
        subjects = _ensure_string_array(payload.get('subjects', []), 'subjects')
        classes_taught = _ensure_string_array(payload.get('classes_taught', []), 'classes_taught')
        students_count = payload.get('students_count')
        years_experience = payload.get('years_experience')
        if not isinstance(students_count, int) or students_count < 0:
            raise ValueError('students_count must be a non-negative integer')
        if not isinstance(years_experience, int) or years_experience < 0:
            raise ValueError('years_experience must be a non-negative integer')
        hobbies = _ensure_string_array(payload.get('hobbies', []), 'hobbies')
        return {
            'school': school,
            'subjects': subjects,
            'classes_taught': classes_taught,
            'students_count': students_count,
            'years_experience': years_experience,
            'hobbies': hobbies
        }
    elif account_type == 'professional':
        sector = _ensure_string(payload.get('sector'), 'sector')
        job_title = _ensure_string(payload.get('job_title'), 'job_title')
        designation = _ensure_string(payload.get('designation'), 'designation')
        years_experience = payload.get('years_experience')
        if not isinstance(years_experience, int) or years_experience < 0:
            raise ValueError('years_experience must be a non-negative integer')
        skills = _ensure_string_array(payload.get('skills', []), 'skills')
        interests = _ensure_string_array(payload.get('interests', []), 'interests')
        hobbies = _ensure_string_array(payload.get('hobbies', []), 'hobbies')
        return {
            'sector': sector,
            'job_title': job_title,
            'designation': designation,
            'years_experience': years_experience,
            'skills': skills,
            'interests': interests,
            'hobbies': hobbies
        }
    elif account_type == 'organization':
        org_name = _ensure_string(payload.get('org_name'), 'org_name')
        contact_email = _ensure_string(payload.get('contact_email'), 'contact_email')
        website = payload.get('website')
        if website is not None and not isinstance(website, str):
            raise ValueError('website must be a string')
        return {
            'org_name': org_name,
            'contact_email': contact_email,
            'website': website.strip() if isinstance(website, str) else None
        }
    else:
        raise ValueError('Unsupported account type')
