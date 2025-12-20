// ==========================================
// MongoDB Initialization Script for AURA Fact-Checker
// ==========================================
// This script runs when MongoDB container starts for the first time

// Switch to the AURA database
db = db.getSiblingDB('aura_factchecker');

print('🚀 Initializing AURA Fact-Checker database...');

// ==========================================
// Create Collections with Validation
// ==========================================

// Claims collection
db.createCollection('claims', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['claim_text', 'status', 'created_at'],
            properties: {
                claim_text: { bsonType: 'string', minLength: 10 },
                status: { 
                    enum: ['pending', 'queued', 'processing', 'completed', 'failed', 'cancelled'] 
                },
                language: { bsonType: 'string' },
                source_context: { bsonType: 'string' },
                priority: { enum: ['normal', 'high', 'urgent'] },
                user_id: { bsonType: 'string' },
                created_at: { bsonType: 'date' }
            }
        }
    }
});

// Verifications collection
db.createCollection('verifications', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['verification_id', 'status', 'created_at'],
            properties: {
                verification_id: { bsonType: 'string' },
                claim: { bsonType: 'string' },
                status: { bsonType: 'string' },
                verdict: { bsonType: 'object' },
                debate_session_id: { bsonType: 'string' },
                created_at: { bsonType: 'date' },
                completed_at: { bsonType: 'date' }
            }
        }
    }
});

// Debate sessions collection
db.createCollection('debate_sessions', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['session_id', 'verification_id', 'status'],
            properties: {
                session_id: { bsonType: 'string' },
                verification_id: { bsonType: 'string' },
                status: { bsonType: 'string' },
                rounds: { bsonType: 'array' },
                final_verdict: { bsonType: 'object' }
            }
        }
    }
});

// Evidence collection
db.createCollection('evidence');

// Users collection
db.createCollection('users', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['created_at'],
            properties: {
                email: { bsonType: 'string' },
                phone: { bsonType: 'string' },
                name: { bsonType: 'string' },
                password_hash: { bsonType: 'string' },
                created_at: { bsonType: 'date' }
            }
        }
    }
});

// Facts collection (for knowledge base)
db.createCollection('facts');

// Trends collection
db.createCollection('trends');

// Audit logs collection
db.createCollection('audit_logs');

// ==========================================
// Create Indexes
// ==========================================

print('📊 Creating indexes...');

// Claims indexes
db.claims.createIndex({ 'created_at': -1 });
db.claims.createIndex({ 'status': 1 });
db.claims.createIndex({ 'user_id': 1 });
db.claims.createIndex({ 'language': 1 });

// Verifications indexes
db.verifications.createIndex({ 'verification_id': 1 }, { unique: true });
db.verifications.createIndex({ 'status': 1 });
db.verifications.createIndex({ 'created_at': -1 });
db.verifications.createIndex({ 'user_id': 1 });
db.verifications.createIndex({ 'verdict.result': 1 });

// Debate sessions indexes
db.debate_sessions.createIndex({ 'session_id': 1 }, { unique: true });
db.debate_sessions.createIndex({ 'verification_id': 1 });
db.debate_sessions.createIndex({ 'status': 1 });

// Evidence indexes
db.evidence.createIndex({ 'evidence_id': 1 }, { unique: true });
db.evidence.createIndex({ 'source': 1 });
db.evidence.createIndex({ 'created_at': -1 });

// Users indexes
db.users.createIndex({ 'email': 1 }, { unique: true, sparse: true });
db.users.createIndex({ 'phone': 1 }, { sparse: true });
db.users.createIndex({ 'user_id': 1 }, { unique: true });

// Facts indexes
db.facts.createIndex({ 'fact_id': 1 }, { unique: true });
db.facts.createIndex({ 'category': 1 });
db.facts.createIndex({ 'verdict': 1 });

// Trends indexes
db.trends.createIndex({ 'date': -1 });
db.trends.createIndex({ 'category': 1 });

// Audit logs - TTL index (auto-delete after 90 days)
db.audit_logs.createIndex({ 'created_at': 1 }, { expireAfterSeconds: 7776000 });

// ==========================================
// Insert Sample/Seed Data (Optional)
// ==========================================

print('🌱 Inserting initial data...');

// Insert a sample fact for testing
db.facts.insertOne({
    fact_id: 'fact_sample_001',
    claim: '5G networks spread coronavirus',
    verdict: 'FALSE',
    evidence: 'Radio waves cannot transmit biological viruses. COVID-19 is caused by SARS-CoV-2, which spreads through respiratory droplets.',
    source: 'WHO',
    source_url: 'https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/myth-busters',
    category: 'health',
    language: 'en',
    created_at: new Date(),
    verified_at: new Date()
});

// Insert a sample trend category
db.trends.insertOne({
    category: 'health',
    name: 'Health & Medical',
    description: 'Health-related misinformation including medical advice, treatments, and disease information',
    claim_count: 0,
    created_at: new Date()
});

print('✅ AURA Database initialized successfully!');
print('📋 Collections created: claims, verifications, debate_sessions, evidence, users, facts, trends, audit_logs');
