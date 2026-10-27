-- ============================================================
-- Pigment Spectral Standards Database: SCHEMA v5 (MySQL 8)
-- Prepared by Maria Gabriela Rivas Carmona, University of Padova
-- ============================================================
-- Same design as pigment_spectral_standards_sqlite_schema.sql (SQLite): 6 tables
--   Material, Specimen, Measurement, Instrument, InstrumentConfiguration, Operator
--
-- Differences from the SQLite file, forced by MySQL:
--   * AUTO_INCREMENT and ENGINE=InnoDB instead of AUTOINCREMENT.
--   * Columns that must be UNIQUE are VARCHAR(255) (MySQL cannot index
--     an unlimited TEXT column without a length).
--   * Measurement.SpectrumData uses the native JSON type, which rejects
--     invalid JSON by itself.
--   * Measurement.ScanDate uses the DATE type, which accepts only valid
--     dates in the format YYYY-MM-DD.
--   * IsSynthetic is CHAR(1): Y = synthetic, N = natural, NULL = not stated.
--   * CHECK constraints need MySQL 8.0.16 or later.
--
-- A field is required (NOT NULL) only where the data dictionary marks it
-- NOT NULL. Every other field is optional.
--
-- No ON DELETE action is set, so the default (NO ACTION) applies: a row
-- cannot be deleted while another row points to it.
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;


-- ---------- Materials and specimens ----------

CREATE TABLE Material (
    MaterialID INT AUTO_INCREMENT PRIMARY KEY,
    MaterialName VARCHAR(255) NOT NULL UNIQUE,
    ChemicalFormula VARCHAR(255),      -- plain text, e.g. 'CaCO3'
    IsSynthetic CHAR(1),               -- Y = synthetic, N = natural, empty = not stated
    Description TEXT,
    ChemicalClass VARCHAR(100),        -- optional, e.g. 'Carbonate', 'Oxide'; several separated by a semicolon
    CHECK (IsSynthetic IN ('Y', 'N'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE Specimen (
    SpecimenID INT AUTO_INCREMENT PRIMARY KEY,
    SpecimenType VARCHAR(255),         -- free text, e.g. 'mineral fragment', 'ground mineral', 'powder pigment'
    PreparationNotes TEXT,
    MaterialID INT,                    -- the material of the specimen; known for standards
    SpecimenSource VARCHAR(255),       -- who supplied the piece, free text
    Tags TEXT,                         -- labels separated by a semicolon, e.g. 'needs-atr-recollection'
    ImageReference VARCHAR(1024),
    FOREIGN KEY (MaterialID) REFERENCES Material(MaterialID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ---------- People and instrumentation ----------

CREATE TABLE Operator (
    OperatorID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(255),
    Email VARCHAR(255),
    Institution VARCHAR(255)           -- free text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE Instrument (
    InstrumentID INT AUTO_INCREMENT PRIMARY KEY,
    InstrumentName VARCHAR(255),
    Model VARCHAR(255),
    Manufacturer VARCHAR(255),
    SerialNumber VARCHAR(255) UNIQUE,     -- from the maker's label; optional
    LabAssetID VARCHAR(255) UNIQUE        -- the lab's own inventory number; optional
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE InstrumentConfiguration (
    InstrumentConfigurationID INT AUTO_INCREMENT PRIMARY KEY,
    InstrumentID INT NOT NULL,            -- the instrument these settings belong to
    Resolution VARCHAR(255),
    NumberOfScans INT,
    BeamSplitterType VARCHAR(255),
    Detector VARCHAR(255) DEFAULT 'LN-MCT',
    AcquisitionMode VARCHAR(10) NOT NULL, -- ER-IR or ATR
    ApertureSize VARCHAR(255),
    Notes TEXT,
    FOREIGN KEY (InstrumentID) REFERENCES Instrument(InstrumentID),
    CHECK (AcquisitionMode IN ('ER-IR', 'ATR'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ---------- The measurement and its spectrum ----------

CREATE TABLE Measurement (
    MeasurementID INT AUTO_INCREMENT PRIMARY KEY,
    SpecimenID INT NOT NULL,
    InstrumentConfigurationID INT NOT NULL,   -- the configuration names the instrument and the mode
    IntensityMode VARCHAR(50) NOT NULL DEFAULT 'Absorbance',
    SpectrumData JSON NOT NULL,           -- array of [wavenumber, intensity] pairs
    OperatorID INT,
    ReferenceMeasurementID INT,           -- links an ER-IR scan to its ATR standard
    ScanDate DATE,                        -- date of the scan, YYYY-MM-DD
    SpecimenSpotDescription TEXT,         -- where on the specimen the spot is
    ImageReference VARCHAR(1024),
    FilePath VARCHAR(1024) NOT NULL,      -- the .dpt file (required)
    Checksum VARCHAR(128),                -- SHA-256 of the file
    UploadedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Notes TEXT,
    FOREIGN KEY (SpecimenID) REFERENCES Specimen(SpecimenID),
    FOREIGN KEY (InstrumentConfigurationID) REFERENCES InstrumentConfiguration(InstrumentConfigurationID),
    FOREIGN KEY (OperatorID) REFERENCES Operator(OperatorID),
    FOREIGN KEY (ReferenceMeasurementID) REFERENCES Measurement(MeasurementID),
    CHECK (IntensityMode = 'Absorbance')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ---------- Indexes on the columns most often joined ----------

CREATE INDEX idx_measurement_specimen  ON Measurement(SpecimenID);
CREATE INDEX idx_measurement_reference ON Measurement(ReferenceMeasurementID);
CREATE INDEX idx_specimen_material     ON Specimen(MaterialID);

SET FOREIGN_KEY_CHECKS = 1;
