-- ================================================================
-- AVILUS Drone BOM Database - Simplified Version
-- This creates the S1000D database structure
-- ================================================================

DROP TABLE IF EXISTS bom_components CASCADE;
DROP TABLE IF EXISTS bom_assemblies CASCADE;

-- ================================================================
-- ASSEMBLIES TABLE
-- These are groups of parts (not purchased directly)
-- ================================================================
CREATE TABLE bom_assemblies (
    id VARCHAR(50) PRIMARY KEY,
    part_number VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100),
    bom_level INTEGER DEFAULT 0,
    parent_assembly_id VARCHAR(50) REFERENCES bom_assemblies(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ================================================================
-- COMPONENTS TABLE  
-- These are actual parts to buy (with prices and suppliers)
-- ================================================================
CREATE TABLE bom_components (
    id VARCHAR(50) PRIMARY KEY,
    assembly_id VARCHAR(50) NOT NULL REFERENCES bom_assemblies(id) ON DELETE CASCADE,
    part_number VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(12, 2) NOT NULL DEFAULT 0,
    supplier VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ================================================================
-- AUTO-UPDATE TIMESTAMP TRIGGER
-- ================================================================
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_asm_timestamp
    BEFORE UPDATE ON bom_assemblies
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trg_comp_timestamp
    BEFORE UPDATE ON bom_components
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ================================================================
-- SAMPLE DATA
-- ================================================================

-- LEVEL 0: Complete Product
INSERT INTO bom_assemblies (id, part_number, description, category, bom_level, parent_assembly_id) VALUES
('DRONE-001', 'AVILUS-X1', 'AVILUS Surveyor X1 Drone', 'Complete System', 0, NULL);

INSERT INTO "public"."bom_assemblies" ("id", "part_number", "description", "category", "bom_level", "parent_assembly_id", "created_at", "updated_at") VALUES ('DRONE-004', 'GRILLE', 'Medical Evacuation Tactical Airlift', 'Complete System', '0', NULL, '2025-11-16 20:17:08.119455', '2025-11-16 20:17:08.119455'),('DRONE-002', 'Wespe', 'Tactical Airlift Close Air Support', 'Complete System', '0', NULL, '2025-11-16 20:17:08.119455', '2025-11-16 20:17:08.119455'),('DRONE-003', 'Bussard', 'Wide-Area Surveillance Target Designation', 'Complete System', '0', NULL, '2025-11-16 20:17:08.119455', '2025-11-16 20:17:08.119455');

-- LEVEL 1: Major Systems
INSERT INTO bom_assemblies (id, part_number, description, category, bom_level, parent_assembly_id) VALUES
('FRAME-001', 'FRAME-ASM', 'Airframe Assembly', 'Structure', 1, 'DRONE-001'),
('PROP-001', 'PROP-SYS', 'Propulsion System', 'Propulsion', 1, 'DRONE-001'),
('AVION-001', 'AVION-SYS', 'Avionics System', 'Electronics', 1, 'DRONE-001'),
('POWER-001', 'POWER-SYS', 'Power System', 'Electrical', 1, 'DRONE-001');

-- LEVEL 2: Sub-Assemblies (only for Propulsion)
INSERT INTO bom_assemblies (id, part_number, description, category, bom_level, parent_assembly_id) VALUES
('MOTOR-FL', 'MOTOR-ASM-FL', 'Front-Left Motor Assembly', 'Propulsion', 2, 'PROP-001'),
('MOTOR-FR', 'MOTOR-ASM-FR', 'Front-Right Motor Assembly', 'Propulsion', 2, 'PROP-001'),
('MOTOR-RL', 'MOTOR-ASM-RL', 'Rear-Left Motor Assembly', 'Propulsion', 2, 'PROP-001'),
('MOTOR-RR', 'MOTOR-ASM-RR', 'Rear-Right Motor Assembly', 'Propulsion', 2, 'PROP-001');

-- ================================================================
-- COMPONENTS
-- ================================================================

-- Airframe Parts
INSERT INTO bom_components (id, assembly_id, part_number, description, quantity, unit_price, supplier) VALUES
('C-FRAME-01', 'FRAME-001', 'CF-BODY', 'Carbon Fiber Body', 1, 450.00, 'CarbonTech GmbH'),
('C-FRAME-02', 'FRAME-001', 'CF-ARM', 'Carbon Fiber Arm 450mm', 4, 85.00, 'CarbonTech GmbH'),
('C-FRAME-03', 'FRAME-001', 'LANDING-GEAR', 'Landing Gear Set', 1, 120.00, 'DronePartsEU'),
('C-FRAME-04', 'FRAME-001', 'CANOPY', 'Weather Resistant Canopy', 1, 95.00, 'AeroShield');

-- Motor Assembly Parts (same for each motor)
INSERT INTO bom_components (id, assembly_id, part_number, description, quantity, unit_price, supplier) VALUES
('C-MOTOR-FL-1', 'MOTOR-FL', 'MOTOR-4112', 'Brushless Motor 320KV', 1, 189.00, 'T-Motor'),
('C-MOTOR-FL-2', 'MOTOR-FL', 'ESC-40A', 'Speed Controller 40A', 1, 65.00, 'Hobbywing'),
('C-MOTOR-FL-3', 'MOTOR-FL', 'PROP-15', 'Carbon Propeller 15 inch', 1, 42.00, 'APC'),

('C-MOTOR-FR-1', 'MOTOR-FR', 'MOTOR-4112', 'Brushless Motor 320KV', 1, 189.00, 'T-Motor'),
('C-MOTOR-FR-2', 'MOTOR-FR', 'ESC-40A', 'Speed Controller 40A', 1, 65.00, 'Hobbywing'),
('C-MOTOR-FR-3', 'MOTOR-FR', 'PROP-15', 'Carbon Propeller 15 inch', 1, 42.00, 'APC'),

('C-MOTOR-RL-1', 'MOTOR-RL', 'MOTOR-4112', 'Brushless Motor 320KV', 1, 189.00, 'T-Motor'),
('C-MOTOR-RL-2', 'MOTOR-RL', 'ESC-40A', 'Speed Controller 40A', 1, 65.00, 'Hobbywing'),
('C-MOTOR-RL-3', 'MOTOR-RL', 'PROP-15', 'Carbon Propeller 15 inch', 1, 42.00, 'APC'),

('C-MOTOR-RR-1', 'MOTOR-RR', 'MOTOR-4112', 'Brushless Motor 320KV', 1, 189.00, 'T-Motor'),
('C-MOTOR-RR-2', 'MOTOR-RR', 'ESC-40A', 'Speed Controller 40A', 1, 65.00, 'Hobbywing'),
('C-MOTOR-RR-3', 'MOTOR-RR', 'PROP-15', 'Carbon Propeller 15 inch', 1, 42.00, 'APC');

-- Avionics Parts
INSERT INTO bom_components (id, assembly_id, part_number, description, quantity, unit_price, supplier) VALUES
('C-AVION-01', 'AVION-001', 'FC-CUBE', 'Flight Controller Cube Orange', 1, 520.00, 'CubePilot'),
('C-AVION-02', 'AVION-001', 'GPS-RTK', 'RTK GPS Module', 1, 890.00, 'Here3+'),
('C-AVION-03', 'AVION-001', 'RC-LINK', 'Long Range Radio 40km', 1, 450.00, 'TBS Crossfire'),
('C-AVION-04', 'AVION-001', 'TELEMETRY', 'Telemetry Radio 915MHz', 1, 175.00, 'Holybro');

-- Power System Parts
INSERT INTO bom_components (id, assembly_id, part_number, description, quantity, unit_price, supplier) VALUES
('C-POWER-01', 'POWER-001', 'BATTERY-6S', 'LiPo Battery 6S 16000mAh', 2, 385.00, 'Tattu'),
('C-POWER-02', 'POWER-001', 'BMS', 'Battery Management System', 1, 145.00, 'BatteryLogic'),
('C-POWER-03', 'POWER-001', 'PDB', 'Power Distribution Board', 1, 89.00, 'Matek');

-- ================================================================
-- ROW LEVEL SECURITY (Allow all operations)
-- ================================================================
ALTER TABLE bom_assemblies ENABLE ROW LEVEL SECURITY;
ALTER TABLE bom_components ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all" ON bom_assemblies FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON bom_components FOR ALL USING (true) WITH CHECK (true);

-- ================================================================
-- VERIFY DATA
-- ================================================================
SELECT 'Summary' as info,
    (SELECT COUNT(*) FROM bom_assemblies) as assemblies,
    (SELECT COUNT(*) FROM bom_components) as components,
    (SELECT ROUND(SUM(quantity * unit_price)::numeric, 2) FROM bom_components) as total_cost;

SELECT 'BOM Tree' as info;
SELECT 
    LPAD('', bom_level * 2, ' ') || part_number as tree,
    description,
    bom_level
FROM bom_assemblies
ORDER BY bom_level, part_number;