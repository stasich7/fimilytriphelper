UPDATE trips
SET title = 'Поездка в Грузию | Trip to Georgia, 2026',
    updated_at = now()
WHERE singleton_key = 'active';
