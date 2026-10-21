BEGIN;

-- Reference data PEMS: aman dijalankan berulang kali.
INSERT INTO estates (code, name, is_active)
VALUES
    ('MAGE', 'MAGE', TRUE),
    ('BMKE', 'BMKE', TRUE),
    ('BKCE', 'BKCE', TRUE),
    ('BBGE', 'BBGE', TRUE),
    ('BHPE', 'BHPE', TRUE),
    ('SPGE', 'SPGE', TRUE)
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    is_active = EXCLUDED.is_active;

INSERT INTO divisions (estate_id, code, division_number, is_active)
SELECT e.id, e.code || n.number, n.number, TRUE
FROM estates e
JOIN (
    VALUES
        ('MAGE', 6), ('BMKE', 4), ('BKCE', 4),
        ('BBGE', 3), ('BHPE', 4), ('SPGE', 3)
) AS limits(code, max_number) ON limits.code = e.code
CROSS JOIN LATERAL generate_series(1, limits.max_number) AS n(number)
ON CONFLICT (code) DO UPDATE
SET estate_id = EXCLUDED.estate_id,
    division_number = EXCLUDED.division_number,
    is_active = EXCLUDED.is_active;

COMMIT;
