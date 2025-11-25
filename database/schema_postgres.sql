-- Schéma PostgreSQL pour Mibeko (Textes de loi du Congo)
-- Créé le 25/11/2025

-- 1. Table des publications (Journaux Officiels)
CREATE TABLE publications (
    id VARCHAR(50) PRIMARY KEY, -- ex: "congo-jo-2025-26"
    numero_parution VARCHAR(50),
    date_parution DATE,
    annee INTEGER,
    titre TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Table des textes légaux (Lois, Décrets, Arrêtés...)
CREATE TABLE textes (
    id VARCHAR(100) PRIMARY KEY, -- ex: "congo-jo-2025-26-loi-10-2025"
    publication_id VARCHAR(50) REFERENCES publications(id) ON DELETE CASCADE,
    type_texte VARCHAR(50), -- LOI, DECRET, ARRETE, etc.
    numero VARCHAR(50), -- ex: "10-2025"
    date_texte DATE,
    titre TEXT,
    contenu TEXT, -- Contenu complet nettoyé
    preambule TEXT,
    page_debut INTEGER,
    page_fin INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour la recherche textuelle
CREATE INDEX idx_textes_type ON textes(type_texte);
CREATE INDEX idx_textes_numero ON textes(numero);
CREATE INDEX idx_textes_date ON textes(date_texte);

-- 3. Structure Hiérarchique : Titres
CREATE TABLE titres (
    id SERIAL PRIMARY KEY,
    texte_id VARCHAR(100) REFERENCES textes(id) ON DELETE CASCADE,
    numero VARCHAR(50), -- ex: "I", "II"
    intitule TEXT, -- ex: "DISPOSITIONS GENERALES"
    contenu_libre TEXT,
    ordre INTEGER -- Pour maintenir l'ordre d'affichage
);

-- 4. Structure Hiérarchique : Chapitres
CREATE TABLE chapitres (
    id SERIAL PRIMARY KEY,
    texte_id VARCHAR(100) REFERENCES textes(id) ON DELETE CASCADE,
    titre_id INTEGER REFERENCES titres(id) ON DELETE CASCADE, -- Peut être NULL si hors titre
    numero VARCHAR(50), -- ex: "1", "premier"
    titre TEXT,
    contenu_libre TEXT,
    ordre INTEGER
);

-- 5. Structure Hiérarchique : Sections
CREATE TABLE sections (
    id SERIAL PRIMARY KEY,
    texte_id VARCHAR(100) REFERENCES textes(id) ON DELETE CASCADE,
    chapitre_id INTEGER REFERENCES chapitres(id) ON DELETE CASCADE, -- Peut être NULL si hors chapitre
    titre_id INTEGER REFERENCES titres(id) ON DELETE CASCADE, -- Rare, mais possible
    numero VARCHAR(50),
    titre TEXT,
    contenu_libre TEXT,
    ordre INTEGER
);

-- 6. Table des articles
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    texte_id VARCHAR(100) REFERENCES textes(id) ON DELETE CASCADE,
    
    -- Liens hiérarchiques (un seul devrait être non-NULL idéalement, ou en cascade)
    titre_id INTEGER REFERENCES titres(id) ON DELETE CASCADE,
    chapitre_id INTEGER REFERENCES chapitres(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES sections(id) ON DELETE CASCADE,
    
    numero VARCHAR(50), -- ex: "1", "1er", "2"
    intitule TEXT, -- Optionnel (ex: "Définitions")
    contenu TEXT NOT NULL,
    ordre INTEGER
);

-- Index pour la recherche d'articles
CREATE INDEX idx_articles_texte ON articles(texte_id);
CREATE INDEX idx_articles_numero ON articles(numero);

-- 7. Table des signataires
CREATE TABLE signataires (
    id SERIAL PRIMARY KEY,
    texte_id VARCHAR(100) REFERENCES textes(id) ON DELETE CASCADE,
    nom VARCHAR(255),
    fonction VARCHAR(255),
    pour VARCHAR(255) -- ex: "Pour le ministre..."
);

-- 8. Table des références (Textes visés : "Vu la loi...")
CREATE TABLE references (
    id SERIAL PRIMARY KEY,
    texte_id VARCHAR(100) REFERENCES textes(id) ON DELETE CASCADE,
    type_reference VARCHAR(50), -- "Vu", "Conformément à"
    contenu_reference TEXT
);

-- Vue pour faciliter la recherche globale (Full Text Search)
-- Nécessite la configuration de la recherche textuelle PostgreSQL (tsvector)
/*
CREATE VIEW vue_recherche_globale AS
SELECT 
    t.id AS texte_id,
    t.titre AS texte_titre,
    a.numero AS article_numero,
    a.contenu AS article_contenu,
    to_tsvector('french', t.titre || ' ' || coalesce(a.contenu, '')) AS document_vector
FROM textes t
JOIN articles a ON a.texte_id = t.id;
*/
